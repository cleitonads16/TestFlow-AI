import anthropic

from modelos import CategoriaCasoDeTeste, Prioridade

from .erros import RespostaIAInvalida
from .provider import CasoTesteGerado, LLMProvider

MODELO_PADRAO = "claude-opus-5"

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
        self._cliente = cliente or anthropic.Anthropic()
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
        resposta = self._cliente.messages.create(
            model=self._modelo,
            max_tokens=16000,
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
        )

        uso = getattr(resposta, "usage", None)
        if uso is not None:
            self._ultimo_tokens_utilizados = uso.input_tokens + uso.output_tokens

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
