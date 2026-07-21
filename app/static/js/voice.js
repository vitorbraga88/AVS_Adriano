/* AVS.Voice — ditado por voz (Web Speech API pt-BR) para textareas */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  function supported() { return !!SR; }

  // btn: elemento clicável; target: <textarea>/<input> a receber o texto
  function attach(btn, target) {
    if (!btn || !target) return;
    if (!supported()) { btn.style.display = "none"; return; }
    var rec = new SR();
    rec.lang = "pt-BR"; rec.continuous = true; rec.interimResults = false;
    var ativo = false, base = "";

    rec.onresult = function (e) {
      var txt = "";
      for (var i = e.resultIndex; i < e.results.length; i++) {
        txt += e.results[i][0].transcript;
      }
      target.value = (base ? base + " " : "") + txt;
      target.dispatchEvent(new Event("input"));
    };
    rec.onend = function () { if (ativo) { try { rec.start(); } catch (x) {} } };
    rec.onerror = function () { stop(); };

    function start() {
      base = target.value.trim();
      ativo = true; btn.classList.add("sec"); btn.setAttribute("aria-pressed", "true");
      btn.textContent = "■ Parar";
      try { rec.start(); } catch (x) {}
    }
    function stop() {
      ativo = false; btn.classList.remove("sec"); btn.removeAttribute("aria-pressed");
      btn.textContent = "🎤 Voz";
      try { rec.stop(); } catch (x) {}
    }
    btn.addEventListener("click", function (e) { e.preventDefault(); ativo ? stop() : start(); });
  }

  AVS.Voice = { attach: attach, supported: supported };
})(window.AVS);
