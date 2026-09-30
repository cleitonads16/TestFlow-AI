from ninja import Query, Router

from modelos.models import Defeito
from schemas import DefeitoAtualizacao, DefeitoSaida, FiltroDefeitos
from servicos import atualizar_status_defeito, listar_defeitos

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Defeitos"])


@router.get(
    "/defeitos",
    response={200: list[DefeitoSaida], **respostas_de_erro(422)},
    summary="Listar defeitos",
)
def listar(request, filtros: Query[FiltroDefeitos]):
    """Lista os defeitos de todos os projetos. Os filtros podem ser combinados."""
    return listar_defeitos(**filtros.dict())


@router.get(
    "/defeitos/{defeito_id}",
    response={200: DefeitoSaida, **respostas_de_erro(404)},
    summary="Detalhar defeito",
)
def detalhar(request, defeito_id: int):
    return obter_ou_404(Defeito, defeito_id)


@router.patch(
    "/defeitos/{defeito_id}",
    response={200: DefeitoSaida, **respostas_de_erro(404, 422)},
    summary="Atualizar status do defeito",
)
def atualizar_status(request, defeito_id: int, payload: DefeitoAtualizacao):
    return atualizar_status_defeito(obter_ou_404(Defeito, defeito_id), payload.status)
