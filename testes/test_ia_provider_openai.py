import json
from types import SimpleNamespace

import openai
import pytest

from ia import ProvedorIAIndisponivel, ProvedorOpenAI, RespostaIAInvalida, obter_provedor_llm
from modelos import CategoriaCasoDeTeste, Prioridade

_CASO = {
    "codigo": "CT-001",
    "titulo": "Validar login",
    "categoria": "funcional",
    "pre_condicao": "Usuário cadastrado",
    "passos": "1. Acessar login\n2. Informar credenciais",
    "resultado_esperado": "Usuário autenticado",
    "prioridade": "alta",
}


class _ClienteFalso:
    """Imita `openai.OpenAI` só no que o adaptador usa: chat.completions.create."""

    def __init__(self, conteudo=None, finish_reason="stop", refusal=None, erro=None):
        self.chat = SimpleNamespace(completions=self)
        self._conteudo = conteudo
        self._finish_reason = finish_reason
        self._refusal = refusal
        self._erro = erro
        self.chamada = None

    def create(self, **kwargs):
        self.chamada = kwargs
        if self._erro is not None:
            raise self._erro
        mensagem = SimpleNamespace(content=self._conteudo, refusal=self._refusal)
        escolha = SimpleNamespace(finish_reason=self._finish_reason, message=mensagem)
        return SimpleNamespace(choices=[escolha], usage=SimpleNamespace(total_tokens=321))


def _erro_do_sdk(classe, code=None, type_=None):
    # Sem passar pelo __init__, que exige um objeto de resposta HTTP do SDK.
    erro = classe.__new__(classe)
    Exception.__init__(erro, "erro simulado")
    erro.code, erro.type = code, type_
    return erro


def test_provedor_openai_converte_resposta_estruturada_em_casos():
    cliente = _ClienteFalso(conteudo=json.dumps({"casos": [_CASO]}))
    provedor = ProvedorOpenAI(cliente=cliente, modelo="modelo-de-teste")

    casos = provedor.gerar_casos_teste("Texto do escopo de exemplo")

    assert len(casos) == 1
    assert casos[0].codigo == "CT-001"
    assert casos[0].categoria is CategoriaCasoDeTeste.FUNCIONAL
    assert casos[0].prioridade is Prioridade.ALTA
    assert provedor.ultimo_tokens_utilizados == 321
    assert provedor.nome == "openai"
    assert cliente.chamada["model"] == "modelo-de-teste"
    assert cliente.chamada["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize(
    ("resposta", "mensagem"),
    [
        ({"finish_reason": "length", "conteudo": '{"casos": ['}, "interrompida"),
        ({"refusal": "Não posso ajudar com isso."}, "recusou"),
        ({"conteudo": "isto não é JSON"}, "formato esperado"),
        ({"conteudo": json.dumps({"casos": [{"codigo": "CT-001"}]})}, "formato esperado"),
    ],
    ids=["cortada", "recusada", "nao-json", "caso-incompleto"],
)
def test_provedor_openai_recusa_resposta_inutilizavel(resposta, mensagem):
    provedor = ProvedorOpenAI(cliente=_ClienteFalso(**resposta), modelo="modelo-de-teste")

    with pytest.raises(RespostaIAInvalida, match=mensagem):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


@pytest.mark.parametrize(
    ("erro", "mensagem"),
    [
        (_erro_do_sdk(openai.AuthenticationError), "recusou a credencial"),
        (
            _erro_do_sdk(openai.RateLimitError, "credit_balance_exhausted", "insufficient_quota"),
            "sem créditos",
        ),
        (_erro_do_sdk(openai.RateLimitError, "rate_limit_exceeded"), "limite de requisições"),
        (openai.OpenAIError("falha de rede"), "Não foi possível obter resposta"),
    ],
    ids=["chave-recusada", "sem-credito", "limite-de-requisicoes", "falha-do-sdk"],
)
def test_provedor_openai_traduz_erros_do_sdk(erro, mensagem):
    provedor = ProvedorOpenAI(cliente=_ClienteFalso(erro=erro), modelo="modelo-de-teste")

    with pytest.raises(ProvedorIAIndisponivel, match=mensagem):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


def test_provedor_openai_sem_credencial_so_falha_na_geracao(monkeypatch):
    """O SDK da OpenAI falha já ao criar o cliente; a API não pode cair por isso."""
    monkeypatch.delenv("OPENAI_API_KEY_FILE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provedor = ProvedorOpenAI()

    with pytest.raises(ProvedorIAIndisponivel, match="OPENAI_API_KEY_FILE"):
        provedor.gerar_casos_teste("Texto do escopo de exemplo")


def test_provedor_openai_le_chave_e_modelo_da_configuracao(monkeypatch, tmp_path):
    arquivo = tmp_path / "chave"
    arquivo.write_text("chave-ficticia-do-arquivo\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(arquivo))
    monkeypatch.setenv("OPENAI_MODEL", "modelo-configurado")

    provedor = ProvedorOpenAI()

    assert provedor._cliente.api_key == "chave-ficticia-do-arquivo"
    assert provedor.modelo == "modelo-configurado"


def test_fabrica_escolhe_openai_pela_variavel_llm_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    assert isinstance(obter_provedor_llm(), ProvedorOpenAI)
