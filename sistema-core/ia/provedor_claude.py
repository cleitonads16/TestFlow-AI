import anthropic

from .credenciais import ler_chave_de_arquivo
from .erros import ProvedorIAIndisponivel, RespostaIAInvalida
from .esquema_casos import ESQUEMA_CASOS, PROMPT_SISTEMA, converter_casos, instrucao_usuario
from .provider import CasoTesteGerado, LLMProvider

MODELO_PADRAO = "claude-opus-5"
MAX_TOKENS_RESPOSTA = 64000

VARIAVEL_ARQUIVO_CHAVE = "ANTHROPIC_API_KEY_FILE"

_FERRAMENTA_REGISTRAR_CASOS = {
    "name": "registrar_casos_de_teste",
    "description": (
        "Registra a lista de casos de teste gerados a partir do escopo fornecido."
    ),
    "input_schema": ESQUEMA_CASOS,
    "strict": True,
}


class ProvedorClaude(LLMProvider):
    """Adaptador que gera casos de teste usando a API oficial da Anthropic (Claude).

    Usa uma tool call forçada (`tool_choice`) com schema estrito em vez de
    pedir texto livre, para que a resposta já venha validada no formato de
    CasoTesteGerado, sem parsing frágil de texto.
    """

    def __init__(
        self,
        cliente: anthropic.Anthropic | None = None,
        modelo: str = MODELO_PADRAO,
    ):
        if cliente is None:
            chave = ler_chave_de_arquivo(VARIAVEL_ARQUIVO_CHAVE)
            cliente = anthropic.Anthropic(api_key=chave) if chave else anthropic.Anthropic()
            # Sem credencial o SDK só falha na chamada, e com TypeError (não com
            # AnthropicError), que viraria 500. Guardado aqui para virar 503.
            self._sem_credencial = all(
                getattr(cliente, atributo) is None
                for atributo in ("api_key", "auth_token", "credentials")
            )
        else:
            self._sem_credencial = False
        self._cliente = cliente
        self._modelo = modelo
        self._ultimo_tokens_utilizados: int | None = None

    @property
    def nome(self) -> str:
        return "claude"

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def ultimo_tokens_utilizados(self) -> int | None:
        return self._ultimo_tokens_utilizados

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        if self._sem_credencial:
            raise ProvedorIAIndisponivel(
                "O provedor de IA (Claude) não tem credencial configurada: informe o "
                f"arquivo da chave em {VARIAVEL_ARQUIVO_CHAVE} (ou a variável "
                "ANTHROPIC_API_KEY) e reinicie a API."
            )

        # Streaming porque um escopo grande gera uma resposta longa: sem ele, o
        # SDK limita o max_tokens para não estourar o tempo da requisição HTTP.
        # Só a mensagem final é usada; os eventos intermediários não interessam.
        try:
            with self._cliente.messages.stream(
                model=self._modelo,
                max_tokens=MAX_TOKENS_RESPOSTA,
                system=PROMPT_SISTEMA,
                tools=[_FERRAMENTA_REGISTRAR_CASOS],
                tool_choice={"type": "tool", "name": "registrar_casos_de_teste"},
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Gere os casos de teste para o escopo abaixo:\n\n" + texto_escopo
                        ),
                    }
                ],
            ) as stream:
                resposta = stream.get_final_message()
        except anthropic.AuthenticationError as erro:
            raise ProvedorIAIndisponivel(
                "O provedor de IA (Claude) recusou a credencial configurada. "
                "Confira se a chave está completa e ativa."
            ) from erro
        except anthropic.AnthropicError as erro:
            raise ProvedorIAIndisponivel(
                "Não foi possível obter resposta do provedor de IA (Claude)."
            ) from erro

        uso = getattr(resposta, "usage", None)
        if uso is not None:
            self._ultimo_tokens_utilizados = uso.input_tokens + uso.output_tokens

        # O stop_reason vem antes do conteúdo: numa resposta cortada ou recusada,
        # a lista de casos viria incompleta ou nem viria.
        if resposta.stop_reason == "max_tokens":
            raise RespostaIAInvalida(
                "A resposta da IA foi interrompida por exceder o tamanho máximo. "
                "Divida o escopo em documentos menores e gere os casos de cada um."
            )
        if resposta.stop_reason == "refusal":
            raise RespostaIAInvalida(
                "O provedor de IA recusou gerar casos de teste para este escopo."
            )

        bloco_ferramenta = next(
            (bloco for bloco in resposta.content if bloco.type == "tool_use"), None
        )
        if bloco_ferramenta is None:
            raise RespostaIAInvalida(
                "O provedor de IA não retornou os casos de teste no formato esperado."
            )

        return converter_casos(bloco_ferramenta.input)
