from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import verify_admin
from app.deps import get_db, templates
from app.routes.orcamentos import ROTA_STATUS, STATUS_LABEL
from app.services import kpis

router = APIRouter(tags=["dashboard"], dependencies=[Depends(verify_admin)])

ORDEM_STATUS = ("orcamento", "aprovado", "em_execucao", "concluido", "recebido")


@router.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    resumo = kpis.kpis_mes_db(db)
    tk = kpis.ticket_medio_db(db)
    serie = kpis.ordens_por_semana_db(db, n=8)
    contagem = kpis.contagem_por_status_db(db)
    contas = kpis.contas_a_receber_db(db)
    proximos = kpis.proximos_servicos_db(db)

    contagens = [{"status": s, "qtd": contagem.get(s, 0)} for s in ORDEM_STATUS]
    return templates.TemplateResponse(request, "dashboard.html", {
        "resumo": resumo, "ticket": tk, "serie": serie,
        "contagens": contagens, "contas": contas, "proximos": proximos,
        "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
    })
