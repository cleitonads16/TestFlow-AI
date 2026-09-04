import pytest
from docx import Document
from pypdf import PdfWriter

from documentos import FormatoDocumentoNaoSuportado, extrair_texto


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
