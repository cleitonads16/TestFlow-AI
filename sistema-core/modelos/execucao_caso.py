from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import StatusExecucaoCaso

if TYPE_CHECKING:
    from .caso_de_teste import CasoDeTeste
    from .defeito import Defeito
    from .rodada_execucao import RodadaDeExecucao


class ExecucaoDeCaso(Base):
    __tablename__ = "execucoes_caso"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[StatusExecucaoCaso] = mapped_column(
        Enum(StatusExecucaoCaso), default=StatusExecucaoCaso.PENDENTE
    )
    observacoes: Mapped[str | None] = mapped_column(String(1000), default=None)
    data_execucao: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    rodada_id: Mapped[int] = mapped_column(ForeignKey("rodadas_execucao.id"))
    rodada: Mapped["RodadaDeExecucao"] = relationship(back_populates="execucoes")

    caso_de_teste_id: Mapped[int] = mapped_column(ForeignKey("casos_de_teste.id"))
    caso_de_teste: Mapped["CasoDeTeste"] = relationship(back_populates="execucoes")

    defeitos: Mapped[list["Defeito"]] = relationship(
        back_populates="execucao", cascade="all, delete-orphan"
    )
