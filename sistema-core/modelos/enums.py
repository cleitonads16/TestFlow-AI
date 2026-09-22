import enum


class Prioridade(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class StatusEscopo(str, enum.Enum):
    PENDENTE = "pendente"
    PROCESSADO = "processado"
    ERRO = "erro"


class CategoriaCasoDeTeste(str, enum.Enum):
    FUNCIONAL = "funcional"
    INTEGRACAO = "integracao"
    REGRA_DE_NEGOCIO = "regra_de_negocio"
    OUTRO = "outro"


class OrigemCasoDeTeste(str, enum.Enum):
    MANUAL = "manual"
    IA = "ia"


class StatusExecucaoCaso(str, enum.Enum):
    PENDENTE = "pendente"
    PASSOU = "passou"
    FALHOU = "falhou"
    BLOQUEADO = "bloqueado"


class SeveridadeDefeito(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class StatusDefeito(str, enum.Enum):
    ABERTO = "aberto"
    EM_ANALISE = "em_analise"
    CORRIGIDO = "corrigido"
    FECHADO = "fechado"


def como_choices(enum_classe: type[enum.Enum]) -> list[tuple[str, str]]:
    """Converte um enum em `choices` de campo Django sem acoplar os enums ao Django."""
    return [(membro.value, membro.value) for membro in enum_classe]
