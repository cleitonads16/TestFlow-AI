import pytest


@pytest.fixture
def projeto(db):
    from modelos.models import Projeto

    return Projeto.objects.create(nome="PDI - Gestor de Casos de Teste")


@pytest.fixture
def escopo(projeto):
    from modelos.models import Escopo

    return Escopo.objects.create(nome_arquivo="escopo.docx", projeto=projeto)


@pytest.fixture(autouse=True)
def diretorio_escopos_temporario(settings, tmp_path):
    """Nenhum teste grava documentos de escopo na pasta uploads/ real do projeto."""
    settings.DIRETORIO_ESCOPOS = tmp_path / "escopos"
    return settings.DIRETORIO_ESCOPOS


@pytest.fixture
def conteudo_docx():
    import io

    from docx import Document

    documento = Document()
    documento.add_paragraph("O sistema deve permitir login de usuários cadastrados.")
    buffer = io.BytesIO()
    documento.save(buffer)
    return buffer.getvalue()
