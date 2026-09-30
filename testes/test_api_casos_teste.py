import pytest

from modelos.models import CasoDeTeste, Escopo, Projeto
from servicos import criar_rodada

pytestmark = pytest.mark.django_db


def _criar_caso(client, escopo_id, **campos):
    corpo = {"codigo": "CT-001", "titulo": "Validar login", **campos}
    return client.post(
        f"/api/escopos/{escopo_id}/casos-de-teste", corpo, content_type="application/json"
    )


def _patch(client, caso_id, corpo):
    return client.patch(f"/api/casos-de-teste/{caso_id}", corpo, content_type="application/json")


def test_criar_caso_manual_usa_valores_padrao(client, escopo):
    resposta = _criar_caso(client, escopo.id)

    assert resposta.status_code == 201
    caso = resposta.json()
    assert caso["origem"] == "manual"
    assert caso["categoria"] == "funcional"
    assert caso["prioridade"] == "media"
    assert caso["escopo_id"] == escopo.id
    assert client.get(f"/api/casos-de-teste/{caso['id']}").json() == caso


def test_criar_caso_com_codigo_repetido_no_escopo_retorna_409(client, escopo):
    _criar_caso(client, escopo.id)

    resposta = _criar_caso(client, escopo.id, titulo="Outro título")

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito"
    assert "CT-001" in resposta.json()["detail"]


def test_criar_caso_com_categoria_invalida_retorna_422(client, escopo):
    resposta = _criar_caso(client, escopo.id, categoria="desempenho")

    assert resposta.status_code == 422
    assert CasoDeTeste.objects.count() == 0


def test_criar_caso_em_escopo_inexistente_retorna_404(client):
    assert _criar_caso(client, 999).status_code == 404


def test_listar_casos_com_filtros(client, projeto, escopo):
    outro_escopo = Escopo.objects.create(nome_arquivo="outro.docx", projeto=projeto)
    outro_projeto = Projeto.objects.create(nome="Outro projeto")
    escopo_de_outro_projeto = Escopo.objects.create(nome_arquivo="x.docx", projeto=outro_projeto)
    _criar_caso(client, escopo.id, codigo="CT-001", categoria="integracao")
    _criar_caso(client, escopo.id, codigo="CT-002")
    _criar_caso(client, outro_escopo.id, codigo="CT-001")
    _criar_caso(client, escopo_de_outro_projeto.id, codigo="CT-009")

    def codigos(consulta):
        return [caso["codigo"] for caso in client.get(f"/api/casos-de-teste{consulta}").json()]

    assert len(codigos("")) == 4
    assert codigos(f"?projeto_id={projeto.id}") == ["CT-001", "CT-002", "CT-001"]
    assert codigos(f"?escopo_id={escopo.id}") == ["CT-001", "CT-002"]
    assert codigos(f"?escopo_id={escopo.id}&categoria=integracao") == ["CT-001"]
    assert codigos("?origem=ia") == []


def test_listar_casos_com_filtro_invalido(client):
    assert client.get("/api/casos-de-teste?categoria=desempenho").status_code == 422
    assert client.get("/api/casos-de-teste?escopo_id=999").status_code == 404


def test_atualizar_caso_altera_so_campos_enviados(client, escopo):
    caso = _criar_caso(client, escopo.id, passos="1. Abrir tela").json()

    resposta = _patch(client, caso["id"], {"titulo": "Validar login com senha", "prioridade": "alta"})

    assert resposta.status_code == 200
    atualizado = resposta.json()
    assert atualizado["titulo"] == "Validar login com senha"
    assert atualizado["prioridade"] == "alta"
    assert atualizado["passos"] == "1. Abrir tela"
    assert atualizado["origem"] == "manual"


def test_atualizar_caso_ignora_campo_origem(client, escopo):
    caso = _criar_caso(client, escopo.id).json()

    resposta = _patch(client, caso["id"], {"origem": "ia"})

    assert resposta.status_code == 200
    assert resposta.json()["origem"] == "manual"


@pytest.mark.parametrize(
    "corpo",
    [{"titulo": " "}, {"codigo": None}, {"categoria": None}],
    ids=["titulo-vazio", "codigo-nulo", "categoria-nula"],
)
def test_atualizar_caso_com_valor_invalido_retorna_400(client, escopo, corpo):
    caso = _criar_caso(client, escopo.id).json()

    assert _patch(client, caso["id"], corpo).status_code == 400


def test_excluir_caso(client, escopo):
    caso = _criar_caso(client, escopo.id).json()

    resposta = client.delete(f"/api/casos-de-teste/{caso['id']}")

    assert resposta.status_code == 204
    assert client.get(f"/api/casos-de-teste/{caso['id']}").status_code == 404


def test_excluir_caso_que_ja_entrou_em_rodada_retorna_409(client, projeto, escopo):
    caso = _criar_caso(client, escopo.id).json()
    criar_rodada(projeto, "Rodada 1", casos=[CasoDeTeste.objects.get(id=caso["id"])])

    resposta = client.delete(f"/api/casos-de-teste/{caso['id']}")

    assert resposta.status_code == 409
    assert CasoDeTeste.objects.filter(id=caso["id"]).exists()


def test_documentacao_openapi_lista_os_endpoints(client):
    caminhos = client.get("/api/openapi.json").json()["paths"]

    assert {
        "/api/projetos",
        "/api/projetos/{projeto_id}/escopos",
        "/api/escopos/{escopo_id}",
        "/api/escopos/{escopo_id}/gerar-casos",
        "/api/escopos/{escopo_id}/casos-de-teste",
        "/api/casos-de-teste",
        "/api/casos-de-teste/{caso_id}",
    } <= set(caminhos)
