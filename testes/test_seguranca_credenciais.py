"""Nenhuma chave de provedor de IA pode estar dentro do projeto.

Cada chave fica num arquivo fora do repositório e chega à API como Docker secret
(docs/arquitetura-e-cronograma.md, D5). Este teste pega o vazamento antes do
commit: um arquivo com chave dentro do projeto falha a suíte. A falha cita só
o arquivo, nunca o trecho encontrado, para o próprio relatório não vazar a chave.
"""

import re
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[1]

_PADROES_DE_CHAVE = {
    "Anthropic": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "OpenAI": re.compile(r"sk-(proj|svcacct|admin)-[A-Za-z0-9_\-]{20,}"),
    "Google (Gemini)": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
}

_IGNORADOS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "uploads"}
_EXTENSOES_BINARIAS = {".db", ".pyc", ".docx", ".png", ".jpg", ".pdf", ".zip"}


def _arquivos_do_projeto():
    for caminho in RAIZ_PROJETO.rglob("*"):
        partes = set(caminho.relative_to(RAIZ_PROJETO).parts)
        if partes & _IGNORADOS or not caminho.is_file():
            continue
        if caminho.suffix.lower() in _EXTENSOES_BINARIAS:
            continue
        yield caminho


def test_nenhuma_chave_de_ia_dentro_do_projeto():
    vazamentos = []
    for caminho in _arquivos_do_projeto():
        try:
            texto = caminho.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for provedor, padrao in _PADROES_DE_CHAVE.items():
            if padrao.search(texto):
                vazamentos.append(f"{caminho.relative_to(RAIZ_PROJETO)} ({provedor})")

    assert not vazamentos, (
        "Chave de provedor de IA encontrada no projeto. Remova o arquivo e revogue a "
        "chave no console do provedor: " + ", ".join(vazamentos)
    )
