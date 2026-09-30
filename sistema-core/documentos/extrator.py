import io
from pathlib import Path
from typing import BinaryIO

import docx
from pypdf import PdfReader

from .erros import DocumentoIlegivel, FormatoDocumentoNaoSuportado


def _extrair_texto_docx(origem: Path | BinaryIO) -> str:
    documento = docx.Document(origem)
    paragrafos = [p.text for p in documento.paragraphs if p.text.strip()]
    return "\n".join(paragrafos)


def _extrair_texto_pdf(origem: Path | BinaryIO) -> str:
    leitor = PdfReader(origem)
    paginas = [pagina.extract_text() or "" for pagina in leitor.pages]
    return "\n".join(pagina for pagina in paginas if pagina.strip())


_EXTRATORES = {
    ".docx": _extrair_texto_docx,
    ".pdf": _extrair_texto_pdf,
}

FORMATOS_SUPORTADOS = tuple(_EXTRATORES)


def extrair_texto(caminho: str | Path) -> str:
    """Extrai o texto de um documento de escopo (.docx ou .pdf).

    Um escopo por vez: a chamada recebe o caminho de um único arquivo e
    devolve o texto já pronto para ser enviado ao provedor de IA.
    """
    caminho = Path(caminho)
    return _extrair(_extrator_para(caminho.suffix), caminho, caminho.suffix)


def validar_documento(conteudo: bytes, extensao: str) -> None:
    """Confere, sem gravar nada, se o conteúdo pode ser lido no formato da extensão."""
    _extrair(_extrator_para(extensao), io.BytesIO(conteudo), extensao)


def _extrator_para(extensao: str):
    extrator = _EXTRATORES.get(extensao.lower())
    if extrator is None:
        raise FormatoDocumentoNaoSuportado(
            f"Formato '{extensao.lower()}' não suportado. Use .docx ou .pdf."
        )
    return extrator


def _extrair(extrator, origem: Path | BinaryIO, extensao: str) -> str:
    try:
        return extrator(origem)
    except OSError:
        raise
    except Exception as erro:
        # python-docx e pypdf levantam tipos variados para arquivo inválido
        # (BadZipFile, KeyError, PdfReadError...); todos significam o mesmo
        # para quem enviou: o arquivo não é um documento legível.
        raise DocumentoIlegivel(
            f"Não foi possível ler o documento como {extensao.lower()}: o arquivo "
            "está corrompido, protegido por senha ou não é realmente desse formato."
        ) from erro
