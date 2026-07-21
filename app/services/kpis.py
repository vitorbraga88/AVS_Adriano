"""KPIs do dashboard — funções puras + wrappers de DB. Adaptado do Doceear
para a entidade `Ordem` e os 8 estados da AVS.
"""
from collections import deque  # noqa: F401  (compat com padrão do Doceear)
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FinanceiroDespesa, FinanceiroVenda, Ordem

STATUS_ATIVOS = ("orcamento", "aprovado", "em_execucao", "concluido", "recebido")


def kpis_mes(receita: int, custo_vendas: int, despesas: int) -> dict:
    lucro = receita - custo_vendas - despesas
    margem = round(lucro / receita * 100, 1) if receita > 0 else 0
    return {
        "receita": receita, "custo_vendas": custo_vendas, "despesas": despesas,
        "lucro": lucro, "margem": margem,
    }


def ticket_medio(total_centavos: int, n_ordens: int) -> int | None:
    if not n_ordens or n_ordens <= 0:
        return None
    return int(total_centavos / n_ordens)


def _label_semana(ini: date) -> str:
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return f"{ini.day}/{meses[ini.month - 1]}"


def agregar_semanas(ordens, hoje: date, n: int = 8) -> list[dict]:
    """Agrupa ordens por semana (n semanas até hoje). Puro/testável.

    ordens: iterável de objetos com .data (date) e .total_centavos (int).
    """
    n = max(1, min(n, 26))
    dias_ate_domingo = (6 - hoje.weekday()) % 7
    fim_atual = hoje + timedelta(days=dias_ate_domingo)
    limites = []
    for i in range(n):
        fim = fim_atual - timedelta(weeks=i)
        ini = fim - timedelta(days=6)
        limites.append((ini, fim))
    limites.reverse()

    buckets = [{"ini": ini, "fim": fim, "valor": 0, "qtd": 0} for ini, fim in limites]
    for o in ordens:
        d = o.data
        for b in buckets:
            if b["ini"] <= d <= b["fim"]:
                b["valor"] += o.total_centavos or 0
                b["qtd"] += 1
                break
    return [{
        "label": _label_semana(b["ini"]),
        "valor": b["valor"], "qtd": b["qtd"], "inicio": b["ini"].isoformat(),
    } for b in buckets]


# ---------- Wrappers de DB ----------

def _inicio_mes(hoje: date) -> date:
    return hoje.replace(day=1)


def kpis_mes_db(db: Session, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    ini = _inicio_mes(hoje)
    receita = db.query(func.sum(FinanceiroVenda.valor_centavos)).filter(
        FinanceiroVenda.data_venda >= ini).scalar() or 0
    custo_v = db.query(func.sum(FinanceiroVenda.custo_centavos)).filter(
        FinanceiroVenda.data_venda >= ini).scalar() or 0
    desp = db.query(func.sum(FinanceiroDespesa.valor_centavos)).filter(
        FinanceiroDespesa.data_despesa >= ini).scalar() or 0
    return kpis_mes(receita, custo_v, desp)


def ticket_medio_db(db: Session, hoje: date | None = None) -> int | None:
    hoje = hoje or date.today()
    ini = _inicio_mes(hoje)
    ordens = (db.query(Ordem.total_centavos)
              .filter(Ordem.status == "recebido",
                      Ordem.data_recebimento >= ini).all())
    total = sum(o.total_centavos or 0 for o in ordens)
    return ticket_medio(total, len(ordens))


def ordens_por_semana_db(db: Session, n: int = 8, hoje: date | None = None) -> list[dict]:
    hoje = hoje or date.today()
    linhas = (db.query(Ordem.created_at, Ordem.total_centavos)
              .filter(Ordem.status.in_(STATUS_ATIVOS),
                      Ordem.created_at.isnot(None)).all())

    class _O:
        def __init__(self, created_at, total):
            self.data = created_at.date() if hasattr(created_at, "date") else created_at
            self.total_centavos = total or 0

    ordens = [_O(c, t) for c, t in linhas]
    return agregar_semanas(ordens, hoje, n)


def contas_a_receber_db(db: Session) -> int:
    """Ordens aprovadas/em execução/concluídas ainda sem data_recebimento."""
    soma = db.query(func.sum(Ordem.total_centavos)).filter(
        Ordem.status.in_(("aprovado", "em_execucao", "concluido")),
        Ordem.data_recebimento.is_(None)).scalar()
    return soma or 0


def contagem_por_status_db(db: Session) -> dict:
    rows = (db.query(Ordem.status, func.count(Ordem.id))
            .filter(Ordem.status.in_(STATUS_ATIVOS))
            .group_by(Ordem.status).all())
    return {status: cnt for status, cnt in rows}


def proximos_servicos_db(db: Session, hoje: date | None = None, limite: int = 10):
    from sqlalchemy.orm import joinedload
    hoje = hoje or date.today()
    return (db.query(Ordem)
            .options(joinedload(Ordem.cliente))
            .filter(Ordem.data_servico.isnot(None),
                    Ordem.status.in_(("aprovado", "em_execucao")))
            .order_by(Ordem.data_servico.asc()).limit(limite).all())
