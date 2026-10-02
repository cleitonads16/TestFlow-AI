from ninja import Field, Schema
from pydantic import ConfigDict


class ErroDeCampo(Schema):
    campo: str = Field(description="Campo recusado, ex.: titulo ou passos.0.")
    origem: str = Field(description="Onde o campo veio: body, query, path ou file.")
    mensagem: str


class ErroSaida(Schema):
    """Formato único de erro da API.

    `codigo` identifica o tipo do erro para quem consome a API: dados_invalidos
    (422), corpo_invalido (400), regra_de_negocio (400), nao_encontrado (404), conflito (409),
    ia_resposta_invalida (502), ia_indisponivel (503), erro_interno (500).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"detail": "Escopo 42 não encontrado.", "codigo": "nao_encontrado"},
                {
                    "detail": "Dados de entrada inválidos.",
                    "codigo": "dados_invalidos",
                    "erros": [
                        {"campo": "titulo", "origem": "body", "mensagem": "Campo obrigatório."}
                    ],
                },
            ]
        }
    )

    detail: str = Field(description="Mensagem em português para exibir ao usuário.")
    codigo: str = Field(description="Tipo do erro, estável para tratar no cliente.")
    erros: list[ErroDeCampo] | None = Field(
        default=None, description="Só nos erros de validação (422): um item por campo recusado."
    )
