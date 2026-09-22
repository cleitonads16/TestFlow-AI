from pathlib import Path

from django.db import transaction
from django.utils import timezone

from documentos import extrair_texto
from ia import LLMProvider
from modelos import OrigemCasoDeTeste, StatusEscopo
from modelos.models import CasoDeTeste, Escopo, GeracaoIA


def processar_escopo(
    escopo: Escopo,
    caminho_arquivo: str | Path,
    provedor: LLMProvider,
) -> list[CasoDeTeste]:
    """Extrai o texto do documento de escopo, gera casos de teste via IA e persiste tudo.

    Fluxo completo descrito na arquitetura (docs/arquitetura-e-cronograma.md,
    seção 4): extrair texto -> LLMProvider.gerar_casos_teste -> casos
    vinculados ao Escopo (origem="ia") + registro de auditoria (GeracaoIA).
    Em caso de erro (extração ou IA), o Escopo é marcado como "erro" e a
    exceção original é repropagada para quem chamou decidir o que fazer.
    A gravação do caminho feliz é atômica: ou salva escopo, casos e
    auditoria juntos, ou não salva nada.
    """
    try:
        escopo.texto_extraido = extrair_texto(caminho_arquivo)
        casos_gerados = provedor.gerar_casos_teste(escopo.texto_extraido)
    except Exception:
        escopo.status = StatusEscopo.ERRO.value
        escopo.save()
        raise

    with transaction.atomic():
        escopo.status = StatusEscopo.PROCESSADO.value
        escopo.save()

        casos = [
            CasoDeTeste.objects.create(
                codigo=caso_gerado.codigo,
                titulo=caso_gerado.titulo,
                categoria=caso_gerado.categoria.value,
                pre_condicao=caso_gerado.pre_condicao,
                passos=caso_gerado.passos,
                resultado_esperado=caso_gerado.resultado_esperado,
                prioridade=caso_gerado.prioridade.value,
                origem=OrigemCasoDeTeste.IA.value,
                escopo=escopo,
            )
            for caso_gerado in casos_gerados
        ]

        GeracaoIA.objects.create(
            provedor=provedor.nome,
            modelo=provedor.modelo,
            quantidade_casos_gerados=len(casos),
            tokens_utilizados=provedor.ultimo_tokens_utilizados,
            data=timezone.now(),
            escopo=escopo,
        )

    return casos
