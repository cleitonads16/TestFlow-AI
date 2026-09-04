from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .escopo import Escopo


class GeracaoIA(Base):
    """Registro de auditoria de cada chamada ao provedor de IA para gerar casos de teste."""

    __tablename__ = "geracoes_ia"

    id: Mapped[int] = mapped_column(primary_key=True)
    provedor: Mapped[str] = mapped_column(String(50))
    modelo: Mapped[str] = mapped_column(String(50))
    quantidade_casos_gerados: Mapped[int] = mapped_column(Integer, default=0)
    tokens_utilizados: Mapped[int | None] = mapped_column(Integer, default=None)
    data: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    escopo_id: Mapped[int] = mapped_column(ForeignKey("escopos.id"))
    escopo: Mapped["Escopo"] = relationship(back_populates="geracoes_ia")
