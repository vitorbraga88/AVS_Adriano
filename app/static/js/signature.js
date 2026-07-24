/* AVS.Signature — pads de assinatura em canvas + memória por nome (sync API) */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  function Pad(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this._drawn = false;
    this._resize();
    this._bind();
  }

  Pad.prototype._resize = function () {
    var dpr = window.devicePixelRatio || 1;
    var rect = this.canvas.getBoundingClientRect();
    var w = rect.width || 300, h = rect.height || 160;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.ctx.lineWidth = 2.2;
    this.ctx.lineCap = "round";
    this.ctx.lineJoin = "round";
    this.ctx.strokeStyle = "#111";
  };

  Pad.prototype._pos = function (e) {
    var rect = this.canvas.getBoundingClientRect();
    var t = e.touches ? e.touches[0] : e;
    return { x: t.clientX - rect.left, y: t.clientY - rect.top };
  };

  Pad.prototype._bind = function () {
    var self = this, drawing = false, last = null;
    var start = function (e) { drawing = true; last = self._pos(e); e.preventDefault(); };
    var move = function (e) {
      if (!drawing) return;
      var p = self._pos(e);
      self.ctx.beginPath();
      self.ctx.moveTo(last.x, last.y);
      self.ctx.lineTo(p.x, p.y);
      self.ctx.stroke();
      last = p; self._drawn = true; e.preventDefault();
    };
    var end = function () { drawing = false; last = null; };
    this.canvas.addEventListener("pointerdown", start);
    this.canvas.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
  };

  Pad.prototype.clear = function () {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this._drawn = false;
  };
  Pad.prototype.isEmpty = function () { return !this._drawn; };
  Pad.prototype.toDataURL = function () { return this._drawn ? this.canvas.toDataURL("image/png") : null; };
  Pad.prototype.load = function (dataUrl) {
    if (!dataUrl) return;
    var img = new Image(), self = this;
    img.onload = function () {
      var rect = self.canvas.getBoundingClientRect();
      self.ctx.drawImage(img, 0, 0, rect.width || 300, rect.height || 160);
      self._drawn = true;
    };
    img.src = dataUrl;
  };

  // Vincula um pad a um <input> de nome: ao sair do campo, carrega assinatura
  // salva; ao salvar o form, o chamador chama saveMemory(nome, dataUrl).
  function attach(canvas, nomeInput) {
    var pad = new Pad(canvas);
    if (nomeInput) {
      nomeInput.addEventListener("change", function () {
        var nome = nomeInput.value.trim();
        if (!nome) return;
        fetch("api/assinatura?nome=" + encodeURIComponent(nome))
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) { if (d && d.data_url && pad.isEmpty()) pad.load(d.data_url); })
          .catch(function () {});
      });
    }
    return pad;
  }

  function saveMemory(nome, dataUrl) {
    if (!nome || !dataUrl) return Promise.resolve();
    return fetch("api/assinatura", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: nome, data_url: dataUrl }),
    }).catch(function () {});
  }

  AVS.Signature = { Pad: Pad, attach: attach, saveMemory: saveMemory };
})(window.AVS);
