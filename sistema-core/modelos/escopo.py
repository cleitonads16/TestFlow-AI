from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import StatusEscopo

if TYPE_CHECKING:
    from .caso_de_teste import CasoDeTeste
    from .geracao_ia import GeracaoIA
    from .projeto import Projeto


class Escopo(Base):
    __tablename__ = "escopos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    texto_extraido: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[StatusEscopo] = mapped_column(
        Enum(StatusEscopo), default=StatusEscopo.PENDENTE
    )
    data_upload: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    projeto_id: Mapped[int] = mapped_column(ForeignKey("projetos.id"))
    projeto: Mapped["Projeto"] = relationship(back_populates="escopos")

    casos_de_teste: Mapped[list["CasoDeTeste"]] = relationship(
        back_populates="escopo", cascade="all, delete-orphan"
    )
    geracoes_ia: Mapped[list["GeracaoIA"]] = relationship(
        back_populates="escopo", cascade="all, delete-orphan"
    )
