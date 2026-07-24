import calendar
import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin
from app.deps import get_db, templates
from app.models import Ordem
from app.routes.orcamentos import ROTA_STATUS, STATUS_LABEL
from app.services.ordens import LABEL_TRANSICAO, TRANSICOES_VALIDAS

router = APIRouter(tags=["agenda"], dependencies=[Depends(verify_admin)])

COLUNAS_KANBAN = ["orcamento", "aprovado", "em_execucao", "concluido", "recebido"]


@router.get("/agenda")
def kanban(request: Request, db: Session = Depends(get_db)):
    ordens = (db.query(Ordem)
              .options(joinedload(Ordem.cliente))
              .filter(Ordem.status.in_(COLUNAS_KANBAN))
              .order_by(Ordem.data_servico.asc().nullslast(),
                        Ordem.created_at.desc()).all())
    colunas = {c: [] for c in COLUNAS_KANBAN}
    for o in ordens:
        if o.status in colunas:
            destinos = TRANSICOES_VALIDAS.get(o.status, set())
            transicoes = {d: LABEL_TRANSICAO.get(d, d) for d in destinos}
            colunas[o.status].append({"o": o, "transicoes": transicoes})
    return templates.TemplateResponse(request, "agenda.html", {
        "colunas": colunas, "colunas_kanban": COLUNAS_KANBAN,
        "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
    })


@router.get("/agenda/calendario")
def calendario(request: Request, mes: str | None = None,
               db: Session = Depends(get_db)):
    hoje = datetime.date.today()
    if mes:
        try:
            inicio = datetime.date.fromisoformat(mes + "-01")
        except ValueError:
            inicio = hoje.replace(day=1)
    else:
        inicio = hoje.replace(day=1)
    ano, num_mes = inicio.year, inicio.month
    prox = (inicio + datetime.timedelta(days=32)).replace(day=1)

    ordens = (db.query(Ordem)
              .options(joinedload(Ordem.cliente))
              .filter(Ordem.data_servico.isnot(None)).all())

    eventos: dict[datetime.date, list] = defaultdict(list)
    for o in ordens:
        d = o.data_servico.date()
        if inicio <= d < prox:
            eventos[d].append(o)

    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(ano, num_mes)
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    mes_ant = (inicio - datetime.timedelta(days=1)).replace(day=1).strftime("%Y-%m")
    mes_prox = prox.strftime("%Y-%m")
    return templates.TemplateResponse(request, "agenda_calendario.html", {
        "semanas": semanas, "dias_semana": dias_semana,
        "eventos": eventos, "hoje": hoje,
        "mes_label": inicio.strftime("%m/%Y"), "mes": inicio.strftime("%Y-%m"),
        "mes_ant": mes_ant, "mes_prox": mes_prox,
        "rota_status": ROTA_STATUS, "status_label": STATUS_LABEL,
    })
