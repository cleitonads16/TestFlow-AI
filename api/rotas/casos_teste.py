from ninja import Query, Router, Status

from modelos.models import CasoDeTeste, Escopo
from schemas import CasoTesteAtualizacao, CasoTesteEntrada, CasoTesteSaida, FiltroCasosTeste
from servicos import (
    atualizar_caso_teste,
    criar_caso_teste,
    excluir_caso_teste,
    listar_casos_teste,
)

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Casos de teste"])


@router.get(
    "/casos-de-teste",
    response={200: list[CasoTesteSaida], **respostas_de_erro(404, 422)},
    summary="Listar casos de teste",
)
def listar(request, filtros: Query[FiltroCasosTeste]):
    """Lista os casos, ordenados por escopo e código. Os filtros podem ser combinados."""
    escopo = obter_ou_404(Escopo, filtros.escopo_id) if filtros.escopo_id is not None else None
    return listar_casos_teste(
        escopo=escopo,
        projeto_id=filtros.projeto_id,
        categoria=filtros.categoria,
        origem=filtros.origem,
    )


@router.post(
    "/escopos/{escopo_id}/casos-de-teste",
    response={201: CasoTesteSaida, **respostas_de_erro(400, 404, 409, 422)},
    summary="Criar caso de teste manual",
)
def criar(request, escopo_id: int, payload: CasoTesteEntrada):
    """Cria um caso de teste manual (origem "manual") no escopo.

    O código precisa ser único dentro do escopo (409 se já existir).
    """
    escopo = obter_ou_404(Escopo, escopo_id)
    return Status(201, criar_caso_teste(escopo, **payload.dict()))


@router.get(
    "/casos-de-teste/{caso_id}",
    response={200: CasoTesteSaida, **respostas_de_erro(404)},
    summary="Detalhar caso de teste",
)
def detalhar(request, caso_id: int):
    return obter_ou_404(CasoDeTeste, caso_id)


@router.patch(
    "/casos-de-teste/{caso_id}",
    response={200: CasoTesteSaida, **respostas_de_erro(400, 404, 409, 422)},
    summary="Revisar caso de teste",
)
def atualizar(request, caso_id: int, payload: CasoTesteAtualizacao):
    """Revisa um caso (manual ou gerado por IA); só os campos enviados são alterados."""
    caso = obter_ou_404(CasoDeTeste, caso_id)
    return atualizar_caso_teste(caso, **payload.dict(exclude_unset=True))


@router.delete(
    "/casos-de-teste/{caso_id}",
    response={204: None, **respostas_de_erro(404, 409)},
    summary="Excluir caso de teste",
)
def excluir(request, caso_id: int):
    """Exclui o caso; recusado (409) se ele já entrou em alguma rodada de execução."""
    excluir_caso_teste(obter_ou_404(CasoDeTeste, caso_id))
    return Status(204, None)
