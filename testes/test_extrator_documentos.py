import pytest
from docx import Document
from pypdf import PdfWriter

from documentos import (
    DocumentoIlegivel,
    FormatoDocumentoNaoSuportado,
    extrair_texto,
    validar_documento,
)


def test_extrai_texto_de_docx(tmp_path):
    caminho = tmp_path / "escopo.docx"
    documento = Document()
    documento.add_paragraph("Título do Escopo")
    documento.add_paragraph("Este é o corpo do escopo de teste.")
    documento.save(caminho)

    texto = extrair_texto(caminho)

    assert "Título do Escopo" in texto
    assert "corpo do escopo de teste" in texto


def test_extrai_texto_de_pdf_sem_erro(tmp_path):
    caminho = tmp_path / "escopo.pdf"
    escritor = PdfWriter()
    escritor.add_blank_page(width=200, height=200)
    with open(caminho, "wb") as arquivo:
        escritor.write(arquivo)

    texto = extrair_texto(caminho)

    assert isinstance(texto, str)


def test_formato_nao_suportado_levanta_erro(tmp_path):
    caminho = tmp_path / "escopo.txt"
    caminho.write_text("conteúdo qualquer", encoding="utf-8")

    with pytest.raises(FormatoDocumentoNaoSuportado):
        extrair_texto(caminho)


@pytest.mark.parametrize("extensao", [".docx", ".pdf"])
def test_arquivo_ilegivel_levanta_documento_ilegivel(tmp_path, extensao):
    caminho = tmp_path / f"escopo{extensao}"
    caminho.write_bytes(b"texto qualquer, so renomeado")

    with pytest.raises(DocumentoIlegivel, match="corrompido"):
        extrair_texto(caminho)


def test_validar_documento_aceita_docx_valido(conteudo_docx):
    validar_documento(conteudo_docx, ".docx")


def test_validar_documento_recusa_conteudo_ilegivel():
    with pytest.raises(DocumentoIlegivel):
        validar_documento(b"nao sou um pdf", ".pdf")
