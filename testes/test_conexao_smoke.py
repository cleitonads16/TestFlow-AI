from io import StringIO

import pytest
from django.core.management import call_command

from modelos import CategoriaCasoDeTeste, Prioridade
from modelos.models import CasoDeTeste, Escopo, Projeto


@pytest.mark.django_db
def test_criar_tabelas_e_inserir_registro():
    projeto = Projeto.objects.create(
        nome="PDI - Gestor de Casos de Teste", descricao="Projeto de teste"
    )
    escopo = Escopo.objects.create(nome_arquivo="escopo-exemplo.docx", projeto=projeto)
    CasoDeTeste.objects.create(
        codigo="CT-001",
        titulo="Validar modelagem das entidades",
        categoria=CategoriaCasoDeTeste.FUNCIONAL.value,
        prioridade=Prioridade.ALTA.value,
        escopo=escopo,
    )

    assert Projeto.objects.count() == 1
    assert Escopo.objects.count() == 1
    assert CasoDeTeste.objects.count() == 1

    caso_salvo = CasoDeTeste.objects.select_related("escopo__projeto").get()
    assert caso_salvo.titulo == "Validar modelagem das entidades"
    assert caso_salvo.categoria == CategoriaCasoDeTeste.FUNCIONAL
    assert caso_salvo.escopo.projeto.nome == "PDI - Gestor de Casos de Teste"


@pytest.mark.django_db
def test_migrations_estao_em_dia_com_os_models():
    saida = StringIO()

    call_command("makemigrations", "--check", "--dry-run", stdout=saida)
