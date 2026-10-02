import io
import json
import socket
import urllib.error

import pytest

from ia import ProvedorIAIndisponivel, ProvedorOllama, RespostaIAInvalida, obter_provedor_llm
from ia.esquema_casos import ESQUEMA_CASOS
from modelos import CategoriaCasoDeTeste

_CASO = {
    "codigo": "CT-001",
    "titulo": "Validar login",
    "categoria": "funcional",
    "pre_condicao": "Usuário cadastrado",
    "passos": "1. Acessar login\n2. Informar credenciais",
    "resultado_esperado": "Usuário autenticado",
    "prioridade": "alta",
}


class _RespostaHttp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def ollama(monkeypatch):
    """Substitui a chamada HTTP ao Ollama; guarda o pedido para conferência."""
    estado = {"pedidos": [], "resposta": None, "erro": None}

    def urlopen_falso(requisicao, timeout):
        estado["pedidos"].append(
            {"url": requisicao.full_url, "corpo": json.loads(requisicao.data), "timeout": timeout}
        )
        if estado["erro"] is not None:
            raise estado["erro"]
        return _RespostaHttp(json.dumps(estado["resposta"]).encode("utf-8"))

    monkeypatch.setattr("ia.provedor_ollama.urllib.request.urlopen", urlopen_falso)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    return estado


def _resposta(conteudo, done_reason="stop"):
    return {
        "message": {"role": "assistant", "content": conteudo},
        "done_reason": done_reason,
        "prompt_eval_count": 100,
        "eval_count": 50,
    }


def test_provedor_ollama_gera_casos_com_o_schema_comum(ollama):
    ollama["resposta"] = _resposta(json.dumps({"casos": [_CASO]}))
    provedor = ProvedorOllama()

    casos = provedor.gerar_casos_teste("Texto do escopo de exemplo")

    assert [caso.codigo for caso in casos] == ["CT-001"]
    assert casos[0].categoria is CategoriaCasoDeTeste.FUNCIONAL
    assert provedor.ultimo_tokens_utilizados == 150
    assert (provedor.nome, provedor.modelo) == ("ollama", "gemma3:4b")
    pedido = ollama["pedidos"][0]
    assert pedido["url"] == "http://127.0.0.1:11434/api/chat"
    assert pedido["corpo"]["format"] == ESQUEMA_CASOS
    assert pedido["corpo"]["stream"] is False


@pytest.mark.parametrize(
    ("resposta", "mensagem"),
    [
        (_resposta('{"casos": [', done_reason="length"), "interrompida"),
        (_resposta("isto não é JSON"), "formato esperado"),
        (_resposta(json.dumps({"casos": [{"codigo": "CT-001"}]})), "formato esperado"),
    ],
    ids=["cortada", "nao-json", "caso-incompleto"],
)
def test_provedor_ollama_recusa_resposta_inutilizavel(ollama, resposta, mensagem):
    ollama["resposta"] = resposta

    with pytest.raises(RespostaIAInvalida, match=mensagem):
        ProvedorOllama().gerar_casos_teste("Texto do escopo de exemplo")


@pytest.mark.parametrize("modelo", ["gpt-oss:120b-cloud", "qwen3-coder:480b-CLOUD"])
def test_modelo_de_nuvem_e_recusado_sem_enviar_o_escopo(ollama, modelo):
    """Modelo de nuvem enviaria o escopo para fora da máquina (serviço não homologado)."""
    with pytest.raises(ProvedorIAIndisponivel, match="nuvem"):
        ProvedorOllama(modelo=modelo).gerar_casos_teste("Texto do escopo de exemplo")

    assert ollama["pedidos"] == []


def test_servidor_fora_da_maquina_e_recusado_sem_enviar_o_escopo(ollama):
    with pytest.raises(ProvedorIAIndisponivel, match="própria máquina"):
        ProvedorOllama(url="http://servidor-externo:11434").gerar_casos_teste("Texto")

    assert ollama["pedidos"] == []


def test_servidor_do_host_visto_do_docker_e_aceito(ollama):
    ollama["resposta"] = _resposta(json.dumps({"casos": [_CASO]}))

    ProvedorOllama(url="http://host.docker.internal:11434").gerar_casos_teste("Texto")

    assert ollama["pedidos"][0]["url"].startswith("http://host.docker.internal:11434")


@pytest.mark.parametrize(
    ("erro", "mensagem"),
    [
        (urllib.error.HTTPError("url", 404, "not found", None, None), "ollama pull gemma3:4b"),
        (urllib.error.HTTPError("url", 500, "erro", None, None), "Não foi possível"),
        (urllib.error.URLError(ConnectionRefusedError()), "Confira se ele está aberto"),
        (urllib.error.URLError(socket.timeout()), "demorou demais"),
        (TimeoutError(), "demorou demais"),
    ],
    ids=["modelo-nao-baixado", "erro-do-servidor", "ollama-fechado", "timeout-na-conexao", "timeout"],
)
def test_provedor_ollama_traduz_falhas_de_comunicacao(ollama, erro, mensagem):
    ollama["erro"] = erro

    with pytest.raises(ProvedorIAIndisponivel, match=mensagem):
        ProvedorOllama().gerar_casos_teste("Texto do escopo de exemplo")


def test_provedor_ollama_le_url_e_modelo_da_configuracao(ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:9999/")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    ollama["resposta"] = _resposta(json.dumps({"casos": [_CASO]}))

    provedor = ProvedorOllama()
    provedor.gerar_casos_teste("Texto")

    assert provedor.modelo == "llama3.2:3b"
    assert ollama["pedidos"][0]["url"] == "http://localhost:9999/api/chat"
    assert ollama["pedidos"][0]["corpo"]["model"] == "llama3.2:3b"


def test_fabrica_escolhe_ollama_pela_variavel_llm_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    assert isinstance(obter_provedor_llm(), ProvedorOllama)
