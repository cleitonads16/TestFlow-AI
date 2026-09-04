from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .execucao_caso import ExecucaoDeCaso
    from .projeto import Projeto


class RodadaDeExecucao(Base):
    __tablename__ = "rodadas_execucao"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    data_inicio: Mapped[date | None] = mapped_column(Date, default=None)
    data_fim: Mapped[date | None] = mapped_column(Date, default=None)

    projeto_id: Mapped[int] = mapped_column(ForeignKey("projetos.id"))
    projeto: Mapped["Projeto"] = relationship(back_populates="rodadas_execucao")

    execucoes: Mapped[list["ExecucaoDeCaso"]] = relationship(
        back_populates="rodada", cascade="all, delete-orphan"
    )
