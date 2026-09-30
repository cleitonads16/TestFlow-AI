from ninja import Query, Router, Status

from modelos.models import Projeto, RodadaDeExecucao
from schemas import (
    ExecucaoSaida,
    FiltroExecucoes,
    InclusaoDeCasos,
    ResumoRodada,
    RodadaDetalhe,
    RodadaEntrada,
    RodadaSaida,
)
from servicos import (
    adicionar_casos_a_rodada,
    criar_rodada,
    listar_execucoes,
    listar_rodadas,
    obter_casos_por_ids,
    resumo_rodada,
)

from .comum import obter_ou_404, respostas_de_erro

router = Router(tags=["Rodadas de execução"])


@router.post(
    "/projetos/{projeto_id}/rodadas",
    response={201: RodadaSaida, **respostas_de_erro(400, 404, 409, 422)},
    summary="Criar rodada de execução",
)
def criar(request, projeto_id: int, payload: RodadaEntrada):
    """Cria a rodada e agenda os casos informados como "pendente" (tudo ou nada).

    Os casos precisam ser do mesmo projeto da rodada; se algum for recusado,
    a rodada não é criada.
    """
    projeto = obter_ou_404(Projeto, projeto_id)
    rodada = criar_rodada(
        projeto,
        payload.nome,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        casos=obter_casos_por_ids(payload.casos_ids),
    )
    return Status(201, rodada)


@router.get(
    "/projetos/{projeto_id}/rodadas",
    response={200: list[RodadaSaida], **respostas_de_erro(404)},
    summary="Listar rodadas do projeto",
)
def listar(request, projeto_id: int):
    return listar_rodadas(obter_ou_404(Projeto, projeto_id))


@router.get(
    "/rodadas/{rodada_id}",
    response={200: RodadaDetalhe, **respostas_de_erro(404)},
    summary="Detalhar rodada",
)
def detalhar(request, rodada_id: int):
    """Dados da rodada junto com o resumo das execuções por status."""
    rodada = obter_ou_404(RodadaDeExecucao, rodada_id)
    rodada.resumo = resumo_rodada(rodada)
    return rodada


@router.get(
    "/rodadas/{rodada_id}/resumo",
    response={200: ResumoRodada, **respostas_de_erro(404)},
    summary="Resumo da rodada",
)
def resumo(request, rodada_id: int):
    """Quantidade de execuções por status na rodada, mais o total."""
    return resumo_rodada(obter_ou_404(RodadaDeExecucao, rodada_id))


@router.post(
    "/rodadas/{rodada_id}/casos",
    response={201: list[ExecucaoSaida], **respostas_de_erro(400, 404, 409, 422)},
    summary="Incluir casos na rodada",
)
def adicionar_casos(request, rodada_id: int, payload: InclusaoDeCasos):
    """Inclui casos do mesmo projeto na rodada, cada um como uma execução "pendente".

    Um caso que já está na rodada é recusado (409).
    """
    rodada = obter_ou_404(RodadaDeExecucao, rodada_id)
    execucoes = adicionar_casos_a_rodada(rodada, obter_casos_por_ids(payload.casos_ids))
    return Status(201, execucoes)


@router.get(
    "/rodadas/{rodada_id}/execucoes",
    response={200: list[ExecucaoSaida], **respostas_de_erro(404, 422)},
    summary="Listar execuções da rodada",
)
def listar_execucoes_da_rodada(request, rodada_id: int, filtros: Query[FiltroExecucoes]):
    return listar_execucoes(obter_ou_404(RodadaDeExecucao, rodada_id), status=filtros.status)
