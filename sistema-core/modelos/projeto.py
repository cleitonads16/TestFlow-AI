from django.db import models


class Projeto(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "projetos"

    def __str__(self) -> str:
        return self.nome
