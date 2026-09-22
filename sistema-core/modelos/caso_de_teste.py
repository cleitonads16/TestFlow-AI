from django.db import models

from .enums import CategoriaCasoDeTeste, OrigemCasoDeTeste, Prioridade, como_choices


class CasoDeTeste(models.Model):
    codigo = models.CharField(max_length=20)
    titulo = models.CharField(max_length=200)
    categoria = models.CharField(
        max_length=20,
        choices=como_choices(CategoriaCasoDeTeste),
        default=CategoriaCasoDeTeste.FUNCIONAL.value,
    )
    pre_condicao = models.TextField(null=True, blank=True)
    passos = models.TextField(null=True, blank=True)
    resultado_esperado = models.TextField(null=True, blank=True)
    prioridade = models.CharField(
        max_length=20, choices=como_choices(Prioridade), default=Prioridade.MEDIA.value
    )
    origem = models.CharField(
        max_length=20,
        choices=como_choices(OrigemCasoDeTeste),
        default=OrigemCasoDeTeste.MANUAL.value,
    )

    escopo = models.ForeignKey(
        "modelos.Escopo", on_delete=models.CASCADE, related_name="casos_de_teste"
    )

    class Meta:
        db_table = "casos_de_teste"

    def __str__(self) -> str:
        return f"{self.codigo} — {self.titulo}"
