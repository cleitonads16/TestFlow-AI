from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from modelos import Base

CAMINHO_BANCO = Path(__file__).resolve().parents[2] / "todo.db"
URL_BANCO = f"sqlite:///{CAMINHO_BANCO}"

engine = create_engine(URL_BANCO)
SessionLocal = sessionmaker(bind=engine)


def criar_tabelas() -> None:
    Base.metadata.create_all(engine)


def obter_sessao() -> Session:
    return SessionLocal()
