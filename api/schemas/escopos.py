from datetime import datetime

from ninja import Schema

from modelos import StatusEscopo

from .casos_teste import CasoTesteSaida


class EscopoSaida(Schema):
    id: int
    projeto_id: int
    nome_arquivo: str
    status: StatusEscopo
    data_upload: datetime | None


class EscopoDetalhe(EscopoSaida):
    texto_extraido: str | None


class GeracaoCasosSaida(Schema):
    escopo: EscopoSaida
    quantidade_casos_gerados: int
    casos: list[CasoTesteSaida]
