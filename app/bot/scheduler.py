"""Agendador (APScheduler) do bot AVS.

Um único job diário às 07:00 (America/Recife) envia ao dono o resumo
dos serviços do dia. No-op quando não há chat_ids configurados.
"""
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.handlers import chat_ids
from app.models import Ordem

logger = logging.getLogger("avs.bot")

TZ_RECIFE = ZoneInfo("America/Recife")
STATUS_AGENDA = ("aprovado", "em_execucao")


def _brl(centavos: int | None) -> str:
    c = centavos or 0
    return f"R$ {c / 100:.2f}".replace(".", ",")


async def _lembrete_hoje(client, session_factory):
    try:
        ids = chat_ids()
        if not ids:
            return
        destino = next(iter(sorted(ids)))
        dia = datetime.now(TZ_RECIFE).date()
        inicio = datetime.combine(dia, time.min)
        fim = datetime.combine(dia, time.max)
        with session_factory() as db:
            ordens = (
                db.query(Ordem)
                .filter(
                    Ordem.data_servico.isnot(None),
                    Ordem.data_servico >= inicio,
                    Ordem.data_servico <= fim,
                    Ordem.status.in_(STATUS_AGENDA),
                )
                .order_by(Ordem.data_servico.asc())
                .all()
            )
        if not ordens:
            texto = f"Bom dia! Nenhum serviço agendado para hoje ({dia.strftime('%d/%m')})."
        else:
            linhas = [f"*Serviços de hoje ({dia.strftime('%d/%m')})*"]
            for o in ordens:
                cli_nome = o.cliente.nome if o.cliente else "—"
                hora = o.data_servico.strftime("%H:%M") if o.data_servico else ""
                linhas.append(f"• {hora} — {o.numero} — {cli_nome} — {_brl(o.total_centavos)}")
            texto = "\n".join(linhas)
        await client.send_message(destino, texto, parse_mode="Markdown")
    except Exception as e:
        logger.warning("bot telegram: lembrete diário falhou: %s", e)


def criar_scheduler(client, session_factory) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Recife")
    scheduler.add_job(
        _lembrete_hoje,
        trigger="cron",
        hour=7,
        minute=0,
        args=[client, session_factory],
        id="lembrete_hoje",
        replace_existing=True,
    )
    return scheduler
