"""
Modelos das tabelas do banco de dados.

Tabelas:
  - Contador   → escritórios contábeis que usam o sistema
  - Cliente    → empresas dos contadores
  - Relatorio  → histórico de relatórios gerados

Relacionamentos:
  Contador → tem muitos → Clientes
  Contador → tem muitos → Relatórios
  Cliente  → tem muitos → Relatórios
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class Contador(Base):
    """
    Representa um escritório contábil / contador que usa o sistema.
    No futuro terá login e senha.
    """
    __tablename__ = "contadores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    escritorio = Column(String(200), nullable=False)
    cor_primaria = Column(String(10), default="#1E40AF")
    cor_secundaria = Column(String(10), default="#7C3AED")
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    clientes = relationship("Cliente", back_populates="contador")
    relatorios = relationship("Relatorio", back_populates="contador")

    def __repr__(self):
        return f"<Contador {self.escritorio}>"


class Cliente(Base):
    """
    Representa uma empresa cliente do contador.
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    contador_id = Column(Integer, ForeignKey("contadores.id"), nullable=False)
    empresa_nome = Column(String(200), nullable=False, index=True)
    cnpj = Column(String(20), nullable=True)
    email_contato = Column(String(200), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    contador = relationship("Contador", back_populates="clientes")
    relatorios = relationship("Relatorio", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente {self.empresa_nome}>"


class Relatorio(Base):
    """
    Histórico de relatórios gerados.
    Guarda os dados financeiros e o caminho do PDF gerado.
    """
    __tablename__ = "relatorios"

    id = Column(Integer, primary_key=True, index=True)
    contador_id = Column(Integer, ForeignKey("contadores.id"), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    # Dados do relatório
    empresa_nome = Column(String(200), nullable=False)
    periodo = Column(String(50), nullable=False)
    arquivo_pdf = Column(String(500), nullable=True)   # caminho do PDF

    # Dados financeiros (para histórico e gráficos futuros)
    faturamento = Column(Float, default=0.0)
    impostos = Column(Float, default=0.0)
    custos_operacionais = Column(Float, default=0.0)
    despesas_administrativas = Column(Float, default=0.0)
    outras_despesas = Column(Float, default=0.0)
    lucro_liquido = Column(Float, default=0.0)

    # Margem calculada para facilitar consultas
    margem_lucro = Column(Float, default=0.0)

    # Configuração white label usada
    nome_escritorio = Column(String(200), nullable=True)
    nome_contador = Column(String(200), nullable=True)
    cor_primaria = Column(String(10), default="#1E40AF")

    criado_em = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    contador = relationship("Contador", back_populates="relatorios")
    cliente = relationship("Cliente", back_populates="relatorios")

    def __repr__(self):
        return f"<Relatorio {self.empresa_nome} - {self.periodo}>"
