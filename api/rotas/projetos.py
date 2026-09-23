from django.shortcuts import get_object_or_404
from ninja import Router, Status

from modelos.models import Projeto
from schemas import ErroSaida, ProjetoEntrada, ProjetoSaida
from servicos import criar_projeto, listar_projetos

router = Router(tags=["Projetos"])


@router.post("/projetos", response={201: ProjetoSaida, 400: ErroSaida})
def criar(request, payload: ProjetoEntrada):
    return Status(201, criar_projeto(**payload.dict()))


@router.get("/projetos", response=list[ProjetoSaida])
def listar(request):
    return listar_projetos()


@router.get("/projetos/{projeto_id}", response={200: ProjetoSaida, 404: ErroSaida})
def detalhar(request, projeto_id: int):
    return get_object_or_404(Projeto, id=projeto_id)
