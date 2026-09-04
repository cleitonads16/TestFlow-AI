from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import SeveridadeDefeito, StatusDefeito

if TYPE_CHECKING:
    from .execucao_caso import ExecucaoDeCaso


class Defeito(Base):
    __tablename__ = "defeitos"

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(1000))
    severidade: Mapped[SeveridadeDefeito] = mapped_column(
        Enum(SeveridadeDefeito), default=SeveridadeDefeito.MEDIA
    )
    status: Mapped[StatusDefeito] = mapped_column(
        Enum(StatusDefeito), default=StatusDefeito.ABERTO
    )

    execucao_id: Mapped[int] = mapped_column(ForeignKey("execucoes_caso.id"))
    execucao: Mapped["ExecucaoDeCaso"] = relationship(back_populates="defeitos")
