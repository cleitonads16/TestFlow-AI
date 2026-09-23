from collections.abc import Iterable
from datetime import date

from django.db import transaction
from django.utils import timezone

from modelos import SeveridadeDefeito, StatusDefeito, StatusExecucaoCaso
from modelos.models import CasoDeTeste, Defeito, ExecucaoDeCaso, Projeto, RodadaDeExecucao

from .erros import OperacaoEmConflito, RegraDeNegocioViolada, converter_enum, exigir_texto


def criar_rodada(
    projeto: Projeto,
    nome: str,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    casos: Iterable[CasoDeTeste] = (),
) -> RodadaDeExecucao:
    """Cria uma rodada de execução e já agenda os casos informados como "pendente"."""
    if data_inicio and data_fim and data_fim < data_inicio:
        raise RegraDeNegocioViolada("A data de fim da rodada não pode ser anterior à de início.")

    with transaction.atomic():
        rodada = RodadaDeExecucao.objects.create(
            projeto=projeto,
            nome=exigir_texto(nome, "nome"),
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        adicionar_casos_a_rodada(rodada, casos)
    return rodada


def adicionar_casos_a_rodada(
    rodada: RodadaDeExecucao, casos: Iterable[CasoDeTeste]
) -> list[ExecucaoDeCaso]:
    """Inclui casos na rodada, cada um como uma ExecucaoDeCaso "pendente".

    Só aceita casos do mesmo projeto da rodada, e cada caso entra uma única
    vez por rodada (reexecutar é registrar de novo a mesma execução).
    """
    casos = list(casos)
    ids_ja_na_rodada = set(rodada.execucoes.values_list("caso_de_teste_id", flat=True))

    for caso in casos:
        if caso.escopo.projeto_id != rodada.projeto_id:
            raise RegraDeNegocioViolada(
                f"O caso {caso.codigo} pertence a outro projeto e não pode entrar nesta rodada."
            )
        if caso.id in ids_ja_na_rodada:
            raise OperacaoEmConflito(f"O caso {caso.codigo} já está nesta rodada.")
        ids_ja_na_rodada.add(caso.id)

    with transaction.atomic():
        return [
            ExecucaoDeCaso.objects.create(
                rodada=rodada,
                caso_de_teste=caso,
                status=StatusExecucaoCaso.PENDENTE.value,
            )
            for caso in casos
        ]


def registrar_execucao(
    execucao: ExecucaoDeCaso,
    status: StatusExecucaoCaso | str,
    observacoes: str | None = None,
) -> ExecucaoDeCaso:
    """Registra o resultado da execução de um caso na rodada.

    O resultado precisa ser "passou", "falhou" ou "bloqueado" ("pendente" é
    só o estado inicial). Um caso bloqueado exige observação explicando o
    impedimento, para que a equipe saiba o que destravar.
    """
    status = converter_enum(StatusExecucaoCaso, status, "status")
    if status == StatusExecucaoCaso.PENDENTE:
        raise RegraDeNegocioViolada(
            "Informe o resultado da execução: passou, falhou ou bloqueado."
        )
    if status == StatusExecucaoCaso.BLOQUEADO and not (observacoes and observacoes.strip()):
        raise RegraDeNegocioViolada("Uma execução bloqueada exige observação do impedimento.")

    execucao.status = status.value
    execucao.observacoes = observacoes
    execucao.data_execucao = timezone.now()
    execucao.save()
    return execucao


def registrar_defeito(
    execucao: ExecucaoDeCaso,
    descricao: str,
    severidade: SeveridadeDefeito | str = SeveridadeDefeito.MEDIA,
) -> Defeito:
    """Registra um defeito encontrado em uma execução que falhou."""
    if execucao.status != StatusExecucaoCaso.FALHOU:
        raise RegraDeNegocioViolada(
            "Defeitos só podem ser registrados em execuções com status 'falhou'."
        )
    return Defeito.objects.create(
        execucao=execucao,
        descricao=exigir_texto(descricao, "descricao"),
        severidade=converter_enum(SeveridadeDefeito, severidade, "severidade").value,
        status=StatusDefeito.ABERTO.value,
    )


def atualizar_status_defeito(defeito: Defeito, status: StatusDefeito | str) -> Defeito:
    defeito.status = converter_enum(StatusDefeito, status, "status").value
    defeito.save()
    return defeito


def resumo_rodada(rodada: RodadaDeExecucao) -> dict[str, int]:
    """Quantidade de execuções por status na rodada, mais o total."""
    resumo = {status.value: 0 for status in StatusExecucaoCaso}
    for status in rodada.execucoes.values_list("status", flat=True):
        resumo[status] += 1
    resumo["total"] = sum(resumo.values())
    return resumo


def listar_rodadas(projeto: Projeto) -> list[RodadaDeExecucao]:
    return list(projeto.rodadas_execucao.order_by("-id"))


def listar_execucoes(
    rodada: RodadaDeExecucao, status: StatusExecucaoCaso | str | None = None
) -> list[ExecucaoDeCaso]:
    consulta = rodada.execucoes.select_related("caso_de_teste").order_by("caso_de_teste__codigo")
    if status is not None:
        consulta = consulta.filter(
            status=converter_enum(StatusExecucaoCaso, status, "status").value
        )
    return list(consulta)


def listar_defeitos(
    execucao: ExecucaoDeCaso | None = None,
    rodada_id: int | None = None,
    projeto_id: int | None = None,
    status: StatusDefeito | str | None = None,
    severidade: SeveridadeDefeito | str | None = None,
) -> list[Defeito]:
    consulta = Defeito.objects.select_related("execucao__caso_de_teste").order_by("-id")
    if execucao is not None:
        consulta = consulta.filter(execucao=execucao)
    if rodada_id is not None:
        consulta = consulta.filter(execucao__rodada_id=rodada_id)
    if projeto_id is not None:
        consulta = consulta.filter(execucao__rodada__projeto_id=projeto_id)
    if status is not None:
        consulta = consulta.filter(status=converter_enum(StatusDefeito, status, "status").value)
    if severidade is not None:
        consulta = consulta.filter(
            severidade=converter_enum(SeveridadeDefeito, severidade, "severidade").value
        )
    return list(consulta)
