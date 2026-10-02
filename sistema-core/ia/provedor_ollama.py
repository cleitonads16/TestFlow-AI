import json
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .erros import ProvedorIAIndisponivel, RespostaIAInvalida
from .esquema_casos import ESQUEMA_CASOS, PROMPT_SISTEMA, converter_casos, instrucao_usuario
from .provider import CasoTesteGerado, LLMProvider

MODELO_PADRAO = "gemma3:4b"
URL_PADRAO = "http://127.0.0.1:11434"
# Sem GPU, um modelo local gera poucos tokens por segundo: um escopo pequeno já
# leva minutos. O gunicorn da imagem corta em 900 s, então o limite fica abaixo.
TIMEOUT_SEGUNDOS = 840
# Contexto padrão do Ollama é curto e cortaria escopos maiores sem aviso.
TAMANHO_CONTEXTO = 16384

# Só servidores na própria máquina (ou no host, visto de dentro do Docker): o
# documento de escopo não pode sair do computador por este provedor.
_HOSTS_LOCAIS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}


class ProvedorOllama(LLMProvider):
    """Adaptador que gera casos de teste com um modelo rodando localmente no Ollama.

    Alternativa gratuita aos provedores pagos: o modelo roda na própria máquina
    e o escopo não sai dela. Usa o `format` do Ollama com o mesmo JSON Schema
    dos outros provedores, que restringe a geração ao formato de CasoTesteGerado.

    Recusa modelos de nuvem do Ollama (sufixo `cloud`) e servidores fora da
    máquina, porque enviariam o escopo para um serviço não homologado
    (docs/arquitetura-e-cronograma.md, D7).
    """

    def __init__(self, url: str | None = None, modelo: str | None = None):
        self._url = (url or os.getenv("OLLAMA_URL") or URL_PADRAO).rstrip("/")
        self._modelo = modelo or os.getenv("OLLAMA_MODEL") or MODELO_PADRAO
        self._ultimo_tokens_utilizados: int | None = None

    @property
    def nome(self) -> str:
        return "ollama"

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def ultimo_tokens_utilizados(self) -> int | None:
        return self._ultimo_tokens_utilizados

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        self._garantir_execucao_local()

        corpo = {
            "model": self._modelo,
            "stream": False,
            "format": ESQUEMA_CASOS,
            "options": {"num_ctx": TAMANHO_CONTEXTO, "temperature": 0.2},
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": instrucao_usuario(texto_escopo)},
            ],
        }
        resposta = self._chamar("/api/chat", corpo)

        self._ultimo_tokens_utilizados = (resposta.get("prompt_eval_count") or 0) + (
            resposta.get("eval_count") or 0
        )
        if resposta.get("done_reason") == "length":
            raise RespostaIAInvalida(
                "A resposta da IA foi interrompida por exceder o tamanho máximo. "
                "Divida o escopo em documentos menores e gere os casos de cada um."
            )

        try:
            conteudo = resposta["message"]["content"]
            return converter_casos(json.loads(conteudo))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
            raise RespostaIAInvalida(
                "O provedor de IA não retornou os casos de teste no formato esperado."
            ) from erro

    def _garantir_execucao_local(self) -> None:
        if "cloud" in self._modelo.lower():
            raise ProvedorIAIndisponivel(
                f"O modelo '{self._modelo}' roda na nuvem do Ollama e enviaria o escopo "
                "para fora da máquina. Use um modelo local (ex.: gemma3:4b)."
            )
        if urlparse(self._url).hostname not in _HOSTS_LOCAIS:
            raise ProvedorIAIndisponivel(
                "O provedor Ollama só aceita servidor na própria máquina "
                f"({', '.join(sorted(_HOSTS_LOCAIS))})."
            )

    def _chamar(self, caminho: str, corpo: dict) -> dict:
        requisicao = urllib.request.Request(
            self._url + caminho,
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            if erro.code == 404:
                raise ProvedorIAIndisponivel(
                    f"O modelo '{self._modelo}' não está baixado no Ollama. "
                    f"Rode: ollama pull {self._modelo}"
                ) from erro
            raise ProvedorIAIndisponivel(
                "Não foi possível obter resposta do provedor de IA (Ollama)."
            ) from erro
        except (TimeoutError, socket.timeout) as erro:
            raise ProvedorIAIndisponivel(
                "O modelo local demorou demais para responder. Tente um escopo menor."
            ) from erro
        except (urllib.error.URLError, ConnectionError) as erro:
            if isinstance(getattr(erro, "reason", None), (TimeoutError, socket.timeout)):
                raise ProvedorIAIndisponivel(
                    "O modelo local demorou demais para responder. Tente um escopo menor."
                ) from erro
            raise ProvedorIAIndisponivel(
                f"O Ollama não respondeu em {self._url}. Confira se ele está aberto."
            ) from erro
