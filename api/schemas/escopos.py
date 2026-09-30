from datetime import datetime

from ninja import Field, Schema

from modelos import StatusEscopo

from .casos_teste import CasoTesteSaida


class EscopoSaida(Schema):
    id: int
    projeto_id: int
    nome_arquivo: str = Field(description="Nome do arquivo como foi enviado.")
    status: StatusEscopo = Field(
        description='"pendente" até a geração de casos; depois "processado" ou "erro".'
    )
    data_upload: datetime | None


class EscopoDetalhe(EscopoSaida):
    texto_extraido: str | None = Field(
        description="Texto lido do documento; vazio enquanto o escopo está pendente."
    )


class GeracaoCasosSaida(Schema):
    escopo: EscopoSaida
    quantidade_casos_gerados: int
    casos: list[CasoTesteSaida]
