import pytest

from ia import (
    CasoTesteGerado,
    LLMProvider,
    ProvedorClaude,
    RespostaIAInvalida,
    obter_provedor_llm,
)
from modelos import CategoriaCasoDeTeste, Prioridade


class _BlocoFerramentaFalso:
    type = "tool_use"

    def __init__(self, input_):
        self.input = input_


class _RespostaFalsa:
    def __init__(self, content):
        self.content = content


class _ClienteFalso:
    """Dublê do cliente Anthropic — evita chamar a API real (e gastar tokens) nos testes."""

    def __init__(self, resposta):
        self._resposta = resposta
        self.chamadas = []

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return self._resposta


def test_llm_provider_e_uma_interface_abstrata():
    with pytest.raises(TypeError):
        LLMProvider()


def test_provedor_claude_gera_casos_a_partir_da_resposta_mockada():
    entrada_ia = {
        "casos": [
            {
                "codigo": "CT-001",
                "titulo": "Validar login",
                "categoria": "funcional",
                "pre_condicao": "Usuário cadastrado",
                "passos": "1. Acessar tela de login\n2. Informar credenciais",
                "resultado_esperado": "Usuário autenticado com sucesso",
                "prioridade": "alta",
            }
        ]
    }
    resposta_falsa = _RespostaFalsa([_BlocoFerramentaFalso(entrada_ia)])
    cliente_falso = _ClienteFalso(resposta_falsa)

    provedor = ProvedorClaude(cliente=cliente_falso)
    casos = provedor.gerar_casos_teste("Texto do escopo de exemplo")

    assert len(casos) == 1
    caso = casos[0]
    assert isinstance(caso, CasoTesteGerado)
    assert caso.codigo == "CT-001"
    assert caso.categoria == CategoriaCasoDeTeste.FUNCIONAL
    assert caso.prioridade == Prioridade.ALTA
    assert cliente_falso.chamadas[0]["tool_choice"] == {
        "type": "tool",
        "name": "registrar_casos_de_teste",
    }


def test_provedor_claude_levanta_erro_sem_tool_use():
    resposta_falsa = _RespostaFalsa([])
    cliente_falso = _ClienteFalso(resposta_falsa)
    provedor = ProvedorClaude(cliente=cliente_falso)

    with pytest.raises(RespostaIAInvalida):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


def test_obter_provedor_llm_retorna_provedor_claude_por_padrao(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-fake-para-teste")

    provedor = obter_provedor_llm()

    assert isinstance(provedor, ProvedorClaude)


def test_obter_provedor_llm_rejeita_provedor_desconhecido():
    with pytest.raises(ValueError):
        obter_provedor_llm("provedor-inexistente")
