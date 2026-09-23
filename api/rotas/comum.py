from django.db.models import Model
from django.http import Http404

from modelos.models import (
    CasoDeTeste,
    Defeito,
    Escopo,
    ExecucaoDeCaso,
    Projeto,
    RodadaDeExecucao,
)
from schemas import ErroSaida

_NAO_ENCONTRADO = {
    Projeto: "Projeto {} não encontrado.",
    Escopo: "Escopo {} não encontrado.",
    CasoDeTeste: "Caso de teste {} não encontrado.",
    RodadaDeExecucao: "Rodada de execução {} não encontrada.",
    ExecucaoDeCaso: "Execução {} não encontrada.",
    Defeito: "Defeito {} não encontrado.",
}


def obter_ou_404[M: Model](modelo: type[M], id_registro: int) -> M:
    """Como o `get_object_or_404` do Django, mas com a mensagem em português e o id buscado."""
    try:
        return modelo.objects.get(id=id_registro)
    except modelo.DoesNotExist:
        raise Http404(_NAO_ENCONTRADO[modelo].format(id_registro)) from None


def respostas_de_erro(*status: int) -> dict[int, type[ErroSaida]]:
    return {codigo: ErroSaida for codigo in status}
