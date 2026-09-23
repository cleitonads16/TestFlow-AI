from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from documentos import FORMATOS_SUPORTADOS
from modelos.models import Escopo, Projeto

from .erros import RegraDeNegocioViolada

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024


def registrar_escopo(projeto: Projeto, nome_arquivo: str, conteudo: bytes) -> Escopo:
    """Guarda o documento de escopo enviado e cria o Escopo "pendente" do projeto.

    O formato é validado já no envio (e não só na geração), para o usuário
    saber na hora que o arquivo não serve. O documento é gravado com o id do
    escopo como nome, e não com o nome enviado, para que um nome de arquivo
    malicioso (ex.: "../../settings.py") não escolha onde o arquivo é salvo.
    """
    nome_arquivo = Path(nome_arquivo or "").name
    extensao = Path(nome_arquivo).suffix.lower()
    if extensao not in FORMATOS_SUPORTADOS:
        raise RegraDeNegocioViolada(
            f"Formato '{extensao or 'sem extensão'}' não suportado. "
            f"Use {' ou '.join(FORMATOS_SUPORTADOS)}."
        )
    if not conteudo:
        raise RegraDeNegocioViolada("O documento de escopo está vazio.")
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise RegraDeNegocioViolada(
            f"O documento de escopo excede o limite de {TAMANHO_MAXIMO_BYTES // (1024 * 1024)} MB."
        )

    with transaction.atomic():
        escopo = Escopo.objects.create(
            projeto=projeto,
            nome_arquivo=nome_arquivo[:255],
            data_upload=timezone.now(),
        )
        destino = _caminho_documento(escopo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    return escopo


def caminho_documento(escopo: Escopo) -> Path:
    """Caminho do documento gravado no envio; é a entrada de `processar_escopo`."""
    caminho = _caminho_documento(escopo)
    if not caminho.exists():
        raise RegraDeNegocioViolada(
            f"O documento do escopo {escopo.nome_arquivo} não foi encontrado; envie-o novamente."
        )
    return caminho


def listar_escopos(projeto: Projeto) -> list[Escopo]:
    return list(projeto.escopos.order_by("-data_upload", "-id"))


def _caminho_documento(escopo: Escopo) -> Path:
    extensao = Path(escopo.nome_arquivo).suffix.lower()
    return Path(settings.DIRETORIO_ESCOPOS) / f"{escopo.id}{extensao}"
