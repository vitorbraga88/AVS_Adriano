"""Cliente HTTP assíncrono para a Telegram Bot API (httpx).

Wrapper mínimo usado pelo runner/scheduler. Nunca levanta no import —
apenas guarda o token e monta a URL base.
"""
import logging
import os

import httpx

log = logging.getLogger("avs.bot")


class BotClient:
    """Wrapper fino sobre a Bot API do Telegram."""

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.base = f"https://api.telegram.org/bot{self.token}"

    def configurado(self) -> bool:
        return bool(self.token)

    async def _post(self, metodo: str, payload: dict, timeout: float = 30):
        if not self.configurado():
            return None
        url = f"{self.base}/{metodo}"
        async with httpx.AsyncClient(timeout=timeout) as cli:
            resp = await cli.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        return await self._post("sendMessage", payload)

    async def send_document(self, chat_id, document_url, caption=None):
        payload = {"chat_id": chat_id, "document": document_url}
        if caption is not None:
            payload["caption"] = caption
        return await self._post("sendDocument", payload)

    async def set_my_commands(self, commands):
        return await self._post("setMyCommands", {"commands": commands})

    async def get_updates(self, offset=None, timeout: int = 25):
        payload = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        return await self._post("getUpdates", payload, timeout=timeout + 10)
