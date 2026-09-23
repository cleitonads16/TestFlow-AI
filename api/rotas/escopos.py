from ninja import File, Router, Status, UploadedFile

from ia import obter_provedor_llm
from modelos.models import Escopo, Projeto
from schemas import EscopoDetalhe, EscopoSaida, GeracaoCasosSaida
from servicos import caminho_documento, listar_escopos, processar_escopo, registrar_escopo

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Escopos"])


@router.post(
    "/projetos/{projeto_id}/escopos",
    response={201: EscopoSaida, **respostas_de_erro(400, 404, 422)},
)
def enviar(request, projeto_id: int, arquivo: File[UploadedFile]):
    """Envia o documento de escopo (.docx ou .pdf, até 10 MB). O escopo nasce "pendente"."""
    projeto = obter_ou_404(Projeto, projeto_id)
    return Status(201, registrar_escopo(projeto, arquivo.name, arquivo.read()))


@router.get(
    "/projetos/{projeto_id}/escopos",
    response={200: list[EscopoSaida], **respostas_de_erro(404)},
)
def listar(request, projeto_id: int):
    return listar_escopos(obter_ou_404(Projeto, projeto_id))


@router.get("/escopos/{escopo_id}", response={200: EscopoDetalhe, **respostas_de_erro(404)})
def detalhar(request, escopo_id: int):
    return obter_ou_404(Escopo, escopo_id)


@router.post(
    "/escopos/{escopo_id}/gerar-casos",
    response={201: GeracaoCasosSaida, **respostas_de_erro(400, 404, 409, 502, 503)},
)
def gerar_casos(request, escopo_id: int):
    """Extrai o texto do escopo e gera os casos de teste via IA (chamada síncrona)."""
    escopo = obter_ou_404(Escopo, escopo_id)
    casos = processar_escopo(escopo, caminho_documento(escopo), obter_provedor_llm())
    return Status(
        201, {"escopo": escopo, "quantidade_casos_gerados": len(casos), "casos": casos}
    )
