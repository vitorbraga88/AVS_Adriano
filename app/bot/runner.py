"""Loop de long-polling do bot Telegram.

Iniciado via asyncio.create_task no lifespan. Degrada silenciosamente
quando o token está ausente. Nunca levanta no import.
"""
import asyncio
import logging

from app.bot.client import BotClient
from app.bot.handlers import (
    autorizado,
    cmd_hoje,
    cmd_menu,
    cmd_orcamentos,
    cmd_semana,
)
from app.database import SessionLocal

logger = logging.getLogger("avs.bot")


async def run_polling():
    client = BotClient()
    if not client.configurado():
        logger.info("bot telegram: token ausente, polling não iniciado")
        return

    offset = None
    logger.info("bot telegram: iniciando long-polling")
    while True:
        try:
            data = await client.get_updates(offset=offset, timeout=25)
            if not data or not data.get("ok"):
                await asyncio.sleep(1)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message")
                if not msg:
                    continue
                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()
                if not text:
                    continue
                if not autorizado(chat_id):
                    continue
                await _dispatch(client, chat_id, text)
        except asyncio.CancelledError:
            logger.info("bot telegram: polling cancelado")
            raise
        except Exception as e:
            logger.warning("bot telegram: erro no polling: %s", e)
            await asyncio.sleep(5)


async def _dispatch(client, chat_id, text):
    cmd = text.split()[0].lower()
    # remove sufixo @nome_do_bot, se houver
    cmd = cmd.split("@", 1)[0]
    if cmd in ("/start", "/menu"):
        await cmd_menu(client, chat_id)
    elif cmd == "/hoje":
        with SessionLocal() as db:
            await cmd_hoje(client, chat_id, db)
    elif cmd == "/semana":
        with SessionLocal() as db:
            await cmd_semana(client, chat_id, db)
    elif cmd == "/orcamentos":
        with SessionLocal() as db:
            await cmd_orcamentos(client, chat_id, db)
