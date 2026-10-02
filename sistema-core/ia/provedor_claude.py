import anthropic

from modelos import CategoriaCasoDeTeste, Prioridade

from .erros import ProvedorIAIndisponivel, RespostaIAInvalida
from .provider import CasoTesteGerado, LLMProvider

MODELO_PADRAO = "claude-opus-5"
MAX_TOKENS_RESPOSTA = 64000

_PROMPT_SISTEMA = (
    "Você é um analista de qualidade de software especialista em elaborar "
    "casos de teste a partir de documentos de escopo de projetos de TI. "
    "Gere casos de teste objetivos e cobrindo os cenários funcionais, de "
    "integração e de regras de negócio descritos no escopo fornecido."
)

_FERRAMENTA_REGISTRAR_CASOS = {
    "name": "registrar_casos_de_teste",
    "description": (
        "Registra a lista de casos de teste gerados a partir do escopo fornecido."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "casos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "codigo": {
                            "type": "string",
                            "description": "Identificador curto do caso, ex.: CT-001",
                        },
                        "titulo": {"type": "string"},
                        "categoria": {
                            "type": "string",
                            "enum": [categoria.value for categoria in CategoriaCasoDeTeste],
                        },
                        "pre_condicao": {"type": "string"},
                        "passos": {"type": "string"},
                        "resultado_esperado": {"type": "string"},
                        "prioridade": {
                            "type": "string",
                            "enum": [prioridade.value for prioridade in Prioridade],
                        },
                    },
                    "required": [
                        "codigo",
                        "titulo",
                        "categoria",
                        "pre_condicao",
                        "passos",
                        "resultado_esperado",
                        "prioridade",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["casos"],
        "additionalProperties": False,
    },
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
            cliente = anthropic.Anthropic()
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
                "O provedor de IA (Claude) não tem credencial configurada: "
                "defina a variável de ambiente ANTHROPIC_API_KEY e reinicie a API."
            )

        # Streaming porque um escopo grande gera uma resposta longa: sem ele, o
        # SDK limita o max_tokens para não estourar o tempo da requisição HTTP.
        # Só a mensagem final é usada; os eventos intermediários não interessam.
        try:
            with self._cliente.messages.stream(
                model=self._modelo,
                max_tokens=MAX_TOKENS_RESPOSTA,
                system=_PROMPT_SISTEMA,
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

        return [
            CasoTesteGerado(
                codigo=caso["codigo"],
                titulo=caso["titulo"],
                categoria=CategoriaCasoDeTeste(caso["categoria"]),
                pre_condicao=caso.get("pre_condicao"),
                passos=caso.get("passos"),
                resultado_esperado=caso.get("resultado_esperado"),
                prioridade=Prioridade(caso["prioridade"]),
            )
            for caso in bloco_ferramenta.input["casos"]
        ]
