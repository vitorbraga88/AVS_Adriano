import calendar
import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import verify_admin, verify_same_origin
from app.deps import get_db, templates
from app.models import FinanceiroVenda, Ordem
from app.routes.orcamentos import ROTA_STATUS, STATUS_LABEL
from app.services.ordens import LABEL_TRANSICAO, TRANSICOES_VALIDAS

router = APIRouter(tags=["agenda"], dependencies=[Depends(verify_admin)])

COLUNAS_KANBAN = ["orcamento", "aprovado", "em_execucao", "concluido", "recebido"]


def _base_rota(status: str) -> str:
    return "/orcamentos" if status == "orcamento" else "/os"


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
            colunas[o.status].append({"o": o, "transicoes": transicoes,
                                      "base": _base_rota(o.status)})
    return templates.TemplateResponse(request, "agenda.html", {
        "colunas": colunas, "colunas_kanban": COLUNAS_KANBAN,
        "status_label": STATUS_LABEL, "rota_status": ROTA_STATUS,
        "voltar": "/agenda",
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
            destinos = TRANSICOES_VALIDAS.get(o.status, set())
            transicoes = {dst: LABEL_TRANSICAO.get(dst, dst) for dst in destinos}
            eventos[d].append({"o": o, "transicoes": transicoes,
                               "base": _base_rota(o.status)})

    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(ano, num_mes)
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    mes_ant = (inicio - datetime.timedelta(days=1)).replace(day=1).strftime("%Y-%m")
    mes_prox = prox.strftime("%Y-%m")
    voltar = "/agenda/calendario?mes=" + inicio.strftime("%Y-%m")
    return templates.TemplateResponse(request, "agenda_calendario.html", {
        "semanas": semanas, "dias_semana": dias_semana,
        "eventos": eventos, "hoje": hoje,
        "mes_label": inicio.strftime("%m/%Y"), "mes": inicio.strftime("%Y-%m"),
        "mes_ant": mes_ant, "mes_prox": mes_prox,
        "rota_status": ROTA_STATUS, "status_label": STATUS_LABEL,
        "voltar": voltar,
    })


@router.post("/agenda/{ordem_id}/apagar")
def apagar_ordem(ordem_id: int, voltar: str = Form("/agenda"),
                 db: Session = Depends(get_db),
                 _csrf: None = Depends(verify_same_origin)):
    """Apaga definitivamente uma ordem (orçamento ou OS) — ex.: cadastro
    por engano, teste, ou serviço que nunca aconteceu. Itens e custos
    seguem junto (cascade). Bloqueado para ordens 'recebido': já geraram
    receita (financeiro_vendas) e não podem sumir silenciosamente."""
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if not ordem:
        return RedirectResponse(f"{voltar}?erro=Não+encontrado", status_code=303)
    if ordem.status == "recebido" or db.query(FinanceiroVenda).filter(
            FinanceiroVenda.ordem_id == ordem_id).first():
        return RedirectResponse(
            f"{voltar}?erro=Ordem+recebida+não+pode+ser+apagada+(gerou+receita)",
            status_code=303)
    numero = ordem.numero
    db.delete(ordem)
    db.commit()
    return RedirectResponse(f"{voltar}?ok=Ordem+{numero}+apagada", status_code=303)
