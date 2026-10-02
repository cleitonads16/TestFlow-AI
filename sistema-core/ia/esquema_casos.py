"""Prompt e formato de saída comuns a todos os provedores de IA.

Os provedores mudam só o transporte (tool call na Anthropic, structured output
na OpenAI); o que se pede e o formato dos casos são os mesmos, para a troca de
provedor não mudar o resultado esperado.
"""

from modelos import CategoriaCasoDeTeste, Prioridade

from .provider import CasoTesteGerado

PROMPT_SISTEMA = (
    "Você é um analista de qualidade de software especialista em elaborar "
    "casos de teste a partir de documentos de escopo de projetos de TI. "
    "Gere casos de teste objetivos e cobrindo os cenários funcionais, de "
    "integração e de regras de negócio descritos no escopo fornecido."
)

ESQUEMA_CASOS = {
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
}


def instrucao_usuario(texto_escopo: str) -> str:
    return "Gere os casos de teste para o escopo abaixo:\n\n" + texto_escopo


def converter_casos(dados: dict) -> list[CasoTesteGerado]:
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
        for caso in dados["casos"]
    ]
