"""Instância do Django Ninja: registra os routers e traduz os erros do core para HTTP.

A API não tem regra de negócio (docs/arquitetura-e-cronograma.md, seção 1):
os routers só validam a entrada, chamam `servicos` e usam os handlers
abaixo para converter as exceções do core em respostas HTTP.
"""

import logging

from ninja import NinjaAPI

from documentos import FormatoDocumentoNaoSuportado
from ia import ProvedorIAIndisponivel, RespostaIAInvalida
from rotas import casos_teste, escopos, projetos
from servicos import RegraDeNegocioViolada

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="TestFlow AI — Gestor de Casos de Teste",
    version="0.5.0",
    description=(
        "API do gestor de casos de teste com geração assistida por IA "
        "(projeto de PDI, Fase 2)."
    ),
)

api.add_router("", projetos.router)
api.add_router("", escopos.router)
api.add_router("", casos_teste.router)


@api.exception_handler(RegraDeNegocioViolada)
@api.exception_handler(FormatoDocumentoNaoSuportado)
def _regra_violada(request, erro):
    return api.create_response(request, {"detail": str(erro)}, status=400)


@api.exception_handler(RespostaIAInvalida)
def _resposta_ia_invalida(request, erro):
    logger.error("Resposta inválida do provedor de IA: %s", erro)
    return api.create_response(request, {"detail": str(erro)}, status=502)


@api.exception_handler(ProvedorIAIndisponivel)
def _provedor_ia_indisponivel(request, erro):
    logger.error("Provedor de IA indisponível", exc_info=erro)
    return api.create_response(request, {"detail": str(erro)}, status=503)
