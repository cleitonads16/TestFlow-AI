# TestFlow AI

Gestor de casos de teste com geração assistida por IA — projeto de PDI (2026-2027) de Cleiton Ferreira.

Evolui a partir de uma ferramenta interna de gestão de casos de teste (processo PM06 no Fluig), generalizada para qualquer processo de negócio: recebe um documento de escopo (docx/pdf), extrai o texto, gera casos de teste via IA e permite organizá-los em rodadas de execução, registrando execuções e defeitos.

## Arquitetura

Construído em camadas, cada fase reaproveitando a anterior sem retrabalho:

- **Fase 1 — Sistema core** (`sistema-core/`): entidades e regras de negócio, sem conhecer API, Docker ou provedor de IA específico.
  - `modelos/` — `Projeto`, `Escopo`, `CasoDeTeste`, `RodadaDeExecucao`, `ExecucaoDeCaso`, `Defeito`, `GeracaoIA` (SQLAlchemy)
  - `repositorio/` — persistência (SQLite)
  - `documentos/` — extração de texto de escopo (docx/pdf)
  - `ia/` — interface `LLMProvider` + adaptador `ProvedorClaude` (Anthropic SDK, saída estruturada via tool call)
  - `servicos/` — orquestração (extrair escopo → gerar casos via IA → persistir)
- **Fase 2 — API** (`api/`): camada HTTP (FastAPI) sobre o core.
- **Fase 3 — Docker** (`docker/`): containerização (API + banco).

Detalhes de decisões técnicas e cronograma completo em [`docs/arquitetura-e-cronograma.md`](docs/arquitetura-e-cronograma.md).

## Stack

Python 3 · SQLAlchemy/SQLite · python-docx/pypdf · SDK oficial `anthropic` · FastAPI · Pydantic · pytest · Docker

## Status atual

Fase 1 em andamento — concluídas: modelagem do domínio, extração de texto de escopo, geração de casos de teste via IA e persistência (com auditoria em `GeracaoIA`). Próximo passo: regras de negócio de execução (rodadas, execuções, defeitos).

## Rodando os testes

```
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
pytest testes/ -q
```
