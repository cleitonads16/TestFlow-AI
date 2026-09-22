from django.contrib import admin

from .models import (
    CasoDeTeste,
    Defeito,
    Escopo,
    ExecucaoDeCaso,
    GeracaoIA,
    Projeto,
    RodadaDeExecucao,
)

admin.site.register(
    [Projeto, Escopo, CasoDeTeste, RodadaDeExecucao, ExecucaoDeCaso, Defeito, GeracaoIA]
)
