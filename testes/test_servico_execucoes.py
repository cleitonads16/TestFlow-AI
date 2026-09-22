from datetime import date

import pytest
from django.db import IntegrityError, transaction

from modelos import SeveridadeDefeito, StatusDefeito, StatusExecucaoCaso
from modelos.models import Defeito, Escopo, ExecucaoDeCaso, Projeto, RodadaDeExecucao
from servicos import (
    RegraDeNegocioViolada,
    adicionar_casos_a_rodada,
    atualizar_status_defeito,
    criar_caso_teste,
    criar_rodada,
    registrar_defeito,
    registrar_execucao,
    resumo_rodada,
)


@pytest.fixture
def casos(escopo):
    return [
        criar_caso_teste(escopo, codigo=f"CT-00{i}", titulo=f"Caso {i}") for i in range(1, 4)
    ]


@pytest.fixture
def rodada(projeto, casos):
    return criar_rodada(projeto, "Rodada 1", casos=casos)


def test_criar_rodada_agenda_casos_como_pendentes(projeto, casos):
    rodada = criar_rodada(
        projeto, "Rodada 1", data_inicio=date(2026, 9, 23), data_fim=date(2026, 9, 29), casos=casos
    )

    execucoes = list(rodada.execucoes.all())
    assert len(execucoes) == 3
    assert {e.status for e in execucoes} == {StatusExecucaoCaso.PENDENTE}
    assert all(e.data_execucao is None for e in execucoes)


def test_criar_rodada_rejeita_datas_invertidas_e_nome_vazio(projeto):
    with pytest.raises(RegraDeNegocioViolada, match="data de fim"):
        criar_rodada(projeto, "Rodada", data_inicio=date(2026, 9, 29), data_fim=date(2026, 9, 23))
    with pytest.raises(RegraDeNegocioViolada, match="nome"):
        criar_rodada(projeto, "  ")
    assert RodadaDeExecucao.objects.count() == 0


def test_criar_rodada_com_caso_de_outro_projeto_nao_grava_nada(projeto, casos):
    outro_projeto = Projeto.objects.create(nome="Outro")
    escopo_alheio = Escopo.objects.create(nome_arquivo="x.docx", projeto=outro_projeto)
    caso_alheio = criar_caso_teste(escopo_alheio, codigo="CT-900", titulo="Alheio")

    with pytest.raises(RegraDeNegocioViolada, match="outro projeto"):
        criar_rodada(projeto, "Rodada 1", casos=[*casos, caso_alheio])

    assert RodadaDeExecucao.objects.count() == 0
    assert ExecucaoDeCaso.objects.count() == 0


def test_adicionar_caso_repetido_na_rodada_e_recusado(rodada, casos, escopo):
    novo = criar_caso_teste(escopo, codigo="CT-004", titulo="Novo")

    with pytest.raises(RegraDeNegocioViolada, match="já está"):
        adicionar_casos_a_rodada(rodada, [casos[0]])
    with pytest.raises(RegraDeNegocioViolada, match="já está"):
        adicionar_casos_a_rodada(rodada, [novo, novo])

    adicionar_casos_a_rodada(rodada, [novo])
    assert rodada.execucoes.count() == 4


def test_banco_impede_caso_duplicado_na_rodada(rodada, casos):
    with pytest.raises(IntegrityError), transaction.atomic():
        ExecucaoDeCaso.objects.create(rodada=rodada, caso_de_teste=casos[0])


def test_registrar_execucao_grava_resultado_e_data(rodada):
    execucao = rodada.execucoes.first()

    registrar_execucao(execucao, "passou", observacoes="OK em homologação")

    execucao.refresh_from_db()
    assert execucao.status == StatusExecucaoCaso.PASSOU
    assert execucao.observacoes == "OK em homologação"
    assert execucao.data_execucao is not None


def test_registrar_execucao_valida_status(rodada):
    execucao = rodada.execucoes.first()

    with pytest.raises(RegraDeNegocioViolada, match="resultado"):
        registrar_execucao(execucao, StatusExecucaoCaso.PENDENTE)
    with pytest.raises(RegraDeNegocioViolada, match="inválido"):
        registrar_execucao(execucao, "aprovado")
    with pytest.raises(RegraDeNegocioViolada, match="bloqueada"):
        registrar_execucao(execucao, "bloqueado")

    registrar_execucao(execucao, "bloqueado", observacoes="Ambiente de QA fora do ar")
    execucao.refresh_from_db()
    assert execucao.status == StatusExecucaoCaso.BLOQUEADO


def test_registrar_defeito_somente_em_execucao_que_falhou(rodada):
    execucao = rodada.execucoes.first()

    with pytest.raises(RegraDeNegocioViolada, match="falhou"):
        registrar_defeito(execucao, "Botão não responde")

    registrar_execucao(execucao, "falhou")
    defeito = registrar_defeito(execucao, "Botão não responde", severidade="alta")

    defeito.refresh_from_db()
    assert defeito.status == StatusDefeito.ABERTO
    assert defeito.severidade == SeveridadeDefeito.ALTA
    assert list(execucao.defeitos.all()) == [defeito]


def test_registrar_defeito_valida_descricao_e_severidade(rodada):
    execucao = registrar_execucao(rodada.execucoes.first(), "falhou")

    with pytest.raises(RegraDeNegocioViolada, match="descricao"):
        registrar_defeito(execucao, "")
    with pytest.raises(RegraDeNegocioViolada, match="inválido"):
        registrar_defeito(execucao, "Erro", severidade="gravissima")
    assert Defeito.objects.count() == 0


def test_atualizar_status_defeito(rodada):
    execucao = registrar_execucao(rodada.execucoes.first(), "falhou")
    defeito = registrar_defeito(execucao, "Erro ao salvar")

    atualizar_status_defeito(defeito, StatusDefeito.CORRIGIDO)
    defeito.refresh_from_db()
    assert defeito.status == StatusDefeito.CORRIGIDO

    with pytest.raises(RegraDeNegocioViolada):
        atualizar_status_defeito(defeito, "resolvido")


def test_resumo_rodada_conta_execucoes_por_status(rodada):
    primeira, segunda, _ = rodada.execucoes.order_by("id")
    registrar_execucao(primeira, "passou")
    registrar_execucao(segunda, "falhou")

    assert resumo_rodada(rodada) == {
        "pendente": 1,
        "passou": 1,
        "falhou": 1,
        "bloqueado": 0,
        "total": 3,
    }
