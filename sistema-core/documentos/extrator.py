from pathlib import Path

import docx
from pypdf import PdfReader

from .erros import FormatoDocumentoNaoSuportado


def _extrair_texto_docx(caminho: Path) -> str:
    documento = docx.Document(caminho)
    paragrafos = [p.text for p in documento.paragraphs if p.text.strip()]
    return "\n".join(paragrafos)


def _extrair_texto_pdf(caminho: Path) -> str:
    leitor = PdfReader(caminho)
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
    extensao = caminho.suffix.lower()
    extrator = _EXTRATORES.get(extensao)
    if extrator is None:
        raise FormatoDocumentoNaoSuportado(
            f"Formato '{extensao}' não suportado. Use .docx ou .pdf."
        )
    return extrator(caminho)
