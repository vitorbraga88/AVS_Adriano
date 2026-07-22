# Prompt — Remodelagem dos documentos do AVS Admin

**Antes de colar:** copie para a raiz do repositório os arquivos `avs-documentos.html`, `logo-avs-512.png` e `logo-avs-256.png`. Depois cole o prompt abaixo no Claude Code.

---

Preciso remodelar os dois documentos PDF gerados por este app (Orçamento e Relatório de Serviço/OS) usando o arquivo `avs-documentos.html` na raiz do repo como **referência canônica de layout**. Ele contém o design system completo ("Voltage" — preto #141414 + amarelo #F5A81C), os dois documentos prontos com dados de exemplo, e o JavaScript de referência para fotos e cálculo. Abra e estude esse arquivo antes de escrever qualquer código.

## Contexto

- O app gera dois documentos: Orçamento (enviado ao dono via n8n/Telegram) e Relatório de Serviço (OS), que herda o número do orçamento (formato `ORC-AAAAMMDD-NNN`).
- Antes de mudar qualquer coisa, **identifique como o PDF é gerado hoje** (impressão client-side via `window.print`, biblioteca JS, ou renderização no backend) e **adapte o layout ao mecanismo existente** — não troque o mecanismo.
- Dinheiro é sempre inteiro em centavos no backend; formatação pt-BR (`R$ 1.234,56`) só na camada de apresentação. Datas em `dd/mm/aaaa`, timezone `America/Recife`.

## Tarefas

1. **Assets e tokens.** Mova `logo-avs-512.png` e `logo-avs-256.png` para o diretório de estáticos do app. Extraia o CSS do arquivo de referência para um stylesheet próprio dos documentos (não misture com o CSS da UI administrativa, que segue tema escuro próprio). As fontes são Archivo Black, Barlow Condensed e Barlow via Google Fonts; se o PDF for gerado sem internet, baixe os `.woff2` e sirva localmente com `@font-face`.

2. **Template do Orçamento** (Jinja2). Reproduza fielmente a estrutura da referência: cabeçalho escuro com logo, eyebrow, título, dois badges (nº e data de emissão) e o filete zigue-zague; grade de metadados (cliente, telefone, tipo, endereço, local, validade); tabela de itens com cabeçalho preto; bloco de totais com subtotal, desconto percentual e o card TOTAL amarelo com sombra dura; observações. Variáveis vindas do modelo existente — não altere o modelo de dados além do necessário.

3. **Template do Relatório de Serviço** (Jinja2). Mesma estrutura de cabeçalho (badge "OS — ref. orçamento"); metadados com pill de status; seções: descrição do serviço executado, peças utilizadas e substituídas lado a lado, normas técnicas, **relatório fotográfico**, assinaturas.

4. **Fluxo de fotos na OS.** No formulário de campo, adicione upload múltiplo de imagens com: compressão client-side em canvas (lado maior ≤ 1600 px, JPEG qualidade 0,82 — o padrão já está no JS da referência), legenda editável com valor inicial = nome do arquivo sem extensão, remoção individual e renumeração automática (`01`, `02`…). Persistência: siga o padrão de armazenamento de imagens que o app já usa; se não houver, armazene os JPEG comprimidos em disco com referência no banco (caminho + legenda + ordem).

5. **Rodapé institucional em todas as páginas do PDF.** O rodapé da referência (33 mm: zigue-zague, escudo + lettering, pill de WhatsApp, linha de serviços, quatro pilares com ícones) deve se repetir na base de **cada** página. No mecanismo de impressão client-side isso é `position: fixed; bottom: 0` dentro de `@media print`, com `padding-bottom: 39mm` no corpo — já implementado na referência.

## Regras de layout obrigatórias

1. Grid de fotos em 2 colunas; cada card de foto tem chip numerado + legenda e **nunca quebra entre páginas** (`break-inside: avoid`).
2. Se a OS não tiver fotos, a seção "Relatório fotográfico" é omitida do PDF por completo.
3. Assinaturas (Cliente e Técnico) vêm **abaixo** do relatório fotográfico, nunca antes.
4. O total do orçamento é o único elemento com fundo amarelo sólido do documento — mantenha o restante disciplinado.
5. Texto revisado por IA (OpenRouter) entra no documento sem nenhuma menção a IA.
6. Nome oficial em todos os documentos: **"AVS Soluções Elétricas"** (plural). Telefones: (81) 9.9352-4445 e (81) 9.9185-4055.
7. Nome do arquivo PDF: `<Tipo> - <Cliente> - <dd_mm_aa>` (ex.: `Orçamento - Marcos Andrade - 21_07_26`). Na geração client-side, defina `document.title` antes do print — a função `updateTitle()` da referência mostra como.
8. Impressão em A4, margens zero, full-bleed (cabeçalho e rodapé encostam nas bordas).

## Critérios de aceite

- Gerar um orçamento e uma OS reais e comparar lado a lado com `avs-documentos.html` impresso: tipografia, cores, espaçamentos e rodapé devem bater.
- OS com 5 fotos: grid distribui sem cortar cards entre páginas, numeração `01`–`05`, contador "05 registros" no título da seção, rodapé presente em todas as páginas.
- Orçamento com desconto 10% sobre R$ 421,00 exibe total R$ 378,90 (arredondamento em centavos).
- Nenhuma rota, modelo ou dependência nova além do estritamente necessário; sem libs pesadas de PDF se o mecanismo atual for print client-side.

Se os templates atuais estiverem em local não óbvio ou o mecanismo de PDF for ambíguo, me pergunte antes de refatorar.
