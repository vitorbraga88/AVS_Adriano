/* AVS.UI — toasts e helpers globais */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  function toast(msg, isError) {
    var box = document.getElementById("toasts");
    if (!box) { (isError ? console.error : console.log)(msg); return; }
    var el = document.createElement("div");
    el.className = "toast" + (isError ? " err" : "");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(function () {
      el.style.transition = "opacity .3s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 320);
    }, isError ? 5200 : 3200);
  }

  function brlFromCentavos(c) {
    return "R$ " + (Number(c || 0) / 100).toFixed(2).replace(".", ",");
  }

  // "1.234,56" | "1234,56" | "1234.56" -> centavos inteiros
  function parseMoneyToCentavos(str) {
    if (str == null) return 0;
    var s = String(str).trim().replace(/\s|R\$/g, "");
    if (!s) return 0;
    if (s.indexOf(",") >= 0) { s = s.replace(/\./g, "").replace(",", "."); }
    var n = parseFloat(s);
    if (isNaN(n)) return 0;
    return Math.round(n * 100);
  }

  function fmtDateBR(d) {
    d = d || new Date();
    var p = function (n) { return String(n).padStart(2, "0"); };
    return p(d.getDate()) + "." + p(d.getMonth() + 1) + "." + String(d.getFullYear()).slice(-2);
  }

  AVS.UI = { toast: toast, brlFromCentavos: brlFromCentavos,
             parseMoneyToCentavos: parseMoneyToCentavos, fmtDateBR: fmtDateBR };

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }
})(window.AVS);
