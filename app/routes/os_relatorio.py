from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import Ordem, OrdemCusto
from app.routes.orcamentos import ROTA_STATUS, STATUS_LABEL
from app.services.ordens import (
    LABEL_TRANSICAO, TRANSICOES_VALIDAS, add_custo, mudar_status,
)

router = APIRouter(tags=["os"], dependencies=[Depends(verify_admin)])

STATUS_OS = ["aprovado", "em_execucao", "concluido", "recebido"]


@router.get("/os")
def lista_os(request: Request, db: Session = Depends(get_db)):
    ordens = (db.query(Ordem).options(joinedload(Ordem.cliente))
              .filter(Ordem.status.in_(STATUS_OS))
              .order_by(Ordem.data_servico.asc().nullslast(),
                        Ordem.created_at.desc()).all())
    return templates.TemplateResponse(request, "os.html", {
        "ordens": ordens, "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
    })


@router.get("/os/novo")
def novo_os(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "os_novo.html", {})


@router.get("/os/{ordem_id}")
def detalhe_os(ordem_id: int, request: Request, db: Session = Depends(get_db)):
    ordem = (db.query(Ordem)
             .options(joinedload(Ordem.cliente), joinedload(Ordem.equipamento),
                      joinedload(Ordem.itens), joinedload(Ordem.custos))
             .filter(Ordem.id == ordem_id).first())
    if not ordem:
        return RedirectResponse("/os?erro=Não+encontrado", status_code=303)
    destinos = TRANSICOES_VALIDAS.get(ordem.status, set())
    transicoes = {d: LABEL_TRANSICAO.get(d, d) for d in destinos}
    custo_total = sum(c.valor_centavos for c in ordem.custos)
    return templates.TemplateResponse(request, "os_detalhe.html", {
        "o": ordem, "transicoes": transicoes, "custo_total": custo_total,
        "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
    })


@router.get("/os/{ordem_id}/relatorio")
def form_relatorio(ordem_id: int, request: Request, db: Session = Depends(get_db)):
    ordem = (db.query(Ordem)
             .options(joinedload(Ordem.cliente), joinedload(Ordem.equipamento),
                      joinedload(Ordem.itens))
             .filter(Ordem.id == ordem_id).first())
    if not ordem:
        return RedirectResponse("/os?erro=Não+encontrado", status_code=303)
    return templates.TemplateResponse(request, "os_form.html", {"ordem": ordem})


@router.post("/os/{ordem_id}/status")
def alterar_status_os(ordem_id: int, status: str = Form(...),
                      db: Session = Depends(get_db),
                      _csrf: None = Depends(verify_same_origin)):
    try:
        mudar_status(db, ordem_id, status)
    except ValueError as e:
        return RedirectResponse(
            f"/os/{ordem_id}?erro={str(e).replace(' ', '+')}", status_code=303)
    return RedirectResponse(f"/os/{ordem_id}?ok=Status+atualizado", status_code=303)


@router.post("/os/{ordem_id}/custos")
def criar_custo(ordem_id: int, descricao: str = Form(...), valor: str = Form(...),
                categoria: str = Form(""), db: Session = Depends(get_db),
                _csrf: None = Depends(verify_same_origin)):
    try:
        centavos = int((Decimal(str(valor).replace(",", ".")) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return RedirectResponse(f"/os/{ordem_id}?erro=Valor+inválido", status_code=303)
    if centavos < 0:
        return RedirectResponse(f"/os/{ordem_id}?erro=Valor+inválido", status_code=303)
    try:
        add_custo(db, ordem_id, descricao, centavos, categoria.strip() or None)
    except ValueError as e:
        return RedirectResponse(
            f"/os/{ordem_id}?erro={str(e).replace(' ', '+')}", status_code=303)
    return RedirectResponse(f"/os/{ordem_id}?ok=Custo+lançado", status_code=303)


@router.post("/os/{ordem_id}/custos/{custo_id}/excluir")
def excluir_custo(ordem_id: int, custo_id: int, db: Session = Depends(get_db),
                  _csrf: None = Depends(verify_same_origin)):
    custo = (db.query(OrdemCusto)
             .filter(OrdemCusto.id == custo_id, OrdemCusto.ordem_id == ordem_id).first())
    if custo:
        db.delete(custo)
        db.commit()
    return RedirectResponse(f"/os/{ordem_id}?ok=Custo+removido", status_code=303)
