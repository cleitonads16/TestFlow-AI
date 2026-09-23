from django.shortcuts import get_object_or_404
from ninja import Query, Router, Status

from modelos.models import CasoDeTeste, Escopo
from schemas import (
    CasoTesteAtualizacao,
    CasoTesteEntrada,
    CasoTesteSaida,
    ErroSaida,
    FiltroCasosTeste,
)
from servicos import (
    atualizar_caso_teste,
    criar_caso_teste,
    excluir_caso_teste,
    listar_casos_teste,
)

router = Router(tags=["Casos de teste"])


@router.get("/casos-de-teste", response={200: list[CasoTesteSaida], 404: ErroSaida})
def listar(request, filtros: Query[FiltroCasosTeste]):
    escopo = (
        get_object_or_404(Escopo, id=filtros.escopo_id) if filtros.escopo_id is not None else None
    )
    return listar_casos_teste(
        escopo=escopo,
        projeto_id=filtros.projeto_id,
        categoria=filtros.categoria,
        origem=filtros.origem,
    )


@router.post(
    "/escopos/{escopo_id}/casos-de-teste",
    response={201: CasoTesteSaida, 400: ErroSaida, 404: ErroSaida},
)
def criar(request, escopo_id: int, payload: CasoTesteEntrada):
    """Cria um caso de teste manual (origem "manual") no escopo."""
    escopo = get_object_or_404(Escopo, id=escopo_id)
    return Status(201, criar_caso_teste(escopo, **payload.dict()))


@router.get("/casos-de-teste/{caso_id}", response={200: CasoTesteSaida, 404: ErroSaida})
def detalhar(request, caso_id: int):
    return get_object_or_404(CasoDeTeste, id=caso_id)


@router.patch(
    "/casos-de-teste/{caso_id}",
    response={200: CasoTesteSaida, 400: ErroSaida, 404: ErroSaida},
)
def atualizar(request, caso_id: int, payload: CasoTesteAtualizacao):
    """Revisa um caso (manual ou gerado por IA); só os campos enviados são alterados."""
    caso = get_object_or_404(CasoDeTeste, id=caso_id)
    return atualizar_caso_teste(caso, **payload.dict(exclude_unset=True))


@router.delete(
    "/casos-de-teste/{caso_id}",
    response={204: None, 400: ErroSaida, 404: ErroSaida},
)
def excluir(request, caso_id: int):
    """Exclui o caso; recusado se ele já entrou em alguma rodada de execução."""
    excluir_caso_teste(get_object_or_404(CasoDeTeste, id=caso_id))
    return Status(204, None)
