"""Serviço de ordens — máquina de estados (orçamento -> OS -> recebimento).

Regras invariáveis:
- Uma ordem é orçamento E OS: progride por status.
- Dinheiro sempre em centavos (Integer).
- Receita (FinanceiroVenda) nasce ao marcar 'recebido'; custo da venda = soma
  dos custos lançados na OS (ordem_custos).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import (
    Cliente, Equipamento, FinanceiroVenda, Ordem, OrdemCusto, OrdemItem,
)

TZ_RECIFE = ZoneInfo("America/Recife")
VALIDADE_DIAS = 7

TRANSICOES_VALIDAS = {
    "rascunho":    {"orcamento", "cancelado"},
    "orcamento":   {"aprovado", "recusado", "cancelado"},
    "aprovado":    {"em_execucao", "cancelado"},
    "em_execucao": {"concluido", "cancelado"},
    "concluido":   {"recebido", "cancelado"},
    "recebido":    set(),
    "recusado":    set(),
    "cancelado":   set(),
}

LABEL_TRANSICAO = {
    "orcamento":   "Enviar orçamento",
    "aprovado":    "Aprovar (gerar OS)",
    "em_execucao": "Iniciar execução",
    "concluido":   "Concluir serviço",
    "recebido":    "Marcar recebido",
    "recusado":    "Recusar",
    "cancelado":   "Cancelar",
}


def _hoje_recife():
    return datetime.now(TZ_RECIFE).date()


def upsert_cliente(db: Session, nome: str, telefone: str | None = None,
                   endereco: str | None = None, email: str | None = None) -> Cliente:
    """Busca cliente por telefone (se houver); senão cria."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip() or None
    cliente = None
    if telefone:
        cliente = db.query(Cliente).filter(Cliente.telefone == telefone).first()
    if cliente is None:
        cliente = Cliente(nome=nome or "Cliente", telefone=telefone,
                          endereco=endereco, email=email)
        db.add(cliente)
        db.flush()
    else:
        if nome and not cliente.nome:
            cliente.nome = nome
        if endereco and not cliente.endereco:
            cliente.endereco = endereco
        if email and not cliente.email:
            cliente.email = email
    return cliente


def upsert_equipamento(db: Session, cliente_id: int, descricao: str | None = None,
                       marca: str | None = None, modelo: str | None = None,
                       numero_serie: str | None = None,
                       patrimonio: str | None = None) -> int:
    """Reaproveita equipamento do cliente por série/patrimônio; senão cria."""
    numero_serie = (numero_serie or "").strip() or None
    patrimonio = (patrimonio or "").strip() or None
    existente = None
    if numero_serie:
        existente = (db.query(Equipamento)
                     .filter(Equipamento.cliente_id == cliente_id,
                             Equipamento.numero_serie == numero_serie).first())
    if existente is None and patrimonio:
        existente = (db.query(Equipamento)
                     .filter(Equipamento.cliente_id == cliente_id,
                             Equipamento.patrimonio == patrimonio).first())
    if existente is not None:
        return existente.id
    eq = Equipamento(
        cliente_id=cliente_id, descricao=(descricao or "").strip() or None,
        marca=(marca or "").strip() or None, modelo=(modelo or "").strip() or None,
        numero_serie=numero_serie, patrimonio=patrimonio,
    )
    db.add(eq)
    db.flush()
    return eq.id


def _proximo_numero(db: Session) -> str:
    """ORC-AAAAMMDD-NNN sequencial por dia (data local de Recife)."""
    hoje = datetime.now(TZ_RECIFE).strftime("%Y%m%d")
    prefixo = f"ORC-{hoje}-"
    ultimo = (db.query(Ordem)
              .filter(Ordem.numero.like(f"{prefixo}%"))
              .order_by(Ordem.numero.desc()).first())
    seq = int(ultimo.numero.rsplit("-", 1)[1]) + 1 if ultimo else 1
    return f"{prefixo}{seq:03d}"


