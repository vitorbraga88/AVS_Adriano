"""Handlers dos comandos do bot Telegram da AVS.

Cada comando confere `autorizado(chat_id)` antes de responder. Consultas
usam a sessão SQLAlchemy passada pelo runner. Fuso America/Recife.
"""
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models import Ordem

TZ_RECIFE = ZoneInfo("America/Recife")

STATUS_AGENDA = ("aprovado", "em_execucao")


def public_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def chat_ids() -> set[str]:
    raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def autorizado(chat_id) -> bool:
    ids = chat_ids()
    if not ids:
        return False
    return str(chat_id) in ids


def _brl(centavos: int | None) -> str:
    c = centavos or 0
    return f"R$ {c / 100:.2f}".replace(".", ",")


def _hoje_recife():
    return datetime.now(TZ_RECIFE).date()


def _janela_dia(dia):
    """Retorna (inicio, fim) naive para comparar com data_servico do dia."""
    inicio = datetime.combine(dia, time.min)
    fim = datetime.combine(dia, time.max)
    return inicio, fim


def _num_link(numero: str, ordem_id: int, kind: str, base: str) -> str:
    return f"[{numero}]({base}/{kind}/{ordem_id})" if base else numero


async def cmd_menu(client, chat_id):
    if not autorizado(chat_id):
        return
    base = public_url()
    linhas = ["*AVS Soluções Elétricas*", "Painel administrativo."]
    if base:
        linhas += ["", f"🌐 Aplicação: {base}/"]
    linhas += [
        "",
        "Comandos:",
        "/hoje — serviços de hoje",
        "/semana — agenda da semana",
        "/orcamentos — últimos orçamentos",
    ]
    reply_markup = None
    if base:
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🌐 Abrir aplicação", "url": base + "/"}],
                [{"text": "📄 Orçamentos (PDFs)", "url": base + "/arquivos/orcamentos"}],
                [{"text": "🧾 Relatórios de Serviço (PDFs)", "url": base + "/arquivos/os"}],
            ]
        }
    await client.send_message(chat_id, "\n".join(linhas), reply_markup=reply_markup, parse_mode="Markdown")


async def cmd_hoje(client, chat_id, db):
    if not autorizado(chat_id):
        return
    dia = _hoje_recife()
    inicio, fim = _janela_dia(dia)
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
        await client.send_message(chat_id, "Nenhum serviço agendado para hoje.")
        return
    linhas = [f"*Serviços de hoje ({dia.strftime('%d/%m')})*"]
    base = public_url()
    for o in ordens:
        cli_nome = o.cliente.nome if o.cliente else "—"
        hora = o.data_servico.strftime("%H:%M") if o.data_servico else ""
        num = _num_link(o.numero, o.id, "os", base)
        linhas.append(f"• {hora} — {num} — {cli_nome} — {_brl(o.total_centavos)}")
    await client.send_message(chat_id, "\n".join(linhas), parse_mode="Markdown")


async def cmd_semana(client, chat_id, db):
    if not autorizado(chat_id):
        return
    dia = _hoje_recife()
    inicio, _ = _janela_dia(dia)
    _, fim = _janela_dia(dia + timedelta(days=7))
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
        await client.send_message(chat_id, "Nenhum serviço agendado nos próximos 7 dias.")
        return
    linhas = ["*Agenda da semana*"]
    base = public_url()
    for o in ordens:
        cli_nome = o.cliente.nome if o.cliente else "—"
        quando = o.data_servico.strftime("%d/%m %H:%M") if o.data_servico else ""
        num = _num_link(o.numero, o.id, "os", base)
        linhas.append(f"• {quando} — {num} — {cli_nome} — {_brl(o.total_centavos)}")
    await client.send_message(chat_id, "\n".join(linhas), parse_mode="Markdown")


async def cmd_orcamentos(client, chat_id, db):
    if not autorizado(chat_id):
        return
    ordens = (
        db.query(Ordem)
        .order_by(Ordem.created_at.desc())
        .limit(5)
        .all()
    )
    if not ordens:
        await client.send_message(chat_id, "Nenhum orçamento cadastrado.")
        return
    linhas = ["*Últimos orçamentos*"]
    base = public_url()
    for o in ordens:
        cli_nome = o.cliente.nome if o.cliente else "—"
        num = _num_link(o.numero, o.id, "orcamentos", base)
        linhas.append(f"• {num} — {cli_nome} — {_brl(o.total_centavos)} — {o.status}")
    await client.send_message(chat_id, "\n".join(linhas), parse_mode="Markdown")
