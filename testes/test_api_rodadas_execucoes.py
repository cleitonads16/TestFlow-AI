import pytest

from modelos.models import ExecucaoDeCaso, Projeto, RodadaDeExecucao
from servicos import criar_caso_teste

pytestmark = pytest.mark.django_db


@pytest.fixture
def casos(escopo):
    return [
        criar_caso_teste(escopo, codigo=f"CT-00{i}", titulo=f"Caso {i}") for i in range(1, 4)
    ]


def _post(client, caminho, corpo):
    return client.post(caminho, corpo, content_type="application/json")


def _put(client, caminho, corpo):
    return client.put(caminho, corpo, content_type="application/json")


def _criar_rodada(client, projeto_id, casos_ids=(), **campos):
    corpo = {"nome": "Rodada 1", "casos_ids": list(casos_ids), **campos}
    return _post(client, f"/api/projetos/{projeto_id}/rodadas", corpo)


@pytest.fixture
def rodada(client, projeto, casos):
    return _criar_rodada(client, projeto.id, [caso.id for caso in casos]).json()


def _execucao_do_caso(client, rodada_id, codigo):
    execucoes = client.get(f"/api/rodadas/{rodada_id}/execucoes").json()
    return next(execucao for execucao in execucoes if execucao["caso_codigo"] == codigo)


def test_criar_rodada_agenda_casos_pendentes(client, projeto, casos):
    resposta = _criar_rodada(
        client,
        projeto.id,
        [casos[0].id, casos[1].id],
        data_inicio="2026-10-07",
        data_fim="2026-10-13",
    )

    assert resposta.status_code == 201
    rodada = resposta.json()
    assert rodada["data_inicio"] == "2026-10-07"
    execucoes = client.get(f"/api/rodadas/{rodada['id']}/execucoes").json()
    assert [e["caso_codigo"] for e in execucoes] == ["CT-001", "CT-002"]
    assert {e["status"] for e in execucoes} == {"pendente"}
    assert client.get(f"/api/projetos/{projeto.id}/rodadas").json() == [rodada]


def test_criar_rodada_sem_casos(client, projeto):
    resposta = _criar_rodada(client, projeto.id)

    assert resposta.status_code == 201
    assert client.get(f"/api/rodadas/{resposta.json()['id']}/resumo").json()["total"] == 0


def test_criar_rodada_com_datas_invertidas_retorna_400(client, projeto):
    resposta = _criar_rodada(client, projeto.id, data_inicio="2026-10-13", data_fim="2026-10-07")

    assert resposta.status_code == 400
    assert RodadaDeExecucao.objects.count() == 0


def test_criar_rodada_com_caso_inexistente_nao_grava_nada(client, projeto, casos):
    resposta = _criar_rodada(client, projeto.id, [casos[0].id, 999])

    assert resposta.status_code == 400
    assert "999" in resposta.json()["detail"]
    assert RodadaDeExecucao.objects.count() == 0


def test_criar_rodada_com_caso_de_outro_projeto_retorna_400(client, casos):
    outro_projeto = Projeto.objects.create(nome="Outro projeto")

    resposta = _criar_rodada(client, outro_projeto.id, [casos[0].id])

    assert resposta.status_code == 400
    assert "outro projeto" in resposta.json()["detail"]


def test_adicionar_casos_a_rodada(client, projeto, casos):
    rodada = _criar_rodada(client, projeto.id, [casos[0].id]).json()

    resposta = _post(client, f"/api/rodadas/{rodada['id']}/casos", {"casos_ids": [casos[2].id]})

    assert resposta.status_code == 201
    assert [e["caso_codigo"] for e in resposta.json()] == ["CT-003"]
    assert client.get(f"/api/rodadas/{rodada['id']}/resumo").json()["total"] == 2


def test_adicionar_caso_que_ja_esta_na_rodada_retorna_409(client, rodada, casos):
    resposta = _post(client, f"/api/rodadas/{rodada['id']}/casos", {"casos_ids": [casos[0].id]})

    assert resposta.status_code == 409


def test_adicionar_lista_vazia_de_casos_retorna_422(client, rodada):
    resposta = _post(client, f"/api/rodadas/{rodada['id']}/casos", {"casos_ids": []})

    assert resposta.status_code == 422


