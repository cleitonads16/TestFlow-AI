from django.db import models


class RodadaDeExecucao(models.Model):
    nome = models.CharField(max_length=120)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)

    projeto = models.ForeignKey(
        "modelos.Projeto", on_delete=models.CASCADE, related_name="rodadas_execucao"
    )

    class Meta:
        db_table = "rodadas_execucao"

    def __str__(self) -> str:
        return self.nome
