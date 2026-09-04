from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from documentos import extrair_texto
from ia import LLMProvider
from modelos import CasoDeTeste, Escopo, GeracaoIA, OrigemCasoDeTeste, StatusEscopo


def processar_escopo(
    sessao: Session,
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
    """
    try:
        escopo.texto_extraido = extrair_texto(caminho_arquivo)
        casos_gerados = provedor.gerar_casos_teste(escopo.texto_extraido)
    except Exception:
        escopo.status = StatusEscopo.ERRO
        sessao.add(escopo)
        sessao.commit()
        raise

    casos = [
        CasoDeTeste(
            codigo=caso_gerado.codigo,
            titulo=caso_gerado.titulo,
            categoria=caso_gerado.categoria,
            pre_condicao=caso_gerado.pre_condicao,
            passos=caso_gerado.passos,
            resultado_esperado=caso_gerado.resultado_esperado,
            prioridade=caso_gerado.prioridade,
            origem=OrigemCasoDeTeste.IA,
            escopo=escopo,
        )
        for caso_gerado in casos_gerados
    ]
    escopo.status = StatusEscopo.PROCESSADO

    geracao = GeracaoIA(
        provedor=provedor.nome,
        modelo=provedor.modelo,
        quantidade_casos_gerados=len(casos),
        tokens_utilizados=provedor.ultimo_tokens_utilizados,
        data=datetime.now(),
        escopo=escopo,
    )

    sessao.add(escopo)
    sessao.add_all(casos)
    sessao.add(geracao)
    sessao.commit()

    return casos
