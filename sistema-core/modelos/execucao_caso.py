from django.db import models

from .enums import StatusExecucaoCaso, como_choices


class ExecucaoDeCaso(models.Model):
    status = models.CharField(
        max_length=20,
        choices=como_choices(StatusExecucaoCaso),
        default=StatusExecucaoCaso.PENDENTE.value,
    )
    observacoes = models.CharField(max_length=1000, null=True, blank=True)
    data_execucao = models.DateTimeField(null=True, blank=True)

    rodada = models.ForeignKey(
        "modelos.RodadaDeExecucao", on_delete=models.CASCADE, related_name="execucoes"
    )
    caso_de_teste = models.ForeignKey(
        "modelos.CasoDeTeste", on_delete=models.CASCADE, related_name="execucoes"
    )

    class Meta:
        db_table = "execucoes_caso"
