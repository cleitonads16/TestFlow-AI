import io
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

import docx
from docx.table import Table

from .erros import DocumentoIlegivel, DocumentoSemTexto, FormatoDocumentoNaoSuportado

FORMATOS_SUPORTADOS = (".docx",)


def extrair_texto(caminho: str | Path) -> str:
    """Extrai o texto de um documento de escopo (.docx).

    Um escopo por vez: a chamada recebe o caminho de um único arquivo e
    devolve o texto já pronto para ser enviado ao provedor de IA.
    """
    caminho = Path(caminho)
    _exigir_formato_suportado(caminho.suffix)
    return _extrair(caminho)


def validar_documento(conteudo: bytes, extensao: str) -> None:
    """Confere, sem gravar nada, se o conteúdo é um .docx legível e com texto."""
    _exigir_formato_suportado(extensao)
    _extrair(io.BytesIO(conteudo))


def _exigir_formato_suportado(extensao: str) -> None:
    if extensao.lower() not in FORMATOS_SUPORTADOS:
        raise FormatoDocumentoNaoSuportado(
            f"Formato '{extensao.lower() or 'sem extensão'}' não suportado. "
            f"Use {' ou '.join(FORMATOS_SUPORTADOS)}."
        )


def _extrair(origem: Path | BinaryIO) -> str:
    try:
        texto = "\n".join(_linhas(docx.Document(origem)))
    except OSError:
        raise
    except Exception as erro:
        # O python-docx levanta tipos variados para arquivo inválido
        # (BadZipFile, KeyError, ValueError...); todos significam o mesmo
        # para quem enviou: o arquivo não é um documento legível.
        raise DocumentoIlegivel(
            "Não foi possível ler o documento como .docx: o arquivo está "
            "corrompido, protegido por senha ou não é realmente desse formato."
        ) from erro
    if not texto.strip():
        raise DocumentoSemTexto(
            "O documento de escopo não tem texto para gerar os casos de teste "
            "(ex.: só imagens ou páginas digitalizadas)."
        )
    return texto


def _linhas(recipiente) -> Iterator[str]:
    """Parágrafos e tabelas na ordem em que aparecem no documento.

    Escopos costumam trazer os requisitos em tabela; ler só os parágrafos
    (`documento.paragraphs`) deixaria esse conteúdo de fora sem nenhum aviso.
    """
    for bloco in recipiente.iter_inner_content():
        if isinstance(bloco, Table):
            yield from _linhas_da_tabela(bloco)
        elif bloco.text.strip():
            yield bloco.text


def _linhas_da_tabela(tabela: Table) -> Iterator[str]:
    """Uma linha de texto por linha da tabela, com as células separadas por " | "."""
    for linha in tabela.rows:
        celulas, vistas = [], set()
        for celula in linha.cells:
            # Célula mesclada na horizontal se repete em `cells`; conta uma vez só.
            if id(celula._tc) in vistas:
                continue
            vistas.add(id(celula._tc))
            celulas.append(" ".join(_linhas(celula)))
        if any(celulas):
            yield " | ".join(celulas)
