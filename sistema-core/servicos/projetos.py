from modelos.models import Projeto

from .erros import exigir_texto


def criar_projeto(nome: str, descricao: str | None = None) -> Projeto:
    return Projeto.objects.create(nome=exigir_texto(nome, "nome"), descricao=descricao)


def listar_projetos() -> list[Projeto]:
    return list(Projeto.objects.order_by("nome"))
