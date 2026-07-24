"""Constrói o HTML autocontido dos documentos (Orçamento e OS) a partir de
uma Ordem, no design system "Voltage". O HTML embute CSS, fontes (.woff2) e
logo em base64, para ser renderizado em PDF por app.services.pdf_render.

Dinheiro sempre em centavos (int); formatação pt-BR só aqui. Datas dd/mm/aaaa
no fuso America/Recife.
"""
import base64
import unicodedata
from datetime import timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import Ordem

TZ_RECIFE = ZoneInfo("America/Recife")
_BASE = Path(__file__).resolve().parent.parent          # app/
_STATIC = _BASE / "static"
_TEMPLATES = _BASE / "templates"

STATUS_LABEL = {
    "rascunho": "Rascunho", "orcamento": "Orçamento", "aprovado": "Aprovado",
    "em_execucao": "Em execução", "concluido": "Concluído", "recebido": "Recebido",
    "recusado": "Recusado", "cancelado": "Cancelado",
}

_FONTES = [
    ("Archivo Black", 400, "archivo-black-400.woff2"),
    ("Barlow", 400, "barlow-400.woff2"),
    ("Barlow", 500, "barlow-500.woff2"),
    ("Barlow", 600, "barlow-600.woff2"),
    ("Barlow", 700, "barlow-700.woff2"),
    ("Barlow Condensed", 500, "barlow-condensed-500.woff2"),
    ("Barlow Condensed", 600, "barlow-condensed-600.woff2"),
    ("Barlow Condensed", 700, "barlow-condensed-700.woff2"),
]

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html"]),
)


@lru_cache(maxsize=1)
def _fonts_css() -> str:
    partes = []
    for fam, peso, arq in _FONTES:
        raw = (_STATIC / "fonts" / arq).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        partes.append(
            f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{peso};"
            f"font-display:swap;src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
        )
    return "".join(partes)


@lru_cache(maxsize=1)
def _documento_css() -> str:
    return (_STATIC / "css" / "documento.css").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _logo_uri() -> str:
    raw = (_STATIC / "img" / "logo-avs-256.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


# ---------- helpers de formatação ----------

def _brl(centavos) -> str:
    s = f"{(centavos or 0) / 100:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def _data_br(dt) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_RECIFE).strftime("%d/%m/%Y")


def _dd_mm_aa(dt) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_RECIFE).strftime("%d_%m_%y")


def _pct_txt(pct) -> str:
    p = float(pct or 0)
    return str(int(p)) if p == int(p) else f"{p:g}".replace(".", ",")


def _fotos_ctx(lista) -> tuple[list, str]:
    fotos = []
    for i, f in enumerate(lista or [], 1):
        data = (f or {}).get("data")
        if not data:
            continue
        fotos.append({"num": f"{len(fotos) + 1:02d}", "data": data,
                      "legenda": (f.get("legenda") or "").strip()})
    n = len(fotos)
    if n == 0:
        conta = ""
    else:
        conta = f"{n:02d} registro" + ("s" if n > 1 else "")
    return fotos, conta


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower()


def _sig(dataurl):
    """Só devolve a assinatura se tiver traço real (evita PNG transparente vazio)."""
    return dataurl if dataurl and len(dataurl) > 2000 else None


# ---------- builders ----------

def build_orcamento(ordem: Ordem) -> tuple[str, str]:
    itens = []
    subtotal = 0
    for it in ordem.itens:
        sub = (it.preco_centavos or 0) * (it.quantidade or 0)
        subtotal += sub
        itens.append({
            "descricao": it.descricao,
            "qtd_txt": f"{it.quantidade} {it.unidade or 'un'}".strip(),
            "unit_txt": _brl(it.preco_centavos),
            "sub_txt": _brl(sub),
        })
    total = ordem.total_centavos or 0
    body = ordem.orcamento_json or {}
    fotos, fotos_count = _fotos_ctx(body.get("fotos"))
    tipo_map = {"instalacao": "Instalação", "manutencao": "Manutenção",
                "laudo": "Laudo", "projeto": "Projeto", "outro": "Outro"}
    ctx = {
        "doc_title": ordem.numero,
        "fonts_css": _fonts_css(), "documento_css": _documento_css(), "logo_uri": _logo_uri(),
        "numero": ordem.numero,
        "data_emissao": _data_br(ordem.created_at),
        "validade": _data_br(ordem.validade_at),
        "cliente_nome": ordem.cliente.nome if ordem.cliente else "—",
        "cliente_telefone": ordem.cliente.telefone if ordem.cliente else "",
        "cliente_endereco": ordem.cliente.endereco if ordem.cliente else "",
        "tipo": tipo_map.get(ordem.tipo, (ordem.tipo or "").capitalize()),
        "local": ordem.local_servico,
        "itens": itens,
        "subtotal_txt": _brl(subtotal),
        "desc_pct": _pct_txt(ordem.desconto_pct),
        "desconto_txt": _brl(subtotal - total),
        "total_txt": _brl(total),
        "observacoes": ordem.observacoes,
        "fotos": fotos, "fotos_count": fotos_count,
        "sig_cliente": _sig(body.get("assinatura")),
        "sig_empresa": _sig(body.get("assinatura_empresa")),
        "empresa_nome": (body.get("empresa_nome") or "").strip() or "AVS - Elétrica",
    }
    html = _env.get_template("doc_orcamento.html").render(**ctx)
    nome = f"Orçamento - {ctx['cliente_nome']} - {_dd_mm_aa(ordem.created_at)}.pdf"
    return html, nome


def build_os(ordem: Ordem) -> tuple[str, str]:
    rel = ordem.relatorio_json or {}
    desc, duo, nota, extra = [], [], [], []
    for b in rel.get("blocos") or []:
        titulo = (b.get("titulo") or "").strip()
        conteudo = (b.get("conteudo") or "").strip()
        if not conteudo:
            continue
        t = _norm(titulo)
        item = {"titulo": titulo, "conteudo": conteudo}
        if "descri" in t:
            desc.append(item)
        elif "utiliz" in t or "substitu" in t or "peca" in t:
            duo.append(item)
        elif "norma" in t:
            nota.append(item)
        else:
            extra.append(item)
    fotos, fotos_count = _fotos_ctx(rel.get("fotos"))
    assin = rel.get("assinaturas") or {}
    data_ref = ordem.data_servico or ordem.created_at
    ctx = {
        "doc_title": ordem.numero,
        "fonts_css": _fonts_css(), "documento_css": _documento_css(), "logo_uri": _logo_uri(),
        "numero": ordem.numero,
        "data_servico": _data_br(data_ref),
        "cliente_nome": ordem.cliente.nome if ordem.cliente else "—",
        "tecnico": rel.get("tecnico"),
        "status_label": STATUS_LABEL.get(ordem.status, ordem.status),
        "servico": ordem.titulo,
        "local": ordem.local_servico,
        "blocos_desc": desc, "blocos_duo": duo, "blocos_nota": nota, "blocos_extra": extra,
        "fotos": fotos, "fotos_count": fotos_count,
        "sig_cliente": _sig(assin.get("cliente")),
        "sig_tecnico": _sig(assin.get("tecnico")),
    }
    html = _env.get_template("doc_os.html").render(**ctx)
    nome = f"Relatório de Serviço - {ctx['cliente_nome']} - {_dd_mm_aa(data_ref)}.pdf"
    return html, nome
