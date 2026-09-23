from ninja import Field, Schema


class ProjetoEntrada(Schema):
    nome: str = Field(max_length=120)
    descricao: str | None = Field(default=None, max_length=500)


class ProjetoSaida(Schema):
    id: int
    nome: str
    descricao: str | None
