from django.db import models

from .enums import SeveridadeDefeito, StatusDefeito, como_choices


class Defeito(models.Model):
    descricao = models.CharField(max_length=1000)
    severidade = models.CharField(
        max_length=20,
        choices=como_choices(SeveridadeDefeito),
        default=SeveridadeDefeito.MEDIA.value,
    )
    status = models.CharField(
        max_length=20, choices=como_choices(StatusDefeito), default=StatusDefeito.ABERTO.value
    )

    execucao = models.ForeignKey(
        "modelos.ExecucaoDeCaso", on_delete=models.CASCADE, related_name="defeitos"
    )

    class Meta:
        db_table = "defeitos"
