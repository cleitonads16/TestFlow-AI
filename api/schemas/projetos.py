from ninja import Field, Schema
from pydantic import ConfigDict


class ProjetoEntrada(Schema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"nome": "Portal do Cliente", "descricao": "Autoatendimento de faturas e pedidos."}
            ]
        }
    )

    nome: str = Field(max_length=120)
    descricao: str | None = Field(default=None, max_length=500)


class ProjetoSaida(Schema):
    id: int
    nome: str
    descricao: str | None