def _calc_total(itens: list[dict], desconto_pct: Decimal) -> int:
    bruto = sum(int(i["preco_centavos"]) * int(i.get("quantidade", 1)) for i in itens)
    return int(Decimal(bruto) * (Decimal("1") - desconto_pct / Decimal("100")))


def criar_orcamento(
    db: Session,
    cliente_nome: str,
    cliente_telefone: str | None,
    itens: list[dict],
    titulo: str | None = None,
    local_servico: str | None = None,
    tipo: str | None = None,
    prioridade: str = "normal",
    equipamento: dict | None = None,
    desconto_pct=0,
    observacoes: str | None = None,
    orcamento_json: dict | None = None,
    cliente_endereco: str | None = None,
) -> dict:
    """Cria ordem em status 'orcamento' com itens livres (preço vindo do form)."""
    if not itens:
        raise ValueError("Orçamento sem itens")
    desconto_pct = Decimal(str(desconto_pct or 0))
    if desconto_pct < 0 or desconto_pct >= 100:
        raise ValueError("Desconto inválido")

    cliente = upsert_cliente(db, cliente_nome, cliente_telefone, cliente_endereco)

    equipamento_id = None
    if equipamento:
        temdados = any((equipamento or {}).get(k) for k in
                       ("descricao", "marca", "modelo", "numero_serie", "patrimonio"))
        if equipamento.get("id"):
            equipamento_id = int(equipamento["id"])
        elif temdados:
            equipamento_id = upsert_equipamento(
                db, cliente.id,
                descricao=equipamento.get("descricao"),
                marca=equipamento.get("marca"), modelo=equipamento.get("modelo"),
                numero_serie=equipamento.get("numero_serie"),
                patrimonio=equipamento.get("patrimonio"),
            )

    ordem = Ordem(
        numero=_proximo_numero(db),
        cliente_id=cliente.id,
        equipamento_id=equipamento_id,
        status="orcamento",
        titulo=(titulo or "").strip() or None,
        tipo=(tipo or "").strip() or None,
        prioridade=prioridade or "normal",
        local_servico=(local_servico or "").strip() or None,
        desconto_pct=desconto_pct,
        validade_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=VALIDADE_DIAS),
        observacoes=(observacoes or "").strip() or None,
        orcamento_json=orcamento_json,
        canal="web",
    )
    db.add(ordem)
    db.flush()

    for it in itens:
        db.add(OrdemItem(
            ordem_id=ordem.id,
            descricao=str(it["descricao"]).strip(),
            quantidade=int(it.get("quantidade", 1)),
            unidade=(it.get("unidade") or "un"),
            preco_centavos=int(it["preco_centavos"]),
            custo_centavos=int(it.get("custo_centavos", 0)),
        ))

    ordem.total_centavos = _calc_total(itens, desconto_pct)
    db.commit()
    db.refresh(ordem)
    return {
        "ordem_id": ordem.id,
        "numero": ordem.numero,
        "total_centavos": ordem.total_centavos,
        "cliente_id": cliente.id,
        "equipamento_id": equipamento_id,
    }


