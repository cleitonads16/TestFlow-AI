from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import Prioridade, StatusTarefa

if TYPE_CHECKING:
    from .projeto import Projeto


class Tarefa(Base):
    __tablename__ = "tarefas"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(String(1000), default=None)
    status: Mapped[StatusTarefa] = mapped_column(
        Enum(StatusTarefa), default=StatusTarefa.PENDENTE
    )
    prioridade: Mapped[Prioridade] = mapped_column(
        Enum(Prioridade), default=Prioridade.MEDIA
    )
    prazo: Mapped[date | None] = mapped_column(Date, default=None)

    projeto_id: Mapped[int | None] = mapped_column(
        ForeignKey("projetos.id"), default=None
    )
    projeto: Mapped["Projeto"] = relationship(back_populates="tarefas")
