from django.db import models

from .enums import StatusEscopo, como_choices


class Escopo(models.Model):
    nome_arquivo = models.CharField(max_length=255)
    texto_extraido = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=como_choices(StatusEscopo), default=StatusEscopo.PENDENTE.value
    )
    data_upload = models.DateTimeField(null=True, blank=True)

    projeto = models.ForeignKey(
        "modelos.Projeto", on_delete=models.CASCADE, related_name="escopos"
    )

    class Meta:
        db_table = "escopos"

    def __str__(self) -> str:
        return self.nome_arquivo
