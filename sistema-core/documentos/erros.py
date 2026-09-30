class FormatoDocumentoNaoSuportado(ValueError):
    """Levantado quando o arquivo de escopo não está em um formato suportado (.docx)."""


class DocumentoIlegivel(ValueError):
    """Levantado quando o arquivo tem a extensão certa, mas o conteúdo não pode ser lido.

    Ex.: arquivo corrompido, protegido por senha ou só renomeado para .docx.
    """


class DocumentoSemTexto(ValueError):
    """Levantado quando o documento é legível, mas não tem texto para enviar à IA.

    Sem isso, a IA receberia um escopo vazio e poderia inventar casos de teste.
    """
