from django.db import models
from django.db.models.functions import Lower


class Projeto(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "projetos"
        constraints = [models.UniqueConstraint(Lower("nome"), name="projeto_nome_unico")]

    def __str__(self) -> str:
        return self.nome
