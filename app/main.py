"""Bootstrap FastAPI da AVS Soluções Elétricas.

- SQLite (schema criado no startup via create_all; sem Alembic).
- Auth HTTP Basic + same-origin nos formulários navegados.
- Bot Telegram opcional: inicia no lifespan só se TELEGRAM_BOT_TOKEN presente,
  guardado por try/except que nunca derruba o app.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import verify_admin
from app.database import Base, engine
from app.deps import templates

load_dotenv()
log = logging.getLogger("avs")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria o schema (todas as tabelas) — import garante o registro dos models.
    from app import models  # noqa: F401
    Base.metadata.create_all(engine)

    bot_task = None
    scheduler = None
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if token:
        try:
            from app.bot.client import BotClient
            from app.bot.runner import run_polling
            from app.bot.scheduler import criar_scheduler
            from app.database import SessionLocal

            client = BotClient(token)
            await client.set_my_commands([
                {"command": "menu", "description": "Abrir o menu do painel"},
                {"command": "hoje", "description": "Serviços agendados para hoje"},
                {"command": "semana", "description": "Agenda da semana"},
                {"command": "orcamentos", "description": "Últimos orçamentos"},
            ])
            scheduler = criar_scheduler(client, SessionLocal)
            scheduler.start()
            bot_task = asyncio.create_task(run_polling())
            log.info("bot telegram: iniciado (token presente)")
        except Exception as e:  # nunca derruba o app por causa do bot
            log.warning("bot telegram: falhou ao iniciar: %s", e)
    else:
        log.info("bot telegram: inativo (TELEGRAM_BOT_TOKEN ausente)")
    yield
    if bot_task:
        bot_task.cancel()
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="AVS Admin", lifespan=lifespan)

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# PDFs gerados são servidos estaticamente
_REL_DIR = Path(__file__).parent.parent / "relatorios"
_REL_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/relatorios", StaticFiles(directory=str(_REL_DIR)), name="relatorios")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8090", "http://127.0.0.1:8090",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

from app.routes import (  # noqa: E402
    agenda, api, arquivos, clientes, dashboard, despesas,
    equipamentos, financeiro, orcamentos, os_relatorio,
)

app.include_router(dashboard.router)
app.include_router(orcamentos.router)
app.include_router(os_relatorio.router)
app.include_router(agenda.router)
app.include_router(financeiro.router)
app.include_router(despesas.router)
app.include_router(clientes.router)
app.include_router(equipamentos.router)
app.include_router(api.router)
app.include_router(arquivos.router)


@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return await http_exception_handler(request, exc)


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    from fastapi.responses import FileResponse
    sw = _STATIC_DIR / "sw.js"
    return FileResponse(str(sw), media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


@app.get("/health", dependencies=[Depends(verify_admin)])
def health():
    try:
        from sqlalchemy import text
        from app.database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        log.exception("healthcheck falhou")
        return {"status": "unhealthy", "database": "erro ao conectar; ver logs"}
