"""Instância do Django Ninja: registra os routers e traduz os erros do core para HTTP.

A API não tem regra de negócio (docs/arquitetura-e-cronograma.md, seção 1):
os routers só validam a entrada, chamam `servicos` e usam os handlers
abaixo para converter as exceções do core em respostas HTTP.

Todo erro sai no mesmo formato (`schemas.ErroSaida`), descrito para quem
consome a API em `_DESCRICAO`, que aparece no topo do Swagger (`/api/docs`).
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

_DESCRICAO = """
API do gestor de casos de teste com geração assistida por IA (projeto de PDI).

**Fluxo de uso**, na ordem das seções abaixo:

1. Crie um **projeto**.
2. Envie o **escopo** do projeto (.docx ou .pdf) e peça a geração dos casos
   de teste via IA.
3. Revise os **casos de teste** gerados ou cadastre casos manuais.
4. Monte uma **rodada de execução** com os casos a testar.
5. Registre o resultado de cada **execução** e abra **defeitos** nas que falharem.

**Formato de erro.** Todo erro sai no mesmo corpo:
`{"detail": "<mensagem>", "codigo": "<tipo do erro>", "erros": [...]}`.
Use `codigo` para tratar o erro no cliente; `erros` só vem nos erros de validação (422).

| HTTP | `codigo` | Quando |
|---|---|---|
| 400 | `regra_de_negocio` | A entrada é válida, mas uma regra do produto recusa a operação |
| 404 | `nao_encontrado` | O registro informado no caminho não existe |
| 409 | `conflito` | A operação duplicaria um registro ou apagaria histórico |
| 422 | `dados_invalidos` | Corpo ou parâmetros fora do formato esperado |
| 502 | `ia_resposta_invalida` | O provedor de IA respondeu fora do formato esperado |
| 503 | `ia_indisponivel` | O provedor de IA não respondeu (tente de novo mais tarde) |
| 500 | `erro_interno` | Falha inesperada, registrada no log do servidor |
"""

_TAGS = [
    {"name": "Projetos", "description": "Sistema ou produto que está sendo testado."},
    {
        "name": "Escopos",
        "description": "Documento de escopo do projeto e geração dos casos de teste via IA.",
    },
    {
        "name": "Casos de teste",
        "description": "Revisão dos casos gerados pela IA e cadastro de casos manuais.",
    },
    {
        "name": "Rodadas de execução",
        "description": "Ciclo de testes: agrupa os casos que serão executados juntos.",
    },
    {"name": "Execuções", "description": "Resultado de cada caso dentro de uma rodada."},
    {"name": "Defeitos", "description": "Falhas encontradas nas execuções e o seu andamento."},
]

api = NinjaAPI(
    title="TestFlow AI — Gestor de Casos de Teste",
    version="0.7.0",
    description=_DESCRICAO.strip(),
    openapi_extra={"tags": _TAGS},
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
