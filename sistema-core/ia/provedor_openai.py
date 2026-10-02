import json
import os

import openai

from .credenciais import ler_chave_de_arquivo
from .erros import ProvedorIAIndisponivel, RespostaIAInvalida
from .esquema_casos import ESQUEMA_CASOS, PROMPT_SISTEMA, converter_casos, instrucao_usuario
from .provider import CasoTesteGerado, LLMProvider

MODELO_PADRAO = "gpt-5.5"
VARIAVEL_ARQUIVO_CHAVE = "OPENAI_API_KEY_FILE"
# A geração espera a resposta completa; o gunicorn da imagem corta em 300 s.
TIMEOUT_SEGUNDOS = 290

# Códigos que a OpenAI usa no 429 quando o problema é saldo, não excesso de
# chamadas: esperar não resolve, alguém precisa colocar créditos na conta.
_CODIGOS_SEM_CREDITO = {"insufficient_quota", "credit_balance_exhausted"}

_FORMATO_RESPOSTA = {
    "type": "json_schema",
    "json_schema": {"name": "casos_de_teste", "schema": ESQUEMA_CASOS, "strict": True},
}


class ProvedorOpenAI(LLMProvider):
    """Adaptador que gera casos de teste usando a API oficial da OpenAI.

    Usa structured output (`response_format` com `json_schema` estrito), o
    equivalente da OpenAI à tool call forçada do ProvedorClaude: a resposta já
    vem no formato de CasoTesteGerado, sem parsing frágil de texto.
    """

    def __init__(self, cliente: openai.OpenAI | None = None, modelo: str | None = None):
        if cliente is None:
            chave = ler_chave_de_arquivo(VARIAVEL_ARQUIVO_CHAVE) or os.getenv("OPENAI_API_KEY")
            # Sem chave, o SDK da OpenAI falha já ao criar o cliente; adiar a
            # falha para a geração mantém o resto da API funcionando (503 só nela).
            cliente = openai.OpenAI(api_key=chave, timeout=TIMEOUT_SEGUNDOS) if chave else None
        self._cliente = cliente
        self._modelo = modelo or os.getenv("OPENAI_MODEL") or MODELO_PADRAO
        self._ultimo_tokens_utilizados: int | None = None

    @property
    def nome(self) -> str:
        return "openai"

    @property
    def modelo(self) -> str:
        return self._modelo

    @property
    def ultimo_tokens_utilizados(self) -> int | None:
        return self._ultimo_tokens_utilizados

    def gerar_casos_teste(self, texto_escopo: str) -> list[CasoTesteGerado]:
        if self._cliente is None:
            raise ProvedorIAIndisponivel(
                "O provedor de IA (OpenAI) não tem credencial configurada: informe o "
                f"arquivo da chave em {VARIAVEL_ARQUIVO_CHAVE} (ou a variável "
                "OPENAI_API_KEY) e reinicie a API."
            )

        try:
            resposta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": instrucao_usuario(texto_escopo)},
                ],
                response_format=_FORMATO_RESPOSTA,
            )
        except openai.AuthenticationError as erro:
            raise ProvedorIAIndisponivel(
                "O provedor de IA (OpenAI) recusou a credencial configurada. "
                "Confira se a chave está completa e ativa."
            ) from erro
        except openai.RateLimitError as erro:
            if {getattr(erro, "code", None), getattr(erro, "type", None)} & _CODIGOS_SEM_CREDITO:
                raise ProvedorIAIndisponivel(
                    "A conta do provedor de IA (OpenAI) está sem créditos. É preciso "
                    "adicionar créditos no painel de cobrança da organização na OpenAI."
                ) from erro
            raise ProvedorIAIndisponivel(
                "O provedor de IA (OpenAI) atingiu o limite de requisições. "
                "Tente de novo em alguns instantes."
            ) from erro
        except openai.OpenAIError as erro:
            raise ProvedorIAIndisponivel(
                "Não foi possível obter resposta do provedor de IA (OpenAI)."
            ) from erro

        uso = getattr(resposta, "usage", None)
        if uso is not None:
            self._ultimo_tokens_utilizados = uso.total_tokens

        escolha = resposta.choices[0]
        # Como no ProvedorClaude: resposta cortada ou recusada traria a lista
        # de casos incompleta ou não traria nada.
        if escolha.finish_reason == "length":
            raise RespostaIAInvalida(
                "A resposta da IA foi interrompida por exceder o tamanho máximo. "
                "Divida o escopo em documentos menores e gere os casos de cada um."
            )
        if getattr(escolha.message, "refusal", None):
            raise RespostaIAInvalida(
                "O provedor de IA recusou gerar casos de teste para este escopo."
            )

        try:
            return converter_casos(json.loads(escolha.message.content or ""))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
            raise RespostaIAInvalida(
                "O provedor de IA não retornou os casos de teste no formato esperado."
            ) from erro
