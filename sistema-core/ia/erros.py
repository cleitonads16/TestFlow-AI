class RespostaIAInvalida(RuntimeError):
    """Levantado quando o provedor de IA não retorna os casos de teste no formato esperado."""


class ProvedorIAIndisponivel(RuntimeError):
    """Levantado quando a chamada ao provedor de IA falha (rede, autenticação, limite de uso, etc.).

    Cada adaptador traduz os erros do seu SDK para esta exceção, para que
    quem consome `LLMProvider` não precise conhecer o SDK de um provedor específico.
    """
