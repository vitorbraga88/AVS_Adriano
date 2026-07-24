# Repository Guidelines

## Project Overview
AVS Soluções Elétricas admin — a single-tenant field-service app for an electrician: create budgets (orçamentos), run them through an 8-state workflow to service orders (OS), track finances, and deliver generated PDFs to the owner's Telegram. It is a single-process **FastAPI + SQLite** app with server-rendered **Jinja2** pages, a vanilla-JS **PWA** (offline drafts, client-side PDF), and a **Telegram bot** (long-polling + scheduled reminders).

## Architecture & Data Flow
Layered, single process. No Alembic — schema is created at startup via `Base.metadata.create_all(engine)` in the lifespan (`app/main.py:35-58`).

```
routes/ (HTTP adapters) → services/ (business logic) → models.py (SQLAlchemy ORM, SQLite)
                                     ↘ telegram_notify.py → Telegram
bot/ (independent async subsystem, only if TELEGRAM_BOT_TOKEN set) → same DB via own SessionLocal
```

- **Composition root** `app/main.py`: app factory, lifespan (DB schema + optional bot/scheduler boot, all in `try/except` so the bot never crashes the app), static mounts `/static` and `/relatorios`, CORS (localhost:8090 only), JSON 404 handler, 9 routers.
- **HTML routers** (`dashboard, orcamentos, os_relatorio, agenda, financeiro, despesas, clientes, equipamentos`) return `TemplateResponse`/`303 RedirectResponse` and guard mutating POSTs with `verify_same_origin`.
- **JSON router** `app/routes/api.py` (`prefix=/api`, **no** same-origin check) is consumed by the PWA form JS.
- **Services** own the logic: `ordens.py` (state machine, cents math, upserts, side-effects), `telegram_notify.py` (only direct Telegram egress), `kpis.py` (dashboard aggregates).

**Finalize flow** (`POST /api/orcamentos/finalizar`, `POST /api/os/finalizar`, `app/routes/api.py:58,89`):
1. JS gathers form → `AVS.Pdf.gerarBlob` renders offscreen HTML → html2canvas → jsPDF → base64.
2. POST `{cliente, equipamento, itens[], desconto_pct, pdf_base64, pdf_filename, ordem_id?}`.
3. `services.ordens.criar_orcamento`/`atualizar_orcamento` (upsert cliente by telefone, equipamento by série/patrimônio; number `ORC-YYYYMMDD-NNN`; total recomputed in cents).
4. `_save_pdf` validates `SAFE_FILENAME`, decodes base64, writes to `relatorios/`, sets `ordem.*_pdf_url`.
5. `_entregar_telegram` → `notificar_telegram` (`sendMessage` + multipart `sendDocument`) → on success inserts a `Notificacao` row. **All Telegram errors are swallowed — finalization never aborts.**

**Status machine** (`app/services/ordens.py` `TRANSICOES_VALIDAS`): `rascunho → orcamento → aprovado → em_execucao → concluido → recebido`, with `recusado`/`cancelado` branches. `aprovado` requires `data_servico`; `recebido` is terminal, stamps `data_recebimento` (Recife date) and inserts a `FinanceiroVenda` (custo = sum of `ordem_custos`). Enforced both in code and by a `CheckConstraint` (`ordem_status_check`) on the `ordens` table.

## Key Directories
- `app/routes/` — one module per feature; each declares `dependencies=[Depends(verify_admin)]`.
- `app/services/` — business logic (`ordens.py`, `telegram_notify.py`, `kpis.py`). Put logic here, not in routes.
- `app/bot/` — `client.py` (httpx Bot API wrapper), `runner.py` (getUpdates loop + `_dispatch`), `handlers.py` (commands), `scheduler.py` (APScheduler cron).
- `app/templates/` — 18 Jinja2 templates.
- `app/static/js/` — the `window.AVS` module system (see conventions).
- `database/` — `avs.db` (SQLite, git-ignored on deploy). `relatorios/` — generated PDFs (git-ignored on deploy).

## Development Commands
```bash
# Dev run (Windows launcher; app object = app.main:app, port 8090, 127.0.0.1)
run_dev.bat
# Manual (any OS)
python -m uvicorn app.main:app --reload --port 8090

# Import smoke checks (the closest thing to tests — NOT a suite)
python _check.py          # "IMPORT OK"
python _test_os.py        # "OS route loads OK"

# Ad-hoc DB inspection
python _tbl.py            # list tables
python _q.py              # dump ordens/itens/equipamentos

# Deploy to servidor-203 (rsync + pip + systemctl restart)
./deploy.sh [host]
```
`deploy.sh` uses `rsync -avz --delete` and **excludes** `.git __pycache__ *.pyc .venv .env database/ relatorios/ _*.py _*.json` — never overwrite the live DB/PDFs/secrets with repo versions.

