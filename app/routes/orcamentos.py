from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import Ordem, OrdemItem
from app.services.ordens import (
    LABEL_TRANSICAO, TRANSICOES_VALIDAS, mudar_status, set_data_servico,
)

TZ_RECIFE = ZoneInfo("America/Recife")

router = APIRouter(tags=["orcamentos"], dependencies=[Depends(verify_admin)])

STATUS_LABEL = {
    "rascunho": "Rascunho", "orcamento": "Orçamento", "aprovado": "Aprovado",
    "em_execucao": "Em execução", "concluido": "Concluído", "recebido": "Recebido",
    "recusado": "Recusado", "cancelado": "Cancelado",
}

ROTA_STATUS = {
    "rascunho": "badge-muted", "orcamento": "badge-info", "aprovado": "badge-warn",
    "em_execucao": "badge-warn", "concluido": "badge-ok", "recebido": "badge-ok",
    "recusado": "badge-red", "cancelado": "badge-red",
}

# Filtro da lista de orçamentos: foca no fluxo de orçamento (antes de virar OS)
STATUS_FILTROS = ["orcamento", "aprovado", "recusado", "cancelado"]


def _parse_dt(valor: str | None):
    """datetime-local 'YYYY-MM-DDTHH:MM' -> datetime naive (hora local Recife)."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


@router.get("/orcamentos")
def lista_orcamentos(request: Request, status: str | None = None,
                     db: Session = Depends(get_db)):
    q = (db.query(Ordem).options(joinedload(Ordem.cliente))
         .order_by(Ordem.created_at.desc()))
    if status:
        q = q.filter(Ordem.status == status)
    ordens = q.all()
    return templates.TemplateResponse(request, "orcamentos.html", {
        "ordens": ordens, "status_atual": status,
        "status_filtros": STATUS_FILTROS, "status_label": STATUS_LABEL,
        "rota_status": ROTA_STATUS,
    })


@router.get("/orcamentos/novo")
def novo_orcamento(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "orcamento_form.html", {
        "ordem": None,
    })


@router.get("/orcamentos/{ordem_id}")
def detalhe_orcamento(ordem_id: int, request: Request, db: Session = Depends(get_db)):
    ordem = (db.query(Ordem)
             .options(joinedload(Ordem.cliente), joinedload(Ordem.equipamento),
                      joinedload(Ordem.itens))
             .filter(Ordem.id == ordem_id).first())
    if not ordem:
        return RedirectResponse("/orcamentos?erro=Não+encontrado", status_code=303)
    destinos = TRANSICOES_VALIDAS.get(ordem.status, set())
    transicoes = {d: LABEL_TRANSICAO.get(d, d) for d in destinos}
    return templates.TemplateResponse(request, "orcamento_detalhe.html", {
        "o": ordem, "transicoes": transicoes,
        "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
    })


@router.post("/orcamentos/{ordem_id}/status")
def alterar_status(ordem_id: int, status: str = Form(...),
                   db: Session = Depends(get_db),
                   _csrf: None = Depends(verify_same_origin)):
    try:
        mudar_status(db, ordem_id, status)
    except ValueError as e:
        return RedirectResponse(
            f"/orcamentos/{ordem_id}?erro={str(e).replace(' ', '+')}", status_code=303)
    return RedirectResponse(
        f"/orcamentos/{ordem_id}?ok=Status+atualizado", status_code=303)


@router.post("/orcamentos/{ordem_id}/agendar")
def agendar(ordem_id: int, data_servico: str = Form(...),
            db: Session = Depends(get_db),
            _csrf: None = Depends(verify_same_origin)):
    dt = _parse_dt(data_servico)
    if dt is None:
        return RedirectResponse(
            f"/orcamentos/{ordem_id}?erro=Data+inválida", status_code=303)
    try:
        set_data_servico(db, ordem_id, dt)
    except ValueError as e:
        return RedirectResponse(
            f"/orcamentos/{ordem_id}?erro={str(e).replace(' ', '+')}", status_code=303)
    return RedirectResponse(
        f"/orcamentos/{ordem_id}?ok=Serviço+agendado", status_code=303)
