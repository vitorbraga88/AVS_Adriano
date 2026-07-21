# Guia de Testes - AVS Soluções Elétricas

## Preparação do Ambiente

### Windows (Desenvolvimento)
```bash
cd C:\Users\vitor\Desktop\Proj. AVS\avs-admin
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set ADMIN_PASSWORD=teste
py -m uvicorn app.main:app --reload --port 8090
```

### Servidor (Produção)
```bash
cd /var/www/avs-admin
source .venv/bin/activate
export ADMIN_PASSWORD=sua_senha_segura
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

## Credenciais Padrão
- **Usuário:** admin
- **Senha (dev):** teste
- **Senha (produção):** DEFINIR no `.env` (ADMIN_PASSWORD)

---

## Testes Funcionais

### 1. Boot e Schema
**Objetivo:** Verificar inicialização do servidor e criação das tabelas

```bash
# Teste de health check
curl http://127.0.0.1:8090/ping
# Esperado: {"status":"ok"}

# Verificar tabelas do SQLite
sqlite3 database/avs.db ".tables"
# Esperado: 10 tabelas:
# - ordens, ordem_itens, ordem_custos
# - clientes, equipamentos
# - financeiro_vendas, financeiro_despesas
# - assinaturas, sugestoes, notificacoes
```

**Validação visual:**
- Acessar `http://127.0.0.1:8090/orcamentos` (login admin/teste)
- Sem erros de JS no console
- Página carrega completamente

---

### 2. Orçamento - Criação Completa
**Objetivo:** Testar fluxo completo de criação de orçamento com PDF

**Passos:**
1. Acessar `/orcamentos/novo`
2. Preencher campos:
   - **Cliente:** João Silva
   - **Telefone:** (81) 99999-9999
   - **Endereço:** Rua Teste, 123
   - **Equipamento (opcional):**
     - Descrição: Quadro Geral
     - Marca: Siemens
     - Modelo: 8US
     - Número de Série: SN12345
   - **Tipo:** Manutenção
   - **Título:** Manutenção Preventiva
   - **Local:** Sala de Comando
   - **Itens:**
     - Item 1: Serviço técnico, Qtd: 1, Un: un, Preço: R$ 100,00
     - Item 2: Peça de reposição, Qtd: 2, Un: un, Preço: R$ 50,00
   - **Desconto:** 10%
   - **Validade:** +7 dias (automático)
   - **Observações:** Cliente preferencial

3. Adicionar 1 foto (câmera ou upload)
4. Assinar no canvas
5. Clicar "⚡ Finalizar e Enviar"

**Validações:**
- [ ] PDF gerado em `relatorios/` com nome `Orçamento - João Silva - ORC-YYYYMMDD-NNN.pdf`
- [ ] PDF contém:
  - [ ] Logo AVS
  - [ ] Dados do cliente
  - [ ] **Bloco de equipamento** (marca, modelo, série)
  - [ ] Tabela de itens (2 linhas)
  - [ ] Total: R$ 180,00 (100 + 100 - 10%)
  - [ ] Seção de fotos (2×2)
  - [ ] Assinatura
  - [ ] **Banner AVS_2 no rodapé**
- [ ] Registro no banco:
  - `ordens`: 1 linha, status `orcamento`, `total_centavos=18000`
  - `clientes`: 1 linha (João Silva)
  - `equipamentos`: 1 linha (Quadro Geral)
  - `ordem_itens`: 2 linhas
  - `orcamento_json`: preenchido
  - `orcamento_pdf_url`: caminho do PDF

---

### 3. Equipamento - Reuso
**Objetivo:** Verificar reutilização de equipamentos do mesmo cliente

**Passos:**
1. Criar novo orçamento para **João Silva** (mesmo cliente)
2. No campo "Equipamento", clicar no seletor
3. Selecionar "Quadro Geral - Siemens 8US"

**Validações:**
- [ ] Seletor mostra o equipamento cadastrado
- [ ] Selecionar **NÃO** cria duplicata em `equipamentos`
- [ ] Orçamento novo referencia o mesmo `equipamento_id`

**Teste de negação:**
- Tentar criar equipamento com mesmo número de série/patrimônio
- [ ] Sistema reutiliza o existente em vez de duplicar

---

### 4. Máquina de Estados + Agenda
**Objetivo:** Testar transições de status e visualização na agenda

**Passos:**
1. No orçamento criado (Teste 2), clicar "📅 Agendar"
2. Definir data: **hoje**
3. Status: `orcamento` → `aprovado`
4. Validar transição inválida: tentar `aprovado` → `recebido`
5. Continuar transições válidas:
   - `aprovado` → `em_execucao`
   - `em_execucao` → `concluido`
   - `concluido` → `recebido`

**Validações:**
- [ ] `orcamento → aprovado`: exige data_servico preenchida
- [ ] Transição inválida mostra erro: "?erro=Transição+inválida"
- [ ] Acessar `/agenda`:
  - [ ] Ordem aparece no Kanban (coluna "aprovado")
  - [ ] Ordem aparece no calendário (data agendada)
