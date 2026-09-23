from django.shortcuts import get_object_or_404
from ninja import File, Router, Status, UploadedFile

from ia import obter_provedor_llm
from modelos.models import Escopo, Projeto
from schemas import ErroSaida, EscopoDetalhe, EscopoSaida, GeracaoCasosSaida
from servicos import caminho_documento, listar_escopos, processar_escopo, registrar_escopo

router = Router(tags=["Escopos"])


@router.post(
    "/projetos/{projeto_id}/escopos",
    response={201: EscopoSaida, 400: ErroSaida, 404: ErroSaida},
)
def enviar(request, projeto_id: int, arquivo: File[UploadedFile]):
    """Envia o documento de escopo (.docx ou .pdf, até 10 MB). O escopo nasce "pendente"."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    return Status(201, registrar_escopo(projeto, arquivo.name, arquivo.read()))


@router.get(
    "/projetos/{projeto_id}/escopos",
    response={200: list[EscopoSaida], 404: ErroSaida},
)
def listar(request, projeto_id: int):
    return listar_escopos(get_object_or_404(Projeto, id=projeto_id))


@router.get("/escopos/{escopo_id}", response={200: EscopoDetalhe, 404: ErroSaida})
def detalhar(request, escopo_id: int):
    return get_object_or_404(Escopo, id=escopo_id)


@router.post(
    "/escopos/{escopo_id}/gerar-casos",
    response={
        201: GeracaoCasosSaida,
        400: ErroSaida,
        404: ErroSaida,
        502: ErroSaida,
        503: ErroSaida,
    },
)
def gerar_casos(request, escopo_id: int):
    """Extrai o texto do escopo e gera os casos de teste via IA (chamada síncrona)."""
    escopo = get_object_or_404(Escopo, id=escopo_id)
    casos = processar_escopo(escopo, caminho_documento(escopo), obter_provedor_llm())
    return Status(
        201, {"escopo": escopo, "quantidade_casos_gerados": len(casos), "casos": casos}
    )
