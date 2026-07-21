/* AVS.Offline — rascunhos offline (IndexedDB) + sync ao reconectar */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  var DB_NAME = "avs-drafts", STORE = "drafts", VERSION = 1;

  function openDB() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, VERSION);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function tx(mode, fn) {
    return openDB().then(function (db) {
      return new Promise(function (resolve, reject) {
        var t = db.transaction(STORE, mode);
        var store = t.objectStore(STORE);
        var out = fn(store);
        t.oncomplete = function () { resolve(out && out.result !== undefined ? out.result : out); };
        t.onerror = function () { reject(t.error); };
      });
    });
  }

  function saveDraft(tipo, endpoint, payload) {
    return tx("readwrite", function (s) {
      return s.add({ tipo: tipo, endpoint: endpoint, payload: payload, created: Date.now() });
    });
  }

  function getDrafts() {
    return tx("readonly", function (s) { return s.getAll(); }).then(function (r) {
      return Array.isArray(r) ? r : (r && r.result) || [];
    });
  }

  function removeDraft(id) {
    return tx("readwrite", function (s) { return s.delete(id); });
  }

  // Reenvia todos os rascunhos pendentes. Remove os que entregarem com sucesso.
  function syncPendingDrafts() {
    return getDrafts().then(function (drafts) {
      if (!drafts.length) return 0;
      var done = 0;
      return drafts.reduce(function (chain, d) {
        return chain.then(function () {
          return fetch(d.endpoint, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(d.payload),
          }).then(function (r) {
            if (r.ok) { done++; return removeDraft(d.id); }
          }).catch(function () { /* segue offline */ });
        });
      }, Promise.resolve()).then(function () {
        if (done) AVS.UI && AVS.UI.toast(done + " rascunho(s) sincronizado(s)");
        return done;
      });
    });
  }

  function monitorConnectivity() {
    window.addEventListener("online", function () {
      AVS.UI && AVS.UI.toast("Conexão restabelecida — sincronizando…");
      syncPendingDrafts();
    });
    if (navigator.onLine) { syncPendingDrafts(); }
  }

  AVS.Offline = {
    saveDraft: saveDraft, getDrafts: getDrafts, removeDraft: removeDraft,
    syncPendingDrafts: syncPendingDrafts, monitorConnectivity: monitorConnectivity,
  };
})(window.AVS);
