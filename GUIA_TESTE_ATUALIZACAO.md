# Guia de Teste — Atualização de 24/07/2026

Passo a passo pra você (Adriano) conferir as 7 melhorias na sua própria mão.
O banco está **vazio** (limpo na Tarefa 2) — use dados fictícios ("Cliente
Teste", etc.) à vontade, dá pra apagar depois com o botão "Apagar" novo.

---

## 0. Subir o sistema

No terminal, dentro da pasta do projeto:

```bash
cd /opt/data/projetos/avs-adriano-repo
source venv/bin/activate
ADMIN_PASSWORD=teste uvicorn app.main:app --reload --host 0.0.0.0 --port 8099
```

Abra `http://127.0.0.1:8099/` no navegador (ou o IP da máquina, se for testar
do celular na mesma rede). Login HTTP Basic:
- usuário: `admin`
- senha: `teste`

Se já estiver publicado em produção, use a URL de sempre — os passos abaixo
são os mesmos, só muda o endereço.

---

## 1. Visual novo (preto + amarelo)

1. Abra qualquer página (ex.: Dashboard).
2. Confira: fundo bem preto, botões e destaques em amarelo/laranja
   (`#F5A81C`), títulos em fonte grossa tipo cartaz (Archivo Black).
3. No topo, o nome deve estar por extenso: **"AVS Soluções Elétricas"**
   (não mais só "AVS Elétrica").
4. Role até o final de qualquer página → tem que aparecer um rodapé com o
   nome da empresa e os dois telefones: `(81) 9.9352-4445` e
   `(81) 9.9185-4055`.
5. Gere um PDF (orçamento ou OS, veja passo 2/3) e confira que os telefones
   também aparecem no cabeçalho do PDF, embaixo do nome da empresa.

**Passou se:** cores, fonte, nome completo e telefones aparecem em todas as
páginas e no PDF.

---

## 2. Assinatura padrão da empresa (orçamento)

1. Vá em **Orçamentos → Novo orçamento**.
2. Role até o final — agora tem **dois** quadros de assinatura lado a lado:
   "Assinatura do cliente" e "Assinatura da empresa".
3. O campo "Assinante" da empresa já vem preenchido com **"AVS - Elétrica"**
   — pode editar esse nome se quiser assinar como outra pessoa.
4. Assine nos dois campos (cliente e empresa), preencha o resto do
   orçamento e finalize.
5. Abra o PDF gerado → as duas assinaturas devem aparecer lado a lado.
6. Crie um **segundo** orçamento qualquer → o campo "Assinante" já deve
   carregar sozinho a assinatura da empresa que você desenhou no passo 4
   (fica salva por nome, não precisa desenhar de novo toda vez).

**Passou se:** assinatura da empresa tem nome padrão editável, aparece no
PDF, e fica lembrada entre orçamentos diferentes.

---

## 3. Relatório de Serviço sem orçamento

Pra quando o serviço é feito sem passar pela etapa de orçamento (ex.:
urgência, garantia, cortesia).

1. Vá em **OS** (menu de cima) → clique no botão flutuante amarelo
   **"⚡ Gerar Relatório de Serviço"** (canto inferior direito).
2. Preencha só o cliente (e equipamento, se quiser) + dados do serviço —
   repare que **não tem itens nem preço** nessa tela, é só abertura rápida.
3. Clique em **"⚡ Gerar relatório de serviço"**.
4. Você cai direto na tela de relatório da OS (a mesma de sempre: blocos de
   texto, fotos, assinaturas). Preencha e finalize normalmente.
5. Confira em **OS** (lista) → a nova OS aparece com número começando em
   `OS-` (diferente do `ORC-` do fluxo de orçamento, pra você saber que
   essa não teve orçamento prévio).

**Passou se:** dá pra abrir uma OS sem passar por orçamento nenhum, e ela
aparece normal na lista de OS e na agenda.

---

## 4. Fotos — câmera/galeria, legenda, remover, numeração

1. Em qualquer formulário com fotos (orçamento ou relatório de OS), clique
   em "Escolher arquivo" — no celular deve abrir a opção de usar a câmera
   ou a galeria.
2. Adicione 2 ou 3 fotos.
3. Confira: cada foto ganha um **número amarelo** no canto (1, 2, 3...).
4. Digite uma legenda embaixo de uma foto — o texto deve ficar salvo.
5. Clique no "×" pra remover a foto do meio → as fotos que sobraram devem
   **renumerar sozinhas** (ex.: se tinha 1, 2, 3 e você apaga a 2, sobra 1
   e 2 — não fica "1, 3").
6. Finalize e confira o PDF: as fotos e legendas aparecem certinho.

**Passou se:** numeração aparece, legenda funciona, remover uma foto
renumera as outras automaticamente.

---

## 5. Agenda — Cancelar e Apagar

### No Kanban (`/agenda`)
1. Abra qualquer card de orçamento/OS que não esteja "Recebido".
2. Deve ter um botão **"Cancelar"** (vermelho) — usa quando o cliente
   desistiu. Clique e confira que o status muda pra "Cancelado".
3. Todo card (inclusive os já cancelados/recebidos) tem um botão
   **"Apagar"** (vermelho, borda) — clique e confirme a caixa de aviso.
   O card some da lista.

### No Calendário (`/agenda/calendario`)
1. Cada evento do dia mostra dois botõezinhos: **Cancelar** (só aparece se
   o status permitir) e **Apagar** (sempre aparece).
2. Testar igual ao Kanban: Cancelar muda status, Apagar remove de vez
   (com confirmação antes).

### Proteção importante
- Tente apagar uma ordem que já está **"Recebido"** (já virou receita no
  financeiro) → o sistema **bloqueia** e mostra uma mensagem de erro. Isso
  é proposital: depois que já entrou dinheiro, apagar sem mais nem menos
  bagunçaria o financeiro. Se precisar corrigir uma dessas, me avisa.

**Passou se:** Cancelar muda status, Apagar remove com confirmação, e
apagar uma ordem "Recebido" é bloqueado com aviso.

---

## 6. Despesas — categorias fixas

1. Vá em **Despesas → Nova despesa**.
2. Abra o menu "Categoria" — deve ter exatamente estas 5 opções:
   **Combustível, Fardamento, Ferramentas, Manutenção carro, Outros.**
3. Lance uma despesa em qualquer categoria e confirme que aparece na
   lista do mês.
4. Repare que despesa **não pede nenhuma ordem de serviço** — é custo
   geral da empresa (gasolina, uniforme, ferramenta, manutenção do carro),
   sem vínculo com orçamento/OS nenhum.

**Passou se:** as 5 categorias aparecem certinho e a despesa é lançada sem
pedir vínculo com OS.

---

## 7. Conferir que nada quebrou (o de sempre continua igual)

Rapidinho, sem precisar repetir tudo:
- Dashboard carrega com os números do mês.
- Criar cliente/equipamento novo continua funcionando.
- Orçamento com itens calcula o total certo (e desconto, se usar).
- Aprovar orçamento → vira OS → lançar custo → marcar "Recebido" → aparece
  em Financeiro.
- PDF de orçamento e de OS continuam sendo gerados e enviados.

---

## Se algo não bater

Anota exatamente: qual tela, o que você clicou, o que esperava ver e o que
apareceu. Isso agiliza demais achar o problema depois.
