"""Entrega direta ao Telegram: resumo (mensagem) + PDF (documento multipart).

Usado ao finalizar orçamento/OS para que o dono receba o resumo e o arquivo
pronto para repassar ao cliente. O PDF é enviado como upload multipart (bytes),
não por URL — a URL da tailnet não é alcançável pelos servidores do Telegram.
Nunca derruba a request: erros são engolidos e logados.
"""
import logging
import os

import httpx

log = logging.getLogger("avs.telegram")


def _token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _chat_ids() -> list[str]:
    raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def notificar_telegram(texto: str, pdf_bytes: bytes | None = None,
                       pdf_filename: str | None = None) -> bool:
    """Envia `texto` e, se houver, o PDF como documento a cada chat autorizado.

    Texto em plain text (URLs viram links automaticamente). Retorna True se ao
    menos uma mensagem foi entregue.
    """
    token = _token()
    ids = _chat_ids()
    if not token or not ids:
        log.info("telegram: token/chat ausente, entrega direta ignorada")
        return False
    base = f"https://api.telegram.org/bot{token}"
    ok_any = False
    for chat_id in ids:
        try:
            r = httpx.post(f"{base}/sendMessage",
                           json={"chat_id": chat_id, "text": texto,
                                 "disable_web_page_preview": True},
                           timeout=30)
            ok_any = ok_any or r.status_code < 400
            if pdf_bytes and pdf_filename:
                httpx.post(f"{base}/sendDocument",
                           data={"chat_id": chat_id},
                           files={"document": (pdf_filename, pdf_bytes,
                                               "application/pdf")},
                           timeout=120)
        except Exception as e:  # nunca derruba a finalização
            log.warning("telegram indisponível (chat %s): %s", chat_id, e)
    return ok_any
