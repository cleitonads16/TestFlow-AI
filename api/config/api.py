"""Instância do Django Ninja: registra os routers e traduz os erros do core para HTTP.

A API não tem regra de negócio (docs/arquitetura-e-cronograma.md, seção 1):
os routers só validam a entrada, chamam `servicos` e usam os handlers
abaixo para converter as exceções do core em respostas HTTP.

Todo erro sai no mesmo formato (`schemas.ErroSaida`):
`{"detail": "<mensagem>", "codigo": "<tipo do erro>", "erros": [...]}`,
em que `erros` só vem preenchido nos erros de validação (422).
"""

import logging

from django.db import IntegrityError
from django.http import Http404
from ninja import NinjaAPI
from ninja.errors import ValidationError

from documentos import FormatoDocumentoNaoSuportado
from ia import ProvedorIAIndisponivel, RespostaIAInvalida
from rotas import casos_teste, defeitos, escopos, execucoes, projetos, rodadas
from servicos import OperacaoEmConflito, RegraDeNegocioViolada

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="TestFlow AI — Gestor de Casos de Teste",
    version="0.6.0",
    description=(
        "API do gestor de casos de teste com geração assistida por IA "
        "(projeto de PDI, Fase 2)."
    ),
)

for modulo in (projetos, escopos, casos_teste, rodadas, execucoes, defeitos):
    api.add_router("", modulo.router)

# Parâmetros de schema que aparecem na localização do erro do Pydantic e não
# dizem nada a quem chama a API (ex.: ["body", "payload", "titulo"] -> "titulo").
_PARAMETROS_DE_SCHEMA = {"payload", "filtros"}


def _erro(request, status: int, codigo: str, detalhe: str, erros: list | None = None):
    corpo = {"detail": detalhe, "codigo": codigo}
    if erros is not None:
        corpo["erros"] = erros
    return api.create_response(request, corpo, status=status)


@api.exception_handler(ValidationError)
def _dados_invalidos(request, erro):
    erros = []
    for item in erro.errors:
        origem, *caminho = item["loc"]
        if caminho and caminho[0] in _PARAMETROS_DE_SCHEMA:
            caminho = caminho[1:]
        erros.append({
            "campo": ".".join(str(parte) for parte in caminho) or str(origem),
            "origem": str(origem),
            "mensagem": item["msg"],
        })
    return _erro(request, 422, "dados_invalidos", "Dados de entrada inválidos.", erros)


@api.exception_handler(RegraDeNegocioViolada)
@api.exception_handler(FormatoDocumentoNaoSuportado)
def _regra_violada(request, erro):
    return _erro(request, 400, "regra_de_negocio", str(erro))


@api.exception_handler(OperacaoEmConflito)
def _conflito(request, erro):
    return _erro(request, 409, "conflito", str(erro))


@api.exception_handler(IntegrityError)
def _conflito_no_banco(request, erro):
    logger.warning("Restrição do banco recusou a gravação: %s", erro)
    return _erro(
        request, 409, "conflito", "A operação conflita com um registro já existente."
    )


@api.exception_handler(Http404)
def _nao_encontrado(request, erro):
    return _erro(request, 404, "nao_encontrado", str(erro) or "Registro não encontrado.")


@api.exception_handler(RespostaIAInvalida)
def _resposta_ia_invalida(request, erro):
    logger.error("Resposta inválida do provedor de IA: %s", erro)
    return _erro(request, 502, "ia_resposta_invalida", str(erro))


@api.exception_handler(ProvedorIAIndisponivel)
def _provedor_ia_indisponivel(request, erro):
    logger.error("Provedor de IA indisponível", exc_info=erro)
    return _erro(request, 503, "ia_indisponivel", str(erro))


@api.exception_handler(Exception)
def _erro_inesperado(request, erro):
    logger.exception("Erro não tratado na API", exc_info=erro)
    return _erro(
        request, 500, "erro_interno", "Erro interno inesperado. A falha foi registrada no log."
    )
