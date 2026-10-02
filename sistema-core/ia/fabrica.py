import os

from .provedor_claude import ProvedorClaude
from .provedor_openai import ProvedorOpenAI
from .provider import LLMProvider

_PROVEDORES = {
    "claude": ProvedorClaude,
    "openai": ProvedorOpenAI,
}


def obter_provedor_llm(nome: str | None = None) -> LLMProvider:
    """Instancia o provedor de IA configurado.

    Lê o nome do provedor de `nome` ou, se omitido, da variável de ambiente
    `LLM_PROVIDER` (padrão: "claude"). Adicionar um novo provedor no futuro
    (ex.: um terceiro provedor) exige apenas implementar `LLMProvider` e registrá-lo em
    `_PROVEDORES` — nenhum outro ponto do sistema precisa mudar.
    """
    nome_provedor = (nome or os.getenv("LLM_PROVIDER", "claude")).lower()
    classe_provedor = _PROVEDORES.get(nome_provedor)
    if classe_provedor is None:
        disponiveis = ", ".join(sorted(_PROVEDORES))
        raise ValueError(
            f"Provedor de IA '{nome_provedor}' não suportado. Disponíveis: {disponiveis}."
        )
    return classe_provedor()
