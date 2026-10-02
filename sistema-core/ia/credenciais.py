"""Leitura da chave de um provedor de IA a partir de um arquivo.

A chave fica num arquivo fora do repositório (no Docker, um secret em
/run/secrets/) cujo caminho vem numa variável `*_FILE`. Preferido à chave em
variável de ambiente, que aparece em `docker inspect` e em relatórios de erro.
Ver docs/arquitetura-e-cronograma.md, D5.
"""

import os
from pathlib import Path


def ler_chave_de_arquivo(variavel_caminho: str) -> str | None:
    """Conteúdo do arquivo indicado na variável, ou None se não houver chave.

    Arquivo ausente ou vazio conta como "sem credencial" (503 na geração),
    sem derrubar a API.
    """
    caminho = os.getenv(variavel_caminho)
    if not caminho:
        return None
    try:
        return Path(caminho).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None
