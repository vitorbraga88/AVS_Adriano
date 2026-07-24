"""Endpoints JSON (sem same-origin): consumidos pelo JS dos formulários de
campo e, potencialmente, pelo n8n. Auth Basic ainda se aplica.
"""
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin
from app.deps import get_db
from app.models import Assinatura, Cliente, Equipamento, Notificacao, Ordem, Sugestao
from app.services.telegram_notify import notificar_telegram
from app.services.ordens import atualizar_orcamento, atualizar_relatorio, criar_orcamento
from app.services.documento_html import build_orcamento, build_os
from app.services.pdf_render import render_pdf

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(verify_admin)])

log = logging.getLogger("avs.api")

REL_DIR = Path(__file__).parent.parent.parent / "relatorios"
REL_DIR.mkdir(parents=True, exist_ok=True)

SAFE_FILENAME = re.compile(r"^[^/\\\x00-\x1f]+\.pdf$")


def _save_pdf_bytes(pdf_bytes: bytes, filename: str, sub: str) -> str:
    """Valida o nome e grava os bytes em relatorios/<sub>/. Retorna a URL pública."""
    if not filename or not SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=422, detail="Nome de arquivo inválido")
    dest = REL_DIR / sub
    dest.mkdir(parents=True, exist_ok=True)
    (dest / filename).write_bytes(pdf_bytes)
    return f"/relatorios/{sub}/{filename}"


def _itens_from_body(body: dict) -> list[dict]:
    itens = []
    for it in body.get("itens", []) or []:
        desc = (it.get("descricao") or "").strip()
        if not desc:
            continue
        itens.append({
            "descricao": desc,
            "quantidade": int(it.get("quantidade") or 1),
            "unidade": (it.get("unidade") or "un"),
            "preco_centavos": int(it.get("preco_centavos") or 0),
            "custo_centavos": int(it.get("custo_centavos") or 0),
        })
    return itens


@router.post("/orcamentos/finalizar")
def finalizar_orcamento(body: dict = Body(...), db: Session = Depends(get_db)):
    cliente = body.get("cliente") or {}
    equipamento = body.get("equipamento") or None
    itens = _itens_from_body(body)
    ordem_id = body.get("ordem_id")

    if ordem_id:
        atualizar_orcamento(
            db, int(ordem_id), itens=itens or None,
            titulo=body.get("titulo"), local_servico=body.get("local_servico"),
            desconto_pct=body.get("desconto_pct"), observacoes=body.get("observacoes"),
            orcamento_json=body,
        )
        res = {"ordem_id": int(ordem_id)}
    else:
        res = criar_orcamento(
            db,
            cliente_nome=cliente.get("nome") or "Cliente",
            cliente_telefone=cliente.get("telefone"),
            cliente_endereco=cliente.get("endereco"),
            itens=itens,
            titulo=body.get("titulo"),
            local_servico=body.get("local_servico"),
            tipo=body.get("tipo"),
            prioridade=body.get("prioridade") or "normal",
            equipamento=equipamento,
            desconto_pct=body.get("desconto_pct") or 0,
            observacoes=body.get("observacoes"),
            orcamento_json=body,
        )

    ordem = (db.query(Ordem).options(joinedload(Ordem.cliente))
             .filter(Ordem.id == res["ordem_id"]).first())

    pdf_url, pdf_bytes, filename = None, None, None
    try:
        html, filename = build_orcamento(ordem)
        pdf_bytes = render_pdf(html)
        pdf_url = _save_pdf_bytes(pdf_bytes, filename, "orcamentos")
        ordem.orcamento_pdf_url = pdf_url
        db.commit()
    except Exception:
        log.exception("falha ao gerar PDF do orçamento %s", ordem.id)
        pdf_bytes, filename = None, None

    resumo = _resumo_ordem(ordem)
    _entregar_telegram(db, ordem, resumo, "orcamentos", pdf_bytes, filename)

    return {"ok": True, "ordem_id": ordem.id, "numero": ordem.numero, "pdf_url": pdf_url}


@router.post("/os/finalizar")
def finalizar_os(body: dict = Body(...), db: Session = Depends(get_db)):
    ordem_id = body.get("ordem_id")
    if not ordem_id:
        raise HTTPException(status_code=422, detail="ordem_id obrigatório")
    atualizar_relatorio(
        db, int(ordem_id),
        blocos=body.get("blocos") or [],
        fotos=body.get("fotos") or [],
        assinaturas=body.get("assinaturas") or {},
        tecnico=body.get("tecnico"),
    )
    ordem = (db.query(Ordem).options(joinedload(Ordem.cliente))
             .filter(Ordem.id == int(ordem_id)).first())
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem não encontrada")

    pdf_url, pdf_bytes, filename = None, None, None
    try:
        html, filename = build_os(ordem)
        pdf_bytes = render_pdf(html)
        pdf_url = _save_pdf_bytes(pdf_bytes, filename, "os")
        ordem.os_pdf_url = pdf_url
        db.commit()
    except Exception:
        log.exception("falha ao gerar PDF da OS %s", ordem.id)
        pdf_bytes, filename = None, None

    resumo = _resumo_ordem(ordem, "OS")
    _entregar_telegram(db, ordem, resumo, "os", pdf_bytes, filename)
    return {"ok": True, "ordem_id": ordem.id, "pdf_url": pdf_url}