- [ ] `aprovado → em_execucao`: muda para coluna "em_execucao"
- [ ] `em_execucao → concluido`: seta `data_conclusao`
- [ ] `concluido → recebido`:
  - [ ] Setar `data_recebimento`
  - [ ] Cria registro em `financeiro_vendas`
  - [ ] `valor_centavos=18000`
  - [ ] `custo_centavos=0` (ainda sem custos lançados)

---

### 5. Custos da OS
**Objetivo:** Testar lançamento de custos na OS

**Passos:**
1. Acessar `/os/{id}` (OS aprovada do Teste 4)
2. Clicar "💰 Adicionar Custo"
3. Preencher:
   - Descrição: Material elétrico
   - Categoria: material
   - Valor: R$ 40,00
4. Continuar transições até `recebido`

**Validações:**
- [ ] `ordem_custos`: 1 linha, `valor_centavos=4000`
- [ ] Ao marcar `recebido`:
  - [ ] `financeiro_vendas.custo_centavos=4000` (soma dos custos)
  - [ ] Lucro calculado: 18000 - 4000 = 14000

---

### 6. Financeiro
**Objetivo:** Verificar dashboard financeiro

**Passos:**
1. Criar despesa geral em `/despesas/novo`:
   - Categoria: transporte
   - Descrição: Viagem ao cliente
   - Valor: R$ 30,00
2. Acessar `/financeiro`

**Validações:**
- [ ] Dashboard mostra:
  - [ ] **Receita:** R$ 180,00 (1 venda)
  - [ ] **Custo:** R$ 40,00 (1 OS)
  - [ ] **Despesas:** R$ 30,00 (1 despesa)
  - [ ] **Lucro:** R$ 110,00 (180 - 40 - 30)
  - [ ] **Margem:** 61,11% (110 / 180)
- [ ] Lista últimas 20 despesas (R$ 30,00 aparece)
- [ ] Contas a receber:
  - [ ] OS aprovada/em_execucao sem `data_recebimento`: aparece
  - [ ] OS recebida: some da lista

---

### 7. Relatório de Serviço (OS)
**Objetivo:** Testar relatório com blocos dinâmicos

**Passos:**
1. Acessar `/os/{id}/relatorio` (OS em execução)
2. Editar blocos:
   - **Descrição Detalhada:** "Serviço executado conforme normas..."
   - **Peças Utilizadas:** "1 disjuntor, 5 metros de cabo..."
   - **Peças Substituídas:** "1 disjuntor antigo..."
   - **Normas Técnicas:** "NR-10, NBR 5410"
3. Adicionar bloco customizado:
   - Título: "Recomendações"
   - Conteúdo: "Realizar manutenção em 6 meses"
4. Adicionar 2 fotos
5. Assinar (cliente + técnico)
6. Clicar "⚡ Gerar relatório e enviar"

**Validações:**
- [ ] PDF gerado com nome `OS - João Silva - ORC-YYYYMMDD-NNN.pdf`
- [ ] PDF contém:
  - [ ] Cabeçalho "Ordem de Serviço"
  - [ ] Dados da OS (número, cliente, equipamento, data)
  - [ ] **4 seções de blocos** (título como cabeçalho)
  - [ ] **Bloco customizado** "Recomendações"
  - [ ] Páginas de fotos (2×2)
  - [ ] **2 assinaturas** (cliente + técnico)
  - [ ] Banner AVS_2 no rodapé
- [ ] `relatorio_json`: preenchido com blocos, fotos, assinaturas
- [ ] `os_pdf_url`: caminho do PDF

---

### 8. n8n Webhook (Contrato)
**Objetivo:** Verificar integração com n8n

**Pré-condição:** `N8N_WEBHOOK_BASE` configurado no `.env`

**Teste:**
1. Configurar webhook de teste: `https://webhook.site/criar-url`
2. Setar `N8N_WEBHOOK_BASE=https://webhook.site`
3. Finalizar orçamento

**Validações:**
- [ ] POST para `https://webhook.site/avs-orcamento`
- [ ] Payload contém:
  - `tipo: "orcamento"`
  - `ordem_numero: "ORC-YYYYMMDD-NNN"`
  - `cliente: "João Silva"`
  - `total_brl: "R$ 180,00"`
  - `pdf_base64: "..."`
  - `pdf_filename: "Orçamento - João Silva - ...pdf"`

**Sem receptor:**
- [ ] Finalização **NÃO falha** (try/except)
- [ ] Ordem é salva normalmente
- [ ] `notificacoes`: 1 registro (tentativa)

---

### 9. PWA / Offline
**Objetivo:** Testar modo offline e sync

**Passos:**
1. Instalar PWA (Chrome/Edge):
   - Abrir DevTools → Application → Manifest
   - Clicar "Install"
2. Simular offline:
   - DevTools → Network → "Offline"
3. Finalizar orçamento offline
4. Voltar online
5. Abrir DevTools → Application → IndexedDB → `drafts`

