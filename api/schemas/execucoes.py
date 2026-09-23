from datetime import date, datetime

from ninja import Field, Schema

from modelos import SeveridadeDefeito, StatusDefeito, StatusExecucaoCaso


class RodadaEntrada(Schema):
    nome: str = Field(max_length=120)
    data_inicio: date | None = None
    data_fim: date | None = None
    casos_ids: list[int] = Field(
        default_factory=list, description="Casos já agendados na rodada, como pendentes."
    )


class InclusaoDeCasos(Schema):
    casos_ids: list[int] = Field(min_length=1)


class ResumoRodada(Schema):
    pendente: int
    passou: int
    falhou: int
    bloqueado: int
    total: int


class RodadaSaida(Schema):
    id: int
    projeto_id: int
    nome: str
    data_inicio: date | None
    data_fim: date | None


class RodadaDetalhe(RodadaSaida):
    resumo: ResumoRodada


class ExecucaoSaida(Schema):
    id: int
    rodada_id: int
    caso_de_teste_id: int
    caso_codigo: str = Field(alias="caso_de_teste.codigo")
    caso_titulo: str = Field(alias="caso_de_teste.titulo")
    status: StatusExecucaoCaso
    observacoes: str | None
    data_execucao: datetime | None


class ResultadoExecucao(Schema):
    status: StatusExecucaoCaso = Field(
        description="passou, falhou ou bloqueado (bloqueado exige observacoes)."
    )
    observacoes: str | None = Field(default=None, max_length=1000)


class FiltroExecucoes(Schema):
    status: StatusExecucaoCaso | None = None


class DefeitoEntrada(Schema):
    descricao: str = Field(max_length=1000)
    severidade: SeveridadeDefeito = SeveridadeDefeito.MEDIA


class DefeitoAtualizacao(Schema):
    status: StatusDefeito


class DefeitoSaida(Schema):
    id: int
    execucao_id: int
    caso_codigo: str = Field(alias="execucao.caso_de_teste.codigo")
    descricao: str
    severidade: SeveridadeDefeito
    status: StatusDefeito


class FiltroDefeitos(Schema):
    projeto_id: int | None = None
    rodada_id: int | None = None
    status: StatusDefeito | None = None
    severidade: SeveridadeDefeito | None = None
