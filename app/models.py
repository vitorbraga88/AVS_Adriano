"""Modelo de domínio da AVS (SQLite).

Empresa fixa (sem multi-tenant). Orçamento e OS são a MESMA linha de
`ordens` progredindo por status. Dinheiro sempre em centavos (Integer).
"""
from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey,
    Integer, JSON, Numeric, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# 8 estados fixos da ordem (orçamento -> OS -> recebimento)
STATUS_ORDEM = (
    "rascunho", "orcamento", "aprovado", "em_execucao",
    "concluido", "recebido", "recusado", "cancelado",
)


class Cliente(Base):
    __tablename__ = "clientes"

    id          = Column(Integer, primary_key=True)
    nome        = Column(Text, nullable=False)
    telefone    = Column(Text)
    endereco    = Column(Text)
    email       = Column(Text)
    observacoes = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    equipamentos = relationship("Equipamento", back_populates="cliente")
    ordens       = relationship("Ordem", back_populates="cliente")


class Equipamento(Base):
    __tablename__ = "equipamentos"

    id           = Column(Integer, primary_key=True)
    cliente_id   = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    descricao    = Column(Text)
    marca        = Column(Text)
    modelo       = Column(Text)
    numero_serie = Column(Text)
    patrimonio   = Column(Text)
    observacoes  = Column(Text)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente = relationship("Cliente", back_populates="equipamentos")


class Ordem(Base):
    __tablename__ = "ordens"
    __table_args__ = (
        CheckConstraint(
            "status IN ('rascunho','orcamento','aprovado','em_execucao',"
            "'concluido','recebido','recusado','cancelado')",
            name="ordem_status_check",
        ),
    )

    id             = Column(Integer, primary_key=True)
    numero         = Column(Text, nullable=False, unique=True)
    cliente_id     = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    equipamento_id = Column(Integer, ForeignKey("equipamentos.id"), nullable=True)
    status         = Column(Text, nullable=False, default="rascunho")
    titulo         = Column(Text)
    tipo           = Column(Text)                       # instalacao|manutencao|laudo|projeto|outro
    prioridade     = Column(Text, nullable=False, default="normal")  # baixa|normal|alta
    local_servico  = Column(Text)
    total_centavos = Column(Integer, nullable=False, default=0)
    desconto_pct   = Column(Numeric(5, 2), nullable=False, default=0)
    validade_at    = Column(DateTime)
    observacoes    = Column(Text)
    data_servico   = Column(DateTime)                   # agenda
    data_conclusao = Column(DateTime)
    data_recebimento = Column(Date)
    canal          = Column(Text, nullable=False, default="web")
    orcamento_json = Column(JSON)                        # snapshot do form de orçamento
    relatorio_json = Column(JSON)                        # blocos "container" da OS
    orcamento_pdf_url = Column(Text)
    os_pdf_url     = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente     = relationship("Cliente", back_populates="ordens")
    equipamento = relationship("Equipamento")
    itens       = relationship("OrdemItem", back_populates="ordem",
                               cascade="all, delete-orphan")
    custos      = relationship("OrdemCusto", back_populates="ordem",
                               cascade="all, delete-orphan")


class OrdemItem(Base):
    __tablename__ = "ordem_itens"

    id             = Column(Integer, primary_key=True)
    ordem_id       = Column(Integer, ForeignKey("ordens.id"), nullable=False)
    descricao      = Column(Text, nullable=False)
    quantidade     = Column(Integer, nullable=False, default=1)
    unidade        = Column(Text, nullable=False, default="un")
    preco_centavos = Column(Integer, nullable=False)
    custo_centavos = Column(Integer, nullable=False, default=0)

    ordem = relationship("Ordem", back_populates="itens")


class OrdemCusto(Base):
    __tablename__ = "ordem_custos"

    id             = Column(Integer, primary_key=True)
    ordem_id       = Column(Integer, ForeignKey("ordens.id"), nullable=False)
    descricao      = Column(Text, nullable=False)
    categoria      = Column(Text)
    valor_centavos = Column(Integer, nullable=False)
    created_at     = Column(DateTime, server_default=func.now())

    ordem = relationship("Ordem", back_populates="custos")


class FinanceiroVenda(Base):
    __tablename__ = "financeiro_vendas"

    id             = Column(Integer, primary_key=True)
    ordem_id       = Column(Integer, ForeignKey("ordens.id"), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    custo_centavos = Column(Integer, nullable=False)
    data_venda     = Column(Date, nullable=False, server_default=func.current_date())

    ordem = relationship("Ordem")


class FinanceiroDespesa(Base):
    __tablename__ = "financeiro_despesas"

    id             = Column(Integer, primary_key=True)
    categoria      = Column(Text, nullable=False)
    descricao      = Column(Text, nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    data_despesa   = Column(Date, nullable=False, server_default=func.current_date())
    fonte          = Column(Text)
    fornecedor     = Column(Text)
    nf             = Column(Text)
    observacoes    = Column(Text)


class Assinatura(Base):
    """Memória de assinatura por nome (sync cross-device)."""
    __tablename__ = "assinaturas"

    nome       = Column(Text, primary_key=True)
    data_url   = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Sugestao(Base):
    """Autocomplete sincronizado (técnicos, tipos de serviço, etc.)."""
    __tablename__ = "sugestoes"

    field      = Column(Text, primary_key=True)
    value      = Column(Text, primary_key=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Notificacao(Base):
    """Dedup de notificações Telegram/n8n."""
    __tablename__ = "notificacoes"

    id         = Column(Integer, primary_key=True)
    ordem_id   = Column(Integer, ForeignKey("ordens.id"), nullable=False)
    tipo       = Column(Text, nullable=False)
    chat_id    = Column(Text)
    enviado_at = Column(DateTime, nullable=False, server_default=func.now())
