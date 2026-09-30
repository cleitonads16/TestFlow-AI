from ninja import Field, Schema
from pydantic import ConfigDict

from modelos import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade


class CasoTesteEntrada(Schema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "codigo": "CT-010",
                    "titulo": "Login com senha expirada",
                    "categoria": "funcional",
                    "pre_condicao": "Usuário cadastrado com senha vencida.",
                    "passos": "1. Abrir a tela de login\n2. Informar usuário e senha\n3. Confirmar",
                    "resultado_esperado": "O sistema pede a troca da senha antes de liberar o acesso.",
                    "prioridade": "alta",
                }
            ]
        }
    )

    codigo: str = Field(max_length=20, description="Único dentro do escopo, ex.: CT-010.")
    titulo: str = Field(max_length=200)
    categoria: CategoriaCasoDeTeste = CategoriaCasoDeTeste.FUNCIONAL
    pre_condicao: str | None = None
    passos: str | None = None
    resultado_esperado: str | None = None
    prioridade: Prioridade = Prioridade.MEDIA


class CasoTesteAtualizacao(Schema):
    """Todos os campos são opcionais: só os enviados no corpo são alterados (PATCH)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"titulo": "Login com senha vencida", "prioridade": "media"}]}
    )

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
    origem: OrigemCasoDeTeste = Field(
        description='"ia" para os casos gerados pela IA, "manual" para os cadastrados à mão.'
    )


class FiltroCasosTeste(Schema):
    projeto_id: int | None = Field(default=None, description="Casos de todos os escopos do projeto.")
    escopo_id: int | None = Field(default=None, description="Casos de um escopo (404 se não existir).")
    categoria: CategoriaCasoDeTeste | None = None
    origem: OrigemCasoDeTeste | None = None
