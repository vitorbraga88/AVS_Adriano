import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import FinanceiroDespesa

router = APIRouter(tags=["despesas"], dependencies=[Depends(verify_admin)])

# Categorias fixas de despesa operacional (sem vínculo com ordem de serviço —
# FinanceiroDespesa não tem ordem_id; é custo geral da empresa, não da OS).
CATEGORIAS = [
    "Combustível", "Fardamento", "Ferramentas", "Manutenção carro", "Outros",
]


def _mes_ini(mes: str | None) -> datetime.date:
    if mes:
        try:
            return datetime.date.fromisoformat(mes + "-01")
        except ValueError:
            pass
    return datetime.date.today().replace(day=1)


def _valor_para_centavos(valor: str) -> int | None:
    try:
        return int((Decimal(str(valor).replace(",", ".")) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return None


@router.get("/despesas")
def lista_despesas(request: Request, mes: str | None = None,
                   db: Session = Depends(get_db)):
    inicio = _mes_ini(mes)
    prox = (inicio + datetime.timedelta(days=32)).replace(day=1)
    despesas = (db.query(FinanceiroDespesa)
                .filter(FinanceiroDespesa.data_despesa >= inicio,
                        FinanceiroDespesa.data_despesa < prox)
                .order_by(FinanceiroDespesa.data_despesa.desc()).all())
    total = sum(d.valor_centavos for d in despesas)
    return templates.TemplateResponse(request, "despesas.html", {
        "despesas": despesas, "total": total, "categorias": CATEGORIAS,
        "mes": inicio.strftime("%Y-%m"), "mes_label": inicio.strftime("%m/%Y"),
        "hoje": datetime.date.today().isoformat(),
    })


@router.post("/despesas")
def criar_despesa(
    request: Request,
    categoria: str = Form(...),
    descricao: str = Form(...),
    valor: str = Form(...),
    data_despesa: str = Form(...),
    fornecedor: str = Form(""),
    nf: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    centavos = _valor_para_centavos(valor)
    if centavos is None or centavos < 0:
        return RedirectResponse("/despesas?erro=Valor+inválido", status_code=303)
    try:
        data = datetime.date.fromisoformat(data_despesa)
    except ValueError:
        return RedirectResponse("/despesas?erro=Data+inválida", status_code=303)
    db.add(FinanceiroDespesa(
        categoria=categoria, descricao=descricao.strip(),
        valor_centavos=centavos, data_despesa=data,
        fornecedor=fornecedor.strip() or None, nf=nf.strip() or None,
        observacoes=observacoes.strip() or None, fonte="web",
    ))
    db.commit()
    return RedirectResponse("/despesas?ok=Despesa+adicionada", status_code=303)


@router.get("/despesas/{despesa_id}/editar")
def editar_despesa(despesa_id: int, request: Request, db: Session = Depends(get_db)):
    desp = db.query(FinanceiroDespesa).filter(FinanceiroDespesa.id == despesa_id).first()
    if not desp:
        return RedirectResponse("/despesas?erro=Não+encontrado", status_code=303)
    return templates.TemplateResponse(request, "despesa_editar.html", {
        "d": desp, "categorias": CATEGORIAS,
    })


@router.post("/despesas/{despesa_id}")
def atualizar_despesa(
    despesa_id: int,
    categoria: str = Form(...),
    descricao: str = Form(...),
    valor: str = Form(...),
    data_despesa: str = Form(...),
    fornecedor: str = Form(""),
    nf: str = Form(""),
    observacoes: str = Form(""),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_same_origin),
):
    desp = db.query(FinanceiroDespesa).filter(FinanceiroDespesa.id == despesa_id).first()
    if not desp:
        return RedirectResponse("/despesas?erro=Não+encontrado", status_code=303)
    centavos = _valor_para_centavos(valor)
    if centavos is None or centavos < 0:
        return RedirectResponse(f"/despesas/{despesa_id}/editar?erro=Valor+inválido",
                                status_code=303)
    try:
        data = datetime.date.fromisoformat(data_despesa)
    except ValueError:
        return RedirectResponse(f"/despesas/{despesa_id}/editar?erro=Data+inválida",
                                status_code=303)
    desp.categoria = categoria
    desp.descricao = descricao.strip()
    desp.valor_centavos = centavos
    desp.data_despesa = data
    desp.fornecedor = fornecedor.strip() or None
    desp.nf = nf.strip() or None
    desp.observacoes = observacoes.strip() or None
    db.commit()
    return RedirectResponse("/despesas?ok=Despesa+atualizada", status_code=303)


@router.post("/despesas/{despesa_id}/excluir")
def excluir_despesa(despesa_id: int, db: Session = Depends(get_db),
                    _csrf: None = Depends(verify_same_origin)):
    desp = db.query(FinanceiroDespesa).filter(FinanceiroDespesa.id == despesa_id).first()
    if not desp:
        return RedirectResponse("/despesas?erro=Não+encontrado", status_code=303)
    db.delete(desp)
    db.commit()
    return RedirectResponse("/despesas?ok=Despesa+excluída", status_code=303)
