from ninja import Router, Status

from modelos.models import ExecucaoDeCaso
from schemas import DefeitoEntrada, DefeitoSaida, ExecucaoSaida, ResultadoExecucao
from servicos import listar_defeitos, registrar_defeito, registrar_execucao

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Execuções"])


@router.get(
    "/execucoes/{execucao_id}",
    response={200: ExecucaoSaida, **respostas_de_erro(404)},
    summary="Detalhar execução",
)
def detalhar(request, execucao_id: int):
    return obter_ou_404(ExecucaoDeCaso, execucao_id)


@router.put(
    "/execucoes/{execucao_id}/resultado",
    response={200: ExecucaoSaida, **respostas_de_erro(400, 404, 422)},
    summary="Registrar resultado da execução",
)
def registrar_resultado(request, execucao_id: int, payload: ResultadoExecucao):
    """Registra (ou corrige) o resultado da execução; a data é gravada automaticamente.

    "pendente" não é aceito como resultado, e "bloqueado" exige observações (400).
    """
    execucao = obter_ou_404(ExecucaoDeCaso, execucao_id)
    return registrar_execucao(execucao, payload.status, payload.observacoes)


@router.post(
    "/execucoes/{execucao_id}/defeitos",
    response={201: DefeitoSaida, **respostas_de_erro(400, 404, 422)},
    summary="Abrir defeito",
)
def abrir_defeito(request, execucao_id: int, payload: DefeitoEntrada):
    """Abre um defeito em uma execução que falhou; o defeito nasce "aberto".

    Em uma execução com outro resultado, o defeito é recusado (400).
    """
    execucao = obter_ou_404(ExecucaoDeCaso, execucao_id)
    return Status(201, registrar_defeito(execucao, payload.descricao, payload.severidade))


@router.get(
    "/execucoes/{execucao_id}/defeitos",
    response={200: list[DefeitoSaida], **respostas_de_erro(404)},
    summary="Listar defeitos da execução",
)
def listar_defeitos_da_execucao(request, execucao_id: int):
    return listar_defeitos(execucao=obter_ou_404(ExecucaoDeCaso, execucao_id))
