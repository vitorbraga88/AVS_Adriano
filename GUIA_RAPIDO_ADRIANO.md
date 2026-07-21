# 🎉 AVS Admin - Guia Rápido para Adriano

## O que é

Sistema completo para gestão da AVS Soluções Elétricas:
- **Orçamentos** com PDF automático
- **Ordens de Serviço (OS)** com relatório técnico
- **Financeiro** (receitas, custos, despesas, lucro, margem)
- **Agenda** (Kanban + calendário)
- **Bot Telegram** (notificações automáticas)

---

## 🚀 Acessar o Sistema

### Em Produção
```
https://servidor-203.tail43f430.ts.net/avs/orcamentos
```

**Login:**
- Usuário: `admin`
- Senha: (definida pelo Vitor)

---

## 📱 Instalar App no Celular

1. Abrir o link no Chrome/Edge do celular
2. Clicar em "Adicionar à Tela Inicial" ou "Instalar App"
3. Pronto! App instalado como PWA

---

## ⚡ Criar Orçamento

1. Clicar "Novo Orçamento"
2. Preencher dados do cliente
3. Adicionar equipamento (opcional)
4. Adicionar itens (serviços, peças, materiais)
5. Aplicar desconto (se necessário)
6. Adicionar fotos (opcional)
7. Assinar no canvas
8. Clicar "⚡ Finalizar e Enviar"

**Resultado:**
- PDF gerado automaticamente
- Notificação no Telegram
- Orçamento salvo no sistema

---

## 📋 Gerar Ordem de Serviço (OS)

1. Em um orçamento, clicar "📅 Agendar"
2. Definir data do serviço
3. Status muda para "aprovado"
4. Clicar "▶️ Iniciar Execução"
5. Status muda para "em_execucao"
6. Executar o serviço
7. Clicar "✅ Concluir"
8. Status muda para "concluido"
9. Clicar "💰 Marcar Recebido"
10. Status muda para "recebido" → **CRIA RECEITA NO FINANCEIRO**

**Lançar Custos:**
- Na OS, clicar "💰 Adicionar Custo"
- Preencher descrição, categoria, valor
- O custo é somado automaticamente no financeiro

---

## 💰 Financeiro

Acessar "Financeiro" no menu:

**Dashboard mostra:**
- Receita total (soma das OS recebidas)
- Custos totais (soma dos custos lançados)
- Despesas gerais (transporte, combustível, etc)
- Lucro (receita - custos - despesas)
- Margem (% do lucro sobre receita)

**Lançar Despesa:**
- Clicar "Nova Despesa"
- Preencher descrição, categoria, valor
- Aparece no dashboard automaticamente

---

## 📅 Agenda

Dois modos:

**Kanban:**
- Colunas: aprovado, em_execucao, concluido
- Arrastar ordens entre colunas
- Clicar para abrir detalhes

**Calendário:**
- Vista mensal
- Clicar no dia para ver serviços agendados
- Clicar na ordem para abrir detalhes

---

## 🤖 Bot Telegram

**Comandos:**
- `/menu` - Menu principal
- `/hoje` - Serviços de hoje
- `/semana` - Agenda da semana
- `/orcamentos` - Últimos 5 orçamentos
- `/os` - Últimas 5 OS
- `/financeiro` - Resumo financeiro

**Notificações Automáticas:**
- Todo dia às 07h - lembrete de serviços do dia
- Orçamento finalizado - recebe resumo + PDF
- OS finalizada - recebe resumo + PDF

---

## 🌐 Modo Offline

**Sem internet?**
- Criar orçamento normalmente
- Clicar "⚡ Finalizar e Enviar"
- Sistema salva no celular (rascunho)
- Quando voltar internet - sincroniza automaticamente
- PDF é gerado e enviado

---

## 📊 Relatório de Serviço (OS)

1. Acessar a OS
2. Clicar "📄 Relatório"
3. Preencher blocos:
   - Descrição Detalhada
   - Peças Utilizadas
   - Peças Substituídas
   - Normas Técnicas
   - + adicionar blocos customizados
4. Adicionar fotos
5. Assinar (cliente + técnico)
6. Clicar "⚡ Gerar relatório e enviar"

**Resultado:**
- PDF com relatório técnico completo
- Enviado para Telegram
- Salvo no sistema

---

## 🔧 Troubleshooting

### App não carrega
- Verificar internet
- Tentar atualizar página (F5)
- Limpar cache do navegador

### PDF não gerou
- Verificar console (F12) para erros
- Tentar novamente
- Se persistir, contactar Vitor

### Bot Telegram não responde
- Verificar se bot está ativo
- Usar comandos: `/menu`, `/hoje`
- Se não responder, contactar Vitor

---

## 📞 Suporte

**Desenvolvedor:** Vitor Braga
**Projeto:** AVS Soluções Elétricas
**Repositório:** https://github.com/vitorbraga88/AVS_Adriano

**Documentação completa:**
- `README.md` - Setup técnico
- `GUIA_TESTES.md` - Testes completos
- `CHECKLIST_ENTREGA.md` - Checklist de entrega
- `prompt_servidor.md` - Prompt do servidor (omp clone)

---

## ✅ Checklist Diário

### Manhã
- [ ] Abrir agenda - ver serviços do dia
- [ ] Iniciar bot Telegram - `/hoje`
- [ ] Ver orçamentos pendentes

### Durante o Dia
- [ ] Criar orçamentos para novos clientes
- [ ] Gerar OS para orçamentos aprovados
- [ ] Executar serviços
- [ ] Lançar custos das OS
- [ ] Marcar OS como recebidas

### Noite
- [ ] Ver financeiro - lucro do dia
- [ ] Ver agenda do dia seguinte
- [ ] Lançar despesas do dia

---

## 🎓 Dicas

### Orçamentos
- **Reutilizar equipamentos:** Se o cliente já tem equipamento cadastrado, selecione no seletor - não cria duplicata
- **Descontos:** Aplicar antes de finalizar
- **Fotos:** Adicione fotos do equipamento/problema para documentação

### OS
- **Blocos customizados:** Adicione seções específicas do serviço (ex: "Recomendações", "Riscos", "Próximos Passos")
- **Custos:** Lance todos os custos (material, peças, transporte) para cálculo correto do lucro

### Financeiro
- **Lucro = Receita - Custos - Despesas**
- **Margem = Lucro / Receita × 100%**
- **Despesas:** Lançar separadamente (transporte, combustível, alimentação, etc)

---

## 🚀 Próximos Passos

1. **Acessar o sistema** - https://servidor-203.tail43f430.ts.net/avs/orcamentos
2. **Criar primeiro orçamento** - teste completo
3. **Gerar primeira OS** - workflow completo
4. **Ver financeiro** - entender números
5. **Usar bot Telegram** - comandos básicos

---

**Sistema 100% funcional! 🎉**

Qualquer dúvida, contactar Vitor.

**Boa sorte! 💪**
