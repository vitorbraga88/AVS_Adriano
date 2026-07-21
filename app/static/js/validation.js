/* AVS.Validation — validação de campos obrigatórios */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  // regras: [{sel, msg, test?}] onde test(valorTrim) -> bool (default: não vazio)
  function check(rules) {
    for (var i = 0; i < rules.length; i++) {
      var r = rules[i];
      var el = typeof r.sel === "string" ? document.querySelector(r.sel) : r.sel;
      var val = el ? String(el.value || "").trim() : "";
      var ok = r.test ? r.test(val, el) : val.length > 0;
      if (!ok) {
        if (el && el.focus) el.focus();
        AVS.UI && AVS.UI.toast(r.msg, true);
        return false;
      }
    }
    return true;
  }

  AVS.Validation = { check: check };
})(window.AVS);
