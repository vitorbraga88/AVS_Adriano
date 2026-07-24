"""Páginas de listagem dos PDFs gerados, separadas por tipo:
/arquivos/orcamentos e /arquivos/os. Consumidas pelos botões do bot Telegram.
"""
import os
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import verify_admin
from app.deps import templates

router = APIRouter(tags=["arquivos"], dependencies=[Depends(verify_admin)])

REL_DIR = Path(__file__).parent.parent.parent / "relatorios"
TZ_RECIFE = ZoneInfo("America/Recife")
TITULOS = {"orcamentos": "Orçamentos", "os": "Relatórios de Serviço"}


def _listar(request: Request, sub: str) -> HTMLResponse:
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    pasta = REL_DIR / sub
    arquivos = []
    if pasta.is_dir():
        pdfs = sorted(pasta.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in pdfs:
            st = p.stat()
            arquivos.append({
                "nome": p.name,
                "url": f"{base}/relatorios/{sub}/" + urllib.parse.quote(p.name),
                "data": datetime.fromtimestamp(st.st_mtime, TZ_RECIFE).strftime("%d/%m/%Y %H:%M"),
                "tamanho": f"{st.st_size / 1024:.0f} KB",
            })
    outro = "os" if sub == "orcamentos" else "orcamentos"
    return templates.TemplateResponse(request, "arquivos.html", {
        "titulo": TITULOS[sub],
        "arquivos": arquivos,
        "app_url": base + "/",
        "outro_url": f"{base}/arquivos/{outro}",
        "outro_titulo": TITULOS[outro],
    })


@router.get("/arquivos/orcamentos", response_class=HTMLResponse)
def arquivos_orcamentos(request: Request):
    return _listar(request, "orcamentos")


@router.get("/arquivos/os", response_class=HTMLResponse)
def arquivos_os(request: Request):
    return _listar(request, "os")