def test_registrar_resultados_e_consultar_resumo(client, rodada):
    passou = _execucao_do_caso(client, rodada["id"], "CT-001")
    bloqueado = _execucao_do_caso(client, rodada["id"], "CT-002")

    resposta = _put(client, f"/api/execucoes/{passou['id']}/resultado", {"status": "passou"})
    _put(
        client,
        f"/api/execucoes/{bloqueado['id']}/resultado",
        {"status": "bloqueado", "observacoes": "Ambiente fora do ar"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "passou"
    assert resposta.json()["data_execucao"] is not None
    detalhe = client.get(f"/api/rodadas/{rodada['id']}").json()
    assert detalhe["resumo"] == {
        "pendente": 1,
        "passou": 1,
        "falhou": 0,
        "bloqueado": 1,
        "total": 3,
    }
    filtradas = client.get(f"/api/rodadas/{rodada['id']}/execucoes?status=bloqueado").json()
    assert [e["observacoes"] for e in filtradas] == ["Ambiente fora do ar"]


@pytest.mark.parametrize(
    "corpo, status_esperado",
    [
        ({"status": "pendente"}, 400),
        ({"status": "bloqueado"}, 400),
        ({"status": "aprovado"}, 422),
    ],
    ids=["pendente", "bloqueado-sem-observacao", "status-inexistente"],
)
def test_registrar_resultado_invalido(client, rodada, corpo, status_esperado):
    execucao = _execucao_do_caso(client, rodada["id"], "CT-001")

    resposta = _put(client, f"/api/execucoes/{execucao['id']}/resultado", corpo)

    assert resposta.status_code == status_esperado
    assert ExecucaoDeCaso.objects.get(id=execucao["id"]).status == "pendente"


def test_abrir_defeito_em_execucao_que_falhou(client, rodada):
    execucao = _execucao_do_caso(client, rodada["id"], "CT-001")
    _put(client, f"/api/execucoes/{execucao['id']}/resultado", {"status": "falhou"})

    resposta = _post(
        client,
        f"/api/execucoes/{execucao['id']}/defeitos",
        {"descricao": "Botão de login não responde", "severidade": "alta"},
    )

    assert resposta.status_code == 201
    defeito = resposta.json()
    assert defeito["status"] == "aberto"
    assert defeito["severidade"] == "alta"
    assert defeito["caso_codigo"] == "CT-001"
    assert client.get(f"/api/execucoes/{execucao['id']}/defeitos").json() == [defeito]
    assert client.get(f"/api/defeitos/{defeito['id']}").json() == defeito


def test_abrir_defeito_em_execucao_pendente_retorna_400(client, rodada):
    execucao = _execucao_do_caso(client, rodada["id"], "CT-001")

    resposta = _post(client, f"/api/execucoes/{execucao['id']}/defeitos", {"descricao": "Falha"})

    assert resposta.status_code == 400
    assert "falhou" in resposta.json()["detail"]


def test_atualizar_status_do_defeito(client, rodada):
    execucao = _execucao_do_caso(client, rodada["id"], "CT-001")
    _put(client, f"/api/execucoes/{execucao['id']}/resultado", {"status": "falhou"})
    defeito = _post(
        client, f"/api/execucoes/{execucao['id']}/defeitos", {"descricao": "Falha"}
    ).json()

    resposta = client.patch(
        f"/api/defeitos/{defeito['id']}", {"status": "corrigido"}, content_type="application/json"
    )

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "corrigido"


def test_listar_defeitos_com_filtros(client, projeto, rodada):
    for codigo, severidade in [("CT-001", "alta"), ("CT-002", "baixa")]:
        execucao = _execucao_do_caso(client, rodada["id"], codigo)
        _put(client, f"/api/execucoes/{execucao['id']}/resultado", {"status": "falhou"})
        _post(
            client,
            f"/api/execucoes/{execucao['id']}/defeitos",
            {"descricao": f"Falha em {codigo}", "severidade": severidade},
        )

    def codigos(consulta):
        return sorted(d["caso_codigo"] for d in client.get(f"/api/defeitos{consulta}").json())

    assert codigos("") == ["CT-001", "CT-002"]
    assert codigos(f"?projeto_id={projeto.id}&severidade=alta") == ["CT-001"]
    assert codigos(f"?rodada_id={rodada['id']}&status=aberto") == ["CT-001", "CT-002"]
    assert codigos("?status=fechado") == []
    assert codigos(f"?projeto_id={projeto.id + 1}") == []


@pytest.mark.parametrize(
    "caminho",
    [
        "/api/projetos/999/rodadas",
        "/api/rodadas/999",
        "/api/rodadas/999/resumo",
        "/api/rodadas/999/execucoes",
        "/api/execucoes/999",
        "/api/execucoes/999/defeitos",
        "/api/defeitos/999",
    ],
)
def test_recurso_inexistente_retorna_404(client, caminho):
    assert client.get(caminho).status_code == 404

