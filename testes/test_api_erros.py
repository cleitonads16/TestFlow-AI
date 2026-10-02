"""Formato padronizado de erro da API: {"detail", "codigo", "erros"}."""

import pytest
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


def test_erro_de_validacao_lista_os_campos_invalidos(client, escopo):
    resposta = client.post(
        f"/api/escopos/{escopo.id}/casos-de-teste",
        {"codigo": "CT-001", "categoria": "desempenho"},
        content_type="application/json",
    )

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert corpo["detail"] == "Dados de entrada inválidos."
    campos = {erro["campo"] for erro in corpo["erros"]}
    assert campos == {"titulo", "categoria"}
    assert {erro["origem"] for erro in corpo["erros"]} == {"body"}


def test_erro_de_validacao_em_parametro_de_consulta(client):
    resposta = client.get("/api/casos-de-teste?categoria=desempenho")

    assert resposta.status_code == 422
    assert [(e["origem"], e["campo"]) for e in resposta.json()["erros"]] == [
        ("query", "categoria")
    ]


@pytest.mark.parametrize(
    "corpo",
    [b'{"nome": "Portal', '{"nome": "Homologação"}'.encode("latin-1")],
    ids=["json-malformado", "texto-fora-de-utf8"],
)
def test_corpo_ilegivel_segue_o_formato_padrao_de_erro(client, corpo):
    resposta = client.post("/api/projetos", corpo, content_type="application/json")

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "corpo_invalido"
    assert "UTF-8" in resposta.json()["detail"]


def test_regra_de_negocio_violada(client):
    resposta = client.post("/api/projetos", {"nome": " "}, content_type="application/json")

    assert resposta.status_code == 400
    assert resposta.json() == {"detail": "O campo nome é obrigatório.", "codigo": "regra_de_negocio"}


def test_recurso_nao_encontrado_tem_mensagem_em_portugues(client):
    resposta = client.get("/api/rodadas/42")

    assert resposta.status_code == 404
    assert resposta.json() == {
        "detail": "Rodada de execução 42 não encontrada.",
        "codigo": "nao_encontrado",
    }


def test_restricao_do_banco_vira_conflito(client, monkeypatch):
    def gravar_com_conflito(*args, **kwargs):
        raise IntegrityError("UNIQUE constraint failed")

    monkeypatch.setattr("rotas.projetos.criar_projeto", gravar_com_conflito)

    resposta = client.post("/api/projetos", {"nome": "X"}, content_type="application/json")

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito"
    assert "UNIQUE" not in resposta.json()["detail"]


def test_erro_inesperado_nao_expoe_detalhes_internos(client, monkeypatch):
    def falhar(*args, **kwargs):
        raise RuntimeError("senha=segredo no traceback")

    monkeypatch.setattr("rotas.projetos.listar_projetos", falhar)

    resposta = client.get("/api/projetos")

    assert resposta.status_code == 500
    assert resposta.json()["codigo"] == "erro_interno"
    assert "segredo" not in resposta.content.decode()
