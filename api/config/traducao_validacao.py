"""Mensagens em português para os erros de validação do Pydantic (422).

O Pydantic só gera mensagens em inglês. A tradução usa o `type` do erro, que é
estável entre versões, e não o texto, que pode mudar. Um tipo sem tradução
mantém a mensagem original, para o erro nunca sair sem explicação.
"""

import re

_DATA = "Deve ser uma data válida no formato AAAA-MM-DD."
_INTEIRO = "Deve ser um número inteiro."

_MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_type": "Deve ser um texto.",
    "string_too_short": "Deve ter no mínimo {min_length} {caracteres}.",
    "string_too_long": "Deve ter no máximo {max_length} {caracteres}.",
    "int_type": _INTEIRO,
    "int_parsing": _INTEIRO,
    "int_from_float": "Deve ser um número inteiro, sem casas decimais.",
    "bool_type": "Deve ser verdadeiro ou falso (true ou false).",
    "bool_parsing": "Deve ser verdadeiro ou falso (true ou false).",
    "date_type": _DATA,
    "date_parsing": _DATA,
    "date_from_datetime_parsing": _DATA,
    "date_from_datetime_inexact": "Deve ser só a data, sem horário (AAAA-MM-DD).",
    "list_type": "Deve ser uma lista.",
    "too_short": "Deve ter pelo menos {min_length} {itens}.",
    "too_long": "Deve ter no máximo {max_length} {itens}.",
    "model_type": "Deve ser um objeto JSON.",
    "dict_type": "Deve ser um objeto JSON.",
}


def traduzir(erro: dict) -> str:
    tipo = erro.get("type")
    contexto = erro.get("ctx") or {}

    if tipo in ("enum", "literal_error"):
        permitidos = re.findall(r"'([^']*)'", str(contexto.get("expected", "")))
        if permitidos:
            return f"Valor inválido. Permitidos: {', '.join(permitidos)}."

    modelo = _MENSAGENS.get(tipo)
    if modelo is None:
        return erro["msg"]
    limite = contexto.get("min_length", contexto.get("max_length"))
    plurais = {
        "caracteres": "caractere" if limite == 1 else "caracteres",
        "itens": "item" if limite == 1 else "itens",
    }
    try:
        return modelo.format(**contexto, **plurais)
    except KeyError:
        return erro["msg"]
