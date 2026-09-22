"""App Django do domínio.

Este `__init__` expõe só os enums, que são Python puro: assim `ia/` e
`documentos/` podem usá-los sem depender do Django. Os models ficam em
`modelos.models` (importar só depois de o Django estar configurado).
"""

from .enums import (
    CategoriaCasoDeTeste,
    OrigemCasoDeTeste,
    Prioridade,
    SeveridadeDefeito,
    StatusDefeito,
    StatusEscopo,
    StatusExecucaoCaso,
)

__all__ = [
    "Prioridade",
    "StatusEscopo",
    "CategoriaCasoDeTeste",
    "OrigemCasoDeTeste",
    "StatusExecucaoCaso",
    "SeveridadeDefeito",
    "StatusDefeito",
]
