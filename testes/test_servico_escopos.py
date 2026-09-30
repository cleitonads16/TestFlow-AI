import pytest

from modelos import StatusEscopo
from modelos.models import Escopo
from servicos import (
    RegraDeNegocioViolada,
    caminho_documento,
    criar_projeto,
    listar_escopos,
    registrar_escopo,
)
from servicos.escopos import TAMANHO_MAXIMO_BYTES

pytestmark = pytest.mark.django_db


def test_criar_projeto_exige_nome():
    with pytest.raises(RegraDeNegocioViolada, match="nome"):
        criar_projeto("   ")


def test_registrar_escopo_grava_documento_e_cria_escopo_pendente(projeto, conteudo_docx):
    escopo = registrar_escopo(projeto, "escopo-login.docx", conteudo_docx)

    assert escopo.status == StatusEscopo.PENDENTE
    assert escopo.nome_arquivo == "escopo-login.docx"
    assert escopo.data_upload is not None
    assert caminho_documento(escopo).read_bytes() == conteudo_docx


def test_registrar_escopo_ignora_diretorios_do_nome_enviado(
    projeto, conteudo_docx, diretorio_escopos_temporario
):
    escopo = registrar_escopo(projeto, "../../settings.docx", conteudo_docx)

    assert escopo.nome_arquivo == "settings.docx"
    assert caminho_documento(escopo).parent == diretorio_escopos_temporario


@pytest.mark.parametrize(
    "nome, conteudo, mensagem",
    [
        ("escopo.txt", b"texto", "não suportado"),
        ("escopo", b"texto", "sem extensão"),
        ("escopo.pdf", b"", "vazio"),
        ("escopo.pdf", b"x" * (TAMANHO_MAXIMO_BYTES + 1), "limite"),
        ("escopo.docx", b"so renomeado para docx", "corrompido"),
        ("escopo.pdf", b"so renomeado para pdf", "corrompido"),
    ],
    ids=[
        "formato-txt",
        "sem-extensao",
        "vazio",
        "acima-do-limite",
        "docx-ilegivel",
        "pdf-ilegivel",
    ],
)
def test_registrar_escopo_recusa_arquivo_invalido(projeto, nome, conteudo, mensagem):
    with pytest.raises(RegraDeNegocioViolada, match=mensagem):
        registrar_escopo(projeto, nome, conteudo)
    assert Escopo.objects.count() == 0


def test_caminho_documento_recusa_escopo_sem_arquivo(escopo):
    with pytest.raises(RegraDeNegocioViolada, match="não foi encontrado"):
        caminho_documento(escopo)


def test_listar_escopos_traz_so_os_do_projeto(projeto, conteudo_docx):
    outro = criar_projeto("Outro projeto")
    registrar_escopo(outro, "outro.docx", conteudo_docx)
    escopo = registrar_escopo(projeto, "meu.docx", conteudo_docx)

    assert listar_escopos(projeto) == [escopo]
