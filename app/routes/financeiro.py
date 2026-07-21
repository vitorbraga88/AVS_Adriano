import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import verify_admin
from app.deps import get_db, templates
from app.models import FinanceiroDespesa, FinanceiroVenda

router = APIRouter(tags=["financeiro"], dependencies=[Depends(verify_admin)])


@router.get("/financeiro")
def get_financeiro(request: Request, db: Session = Depends(get_db)):
    hoje = datetime.date.today()
    mes_ini = hoje.replace(day=1)
    receita = db.query(func.sum(FinanceiroVenda.valor_centavos)).filter(
        FinanceiroVenda.data_venda >= mes_ini).scalar() or 0
    custo_v = db.query(func.sum(FinanceiroVenda.custo_centavos)).filter(
        FinanceiroVenda.data_venda >= mes_ini).scalar() or 0
    despesas = db.query(func.sum(FinanceiroDespesa.valor_centavos)).filter(
        FinanceiroDespesa.data_despesa >= mes_ini).scalar() or 0
    lucro = receita - custo_v - despesas
    margem = round(lucro / receita * 100, 1) if receita > 0 else 0
    ultimas_despesas = (db.query(FinanceiroDespesa)
                        .order_by(FinanceiroDespesa.data_despesa.desc()).limit(20).all())
    return templates.TemplateResponse(request, "financeiro.html", {
        "receita": receita, "custo_v": custo_v, "despesas": despesas,
        "lucro": lucro, "margem": margem,
        "mes": mes_ini.strftime("%m/%Y"),
        "ultimas_despesas": ultimas_despesas,
    })
