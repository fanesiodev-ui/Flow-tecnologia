"""
Configuração do banco de dados com SQLAlchemy.

Usa SQLite por padrão (arquivo local, zero configuração).
Para produção, basta trocar a DATABASE_URL por PostgreSQL:
  postgresql://usuario:senha@host:5432/nome_banco

Tabelas criadas automaticamente na primeira execução.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Caminho do arquivo do banco de dados SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "storage", "contafacil.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Cria o motor de conexão
# check_same_thread=False é necessário para SQLite com FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Fábrica de sessões — usada para abrir/fechar conexões com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base para todos os modelos de tabela
Base = declarative_base()


def get_db():
    """
    Gerador de sessão do banco de dados.
    Usado como dependência no FastAPI (Depends).
    Garante que a sessão seja fechada após cada requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas():
    """Cria todas as tabelas no banco de dados se não existirem."""
    Base.metadata.create_all(bind=engine)
