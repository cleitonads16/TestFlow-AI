from modelos.models import Projeto

from .erros import OperacaoEmConflito, exigir_texto


def criar_projeto(nome: str, descricao: str | None = None) -> Projeto:
    nome = exigir_texto(nome, "nome")
    existente = Projeto.objects.filter(nome__iexact=nome).first()
    if existente is not None:
        raise OperacaoEmConflito(f"Já existe um projeto com o nome '{existente.nome}'.")
    return Projeto.objects.create(nome=nome, descricao=descricao)


def listar_projetos() -> list[Projeto]:
    return list(Projeto.objects.order_by("nome"))