def atualizar_orcamento(db: Session, ordem_id: int, itens: list[dict] | None = None,
                        titulo: str | None = None, local_servico: str | None = None,
                        desconto_pct=None, observacoes: str | None = None,
                        orcamento_json: dict | None = None) -> dict:
    """Atualiza um orçamento existente (rascunho/orcamento) e recalcula total."""
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    if titulo is not None:
        ordem.titulo = titulo.strip() or None
    if local_servico is not None:
        ordem.local_servico = local_servico.strip() or None
    if observacoes is not None:
        ordem.observacoes = observacoes.strip() or None
    if orcamento_json is not None:
        ordem.orcamento_json = orcamento_json
    if desconto_pct is not None:
        ordem.desconto_pct = Decimal(str(desconto_pct))
    if itens is not None:
        for antigo in list(ordem.itens):
            db.delete(antigo)
        db.flush()
        for it in itens:
            db.add(OrdemItem(
                ordem_id=ordem.id, descricao=str(it["descricao"]).strip(),
                quantidade=int(it.get("quantidade", 1)),
                unidade=(it.get("unidade") or "un"),
                preco_centavos=int(it["preco_centavos"]),
                custo_centavos=int(it.get("custo_centavos", 0)),
            ))
        ordem.total_centavos = _calc_total(itens, Decimal(str(ordem.desconto_pct or 0)))
    db.commit()
    db.refresh(ordem)
    return {"ordem_id": ordem.id, "numero": ordem.numero,
            "total_centavos": ordem.total_centavos}


def mudar_status(db: Session, ordem_id: int, novo_status: str) -> dict:
    """Transiciona o status validando o fluxo. Levanta ValueError se inválido."""
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    if novo_status not in TRANSICOES_VALIDAS:
        raise ValueError(f"Status '{novo_status}' desconhecido")
    if novo_status not in TRANSICOES_VALIDAS[ordem.status]:
        raise ValueError(f"Transição inválida: {ordem.status} -> {novo_status}")

    if novo_status == "aprovado" and ordem.data_servico is None:
        raise ValueError("Defina a data do serviço para agendar")

    ordem.status = novo_status
    ordem.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    if novo_status == "concluido" and ordem.data_conclusao is None:
        ordem.data_conclusao = datetime.now(timezone.utc).replace(tzinfo=None)

    # 'recebido' é terminal e alcançável só a partir de 'concluido' — roda 1x.
    if novo_status == "recebido":
        ordem.data_recebimento = _hoje_recife()
        custo_total = sum(c.valor_centavos or 0 for c in ordem.custos)
        db.add(FinanceiroVenda(
            ordem_id=ordem.id,
            valor_centavos=ordem.total_centavos,
            custo_centavos=custo_total,
        ))
    db.commit()
    return {"ordem_id": ordem.id, "numero": ordem.numero, "status": ordem.status}


def set_data_servico(db: Session, ordem_id: int, dt: datetime) -> None:
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    ordem.data_servico = dt
    db.commit()


def add_item(db: Session, ordem_id: int, descricao: str, preco_centavos: int,
             quantidade: int = 1, unidade: str = "un", custo_centavos: int = 0) -> None:
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    db.add(OrdemItem(ordem_id=ordem_id, descricao=descricao.strip(),
                     quantidade=quantidade, unidade=unidade,
                     preco_centavos=preco_centavos, custo_centavos=custo_centavos))
    db.flush()
    itens = [{"preco_centavos": i.preco_centavos, "quantidade": i.quantidade}
             for i in ordem.itens]
    ordem.total_centavos = _calc_total(itens, Decimal(str(ordem.desconto_pct or 0)))
    db.commit()


def add_custo(db: Session, ordem_id: int, descricao: str, valor_centavos: int,
              categoria: str | None = None) -> None:
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    db.add(OrdemCusto(ordem_id=ordem_id, descricao=descricao.strip(),
                      valor_centavos=valor_centavos, categoria=categoria))
    db.commit()


def atualizar_relatorio(db: Session, ordem_id: int, blocos, fotos, assinaturas) -> dict:
    """Grava o relatório da OS (blocos + fotos + assinaturas) em relatorio_json."""
    ordem = db.query(Ordem).filter(Ordem.id == ordem_id).first()
    if ordem is None:
        raise ValueError(f"Ordem {ordem_id} não encontrada")
    ordem.relatorio_json = {
        "blocos": blocos or [],
        "fotos": fotos or [],
        "assinaturas": assinaturas or {},
    }
    db.commit()
    return {"ordem_id": ordem.id, "numero": ordem.numero}
