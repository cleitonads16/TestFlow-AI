"""Documentação OpenAPI (Swagger em /api/docs): completa e com exemplos que a própria API aceita."""

import pytest

import schemas

ORDEM_DAS_TAGS = [
    "Projetos",
    "Escopos",
    "Casos de teste",
    "Rodadas de execução",
    "Execuções",
    "Defeitos",
]

SCHEMAS_DE_ENTRADA = [
    schemas.ProjetoEntrada,
    schemas.CasoTesteEntrada,
    schemas.CasoTesteAtualizacao,
    schemas.RodadaEntrada,
    schemas.InclusaoDeCasos,
    schemas.ResultadoExecucao,
    schemas.DefeitoEntrada,
    schemas.DefeitoAtualizacao,
]


@pytest.fixture
def openapi(client):
    return client.get("/api/openapi.json").json()


def _operacoes(openapi):
    for caminho, metodos in openapi["paths"].items():
        for metodo, operacao in metodos.items():
            yield f"{metodo.upper()} {caminho}", operacao


def test_tags_aparecem_na_ordem_do_fluxo_e_com_descricao(openapi):
    assert [tag["name"] for tag in openapi["tags"]] == ORDEM_DAS_TAGS
    assert all(tag["description"] for tag in openapi["tags"])


def test_toda_operacao_tem_tag_conhecida_e_resumo_proprio(openapi):
    for nome, operacao in _operacoes(openapi):
        assert operacao["tags"][0] in ORDEM_DAS_TAGS, nome
        # Sem `summary=` o Ninja deriva o resumo do nome da função ("Listar", "Criar"),
        # que se repete entre as seções e perde os acentos.
        assert len(operacao["summary"].split()) >= 2, nome


def test_toda_resposta_de_erro_usa_o_formato_padrao(openapi):
    for nome, operacao in _operacoes(openapi):
        for status, resposta in operacao["responses"].items():
            if int(status) >= 400:
                esquema = resposta["content"]["application/json"]["schema"]
                assert esquema == {"$ref": "#/components/schemas/ErroSaida"}, (nome, status)


def test_descricao_da_api_explica_os_codigos_de_erro(openapi):
    descricao = openapi["info"]["description"]

    for codigo in (
        "regra_de_negocio",
        "nao_encontrado",
        "conflito",
        "dados_invalidos",
        "ia_resposta_invalida",
        "ia_indisponivel",
        "erro_interno",
    ):
        assert codigo in descricao


@pytest.mark.parametrize("schema", SCHEMAS_DE_ENTRADA, ids=lambda s: s.__name__)
def test_exemplo_do_corpo_e_aceito_pelo_proprio_schema(openapi, schema):
    exemplos = openapi["components"]["schemas"][schema.__name__]["examples"]

    assert exemplos
    for exemplo in exemplos:
        schema.model_validate(exemplo)
