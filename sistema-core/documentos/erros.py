class FormatoDocumentoNaoSuportado(ValueError):
    """Levantado quando o arquivo de escopo não está em um formato suportado (.docx ou .pdf)."""


class DocumentoIlegivel(ValueError):
    """Levantado quando o arquivo tem a extensão certa, mas o conteúdo não pode ser lido.

    Ex.: arquivo corrompido, protegido por senha ou só renomeado para .docx/.pdf.
    """
