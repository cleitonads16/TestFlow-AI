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
    summary="Enviar documento de escopo",
)
def enviar(request, projeto_id: int, arquivo: File[UploadedFile]):
    """Envia o documento de escopo (.docx ou .pdf, até 10 MB). O escopo nasce "pendente".

    O formato é conferido já no envio: um arquivo em outro formato, vazio ou
    acima do limite é recusado com 400.
    """
    projeto = obter_ou_404(Projeto, projeto_id)
    return Status(201, registrar_escopo(projeto, arquivo.name, arquivo.read()))


@router.get(
    "/projetos/{projeto_id}/escopos",
    response={200: list[EscopoSaida], **respostas_de_erro(404)},
    summary="Listar escopos do projeto",
)
def listar(request, projeto_id: int):
    return listar_escopos(obter_ou_404(Projeto, projeto_id))


@router.get(
    "/escopos/{escopo_id}",
    response={200: EscopoDetalhe, **respostas_de_erro(404)},
    summary="Detalhar escopo",
)
def detalhar(request, escopo_id: int):
    """Inclui o texto extraído do documento, preenchido depois da geração de casos."""
    return obter_ou_404(Escopo, escopo_id)


@router.post(
    "/escopos/{escopo_id}/gerar-casos",
    response={201: GeracaoCasosSaida, **respostas_de_erro(400, 404, 409, 502, 503)},
    summary="Gerar casos de teste via IA",
)
def gerar_casos(request, escopo_id: int):
    """Extrai o texto do escopo e gera os casos de teste via IA (chamada síncrona).

    A resposta pode levar alguns segundos, o tempo de o provedor de IA
    responder. Os casos nascem com origem "ia" e o escopo passa a
    "processado"; um escopo já processado é recusado (409) para não duplicar
    os casos. Se a IA falhar (502/503), o escopo fica como "erro" e pode ser
    gerado de novo.
    """
    escopo = obter_ou_404(Escopo, escopo_id)
    casos = processar_escopo(escopo, caminho_documento(escopo), obter_provedor_llm())
    return Status(
        201, {"escopo": escopo, "quantidade_casos_gerados": len(casos), "casos": casos}
    )
