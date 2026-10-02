import anthropic
import pytest

from ia import (
    CasoTesteGerado,
    LLMProvider,
    ProvedorClaude,
    ProvedorIAIndisponivel,
    RespostaIAInvalida,
    obter_provedor_llm,
)
from modelos import CategoriaCasoDeTeste, Prioridade


class _BlocoFerramentaFalso:
    type = "tool_use"

    def __init__(self, input_):
        self.input = input_


class _RespostaFalsa:
    def __init__(self, content, stop_reason="tool_use"):
        self.content = content
        self.stop_reason = stop_reason


class _StreamFalso:
    def __init__(self, resposta):
        self._resposta = resposta

    def __enter__(self):
        return self

    def __exit__(self, *excecao):
        return False

    def get_final_message(self):
        return self._resposta


class _ClienteFalso:
    """Dublê do cliente Anthropic — evita chamar a API real (e gastar tokens) nos testes."""

    def __init__(self, resposta):
        self._resposta = resposta
        self.chamadas = []

    @property
    def messages(self):
        return self

    def stream(self, **kwargs):
        self.chamadas.append(kwargs)
        return _StreamFalso(self._resposta)


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


@pytest.mark.parametrize(
    "stop_reason, mensagem",
    [("max_tokens", "tamanho máximo"), ("refusal", "recusou")],
    ids=["resposta-cortada", "recusa"],
)
def test_provedor_claude_nao_aproveita_resposta_cortada_ou_recusada(stop_reason, mensagem):
    """Numa resposta cortada, a lista de casos viria incompleta sem nenhum aviso."""
    caso_parcial = {"casos": [{"codigo": "CT-001"}]}
    resposta_falsa = _RespostaFalsa([_BlocoFerramentaFalso(caso_parcial)], stop_reason)
    provedor = ProvedorClaude(cliente=_ClienteFalso(resposta_falsa))

    with pytest.raises(RespostaIAInvalida, match=mensagem):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


def test_obter_provedor_llm_retorna_provedor_claude_por_padrao(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-fake-para-teste")

    provedor = obter_provedor_llm()

    assert isinstance(provedor, ProvedorClaude)


def test_obter_provedor_llm_rejeita_provedor_desconhecido():
    with pytest.raises(ValueError):
        obter_provedor_llm("provedor-inexistente")


class _ClienteComFalha:
    @property
    def messages(self):
        return self

    def stream(self, **kwargs):
        raise anthropic.AnthropicError("sem credencial")


def test_provedor_claude_traduz_erro_do_sdk_para_provedor_indisponivel():
    provedor = ProvedorClaude(cliente=_ClienteComFalha())

    with pytest.raises(ProvedorIAIndisponivel) as erro:
        provedor.gerar_casos_teste("Texto do escopo de exemplo")

    assert isinstance(erro.value.__cause__, anthropic.AnthropicError)


def test_provedor_claude_sem_credencial_levanta_provedor_indisponivel(monkeypatch):
    """Sem credencial o SDK levanta TypeError na chamada, o que viraria 500 na API."""
    from types import SimpleNamespace

    sem_credencial = SimpleNamespace(api_key=None, auth_token=None, credentials=None)
    monkeypatch.delenv("ANTHROPIC_API_KEY_FILE", raising=False)
    monkeypatch.setattr("ia.provedor_claude.anthropic.Anthropic", lambda: sem_credencial)
    provedor = ProvedorClaude()

    with pytest.raises(ProvedorIAIndisponivel, match="ANTHROPIC_API_KEY"):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


def test_provedor_claude_le_a_chave_do_arquivo_indicado(monkeypatch, tmp_path):
    """A chave vem de um arquivo (Docker secret), não de variável de ambiente."""
    arquivo = tmp_path / "chave"
    arquivo.write_text("  chave-ficticia-do-arquivo\n", encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY_FILE", str(arquivo))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    provedor = ProvedorClaude()

    assert provedor._cliente.api_key == "chave-ficticia-do-arquivo"


@pytest.mark.parametrize("conteudo", [None, "   \n"], ids=["arquivo-ausente", "arquivo-vazio"])
def test_arquivo_de_chave_ausente_ou_vazio_vira_provedor_indisponivel(
    monkeypatch, tmp_path, conteudo
):
    arquivo = tmp_path / "chave"
    if conteudo is not None:
        arquivo.write_text(conteudo, encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY_FILE", str(arquivo))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    with pytest.raises(ProvedorIAIndisponivel, match="ANTHROPIC_API_KEY_FILE"):
        ProvedorClaude().gerar_casos_teste("Texto do escopo de exemplo")


class _ClienteComChaveRecusada:
    @property
    def messages(self):
        return self

    def stream(self, **kwargs):
        # Sem passar pelo __init__, que exige um objeto de resposta HTTP do SDK.
        erro = anthropic.AuthenticationError.__new__(anthropic.AuthenticationError)
        Exception.__init__(erro, "invalid x-api-key")
        raise erro


def test_chave_recusada_tem_mensagem_propria():
    provedor = ProvedorClaude(cliente=_ClienteComChaveRecusada())

    with pytest.raises(ProvedorIAIndisponivel, match="recusou a credencial"):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")
