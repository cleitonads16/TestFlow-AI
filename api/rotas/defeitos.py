from ninja import Query, Router

from modelos.models import Defeito
from schemas import DefeitoAtualizacao, DefeitoSaida, FiltroDefeitos
from servicos import atualizar_status_defeito, listar_defeitos

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Defeitos"])


@router.get("/defeitos", response={200: list[DefeitoSaida], **respostas_de_erro(422)})
def listar(request, filtros: Query[FiltroDefeitos]):
    return listar_defeitos(**filtros.dict())


@router.get("/defeitos/{defeito_id}", response={200: DefeitoSaida, **respostas_de_erro(404)})
def detalhar(request, defeito_id: int):
    return obter_ou_404(Defeito, defeito_id)


@router.patch(
    "/defeitos/{defeito_id}",
    response={200: DefeitoSaida, **respostas_de_erro(404, 422)},
)
def atualizar_status(request, defeito_id: int, payload: DefeitoAtualizacao):
    return atualizar_status_defeito(obter_ou_404(Defeito, defeito_id), payload.status)
