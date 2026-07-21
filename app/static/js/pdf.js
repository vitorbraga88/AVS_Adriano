/* AVS.Pdf — geração de PDF no cliente (iframe offscreen -> html2canvas -> jsPDF).
   Layout A4 CLARO (documento), independente do tema escuro da UI. */
window.AVS = window.AVS || {};
(function (AVS) {
  "use strict";

  var PW = 794, PH = 1123; // A4 @ 96dpi (px)
  var BANNER = "/static/img/banner_avs.jpg";
  var LOGO = "/static/img/logo_avs.png";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function brl(c) { return "R$ " + (Number(c || 0) / 100).toFixed(2).replace(".", ","); }

  function safeName(s) { return String(s || "").replace(/[\\/\x00-\x1f]/g, "").trim(); }

  function fmtDate(d) {
    d = d || new Date();
    var p = function (n) { return String(n).padStart(2, "0"); };
    return p(d.getDate()) + "." + p(d.getMonth() + 1) + "." + String(d.getFullYear()).slice(-2);
  }

  function buildPdfFilename(tipo, cliente, numero) {
    var pref = tipo === "os" ? "OS" : "Orçamento";
    return pref + " - " + safeName(cliente || "cliente") + " - " +
           safeName(numero || "") + " " + fmtDate(new Date()) + ".pdf";
  }

  var STYLE = "" +
    "*{box-sizing:border-box;margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;}" +
    ".page{width:" + PW + "px;height:" + PH + "px;background:#fff;color:#1a1a1a;position:relative;padding:38px 40px 90px;overflow:hidden;}" +
    ".hd{display:flex;align-items:center;gap:14px;border-bottom:3px solid #FFB800;padding-bottom:12px;}" +
    ".hd img{height:54px;}" +
    ".hd .t{font-size:22px;font-weight:800;letter-spacing:-.5px;}" +
    ".hd .s{font-size:12px;color:#555;text-transform:uppercase;letter-spacing:2px;}" +
    ".doc{margin-left:auto;text-align:right;font-size:12px;color:#333;}" +
    ".doc b{font-size:15px;}" +
    "h2{font-size:13px;text-transform:uppercase;letter-spacing:1.5px;color:#8a6d00;margin:18px 0 6px;border-left:4px solid #FFB800;padding-left:8px;}" +
    ".kv{font-size:13px;line-height:1.7;}" +
    ".kv b{display:inline-block;min-width:90px;color:#555;font-weight:600;}" +
    "table{width:100%;border-collapse:collapse;margin-top:6px;font-size:13px;}" +
    "th{background:#1a1a1a;color:#fff;text-align:left;padding:7px 8px;font-size:11px;text-transform:uppercase;letter-spacing:1px;}" +
    "td{padding:7px 8px;border-bottom:1px solid #e2e2e2;}" +
    "td.n,th.n{text-align:right;}" +
    ".tot{margin-top:8px;text-align:right;font-size:14px;}" +
    ".tot .big{font-size:20px;font-weight:800;color:#1a1a1a;}" +
    ".blk{margin-top:10px;font-size:13px;line-height:1.6;}" +
    ".blk .bt{font-weight:700;color:#1a1a1a;}" +
    ".blk .bc{white-space:pre-wrap;color:#333;}" +
    ".fotos{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;}" +
    ".fotos figure{border:1px solid #ddd;}" +
    ".fotos img{width:100%;height:210px;object-fit:cover;display:block;}" +
    ".fotos figcaption{font-size:11px;padding:4px 6px;color:#555;}" +
    ".sigs{display:flex;gap:40px;margin-top:26px;}" +
    ".sig{flex:1;text-align:center;}" +
    ".sig img{height:70px;max-width:100%;object-fit:contain;}" +
    ".sig .ln{border-top:1px solid #1a1a1a;margin-top:6px;padding-top:4px;font-size:12px;color:#333;}" +
    ".banner{position:absolute;left:0;right:0;bottom:0;width:100%;}" +
    ".banner img{width:100%;display:block;}" +
    ".obs{font-size:12px;color:#444;margin-top:10px;white-space:pre-wrap;}";

  function headerHTML(titulo, numero, dataTxt) {
    return "<div class='hd'><img src='" + LOGO + "'>" +
      "<div><div class='t'>AVS Soluções Elétricas</div>" +
      "<div class='s'>" + esc(titulo) + "</div></div>" +
      "<div class='doc'><b>" + esc(numero || "") + "</b><br>" + esc(dataTxt || "") + "</div></div>";
  }

  function bannerHTML() { return "<div class='banner'><img src='" + BANNER + "'></div>"; }

  function equipHTML(eq) {
    if (!eq) return "";
    var has = eq.descricao || eq.marca || eq.modelo || eq.numero_serie || eq.patrimonio;
    if (!has) return "";
    var r = "<h2>Equipamento</h2><div class='kv'>";
    if (eq.descricao) r += "<div><b>Descrição:</b> " + esc(eq.descricao) + "</div>";
    if (eq.marca || eq.modelo) r += "<div><b>Marca/Modelo:</b> " + esc(eq.marca || "-") + " / " + esc(eq.modelo || "-") + "</div>";
    if (eq.numero_serie) r += "<div><b>Nº Série:</b> " + esc(eq.numero_serie) + "</div>";
    if (eq.patrimonio) r += "<div><b>Patrimônio:</b> " + esc(eq.patrimonio) + "</div>";
    return r + "</div>";
  }

  function fotosPages(fotos, withBanner) {
    var pages = [];
    for (var i = 0; i < fotos.length; i += 4) {
      var grp = fotos.slice(i, i + 4);
      var g = "<div class='page'>" + headerHTML("Registro fotográfico", "", "") +
        "<h2>Fotos</h2><div class='fotos'>";
      grp.forEach(function (f) {
        g += "<figure><img src='" + f.data + "'>" +
          (f.legenda ? "<figcaption>" + esc(f.legenda) + "</figcaption>" : "") + "</figure>";
      });
      g += "</div>" + (withBanner ? bannerHTML() : "") + "</div>";
      pages.push(g);
    }
    return pages;
  }

  function buildOrcamentoHTML(d) {
    d = d || {};
    var cli = d.cliente || {}, itens = d.itens || [], fotos = d.fotos || [];
    var bruto = 0;
    var rows = itens.map(function (it) {
      var sub = (it.preco_centavos || 0) * (it.quantidade || 1);
      bruto += sub;
      return "<tr><td>" + esc(it.descricao) + "</td><td class='n'>" + (it.quantidade || 1) +
        " " + esc(it.unidade || "un") + "</td><td class='n'>" + brl(it.preco_centavos) +
        "</td><td class='n'>" + brl(sub) + "</td></tr>";
    }).join("");
    var desc = Number(d.desconto_pct || 0);
    var total = Math.round(bruto * (1 - desc / 100));

    var p1 = "<div class='page'>" + headerHTML("Orçamento", d.numero || "", fmtDate(new Date())) +
      "<h2>Cliente</h2><div class='kv'>" +
      "<div><b>Nome:</b> " + esc(cli.nome) + "</div>" +
      (cli.telefone ? "<div><b>Telefone:</b> " + esc(cli.telefone) + "</div>" : "") +
      (cli.endereco ? "<div><b>Endereço:</b> " + esc(cli.endereco) + "</div>" : "") +
      (d.local_servico ? "<div><b>Local:</b> " + esc(d.local_servico) + "</div>" : "") +
      (d.tipo ? "<div><b>Tipo:</b> " + esc(d.tipo) + "</div>" : "") +
      "</div>" +
      equipHTML(d.equipamento) +
      "<h2>Itens</h2><table><thead><tr><th>Descrição</th><th class='n'>Qtd</th><th class='n'>Unit.</th><th class='n'>Subtotal</th></tr></thead><tbody>" +
      rows + "</tbody></table>" +
      "<div class='tot'>" + (desc > 0 ? "Subtotal: " + brl(bruto) + " &nbsp; Desconto: " + desc + "%<br>" : "") +
      "<span class='big'>Total: " + brl(total) + "</span></div>" +
      (d.validade_txt ? "<div class='obs'>Validade: " + esc(d.validade_txt) + "</div>" : "") +
      (d.observacoes ? "<h2>Observações</h2><div class='obs'>" + esc(d.observacoes) + "</div>" : "");

    var hasFotos = fotos.length > 0;
    if (!hasFotos && d.assinatura) {
      p1 += "<div class='sigs'><div class='sig'><img src='" + d.assinatura + "'><div class='ln'>" +
        esc(cli.nome || "Assinatura") + "</div></div></div>";
    }
    p1 += bannerHTML() + "</div>";

    var pages = [p1];
    var fp = fotosPages(fotos, !d.assinatura);
    pages = pages.concat(fp);
    if (hasFotos && d.assinatura) {
      pages.push("<div class='page'>" + headerHTML("Orçamento", d.numero || "", fmtDate(new Date())) +
        "<div class='sigs'><div class='sig'><img src='" + d.assinatura + "'><div class='ln'>" +
        esc(cli.nome || "Assinatura") + "</div></div></div>" + bannerHTML() + "</div>");
    }
    return "<style>" + STYLE + "</style>" + pages.join("");
  }

  function buildOsHTML(d) {
    d = d || {};
    var cli = d.cliente || {}, blocos = d.blocos || [], fotos = d.fotos || [];
    var sig = d.assinaturas || {};
    var p1 = "<div class='page'>" + headerHTML("Ordem de Serviço", d.numero || "", d.data_txt || fmtDate(new Date())) +
      "<h2>Dados</h2><div class='kv'>" +
      "<div><b>Cliente:</b> " + esc(cli.nome) + "</div>" +
      (d.titulo ? "<div><b>Serviço:</b> " + esc(d.titulo) + "</div>" : "") +
      (d.tecnico ? "<div><b>Técnico:</b> " + esc(d.tecnico) + "</div>" : "") +
      "</div>" + equipHTML(d.equipamento);
    blocos.forEach(function (b) {
      if (!b || !(b.conteudo || "").trim()) return;
      p1 += "<div class='blk'><div class='bt'>" + esc(b.titulo || "") + "</div>" +
        "<div class='bc'>" + esc(b.conteudo) + "</div></div>";
    });
    p1 += bannerHTML() + "</div>";

    var pages = [p1].concat(fotosPages(fotos, false));
    // Página de assinaturas (cliente + técnico)
    pages.push("<div class='page'>" + headerHTML("Ordem de Serviço", d.numero || "", d.data_txt || fmtDate(new Date())) +
      "<h2>Assinaturas</h2><div class='sigs'>" +
      "<div class='sig'>" + (sig.cliente ? "<img src='" + sig.cliente + "'>" : "") +
      "<div class='ln'>Cliente" + (cli.nome ? " — " + esc(cli.nome) : "") + "</div></div>" +
      "<div class='sig'>" + (sig.tecnico ? "<img src='" + sig.tecnico + "'>" : "") +
      "<div class='ln'>Técnico" + (d.tecnico ? " — " + esc(d.tecnico) : "") + "</div></div>" +
      "</div>" + bannerHTML() + "</div>");
    return "<style>" + STYLE + "</style>" + pages.join("");
  }

  function waitImages(doc) {
    var imgs = Array.prototype.slice.call(doc.images || []);
    return Promise.all(imgs.map(function (img) {
      if (img.complete && img.naturalWidth) return Promise.resolve();
      return new Promise(function (res) { img.onload = img.onerror = res; });
    }));
  }

  // Renderiza o HTML num iframe offscreen e monta o PDF por .page. Retorna base64.
  function gerarBlob(tipo, data) {
    var html = tipo === "os" ? buildOsHTML(data) : buildOrcamentoHTML(data);
    return new Promise(function (resolve, reject) {
      if (!window.html2canvas || !window.jspdf) {
        reject(new Error("Bibliotecas de PDF não carregadas"));
        return;
      }
      var iframe = document.createElement("iframe");
      iframe.style.cssText = "position:fixed;left:-10000px;top:0;width:" + PW + "px;height:" + PH + "px;border:0;";
      document.body.appendChild(iframe);
      var idoc = iframe.contentDocument;
      idoc.open();
      idoc.write("<!doctype html><html><head><meta charset='utf-8'></head><body>" + html + "</body></html>");
      idoc.close();

      waitImages(idoc).then(function () {
        var pages = Array.prototype.slice.call(idoc.querySelectorAll(".page"));
        var jsPDF = window.jspdf.jsPDF;
        var pdf = new jsPDF({ orientation: "portrait", unit: "px", format: [PW, PH] });
        var i = 0;
        function next() {
          if (i >= pages.length) {
            document.body.removeChild(iframe);
            var b64 = pdf.output("datauristring").split(",")[1];
            resolve(b64);
            return;
          }
          window.html2canvas(pages[i], { scale: 2, useCORS: true, backgroundColor: "#ffffff" })
            .then(function (canvas) {
              var img = canvas.toDataURL("image/jpeg", 0.92);
              if (i > 0) pdf.addPage([PW, PH], "portrait");
              pdf.addImage(img, "JPEG", 0, 0, PW, PH);
              i++; next();
            }).catch(function (e) { document.body.removeChild(iframe); reject(e); });
        }
        next();
      }).catch(reject);
    });
  }

  AVS.Pdf = {
    gerarBlob: gerarBlob, buildOrcamentoHTML: buildOrcamentoHTML,
    buildOsHTML: buildOsHTML, buildPdfFilename: buildPdfFilename,
  };
})(window.AVS);
