import pytest

from modelos import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade
from modelos.models import CasoDeTeste, Escopo, Projeto
from servicos import (
    RegraDeNegocioViolada,
    atualizar_caso_teste,
    criar_caso_teste,
    criar_rodada,
    excluir_caso_teste,
    listar_casos_teste,
)


def test_criar_caso_manual_com_valores_em_texto(escopo):
    caso = criar_caso_teste(
        escopo, codigo=" CT-001 ", titulo="Validar login", categoria="integracao", prioridade="alta"
    )

    caso.refresh_from_db()
    assert caso.codigo == "CT-001"
    assert caso.origem == OrigemCasoDeTeste.MANUAL
    assert caso.categoria == CategoriaCasoDeTeste.INTEGRACAO
    assert caso.prioridade == Prioridade.ALTA


def test_criar_caso_rejeita_codigo_duplicado_no_mesmo_escopo(escopo):
    criar_caso_teste(escopo, codigo="CT-001", titulo="Primeiro")

    with pytest.raises(RegraDeNegocioViolada, match="CT-001"):
        criar_caso_teste(escopo, codigo="CT-001", titulo="Segundo")


def test_mesmo_codigo_e_permitido_em_escopos_diferentes(escopo, projeto):
    outro_escopo = Escopo.objects.create(nome_arquivo="outro.pdf", projeto=projeto)
    criar_caso_teste(escopo, codigo="CT-001", titulo="Primeiro")

    criar_caso_teste(outro_escopo, codigo="CT-001", titulo="Segundo")

    assert CasoDeTeste.objects.filter(codigo="CT-001").count() == 2


@pytest.mark.parametrize(
    "campos",
    [
        {"codigo": "", "titulo": "Sem código"},
        {"codigo": "CT-001", "titulo": "   "},
        {"codigo": "CT-001", "titulo": "Categoria inválida", "categoria": "estresse"},
        {"codigo": "CT-001", "titulo": "Prioridade inválida", "prioridade": "urgente"},
    ],
)
def test_criar_caso_valida_campos(escopo, campos):
    with pytest.raises(RegraDeNegocioViolada):
        criar_caso_teste(escopo, **campos)
    assert CasoDeTeste.objects.count() == 0


def test_listar_casos_filtra_por_escopo_projeto_categoria_e_origem(escopo, projeto):
    outro_projeto = Projeto.objects.create(nome="Outro projeto")
    escopo_outro_projeto = Escopo.objects.create(nome_arquivo="x.docx", projeto=outro_projeto)
    criar_caso_teste(escopo, codigo="CT-002", titulo="B", categoria="integracao")
    criar_caso_teste(escopo, codigo="CT-001", titulo="A")
    criar_caso_teste(escopo_outro_projeto, codigo="CT-001", titulo="C")
    CasoDeTeste.objects.create(escopo=escopo, codigo="CT-003", titulo="IA", origem="ia")

    assert [c.codigo for c in listar_casos_teste(escopo=escopo)] == ["CT-001", "CT-002", "CT-003"]
    assert len(listar_casos_teste(projeto_id=projeto.id)) == 3
    assert [c.codigo for c in listar_casos_teste(categoria="integracao")] == ["CT-002"]
    assert [c.codigo for c in listar_casos_teste(origem=OrigemCasoDeTeste.IA)] == ["CT-003"]
    assert len(listar_casos_teste()) == 4


def test_atualizar_caso_gerado_por_ia_mantem_origem(escopo):
    caso = CasoDeTeste.objects.create(escopo=escopo, codigo="CT-001", titulo="Gerado", origem="ia")

    atualizar_caso_teste(caso, titulo="Revisado pelo usuário", prioridade="baixa")

    caso.refresh_from_db()
    assert caso.titulo == "Revisado pelo usuário"
    assert caso.prioridade == Prioridade.BAIXA
    assert caso.origem == OrigemCasoDeTeste.IA


def test_atualizar_caso_rejeita_campo_nao_editavel_e_codigo_duplicado(escopo):
    criar_caso_teste(escopo, codigo="CT-001", titulo="A")
    caso = criar_caso_teste(escopo, codigo="CT-002", titulo="B")

    with pytest.raises(RegraDeNegocioViolada, match="origem"):
        atualizar_caso_teste(caso, origem="manual")
    with pytest.raises(RegraDeNegocioViolada, match="CT-001"):
        atualizar_caso_teste(caso, codigo="CT-001")

    atualizar_caso_teste(caso, codigo="CT-002", titulo="B editado")
    caso.refresh_from_db()
    assert caso.titulo == "B editado"


def test_excluir_caso_sem_execucoes(escopo):
    caso = criar_caso_teste(escopo, codigo="CT-001", titulo="A")

    excluir_caso_teste(caso)

    assert CasoDeTeste.objects.count() == 0


def test_excluir_caso_ja_executado_e_recusado(escopo, projeto):
    caso = criar_caso_teste(escopo, codigo="CT-001", titulo="A")
    criar_rodada(projeto, "Rodada 1", casos=[caso])

    with pytest.raises(RegraDeNegocioViolada, match="rodadas"):
        excluir_caso_teste(caso)

    assert CasoDeTeste.objects.count() == 1


def test_obter_casos_por_ids_preserva_a_ordem(escopo):
    from servicos import obter_casos_por_ids

    primeiro = criar_caso_teste(escopo, codigo="CT-001", titulo="A")
    segundo = criar_caso_teste(escopo, codigo="CT-002", titulo="B")

    assert obter_casos_por_ids([segundo.id, primeiro.id]) == [segundo, primeiro]


def test_obter_casos_por_ids_recusa_ids_inexistentes(escopo):
    from servicos import obter_casos_por_ids

    caso = criar_caso_teste(escopo, codigo="CT-001", titulo="A")

    with pytest.raises(RegraDeNegocioViolada, match="998, 999"):
        obter_casos_por_ids([caso.id, 998, 999])
