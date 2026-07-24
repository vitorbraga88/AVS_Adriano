/* AVS.OS — controlador do relatório de OS (blocos "container" dinâmicos) */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";
  var UI = AVS.UI;

  var ordem, blocosEl, cam, padCli, padTec;
  var SEED = [
    "Descrição Detalhada do Serviço",
    "Peças Utilizadas",
    "Peças Substituídas",
    "Normas Técnicas Aplicadas",
  ];

  function el(id) { return document.getElementById(id); }

  function addBloco(titulo, conteudo) {
    var card = document.createElement("div");
    card.className = "bloco";
    card.innerHTML =
      "<div class='bhead'>" +
      "<input class='b-tit' placeholder='Título do bloco'>" +
      "<button type='button' class='btn sec sm b-voz'>🎤 Voz</button>" +
      "<button type='button' class='btn danger sm b-rm'>×</button></div>" +
      "<textarea class='b-cont' placeholder='Conteúdo…'></textarea>";
    blocosEl.appendChild(card);
    card.querySelector(".b-tit").value = titulo || "";
    card.querySelector(".b-cont").value = conteudo || "";
    card.querySelector(".b-rm").addEventListener("click", function () { card.remove(); });
    AVS.Voice.attach(card.querySelector(".b-voz"), card.querySelector(".b-cont"));
    return card;
  }

  function coletarBlocos() {
    var out = [];
    blocosEl.querySelectorAll(".bloco").forEach(function (c) {
      out.push({
        titulo: c.querySelector(".b-tit").value.trim(),
        conteudo: c.querySelector(".b-cont").value.trim(),
      });
    });
    return out;
  }

  function coletarDados() {
    return {
      ordem_id: ordem.id,
      numero: ordem.numero,
      titulo: ordem.titulo,
      cliente: ordem.cliente,
      equipamento: ordem.equipamento,
      tecnico: el("f-tecnico").value.trim(),
      data_txt: new Date().toLocaleDateString("pt-BR"),
      blocos: coletarBlocos(),
      fotos: cam.getPhotos(),
      assinaturas: { cliente: padCli.toDataURL(), tecnico: padTec.toDataURL() },
    };
  }

  function finalizar() {
    var btn = el("btn-finalizar");
    var dados = coletarDados();
    var preenchidos = dados.blocos.filter(function (b) { return b.conteudo; });
    if (!preenchidos.length) { UI.toast("Preencha ao menos um bloco", true); return; }

    btn.disabled = true; btn.textContent = "Enviando…";
    if (dados.assinaturas.cliente && dados.cliente && dados.cliente.nome)
      AVS.Signature.saveMemory(dados.cliente.nome, dados.assinaturas.cliente);
    if (dados.assinaturas.tecnico && dados.tecnico)
      AVS.Signature.saveMemory(dados.tecnico, dados.assinaturas.tecnico);

    var payload = {
      ordem_id: ordem.id,
      tecnico: dados.tecnico,
      blocos: dados.blocos,
      fotos: dados.fotos,
      assinaturas: dados.assinaturas,
    };
    fetch("api/os/finalizar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function () {
      UI.toast("Relatório enviado ⚡");
      setTimeout(function () { window.location = "os/" + ordem.id; }, 900);
    }).catch(function () {
      AVS.Offline.saveDraft("os", "api/os/finalizar", payload).then(function () {
        UI.toast("Sem conexão — salvo como rascunho", true);
        btn.disabled = false; btn.textContent = "⚡ Gerar relatório e enviar";
      });
    });
  }

  function init() {
    ordem = JSON.parse(el("ordem-data").textContent);
    blocosEl = el("blocos");
    SEED.forEach(function (t) { addBloco(t, ""); });
    el("btn-add-bloco").addEventListener("click", function () { addBloco("", ""); });

    cam = AVS.Camera.create(el("foto-input"), el("foto-grid"));
    padCli = new AVS.Signature.Pad(el("sig-cliente"));
    padTec = new AVS.Signature.Pad(el("sig-tecnico"));
    el("clear-cliente").addEventListener("click", function () { padCli.clear(); });
    el("clear-tecnico").addEventListener("click", function () { padTec.clear(); });
    el("f-tecnico").addEventListener("change", function () {
      var nome = this.value.trim();
      if (!nome) return;
      fetch("api/assinatura?nome=" + encodeURIComponent(nome))
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (d && d.data_url && padTec.isEmpty()) padTec.load(d.data_url); })
        .catch(function () {});
    });

    AVS.Offline.monitorConnectivity();
    el("btn-finalizar").addEventListener("click", finalizar);
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);

  AVS.OS = { coletarDados: coletarDados };
})(window.AVS);