def _entregar_telegram(db: Session, ordem: Ordem, resumo: str, kind: str,
                       pdf_bytes: bytes | None, filename: str | None) -> None:
    """Envia resumo + PDF (bytes) direto ao Telegram (dono repassa ao cliente).

    Registra em `notificacoes` quando entregue. Nunca derruba a finalização.
    """
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    texto = f"{resumo}\n\n{base}/{kind}/{ordem.id}" if base else resumo
    if notificar_telegram(texto, pdf_bytes, filename):
        try:
            db.add(Notificacao(ordem_id=ordem.id, tipo=kind,
                               chat_id=os.getenv("TELEGRAM_CHAT_IDS", "") or None))
            db.commit()
        except Exception:
            db.rollback()


def _resumo_ordem(ordem: Ordem, prefixo: str = "Orçamento") -> str:
    cli = ordem.cliente.nome if ordem.cliente else "-"
    total = f"{(ordem.total_centavos or 0) / 100:.2f}".replace(".", ",")
    return (f"{prefixo} {ordem.numero}\nCliente: {cli}\n"
            f"Título: {ordem.titulo or '-'}\nTotal: R$ {total}")


# ---------- Equipamentos (seletor do form) ----------

@router.get("/equipamentos")
def api_equipamentos(cliente_id: int, db: Session = Depends(get_db)):
    eqs = (db.query(Equipamento)
           .filter(Equipamento.cliente_id == cliente_id)
           .order_by(Equipamento.created_at.desc()).all())
    return [{
        "id": e.id, "descricao": e.descricao, "marca": e.marca, "modelo": e.modelo,
        "numero_serie": e.numero_serie, "patrimonio": e.patrimonio,
    } for e in eqs]


# ---------- Clientes (autocomplete do form) ----------

@router.get("/clientes")
def api_clientes(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Cliente).order_by(Cliente.nome.asc())
    if q:
        like = f"%{q}%"
        query = query.filter(Cliente.nome.like(like) | Cliente.telefone.like(like))
    return [{
        "id": c.id, "nome": c.nome, "telefone": c.telefone,
        "endereco": c.endereco, "email": c.email,
    } for c in query.limit(20).all()]


# ---------- Sugestões (autocomplete sincronizado) ----------

@router.get("/suggestions")
def get_suggestions(field: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Sugestao)
    if field:
        q = q.filter(Sugestao.field == field)
    out: dict[str, list[str]] = {}
    for s in q.order_by(Sugestao.value.asc()).all():
        out.setdefault(s.field, []).append(s.value)
    return out


@router.post("/suggestion")
def add_suggestion(body: dict = Body(...), db: Session = Depends(get_db)):
    field = (body.get("field") or "").strip()
    value = (body.get("value") or "").strip()
    if not field or not value:
        raise HTTPException(status_code=422, detail="field e value obrigatórios")
    if not db.get(Sugestao, (field, value)):
        db.add(Sugestao(field=field, value=value))
        db.commit()
    return {"ok": True}


@router.delete("/suggestion")
def del_suggestion(field: str, value: str, db: Session = Depends(get_db)):
    s = db.get(Sugestao, (field, value))
    if s:
        db.delete(s)
        db.commit()
    return {"ok": True}


# ---------- Assinaturas (memória por nome, sync cross-device) ----------

@router.get("/assinaturas")
def get_assinaturas(db: Session = Depends(get_db)):
    return {a.nome: a.data_url for a in db.query(Assinatura).all()}


@router.get("/assinatura")
def get_assinatura(nome: str, db: Session = Depends(get_db)):
    a = db.get(Assinatura, nome)
    if not a:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    return {"nome": a.nome, "data_url": a.data_url}


@router.post("/assinatura")
def post_assinatura(body: dict = Body(...), db: Session = Depends(get_db)):
    nome = (body.get("nome") or "").strip()
    data_url = body.get("data_url") or ""
    if not nome or not data_url:
        raise HTTPException(status_code=422, detail="nome e data_url obrigatórios")
    a = db.get(Assinatura, nome)
    if a:
        a.data_url = data_url
        a.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        db.add(Assinatura(nome=nome, data_url=data_url))
    db.commit()
    return {"ok": True}


@router.delete("/assinatura")
def del_assinatura(nome: str, db: Session = Depends(get_db)):
    a = db.get(Assinatura, nome)
    if a:
        db.delete(a)
        db.commit()
    return {"ok": True}
