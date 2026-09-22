import pytest


@pytest.fixture
def projeto(db):
    from modelos.models import Projeto

    return Projeto.objects.create(nome="PDI - Gestor de Casos de Teste")


@pytest.fixture
def escopo(projeto):
    from modelos.models import Escopo

    return Escopo.objects.create(nome_arquivo="escopo.docx", projeto=projeto)
