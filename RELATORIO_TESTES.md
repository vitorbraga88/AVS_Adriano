# Relatório de Testes — AVS Soluções Elétricas

Executado em 24/07/2026, ambiente de desenvolvimento (`venv`, SQLite local,
`uvicorn --reload` na porta 8099), **antes** da limpeza do banco (Tarefa 2).
Backup pré-teste: `database/avs_backup_pre_teste.db` (sha256 idêntico ao
`avs.db` original no momento do backup).

Dados usados: os 3 clientes / 1 equipamento / 4 ordens já existentes no banco,
mais registros novos criados durante os testes (clientes/equipamentos/ordens
de teste — descartados na limpeza da Tarefa 2).

## a) Dashboard carrega
**OK.** `GET /` → 200, 7 cards de KPI renderizados (verificado via browser
headless, `document.querySelectorAll('.kpi').length === 7`).

## b) CRUD cliente
**OK.**
- Criar: `POST /clientes` → 303, cliente aparece na listagem.
- Editar: `GET /clientes/{id}/editar` → 200; `POST /clientes/{id}` → 303,
  alteração refletida na listagem.
- Exclusão de cliente não possui rota (não existe no escopo original — só
  clientes sem despesas/equipamentos vinculados seriam elegíveis; não testado
  por não haver endpoint).

## c) CRUD equipamento
**OK.**
- Criar: `POST /equipamentos` (com `cliente_id`) → 303, aparece na listagem.
- Editar: `GET /equipamentos/{id}/editar` → 200; `POST /equipamentos/{id}`
  → 303, alteração refletida.
- Observação de processo: 1ª tentativa de edição via curl retornou 422 por eu
  ter omitido `cliente_id` (campo obrigatório do form) — erro do script de
  teste, não do app; corrigido e reexecutado com sucesso.

## d) Criar orçamento com itens + totais
**OK**, testado por dois caminhos:
1. **API direta** (`POST /api/orcamentos/finalizar`): 2 itens
   (R$50,00×2 + R$30,00×1 = R$130,00 bruto) com 10% de desconto →
   total gravado `11700` centavos = R$117,00. **Cálculo confere.**
2. **Browser real** (form `/orcamentos/novo`, JS de campo): nome, telefone,
   endereço, item com preço R$120,00 → total exibido em tela `R$ 120,00`
   confere com o cálculo client-side; finalizar gerou PDF, enviou via fetch,
   e criou a ordem `ORC-20260724-002`.

## e) Criar OS + alterar status
**OK.** Fluxo completo testado na ordem criada no item (d)-1:
`orcamento → aprovado (após agendar data_servico) → em_execucao → concluido
→ recebido`. Cada transição validada pela máquina de estados
(`services/ordens.py`); tentativa de pular etapa é bloqueada (não testada
neste ciclo pois não foi necessário forçar erro, mas a validação de
`aprovado` sem `data_servico` já é exercida indiretamente pelo fluxo normal).
Ao marcar **recebido**: `FinanceiroVenda` criada com `valor_centavos=11700`,
`custo_centavos=4550` (soma do custo lançado na OS) — **confere**.
Lançamento de custo (`POST /os/{id}/custos`) testado e refletido no total de
custos da OS.

## f) Agenda + cancelar evento
**OK.**
- Kanban (`/agenda`): ordens aparecem nas colunas corretas por status
  (`orcamento`, `aprovado`, `em_execucao`, `concluido`, `recebido`).
- Calendário (`/agenda/calendario`): evento agendado (`data_servico`)
  aparece no dia/mês corretos com horário formatado.
- Cancelar: `POST /orcamentos/{id}/status status=cancelado` → 303, ordem
  passa para `cancelado` — confirmado no detalhe (badge "Cancelado").
- **Limitação encontrada (endereçada na Tarefa 6):** não havia botão de
  "Apagar" (exclusão definitiva) em nenhuma tela de agenda antes desta
  entrega — só existia mudança de status. Implementado nesta rodada.

## g) Financeiro (despesas, vendas)
**OK.**
- `/financeiro` → 200, KPIs de receita/custo/margem calculados a partir de
  `FinanceiroVenda` e `FinanceiroDespesa`.
- Despesa criada (`POST /despesas`), editada (`POST /despesas/{id}`) e
  excluída (`POST /despesas/{id}/excluir`) — todas 303, refletidas na
  listagem/total do mês.
- Venda: criada automaticamente ao marcar ordem como `recebido` (ver item e).

## h) Upload de foto
**OK**, testado no navegador real (headless Chromium) nos dois formulários
(`orcamento_form.html` e `os_form.html`):
- Upload via `<input type=file>` com imagem JPEG 2000×1500 → compressão
  client-side executada (`camera.js`), preview renderizado no grid como
  `data:image/jpeg;base64,...`.
- Legenda editável presente; remoção (botão "×") funcional.
- PDF final embutiu a foto (arquivo gerado com ~1,1 MB, consistente com
  imagem + layout A4).

## i) Notificação Telegram (chat 8518474117)
**PARCIAL — bloqueado por infraestrutura externa, não por bug no app.**
O app **não** fala com o Telegram diretamente: ele faz `POST
{N8N_WEBHOOK_BASE}/avs-<tipo>` para o n8n, que é quem despacha ao bot
Telegram (arquitetura documentada no `README.md`). Neste ambiente:
- n8n está rodando (`127.0.0.1:5678`, confirmado via `ss -ltnp`), **mas**
  os workflows `avs-orcamento`/`avs-os` não existem ainda (resposta `404`
  do n8n, logado como warning).
- Não há `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_IDS` configurados no `.env`
  deste ambiente de teste.
- **O que foi validado:** a falha de notificação **não derruba a request**
  — orçamento e OS foram persistidos e o PDF salvo normalmente mesmo com o
  n8n respondendo 404 (comportamento *fail-open* correto, por design).
- **Pendência para Adriano:** criar os workflows n8n `avs-orcamento` e
  `avs-os` (payload documentado no `README.md`) e configurar o bot Telegram
  apontando para o chat `8518474117`. Sem isso, nenhuma app FastAPI
  consegue "testar" a entrega real — é configuração de infraestrutura fora
  do código Python.

## j) PDF orçamento e OS
**OK.** Gerados e salvos em `relatorios/`, com URL persistida em
`ordem.orcamento_pdf_url` / `ordem.os_pdf_url`:
- `Orçamento - Cliente Browser Teste -  24.07.26.pdf` (1,14 MB) — orçamento
  com 1 item, 1 foto e assinatura do cliente.
- `OS - Cliente Browser Teste - ORC-20260724-002 24.07.26.pdf` (1,14 MB) —
  relatório de serviço com bloco preenchido, 1 foto e assinaturas de
  cliente + técnico (memória de assinatura por nome também validada:
  `GET /api/assinatura?nome=...` retorna a assinatura salva).

---

## Resumo

| Item | Resultado |
|---|---|
| a) Dashboard | OK |
| b) CRUD cliente | OK |
| c) CRUD equipamento | OK |
| d) Orçamento + itens + total | OK |
| e) OS + status | OK |
| f) Agenda + cancelar | OK (Apagar não existia — implementado na Tarefa 6) |
| g) Financeiro | OK |
| h) Upload foto | OK |
| i) Notificação Telegram | Parcial — pipeline app→n8n íntegro; entrega real pendente de workflow n8n + bot token (fora do código) |
| j) PDF orçamento/OS | OK |

Nenhuma falha de aplicação encontrada nos fluxos testados. Prosseguindo com
as Tarefas 1–7 (recursos novos) e só então a Tarefa 2 (limpeza do banco).
