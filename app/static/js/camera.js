/* AVS.Camera — captura (câmera/galeria) + compressão para base64 + grid */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  var MAX_DIM = 1280, QUALITY = 0.7;

  function compress(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var img = new Image();
        img.onload = function () {
          var w = img.width, h = img.height;
          if (w > h && w > MAX_DIM) { h = Math.round(h * MAX_DIM / w); w = MAX_DIM; }
          else if (h >= w && h > MAX_DIM) { w = Math.round(w * MAX_DIM / h); h = MAX_DIM; }
          var c = document.createElement("canvas");
          c.width = w; c.height = h;
          c.getContext("2d").drawImage(img, 0, 0, w, h);
          resolve(c.toDataURL("image/jpeg", QUALITY));
        };
        img.onerror = reject;
        img.src = reader.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function Controller(input, grid) {
    this.grid = grid;
    this.photos = []; // [{data, legenda}]
    var self = this;
    input.addEventListener("change", function (e) {
      var files = Array.prototype.slice.call(e.target.files || []);
      Promise.all(files.map(compress)).then(function (datas) {
        datas.forEach(function (d) { self.photos.push({ data: d, legenda: "" }); });
        self.render();
        input.value = "";
      }).catch(function () { AVS.UI && AVS.UI.toast("Falha ao processar foto", true); });
    });
  }

  Controller.prototype.render = function () {
    var self = this;
    this.grid.innerHTML = "";
    this.photos.forEach(function (p, i) {
      var fig = document.createElement("figure");
      var img = document.createElement("img");
      img.src = p.data;
      var cap = document.createElement("input");
      cap.type = "text"; cap.placeholder = "Legenda"; cap.value = p.legenda || "";
      cap.addEventListener("input", function () { self.photos[i].legenda = cap.value; });
      var rm = document.createElement("button");
      rm.type = "button"; rm.className = "btn danger sm rm"; rm.textContent = "×";
      rm.addEventListener("click", function () { self.photos.splice(i, 1); self.render(); });
      fig.appendChild(img); fig.appendChild(rm); fig.appendChild(cap);
      self.grid.appendChild(fig);
    });
  };

  Controller.prototype.getPhotos = function () { return this.photos.slice(); };
  Controller.prototype.setPhotos = function (arr) { this.photos = (arr || []).slice(); this.render(); };
  Controller.prototype.clear = function () { this.photos = []; this.render(); };

  function create(input, grid) { return new Controller(input, grid); }

  AVS.Camera = { create: create, compress: compress };
})(window.AVS);
