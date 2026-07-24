"""Agendador (APScheduler) do bot AVS (America/Recife).

Jobs diários/semanais que avisam o dono:
- 07:00 todo dia: serviços agendados para hoje (dia do serviço).
- 08:00 todo dia: cobranças pendentes (serviços concluídos ainda não recebidos).
- 07:00 na segunda: programação da semana.
No-op quando não há chat_ids configurados.
"""
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.handlers import _num_link, chat_ids, public_url
from app.models import Ordem

logger = logging.getLogger("avs.bot")

TZ_RECIFE = ZoneInfo("America/Recife")
STATUS_AGENDA = ("aprovado", "em_execucao")


def _brl(centavos: int | None) -> str:
    c = centavos or 0
    return f"R$ {c / 100:.2f}".replace(".", ",")


def _destino():
    ids = chat_ids()
    return next(iter(sorted(ids))) if ids else None


async def _lembrete_hoje(client, session_factory):
    try:
        destino = _destino()
        if not destino:
            return
        base = public_url()
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
                    num = _num_link(o.numero, o.id, "os", base)
                    linhas.append(f"• {hora} — {num} — {cli_nome} — {_brl(o.total_centavos)}")
                texto = "\n".join(linhas)
        await client.send_message(destino, texto, parse_mode="Markdown")
    except Exception as e:
        logger.warning("bot telegram: lembrete diário falhou: %s", e)


async def _lembrete_cobranca(client, session_factory):
    """Serviços concluídos e ainda não recebidos — cobrança pendente."""
    try:
        destino = _destino()
        if not destino:
            return
        base = public_url()
        with session_factory() as db:
            ordens = (
                db.query(Ordem)
                .filter(
                    Ordem.status == "concluido",
                    Ordem.data_recebimento.is_(None),
                )
                .order_by(Ordem.data_conclusao.asc())
                .all()
            )
            if not ordens:
                return  # nada a cobrar: silêncio
            total = sum(o.total_centavos or 0 for o in ordens)
            linhas = [f"*Cobranças pendentes ({len(ordens)})*"]
            for o in ordens:
                cli_nome = o.cliente.nome if o.cliente else "—"
                num = _num_link(o.numero, o.id, "os", base)
                linhas.append(f"• {num} — {cli_nome} — {_brl(o.total_centavos)}")
            linhas.append(f"\nTotal a receber: {_brl(total)}")
            texto = "\n".join(linhas)
        await client.send_message(destino, texto, parse_mode="Markdown")
    except Exception as e:
        logger.warning("bot telegram: lembrete de cobrança falhou: %s", e)


async def _resumo_semana(client, session_factory):
    """Programação dos próximos 7 dias — enviada na segunda-feira."""
    try:
        destino = _destino()
        if not destino:
            return
        base = public_url()
        hoje = datetime.now(TZ_RECIFE).date()
        inicio = datetime.combine(hoje, time.min)
        fim = datetime.combine(hoje + timedelta(days=7), time.max)
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
                texto = "Programação da semana: nenhum serviço agendado nos próximos 7 dias."
            else:
                linhas = ["*Programação da semana*"]
                for o in ordens:
                    cli_nome = o.cliente.nome if o.cliente else "—"
                    quando = o.data_servico.strftime("%d/%m %H:%M") if o.data_servico else ""
                    num = _num_link(o.numero, o.id, "os", base)
                    linhas.append(f"• {quando} — {num} — {cli_nome} — {_brl(o.total_centavos)}")
                texto = "\n".join(linhas)
        await client.send_message(destino, texto, parse_mode="Markdown")
    except Exception as e:
        logger.warning("bot telegram: resumo da semana falhou: %s", e)


def criar_scheduler(client, session_factory) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="America/Recife")
    scheduler.add_job(
        _lembrete_hoje, trigger="cron", hour=7, minute=0,
        args=[client, session_factory], id="lembrete_hoje", replace_existing=True,
    )
    scheduler.add_job(
        _lembrete_cobranca, trigger="cron", hour=8, minute=0,
        args=[client, session_factory], id="lembrete_cobranca", replace_existing=True,
    )
    scheduler.add_job(
        _resumo_semana, trigger="cron", day_of_week="mon", hour=7, minute=0,
        args=[client, session_factory], id="resumo_semana", replace_existing=True,
    )
    return scheduler
