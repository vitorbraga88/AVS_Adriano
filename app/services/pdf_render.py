"""Renderiza HTML -> PDF A4 via Chromium headless (Chrome do sistema).

Usa o motor de impressão do próprio navegador, que honra @page, @media print,
rodapé fixo por página e break-inside:avoid — impossível com html2canvas.
O Chrome é o instalado no sistema (channel="chrome"); nada é baixado.
"""
import logging

from playwright.sync_api import sync_playwright

log = logging.getLogger("avs.pdf")

_MARGENS = {"top": "0", "right": "0", "bottom": "0", "left": "0"}


def render_pdf(html: str) -> bytes:
    """HTML autocontido (CSS + fontes/imagens em base64) -> bytes de PDF A4.

    Síncrono: chamado a partir de endpoints sync do FastAPI (rodam em
    threadpool, sem event loop no thread), então a API sync do Playwright
    é segura aqui.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.emulate_media(media="print")
            return page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin=_MARGENS,
            )
        finally:
            browser.close()
