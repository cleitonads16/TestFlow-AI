from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .escopo import Escopo
    from .rodada_execucao import RodadaDeExecucao


class Projeto(Base):
    __tablename__ = "projetos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(String(500), default=None)

    escopos: Mapped[list["Escopo"]] = relationship(
        back_populates="projeto", cascade="all, delete-orphan"
    )
    rodadas_execucao: Mapped[list["RodadaDeExecucao"]] = relationship(
        back_populates="projeto", cascade="all, delete-orphan"
    )