## Code Conventions & Common Patterns
- **Money is always integer cents** (`total_centavos`, `preco_centavos`, `custo_centavos`, `valor_centavos`). Never use floats. Parse UI money with `AVS.UI.parseMoneyToCentavos`; render with Jinja `brl_c` filter or `AVS.UI.brlFromCentavos`.
- **Timezone** is `America/Recife` via stdlib `zoneinfo` (`TZ_RECIFE = ZoneInfo("America/Recife")`); datetimes stored naive/UTC as noted per column. No `pytz`.
- **Auth**: HTTP Basic, username fixed `admin`, password = `ADMIN_PASSWORD` (`secrets.compare_digest`). `AVS_DEV=1` with no password bypasses auth (dev only — never prod). Mutating HTML forms also call `verify_same_origin` (CSRF guard); `/api/*` does **not**.
- **Route → service delegation**: routes stay thin; all CRUD/state logic lives in `app/services/`. Follow the existing pattern, don't inline logic in routes.
- **State transitions** go through `services.ordens.mudar_status`, which raises `ValueError` on invalid transitions (routes catch → `303` redirect). Never mutate `ordem.status` directly.
- **Upserts**: cliente reused by `telefone`, equipamento by `numero_serie`/`patrimonio` within `cliente_id` (`upsert_cliente`, `upsert_equipamento`).
- **Resilient side-effects**: Telegram/notification calls are wrapped in `try/except` and swallowed — they must never break a request.
- **Frontend module pattern** (`app/static/js/*.js`): IIFE registering onto a global namespace, e.g. `window.AVS = window.AVS || {}; (function (AVS) { "use strict"; ... AVS.Orcamento = {...}; })(window.AVS);`. Shared helpers: `el(id)`, `AVS.UI.toast`, `AVS.Validation.check([{sel,msg}])`, `AVS.Pdf.gerarBlob`, `AVS.Offline.saveDraft` (IndexedDB `avs-drafts/drafts`), `AVS.Signature`, `AVS.Camera`, `AVS.Voice`.
- **PDFs are client-side only** (html2canvas → jsPDF). The server never renders PDFs — it only base64-decodes and stores them.
- **PWA/offline**: failed finalize POSTs fall back to `AVS.Offline.saveDraft(...)`; `monitorConnectivity()` re-syncs on `online`.

## Important Files
- `app/main.py` — entry point, lifespan, mounts, router registration.
- `app/auth.py` — `verify_admin`, `verify_same_origin`.
- `app/models.py` — 10 tables; `STATUS_ORDEM` enum + `CheckConstraint`; money-as-cents; `orcamento_json`/`relatorio_json` snapshot columns.
- `app/services/ordens.py` — `TRANSICOES_VALIDAS`, `criar_orcamento`, `atualizar_relatorio`, `mudar_status`.
- `app/routes/api.py` — the JSON API + finalize endpoints + `_save_pdf`/`_entregar_telegram`.
- `app/static/js/orcamento.js`, `os.js`, `pdf.js` — form controllers + PDF pipeline.
- `.env.example` — canonical env keys.

## Runtime/Tooling Preferences
- **Python 3.12** (server runs 3.12.3). Not Bun/Node — frontend JS is served static, no build step.
- **pip + venv** (`.venv/bin/pip install -r requirements.txt`). Dependencies in `requirements.txt` are unpinned except `sqlalchemy>=2`: `fastapi, uvicorn[standard], jinja2, python-dotenv, httpx, python-multipart, apscheduler`.
- **Jinja2 must stay on 3.1.5** — 3.1.6 has a template-cache bug (`TypeError: unhashable type: 'dict'`). Pin it if you touch `requirements.txt`.
- **Prod**: systemd service `avs-admin`, binds `0.0.0.0:8091`, reached externally via a reverse proxy under the `/avs` prefix (`PUBLIC_BASE_URL`). Note the mismatch: dev/docs assume port **8090**; the deployed service uses **8091** (8090 was taken). Static assets use absolute `/static/...` paths, so the app works at the site root (or `:8091` direct) but not under the `/avs` proxy prefix without rewriting.

### Environment variables
| Var | Purpose |
|---|---|
| `ADMIN_PASSWORD` | Basic-auth password (user `admin`). Empty + `AVS_DEV=1` → open. Empty alone → API returns 503. |
| `AVS_DEV` | `1` bypasses auth. Dev only. |
| `PUBLIC_BASE_URL` | Public URL used in bot links and PDF URLs. |
| `TELEGRAM_BOT_TOKEN` | Enables the bot + scheduler; absent → bot inactive. |
| `TELEGRAM_CHAT_IDS` | CSV of authorized chat ids; bot only answers these, notifications only sent here. |

> Security note: `.env` currently committed with a real bot token — do **not** treat committed secrets as intended; keep real secrets out of git and never sync `.env` on deploy.

## Bot & Scheduler
- **Commands** (long-polling `getUpdates`, dispatched in `bot/runner.py:_dispatch`): `/menu` (`/start`), `/hoje`, `/semana`, `/orcamentos`. Only these four exist.
- **Scheduler jobs** (APScheduler cron, America/Recife): `lembrete_hoje` 07:00 daily, `lembrete_cobranca` 08:00 daily (concluído + unpaid), `resumo_semana` Monday 07:00. All no-op when `TELEGRAM_CHAT_IDS` is empty.

## Testing & QA
- **No automated test framework** (no pytest/unittest, no `pyproject.toml`/`conftest.py`). The root `_*.py` files are ad-hoc smoke/inspection scripts, not a suite.
- Verify changes by: `python _check.py` (imports load), starting the server and exercising the affected route, and inspecting `database/avs.db` with the `_q*.py`/`_tbl.py` scripts.
- Manual test scenarios and known issues are documented in `GUIA_TESTES.md` (10 scenarios) and `CHECKLIST_ENTREGA.md`.
- **Known issues to keep in mind**: Jinja2 3.1.6 cache bug (stay on 3.1.5); html2canvas flash mitigated via offscreen iframe; SQLite write-lock under concurrency; Windows port 8090 binding.
