/* AVS.OsNovo — controlador do formulário "Gerar Relatório de Serviço" (OS
   direta, sem orçamento prévio). */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";
  var UI = AVS.UI;

  function el(id) { return document.getElementById(id); }

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
      data_servico: el("f-data-servico").value || null,
    };
  }

  function carregarEquipamentos(clienteId) {
    var sel = el("eq-select");
    sel.innerHTML = "<option value=''>— novo equipamento —</option>";
    if (!clienteId) return;
    fetch("/api/equipamentos?cliente_id=" + encodeURIComponent(clienteId))
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
      fetch("/api/clientes?q=" + encodeURIComponent(q))
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

  function criar() {
    var btn = el("btn-criar");
    if (!AVS.Validation.check([
      { sel: "#f-nome", msg: "Informe o nome do cliente" },
    ])) return;
    var dados = coletarDados();
    btn.disabled = true; btn.textContent = "Gerando…";
    fetch("/api/os/criar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (res) {
      UI.toast("OS " + (res.numero || "") + " criada ⚡");
      window.location = "/os/" + res.ordem_id + "/relatorio";
    }).catch(function (e) {
      UI.toast("Falha ao criar OS: " + e.message, true);
      btn.disabled = false; btn.textContent = "⚡ Gerar relatório de serviço";
    });
  }

  function init() {
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
    bindClienteAutocomplete();
    el("btn-criar").addEventListener("click", criar);
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);

  AVS.OsNovo = { coletarDados: coletarDados };
})(window.AVS);
