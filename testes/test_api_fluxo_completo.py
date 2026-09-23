"""Teste de integração: o fluxo inteiro do produto, só pela API.

Projeto -> envio do escopo -> geração de casos via IA (dublê) -> caso manual
-> revisão -> rodada -> resultados -> defeito -> resumo -> correção do defeito.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ia import CasoTesteGerado, LLMProvider
from modelos import CategoriaCasoDeTeste, Prioridade

pytestmark = pytest.mark.django_db


class _ProvedorFalso(LLMProvider):
    @property
    def nome(self) -> str:
        return "falso"

    @property
    def modelo(self) -> str:
        return "modelo-de-teste"

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        return [
            CasoTesteGerado(
                codigo=f"CT-00{i}",
                titulo=titulo,
                categoria=CategoriaCasoDeTeste.FUNCIONAL,
                pre_condicao=None,
                passos=None,
                resultado_esperado=None,
                prioridade=Prioridade.ALTA,
            )
            for i, titulo in enumerate(["Login válido", "Login com senha errada"], start=1)
        ]


def _json(client, metodo, caminho, corpo=None, esperado=200):
    resposta = getattr(client, metodo)(caminho, corpo, content_type="application/json")
    assert resposta.status_code == esperado, resposta.content
    return resposta.json() if resposta.content else None


def test_fluxo_completo_do_escopo_ao_defeito(client, conteudo_docx, monkeypatch):
    monkeypatch.setattr("rotas.escopos.obter_provedor_llm", lambda: _ProvedorFalso())

    projeto = _json(client, "post", "/api/projetos", {"nome": "Portal RH"}, esperado=201)

    envio = client.post(
        f"/api/projetos/{projeto['id']}/escopos",
        {"arquivo": SimpleUploadedFile("escopo-portal.docx", conteudo_docx)},
    )
    assert envio.status_code == 201
    escopo = envio.json()

    geracao = _json(client, "post", f"/api/escopos/{escopo['id']}/gerar-casos", esperado=201)
    assert geracao["quantidade_casos_gerados"] == 2

    manual = _json(
        client,
        "post",
        f"/api/escopos/{escopo['id']}/casos-de-teste",
        {"codigo": "CT-003", "titulo": "Logout", "categoria": "funcional"},
        esperado=201,
    )
    revisado = _json(
        client,
        "patch",
        f"/api/casos-de-teste/{geracao['casos'][1]['id']}",
        {"passos": "1. Informar senha errada\n2. Confirmar"},
    )
    assert revisado["origem"] == "ia"

    casos = _json(client, "get", f"/api/casos-de-teste?projeto_id={projeto['id']}")
    assert [c["codigo"] for c in casos] == ["CT-001", "CT-002", "CT-003"]

    rodada = _json(
        client,
        "post",
        f"/api/projetos/{projeto['id']}/rodadas",
        {"nome": "Homologação 1", "casos_ids": [c["id"] for c in casos]},
        esperado=201,
    )
    execucoes = {
        e["caso_codigo"]: e
        for e in _json(client, "get", f"/api/rodadas/{rodada['id']}/execucoes")
    }

    _json(client, "put", f"/api/execucoes/{execucoes['CT-001']['id']}/resultado", {"status": "passou"})
    _json(client, "put", f"/api/execucoes/{execucoes['CT-002']['id']}/resultado", {"status": "falhou"})
    defeito = _json(
        client,
        "post",
        f"/api/execucoes/{execucoes['CT-002']['id']}/defeitos",
        {"descricao": "Mensagem de erro não aparece", "severidade": "media"},
        esperado=201,
    )

    resumo = _json(client, "get", f"/api/rodadas/{rodada['id']}/resumo")
    assert resumo == {"pendente": 1, "passou": 1, "falhou": 1, "bloqueado": 0, "total": 3}

    abertos = _json(client, "get", f"/api/defeitos?projeto_id={projeto['id']}&status=aberto")
    assert [d["id"] for d in abertos] == [defeito["id"]]

    _json(client, "patch", f"/api/defeitos/{defeito['id']}", {"status": "corrigido"})
    _json(client, "put", f"/api/execucoes/{execucoes['CT-002']['id']}/resultado", {"status": "passou"})
    resumo = _json(client, "get", f"/api/rodadas/{rodada['id']}/resumo")
    assert resumo["passou"] == 2

    _json(client, "delete", f"/api/casos-de-teste/{manual['id']}", esperado=409)
