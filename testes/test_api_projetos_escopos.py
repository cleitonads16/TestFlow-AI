import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ia import CasoTesteGerado, LLMProvider, ProvedorIAIndisponivel, RespostaIAInvalida
from modelos import CategoriaCasoDeTeste, Prioridade, StatusEscopo
from modelos.models import CasoDeTeste, Escopo, GeracaoIA

pytestmark = pytest.mark.django_db


class _ProvedorFalso(LLMProvider):
    """Dublê de LLMProvider — a API é testada sem chamar a IA real."""

    def __init__(self, casos=(), erro=None):
        self._casos = list(casos)
        self._erro = erro

    @property
    def nome(self) -> str:
        return "falso"

    @property
    def modelo(self) -> str:
        return "modelo-de-teste"

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        if self._erro is not None:
            raise self._erro
        return self._casos


def _caso_gerado(codigo="CT-001"):
    return CasoTesteGerado(
        codigo=codigo,
        titulo="Validar login",
        categoria=CategoriaCasoDeTeste.FUNCIONAL,
        pre_condicao="Usuário cadastrado",
        passos="1. Acessar login\n2. Informar credenciais",
        resultado_esperado="Usuário autenticado",
        prioridade=Prioridade.ALTA,
    )


@pytest.fixture
def usar_provedor(monkeypatch):
    def _usar(provedor):
        monkeypatch.setattr("rotas.escopos.obter_provedor_llm", lambda: provedor)

    return _usar


def _enviar_escopo(client, projeto_id, conteudo, nome="escopo.docx"):
    return client.post(
        f"/api/projetos/{projeto_id}/escopos",
        {"arquivo": SimpleUploadedFile(nome, conteudo)},
    )


def test_criar_listar_e_detalhar_projeto(client):
    resposta = client.post(
        "/api/projetos",
        {"nome": "Portal RH", "descricao": "Escopo do portal"},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    projeto = resposta.json()
    assert projeto["nome"] == "Portal RH"
    assert client.get("/api/projetos").json() == [projeto]
    assert client.get(f"/api/projetos/{projeto['id']}").json() == projeto


def test_criar_projeto_com_nome_vazio_retorna_400(client):
    resposta = client.post("/api/projetos", {"nome": "  "}, content_type="application/json")

    assert resposta.status_code == 400
    assert "nome" in resposta.json()["detail"]


def test_projeto_inexistente_retorna_404(client):
    assert client.get("/api/projetos/999").status_code == 404


def test_enviar_escopo_cria_escopo_pendente(client, projeto, conteudo_docx):
    resposta = _enviar_escopo(client, projeto.id, conteudo_docx)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "pendente"
    assert corpo["nome_arquivo"] == "escopo.docx"
    assert corpo["projeto_id"] == projeto.id
    listagem = client.get(f"/api/projetos/{projeto.id}/escopos").json()
    assert [escopo["id"] for escopo in listagem] == [corpo["id"]]


def test_enviar_escopo_em_formato_nao_suportado_retorna_400(client, projeto):
    resposta = _enviar_escopo(client, projeto.id, b"texto", nome="escopo.txt")

    assert resposta.status_code == 400
    assert "não suportado" in resposta.json()["detail"]
    assert Escopo.objects.count() == 0


def test_enviar_escopo_corrompido_retorna_400(client, projeto):
    resposta = _enviar_escopo(client, projeto.id, b"so renomeado para docx")

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "regra_de_negocio"
    assert "corrompido" in resposta.json()["detail"]
    assert Escopo.objects.count() == 0


def test_enviar_escopo_sem_arquivo_retorna_422(client, projeto):
    assert client.post(f"/api/projetos/{projeto.id}/escopos").status_code == 422


def test_gerar_casos_persiste_e_retorna_casos(client, projeto, conteudo_docx, usar_provedor):
    escopo_id = _enviar_escopo(client, projeto.id, conteudo_docx).json()["id"]
    usar_provedor(_ProvedorFalso([_caso_gerado("CT-001"), _caso_gerado("CT-002")]))

    resposta = client.post(f"/api/escopos/{escopo_id}/gerar-casos")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["quantidade_casos_gerados"] == 2
    assert corpo["escopo"]["status"] == "processado"
    assert {caso["codigo"] for caso in corpo["casos"]} == {"CT-001", "CT-002"}
    assert all(caso["origem"] == "ia" for caso in corpo["casos"])
    assert GeracaoIA.objects.get().escopo_id == escopo_id
    detalhe = client.get(f"/api/escopos/{escopo_id}").json()
    assert "login" in detalhe["texto_extraido"].lower()


def test_gerar_casos_de_novo_retorna_409(client, projeto, conteudo_docx, usar_provedor):
    escopo_id = _enviar_escopo(client, projeto.id, conteudo_docx).json()["id"]
    usar_provedor(_ProvedorFalso([_caso_gerado()]))
    client.post(f"/api/escopos/{escopo_id}/gerar-casos")

    resposta = client.post(f"/api/escopos/{escopo_id}/gerar-casos")

    assert resposta.status_code == 409
    assert "já foi processado" in resposta.json()["detail"]
    assert CasoDeTeste.objects.count() == 1


@pytest.mark.parametrize(
    "erro, status_esperado",
    [
        (RespostaIAInvalida("formato inesperado"), 502),
        (ProvedorIAIndisponivel("sem resposta"), 503),
    ],
    ids=["resposta-invalida", "provedor-indisponivel"],
)
def test_falha_da_ia_retorna_5xx_e_marca_escopo_com_erro(
    client, projeto, conteudo_docx, usar_provedor, erro, status_esperado
):
    escopo_id = _enviar_escopo(client, projeto.id, conteudo_docx).json()["id"]
    usar_provedor(_ProvedorFalso(erro=erro))

    resposta = client.post(f"/api/escopos/{escopo_id}/gerar-casos")

    assert resposta.status_code == status_esperado
    assert resposta.json()["detail"] == str(erro)
    assert Escopo.objects.get(id=escopo_id).status == StatusEscopo.ERRO


def test_gerar_casos_sem_documento_gravado_retorna_400(client, escopo, usar_provedor):
    usar_provedor(_ProvedorFalso([_caso_gerado()]))

    resposta = client.post(f"/api/escopos/{escopo.id}/gerar-casos")

    assert resposta.status_code == 400
    assert "não foi encontrado" in resposta.json()["detail"]


def _docx_vazio():
    import io

    from docx import Document

    buffer = io.BytesIO()
    Document().save(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "conteudo, mensagem",
    [(b"conteudo invalido", "corrompido"), (_docx_vazio(), "não tem texto")],
    ids=["ilegivel", "sem-texto"],
)
def test_gerar_casos_com_documento_gravado_invalido_retorna_400(
    client, escopo, diretorio_escopos_temporario, usar_provedor, conteudo, mensagem
):
    """Documento gravado antes da validação no envio: a geração recusa com 400, não 500."""
    diretorio_escopos_temporario.mkdir(parents=True)
    (diretorio_escopos_temporario / f"{escopo.id}.docx").write_bytes(conteudo)
    usar_provedor(_ProvedorFalso([_caso_gerado()]))

    resposta = client.post(f"/api/escopos/{escopo.id}/gerar-casos")

    assert resposta.status_code == 400
    assert mensagem in resposta.json()["detail"]
    assert Escopo.objects.get(id=escopo.id).status == StatusEscopo.ERRO


def test_gerar_casos_de_escopo_inexistente_retorna_404(client):
    assert client.post("/api/escopos/999/gerar-casos").status_code == 404
