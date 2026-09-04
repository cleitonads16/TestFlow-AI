from abc import ABC, abstractmethod
from dataclasses import dataclass

from modelos import CategoriaCasoDeTeste, Prioridade


@dataclass
class CasoTesteGerado:
    """Caso de teste gerado por um provedor de IA, antes de virar um CasoDeTeste persistido.

    É um tipo de dados simples (não é o modelo SQLAlchemy) para que a camada
    de IA não precise conhecer detalhes de persistência — quem grava no banco
    é o serviço que consome o provedor.
    """

    codigo: str
    titulo: str
    categoria: CategoriaCasoDeTeste
    pre_condicao: str | None
    passos: str | None
    resultado_esperado: str | None
    prioridade: Prioridade


class LLMProvider(ABC):
    """Contrato comum para qualquer provedor de LLM usado na geração de casos de teste.

    O sistema core depende apenas desta interface — nunca de um provedor
    específico (Strategy Pattern) — o que permite adicionar outro provedor no
    futuro implementando esta mesma classe, sem alterar quem a consome.
    """

    @property
    @abstractmethod
    def nome(self) -> str:
        """Identificador curto do provedor (ex.: "claude"), usado no log de auditoria (GeracaoIA)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def modelo(self) -> str:
        """Modelo de IA configurado, usado no log de auditoria (GeracaoIA)."""
        raise NotImplementedError

    @property
    def ultimo_tokens_utilizados(self) -> int | None:
        """Tokens consumidos na última chamada a `gerar_casos_teste`, se o provedor expuser essa informação."""
        return None

    @abstractmethod
    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        """Gera casos de teste a partir do texto extraído de um documento de escopo."""
        raise NotImplementedError
