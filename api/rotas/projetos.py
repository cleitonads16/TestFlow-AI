from ninja import Router, Status

from modelos.models import Projeto
from schemas import ProjetoEntrada, ProjetoSaida
from servicos import criar_projeto, listar_projetos

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Projetos"])


@router.post(
    "/projetos",
    response={201: ProjetoSaida, **respostas_de_erro(400, 409, 422)},
    summary="Criar projeto",
)
def criar(request, payload: ProjetoEntrada):
    return Status(201, criar_projeto(**payload.dict()))


@router.get("/projetos", response=list[ProjetoSaida], summary="Listar projetos")
def listar(request):
    """Lista todos os projetos, em ordem alfabética de nome."""
    return listar_projetos()


@router.get(
    "/projetos/{projeto_id}",
    response={200: ProjetoSaida, **respostas_de_erro(404)},
    summary="Detalhar projeto",
)
def detalhar(request, projeto_id: int):
    return obter_ou_404(Projeto, projeto_id)
