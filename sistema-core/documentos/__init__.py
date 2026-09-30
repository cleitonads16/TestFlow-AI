from .erros import DocumentoIlegivel, FormatoDocumentoNaoSuportado
from .extrator import FORMATOS_SUPORTADOS, extrair_texto, validar_documento

__all__ = [
    "extrair_texto",
    "validar_documento",
    "FormatoDocumentoNaoSuportado",
    "DocumentoIlegivel",
    "FORMATOS_SUPORTADOS",
]
