"""Entrega provider-agnóstica ao n8n.

O app persiste no SQLite e faz POST server-to-server ao webhook n8n, que
envia resumo + PDF ao bot Telegram (ou WhatsApp, via fan-out no n8n). Nunca
derruba a request do usuário: erros são engolidos e logados.
"""
import logging
import os

import httpx

from app.models import Notificacao

log = logging.getLogger("avs.notificacoes")


def _webhook_base() -> str:
    return os.getenv("N8N_WEBHOOK_BASE", "http://127.0.0.1:5678/webhook").rstrip("/")


def notificar_n8n(db, tipo: str, ordem, resumo: str,
                  pdf_base64: str | None = None, pdf_filename: str | None = None) -> bool:
    """POST {N8N_WEBHOOK_BASE}/avs-<tipo>. Retorna True se entregue.

    tipo: 'orcamento' | 'os'. Registra em `notificacoes` quando enviado.
    """
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    pdf_url = None
    if pdf_filename:
        pdf_url = f"{base}/relatorios/{pdf_filename}" if base else f"/relatorios/{pdf_filename}"
    cliente_nome = ordem.cliente.nome if getattr(ordem, "cliente", None) else None
    payload = {
        "tipo": tipo,
        "ordem_numero": ordem.numero,
        "cliente": cliente_nome,
        "titulo": ordem.titulo,
        "total_brl": f"{(ordem.total_centavos or 0) / 100:.2f}".replace(".", ","),
        "status": ordem.status,
        "resumo_texto": resumo,
        "pdf_url": pdf_url,
        "pdf_base64": pdf_base64,
        "pdf_filename": pdf_filename,
    }
    url = f"{_webhook_base()}/avs-{tipo}"
    try:
        resp = httpx.post(url, json=payload, timeout=120)
        ok = resp.status_code < 400
        if ok:
            try:
                db.add(Notificacao(ordem_id=ordem.id, tipo=tipo,
                                   chat_id=os.getenv("TELEGRAM_CHAT_IDS", "") or None))
                db.commit()
            except Exception:
                db.rollback()
                log.warning("falha ao registrar notificação (não crítico)")
        else:
            log.warning("n8n respondeu %s para %s", resp.status_code, url)
        return ok
    except Exception as e:
        log.warning("n8n indisponível (%s): %s — ordem persistida mesmo assim", url, e)
        return False
