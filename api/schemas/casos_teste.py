from ninja import Field, Schema

from modelos import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade


class CasoTesteEntrada(Schema):
    codigo: str = Field(max_length=20)
    titulo: str = Field(max_length=200)
    categoria: CategoriaCasoDeTeste = CategoriaCasoDeTeste.FUNCIONAL
    pre_condicao: str | None = None
    passos: str | None = None
    resultado_esperado: str | None = None
    prioridade: Prioridade = Prioridade.MEDIA


class CasoTesteAtualizacao(Schema):
    """Todos os campos são opcionais: só os enviados no corpo são alterados (PATCH)."""

    codigo: str | None = Field(default=None, max_length=20)
    titulo: str | None = Field(default=None, max_length=200)
    categoria: CategoriaCasoDeTeste | None = None
    pre_condicao: str | None = None
    passos: str | None = None
    resultado_esperado: str | None = None
    prioridade: Prioridade | None = None


class CasoTesteSaida(Schema):
    id: int
    escopo_id: int
    codigo: str
    titulo: str
    categoria: CategoriaCasoDeTeste
    pre_condicao: str | None
    passos: str | None
    resultado_esperado: str | None
    prioridade: Prioridade
    origem: OrigemCasoDeTeste


class FiltroCasosTeste(Schema):
    projeto_id: int | None = None
    escopo_id: int | None = None
    categoria: CategoriaCasoDeTeste | None = None
    origem: OrigemCasoDeTeste | None = None
