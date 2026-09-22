from django.db import models


class GeracaoIA(models.Model):
    """Registro de auditoria de cada chamada ao provedor de IA para gerar casos de teste."""

    provedor = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    quantidade_casos_gerados = models.IntegerField(default=0)
    tokens_utilizados = models.IntegerField(null=True, blank=True)
    data = models.DateTimeField(null=True, blank=True)

    escopo = models.ForeignKey(
        "modelos.Escopo", on_delete=models.CASCADE, related_name="geracoes_ia"
    )

    class Meta:
        db_table = "geracoes_ia"
