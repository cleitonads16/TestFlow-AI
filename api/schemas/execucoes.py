from datetime import date, datetime

from ninja import Field, Schema
from pydantic import ConfigDict

from modelos import SeveridadeDefeito, StatusDefeito, StatusExecucaoCaso


class RodadaEntrada(Schema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "nome": "Regressão da versão 2.4",
                    "data_inicio": "2026-10-14",
                    "data_fim": "2026-10-18",
                    "casos_ids": [1, 2, 3],
                }
            ]
        }
    )

    nome: str = Field(max_length=120)
    data_inicio: date | None = None
    data_fim: date | None = Field(default=None, description="Não pode ser anterior a data_inicio.")
    casos_ids: list[int] = Field(
        default_factory=list, description="Casos já agendados na rodada, como pendentes."
    )


class InclusaoDeCasos(Schema):
    model_config = ConfigDict(json_schema_extra={"examples": [{"casos_ids": [4, 5]}]})

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
    data_execucao: datetime | None = Field(
        description="Momento em que o resultado foi registrado; vazio enquanto pendente."
    )


class ResultadoExecucao(Schema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "falhou", "observacoes": "A tela de troca de senha não abriu."}
            ]
        }
    )

    status: StatusExecucaoCaso = Field(
        description="passou, falhou ou bloqueado (bloqueado exige observacoes)."
    )
    observacoes: str | None = Field(default=None, max_length=1000)


class FiltroExecucoes(Schema):
    status: StatusExecucaoCaso | None = None


class DefeitoEntrada(Schema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "descricao": "Usuário com senha vencida entra direto, sem pedido de troca.",
                    "severidade": "alta",
                }
            ]
        }
    )

    descricao: str = Field(max_length=1000)
    severidade: SeveridadeDefeito = SeveridadeDefeito.MEDIA


class DefeitoAtualizacao(Schema):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "corrigido"}]})

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
