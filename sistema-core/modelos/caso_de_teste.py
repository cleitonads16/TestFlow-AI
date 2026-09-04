from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade

if TYPE_CHECKING:
    from .escopo import Escopo
    from .execucao_caso import ExecucaoDeCaso


class CasoDeTeste(Base):
    __tablename__ = "casos_de_teste"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20))
    titulo: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[CategoriaCasoDeTeste] = mapped_column(
        Enum(CategoriaCasoDeTeste), default=CategoriaCasoDeTeste.FUNCIONAL
    )
    pre_condicao: Mapped[str | None] = mapped_column(Text, default=None)
    passos: Mapped[str | None] = mapped_column(Text, default=None)
    resultado_esperado: Mapped[str | None] = mapped_column(Text, default=None)
    prioridade: Mapped[Prioridade] = mapped_column(
        Enum(Prioridade), default=Prioridade.MEDIA
    )
    origem: Mapped[OrigemCasoDeTeste] = mapped_column(
        Enum(OrigemCasoDeTeste), default=OrigemCasoDeTeste.MANUAL
    )

    escopo_id: Mapped[int] = mapped_column(ForeignKey("escopos.id"))
    escopo: Mapped["Escopo"] = relationship(back_populates="casos_de_teste")

    execucoes: Mapped[list["ExecucaoDeCaso"]] = relationship(
        back_populates="caso_de_teste", cascade="all, delete-orphan"
    )
