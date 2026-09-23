from ninja import Schema


class ErroDeCampo(Schema):
    campo: str
    origem: str
    mensagem: str


class ErroSaida(Schema):
    """Formato único de erro da API.

    `codigo` identifica o tipo do erro para quem consome a API: dados_invalidos
    (422), regra_de_negocio (400), nao_encontrado (404), conflito (409),
    ia_resposta_invalida (502), ia_indisponivel (503), erro_interno (500).
    """

    detail: str
    codigo: str
    erros: list[ErroDeCampo] | None = None
