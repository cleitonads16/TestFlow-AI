import enum


class RegraDeNegocioViolada(Exception):
    """Operação recusada por uma regra de negócio (a API traduz para 4xx)."""


def converter_enum(enum_classe: type[enum.Enum], valor: enum.Enum | str, campo: str):
    """Aceita o membro do enum ou seu valor em texto; rejeita valores fora do domínio."""
    try:
        return enum_classe(valor)
    except ValueError:
        permitidos = ", ".join(membro.value for membro in enum_classe)
        raise RegraDeNegocioViolada(
            f"Valor '{valor}' inválido para {campo}. Permitidos: {permitidos}."
        ) from None


def exigir_texto(valor: str | None, campo: str) -> str:
    if valor is None or not valor.strip():
        raise RegraDeNegocioViolada(f"O campo {campo} é obrigatório.")
    return valor.strip()
