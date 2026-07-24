/* AVS.Orcamento — controlador do formulário de orçamento de campo */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";
  var UI = AVS.UI;

  var itensEl, totalEl, descEl, cam, pad, camposCliente = {};

  function el(id) { return document.getElementById(id); }

  function addItem(data) {
    data = data || {};
    var row = document.createElement("div");
    row.className = "item-row";
    row.innerHTML =
      "<div><label>Descrição</label><input class='it-desc'></div>" +
      "<div><label>Qtd</label><input class='it-qtd' inputmode='decimal' value='1'></div>" +
      "<div><label>Un</label><input class='it-un' value='un'></div>" +
      "<div><label>Preço</label><input class='it-preco' inputmode='decimal' placeholder='0,00'></div>" +
      "<div><label>&nbsp;</label><button type='button' class='btn danger sm it-rm'>×</button></div>";
    itensEl.appendChild(row);
    if (data.descricao) row.querySelector(".it-desc").value = data.descricao;
    row.querySelector(".it-rm").addEventListener("click", function () { row.remove(); recalc(); });
    row.querySelectorAll("input").forEach(function (i) {
      i.addEventListener("input", recalc);
    });
    recalc();
  }

  function coletarItens() {
    var out = [];
    itensEl.querySelectorAll(".item-row").forEach(function (row) {
      var desc = row.querySelector(".it-desc").value.trim();
      if (!desc) return;
      var qtd = parseFloat(String(row.querySelector(".it-qtd").value).replace(",", ".")) || 1;
      out.push({
        descricao: desc,
        quantidade: Math.round(qtd),
        unidade: row.querySelector(".it-un").value.trim() || "un",
        preco_centavos: UI.parseMoneyToCentavos(row.querySelector(".it-preco").value),
      });
    });
    return out;
  }

  function recalc() {
    var itens = coletarItens();
    var bruto = itens.reduce(function (s, it) { return s + it.preco_centavos * it.quantidade; }, 0);
    var desc = parseFloat(String(descEl.value).replace(",", ".")) || 0;
    var total = Math.round(bruto * (1 - desc / 100));
    totalEl.textContent = UI.brlFromCentavos(total);
    return total;
  }

  function coletarEquipamento() {
    var box = el("eq-box");
    if (box.hidden) return null;
    var sel = el("eq-select");
    if (sel.value) return { id: parseInt(sel.value, 10) };
    var eq = {
      descricao: el("eq-descricao").value.trim(),
      marca: el("eq-marca").value.trim(),
      modelo: el("eq-modelo").value.trim(),
      numero_serie: el("eq-serie").value.trim(),
      patrimonio: el("eq-patrimonio").value.trim(),
    };
    var has = Object.keys(eq).some(function (k) { return eq[k]; });
    return has ? eq : null;
  }

  function validadeTxt() {
    var d = new Date(); d.setDate(d.getDate() + 7);
    var p = function (n) { return String(n).padStart(2, "0"); };
    return p(d.getDate()) + "/" + p(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function coletarDados() {
    return {
      cliente: {
        nome: el("f-nome").value.trim(),
        telefone: el("f-telefone").value.trim(),
        endereco: el("f-endereco").value.trim(),
      },
      equipamento: coletarEquipamento(),
      tipo: el("f-tipo").value || null,
      prioridade: el("f-prioridade").value || "normal",
      titulo: el("f-titulo").value.trim(),
      local_servico: el("f-local").value.trim(),
      itens: coletarItens(),
      desconto_pct: parseFloat(String(descEl.value).replace(",", ".")) || 0,
      observacoes: el("f-observacoes").value.trim(),
      validade_txt: validadeTxt(),
      fotos: cam.getPhotos(),
      assinatura: pad.toDataURL(),
    };
  }

  function carregarEquipamentos(clienteId) {
    var sel = el("eq-select");
    sel.innerHTML = "<option value=''>— novo equipamento —</option>";
    if (!clienteId) return;
    fetch("api/equipamentos?cliente_id=" + encodeURIComponent(clienteId))
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        list.forEach(function (e) {
          var o = document.createElement("option");
          o.value = e.id;
          o.textContent = (e.descricao || "Equipamento") +
            (e.marca ? " — " + e.marca : "") + (e.modelo ? " " + e.modelo : "");
          o.dataset.eq = JSON.stringify(e);
          sel.appendChild(o);
        });
      }).catch(function () {});
  }

  function bindClienteAutocomplete() {
    var nome = el("f-nome"), dl = el("dl-clientes");
    var cache = {};
    nome.addEventListener("input", function () {
      var q = nome.value.trim();
      // se casar exatamente com um cliente conhecido, preenche
      if (cache[q]) {
        var c = cache[q];
        el("f-cliente-id").value = c.id;
        if (c.telefone && !el("f-telefone").value) el("f-telefone").value = c.telefone;
        if (c.endereco && !el("f-endereco").value) el("f-endereco").value = c.endereco;
        carregarEquipamentos(c.id);
        return;
      }
      el("f-cliente-id").value = "";
      if (q.length < 2) return;
      fetch("api/clientes?q=" + encodeURIComponent(q))
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (list) {
          dl.innerHTML = "";
          list.forEach(function (c) {
            cache[c.nome] = c;
            var o = document.createElement("option");
            o.value = c.nome;
            dl.appendChild(o);
          });
        }).catch(function () {});
    });
  }

  function finalizar() {
    var btn = el("btn-finalizar");
    if (!AVS.Validation.check([
      { sel: "#f-nome", msg: "Informe o nome do cliente" },
    ])) return;
    var dados = coletarDados();
    if (!dados.itens.length) { UI.toast("Adicione ao menos um item", true); return; }

    btn.disabled = true; btn.textContent = "Enviando…";
    if (dados.assinatura && dados.cliente.nome) {
      AVS.Signature.saveMemory(dados.cliente.nome, dados.assinatura);
    }
    fetch("api/orcamentos/finalizar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (res) {
      UI.toast("Orçamento " + (res.numero || "") + " enviado ⚡");
      setTimeout(function () { window.location = "orcamentos/" + res.ordem_id; }, 900);
    }).catch(function () {
      AVS.Offline.saveDraft("orcamento", "api/orcamentos/finalizar", dados).then(function () {
        UI.toast("Sem conexão — salvo como rascunho, será enviado ao reconectar", true);
        btn.disabled = false; btn.textContent = "⚡ Finalizar e enviar";
      });
    });
  }

  function init() {
    itensEl = el("itens"); totalEl = el("total"); descEl = el("f-desconto");
    el("validade").textContent = validadeTxt();
    addItem();
    el("btn-add-item").addEventListener("click", function () { addItem(); });
    descEl.addEventListener("input", recalc);

    el("eq-toggle").addEventListener("click", function () {
      var box = el("eq-box");
      box.hidden = !box.hidden;
      this.textContent = box.hidden ? "Adicionar equipamento" : "Ocultar equipamento";
    });
    el("eq-select").addEventListener("change", function () {
      var opt = this.selectedOptions[0];
      if (opt && opt.dataset.eq) {
        var e = JSON.parse(opt.dataset.eq);
        el("eq-descricao").value = e.descricao || "";
        el("eq-marca").value = e.marca || "";
        el("eq-modelo").value = e.modelo || "";
        el("eq-serie").value = e.numero_serie || "";
        el("eq-patrimonio").value = e.patrimonio || "";
      }
    });

    cam = AVS.Camera.create(el("foto-input"), el("foto-grid"));
    pad = AVS.Signature.attach(el("sigpad"), el("f-nome"));
    el("sig-clear").addEventListener("click", function () { pad.clear(); });
    AVS.Voice.attach(el("voz-obs"), el("f-observacoes"));
    bindClienteAutocomplete();
    AVS.Offline.monitorConnectivity();
    el("btn-finalizar").addEventListener("click", finalizar);
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);

  AVS.Orcamento = { coletarDados: coletarDados };
})(window.AVS);
