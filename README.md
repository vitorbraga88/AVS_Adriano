# AVS Soluções Elétricas — Admin

App web único (FastAPI + Jinja2 + SQLite) para orçamentos, ordens de serviço (OS),
agenda e financeiro da AVS Soluções Elétricas. Uma "ordem" progride por estados:
orçamento → OS → recebimento. Dinheiro é sempre armazenado em **centavos** (int).
Fuso horário: `America/Recife`.

---

## Setup de desenvolvimento (Windows)

```bat
cd avs-admin

py -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

set ADMIN_PASSWORD=teste

uvicorn app.main:app --reload --port 8090
```

O banco `database/avs.db` e todas as tabelas são criados automaticamente no startup
(`Base.metadata.create_all`). Não há Alembic.

Verificação rápida:

- `http://127.0.0.1:8090/ping` → `{"status": "ok"}` (sem auth).
- `http://127.0.0.1:8090/orcamentos` → pede autenticação HTTP Basic.

## Autenticação

HTTP Basic com usuário fixo **`admin`** e senha da variável `ADMIN_PASSWORD`.
Sem `ADMIN_PASSWORD` definida, as rotas administrativas respondem **503**
(em dev local, `AVS_DEV=1` libera sem senha — **nunca** em produção).

POSTs de formulários navegados exigem *same-origin* (header `Origin` do navegador);
as rotas `/api/*` chamadas pelo n8n **não** aplicam same-origin.

## Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste. Variáveis:

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ADMIN_PASSWORD` | sim (prod) | Senha do painel (usuário `admin`). Sem ela → 503. |
| `AVS_DEV` | não | `1` libera sem senha (somente dev local). |
| `PUBLIC_BASE_URL` | não | URL pública do app (botões do bot e links de PDF). Ex.: `https://servidor-203.tail43f430.ts.net/avs`. |
| `N8N_WEBHOOK_BASE` | não | Base dos webhooks n8n. Default `http://127.0.0.1:5678/webhook`. |
| `TELEGRAM_BOT_TOKEN` | não | Token do bot (@BotFather). Sem ele o bot fica **inativo**. |
| `TELEGRAM_CHAT_IDS` | não | `chat_id`s autorizados do dono, separados por vírgula (CSV). |

## Bot Telegram (opcional)

Iniciado apenas quando `TELEGRAM_BOT_TOKEN` está presente (no `lifespan` do app).
Long-polling; nunca derruba o app se falhar. Comandos:

- `/menu` (ou `/start`) — menu com botões para `/orcamentos` e `/agenda` (usa `PUBLIC_BASE_URL`).
- `/hoje` — serviços com `data_servico` hoje (status `aprovado`/`em_execucao`).
- `/semana` — serviços dos próximos 7 dias.
- `/orcamentos` — últimos 5 orçamentos por data de criação.

Apenas `chat_id`s listados em `TELEGRAM_CHAT_IDS` são atendidos. Um lembrete
automático dos serviços do dia é enviado ao primeiro `chat_id` todo dia às **07:00**
(horário de Recife) via APScheduler.

---

## n8n — workflows a criar manualmente

O app persiste no SQLite e faz **POST server-to-server** para
`{N8N_WEBHOOK_BASE}/avs-<tipo>`. O app depende apenas do **contrato HTTP**: se o n8n
estiver fora do ar, a finalização **não falha** (try/except) — a ordem é gravada e a
notificação é apenas ignorada. Crie estes três workflows no n8n:

### `avs-orcamento` e `avs-os`

Webhook que recebe o JSON abaixo e:

1. `sendDocument` do PDF ao Telegram do dono (usar `pdf_url` público ou `pdf_base64`);
2. `sendMessage` com `resumo_texto` ao dono;
3. (opcional) fan-out para WhatsApp usando os mesmos campos.

Payload:

```json
{
  "tipo": "orcamento",
  "ordem_numero": "ORC-20260721-001",
  "cliente": "Nome do Cliente",
  "titulo": "Manutenção do quadro geral",
  "total_brl": "R$ 180,00",
  "status": "orcamento",
  "resumo_texto": "Resumo legível do orçamento/OS...",
  "pdf_url": "https://.../relatorios/arquivo.pdf",
  "pdf_base64": "JVBERi0xLjc...",
  "pdf_filename": "Orçamento - Cliente - ORC-... 21.07.26.pdf"
}
```

`avs-os` recebe o mesmo formato com `tipo: "os"`.

### `avs-ai`

Webhook que recebe `{ "texto": "..." }`, chama um modelo (OpenRouter / DeepSeek) para
revisar/estruturar a descrição, e retorna:

```json
{
  "resumo": "Texto revisado...",
  "recomendacoes": ["item 1", "item 2"]
}
```

Usado pelo botão "✨ Revisar com IA". Sem esse workflow, o botão só exibe erro de
rede — o app continua funcionando normalmente.

---

## Máquina de estados da ordem

```
rascunho → orcamento → aprovado → em_execucao → concluido → recebido
                    ↘ recusado
        (qualquer estado ativo) → cancelado
```

A **receita** (`financeiro_vendas`) é criada ao marcar a ordem como **`recebido`**;
o custo da venda é a soma dos custos lançados na OS (`ordem_custos`). Transições
inválidas (ex.: `orcamento → recebido`) são rejeitadas.