**Validações:**
- [ ] Toast: "Salvo no modo offline"
- [ ] IndexedDB: 1 rascunho (`drafts` store)
- [ ] Voltar online:
  - [ ] Toast: "Sincronizando..."
  - [ ] Rascunho enviado ao servidor
  - [ ] PDF gerado
  - [ ] Rascunho removido do IndexedDB
  - [ ] Ordem aparece em `/orcamentos`

---

### 10. Telegram Bot
**Objetivo:** Testar notificações do bot

**Pré-condição:** `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_IDS` configurados

**Passos:**
1. Iniciar conversa com o bot
2. Enviar comandos:
   - `/menu`
   - `/hoje`
   - `/semana`
   - `/orcamentos`

**Validações:**
- [ ] `/menu`: menu principal
- [ ] `/hoje`: lista serviços agendados para hoje
- [ ] `/semana`: agenda da semana
- [ ] `/orcamentos`: últimos 5 orçamentos com PDF

**Notificações automáticas:**
- [ ] Ao finalizar orçamento: bot recebe resumo + PDF
- [ ] Ao finalizar OS: bot recebe resumo + PDF

---

## Testes de Integração

### Caddy (Proxy Reverso)
```bash
# /etc/caddy/Caddyfile
:443 {
    tls /etc/ssl/certs/fullchain.pem /etc/ssl/certs/privkey.pem
    
    handle /avs/* {
        reverse_proxy 127.0.0.1:8090
    }
    
    handle /avs/static/img/* {
        root * /var/www/avs-admin/app/static
        file_server browse
    }
    
    handle /webhook/* {
        reverse_proxy 127.0.0.1:5678
    }
}
```

**Validação:**
- [ ] `https://servidor-203.tail43f430.ts.net/avs/orcamentos` acessível
- [ ] PDFs servidos via `/avs/static/img/relatorios/`
- [ ] Webhooks n8n roteados

---

### Systemd Service
```bash
# /etc/systemd/system/avs-admin.service
[Unit]
Description=AVS Soluções Elétricas - Admin
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/avs-admin
Environment="PATH=/var/www/avs-admin/.venv/bin"
Environment="ADMIN_PASSWORD=${ADMIN_PASSWORD}"
EnvironmentFile=/var/www/avs-admin/.env
ExecStart=/var/www/avs-admin/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Validação:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable avs-admin
sudo systemctl start avs-admin
sudo systemctl status avs-admin
```

---

## Checklist Final

### Backend
- [ ] Todas as 10 tabelas criadas
- [ ] 8 estados funcionando (rascunho → orcamento → aprovado → em_execucao → concluido → recebido + recusado/cancelado)
- [ ] Dinheiro em centavos (sem float)
- [ ] Fuso America/Recife
- [ ] Auth HTTP Basic + CSRF
- [ ] API endpoints funcionando

### Frontend
- [ ] Todos os painéis acessíveis (Dashboard, Orçamentos, OS, Agenda, Financeiro, Despesas, Clientes, Equipamentos)
- [ ] Formulários de campo (Orçamento, OS) funcionando
- [ ] PDFs gerados corretamente (Orçamento e OS)
- [ ] PWA instalável
- [ ] Offline mode funcionando

### Integrações
- [ ] n8n webhook enviado
- [ ] Telegram bot respondendo
- [ ] Assinaturas sincronizadas
- [ ] Equipamentos reutilizados

### Segurança
- [ ] ADMIN_PASSWORD definido
- [ ] HTTPS configurado (Caddy)
- [ ] CSRF ativado
- [ ] SQL injection prevenido (SQLAlchemy)
- [ ] XSS prevenido (Jinja2 autoescape)

---

## Troubleshooting

### Erro: "Transição inválida"
- **Causa:** Tentativa de transição não permitida pela máquina de estados
- **Solução:** Verificar `TRANSICOES_VALIDAS` em `services/ordens.py`

### PDF não gerado
- **Causa:** html2canvas ou jsPDF falhando
- **Solução:** Verificar console do navegador; confirmar que todas as imagens estão carregadas

### Equipamento duplicado
- **Causa:** Lógica de reuso não funcionando
- **Solução:** Verificar `upsert_equipamento` em `services/ordens.py`

### Webhook n8n falhando
- **Causa:** `N8N_WEBHOOK_BASE` não configurado ou n8n offline
- **Solução:** Verificar `.env`; confirmar que n8n está rodando

### Telegram bot não responde
- **Causa:** `TELEGRAM_BOT_TOKEN` inválido ou `TELEGRAM_CHAT_IDS` vazio
- **Solução:** Verificar token com @BotFather; confirmar chat IDs

---

## Performance

### Tempos esperados (dev):
- Boot servidor: < 3s
- Geração PDF: < 5s
- Criação orçamento: < 10s (incluindo PDF)
- Load dashboard: < 2s

### Tempos esperados (produção):
- Boot servidor: < 2s
- Geração PDF: < 3s
- Criação orçamento: < 7s
- Load dashboard: < 1s
