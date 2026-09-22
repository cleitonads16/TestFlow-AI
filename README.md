# TestFlow AI

Gestor de casos de teste com geração assistida por IA — projeto de PDI (2026-2027) de Cleiton Ferreira.

Evolui a partir de uma ferramenta interna de gestão de casos de teste (processo PM06 no Fluig), generalizada para qualquer processo de negócio: recebe um documento de escopo (docx/pdf), extrai o texto, gera casos de teste via IA e permite organizá-los em rodadas de execução, registrando execuções e defeitos.

## Arquitetura

Construído em camadas, cada fase reaproveitando a anterior:

- **Fase 1 — Sistema core** (`sistema-core/`): entidades e regras de negócio. A API não contém regra de negócio e nenhuma camada depende de um provedor de IA específico.
  - `modelos/` — app Django com `Projeto`, `Escopo`, `CasoDeTeste`, `RodadaDeExecucao`, `ExecucaoDeCaso`, `Defeito`, `GeracaoIA` (ORM do Django + migrations)
  - `documentos/` — extração de texto de escopo (docx/pdf)
  - `ia/` — interface `LLMProvider` + adaptador `ProvedorClaude` (Anthropic SDK, saída estruturada via tool call)
  - `servicos/` — orquestração (extrair escopo → gerar casos via IA → persistir)
- **Fase 2 — API** (`api/`): projeto Django (`config/`) + camada HTTP com Django Ninja (routers e Schemas) sobre o core.
- **Fase 3 — Docker** (`docker/`): containerização (API + MySQL).

Detalhes de arquitetura, cronograma completo e o **registro de decisões** (motivos, alternativas avaliadas e custos de cada escolha) em [`docs/arquitetura-e-cronograma.md`](docs/arquitetura-e-cronograma.md).

## Stack

Python 3 · Django + Django Ninja · ORM do Django · MySQL (Docker; SQLite só em dev/testes locais) · python-docx/pypdf · SDK oficial `anthropic` · Pydantic · pytest + pytest-django · Docker

### Por que esta stack (resumo)

- **Django Ninja no lugar de FastAPI:** solicitado pelo Tech Lead que avaliará o projeto, por ser o padrão de API usado na ComBio, sem abrir mão do que motivou o FastAPI: Swagger/OpenAPI automático e validação com Pydantic.
- **ORM do Django no lugar de SQLAlchemy:** um framework só para HTTP, configuração e persistência, com integração nativa com o Ninja, migrations versionadas e Django Admin. A troca foi feita cedo, enquanto o custo de migração ainda era baixo.
- **MySQL no lugar de PostgreSQL:** é o banco do padrão da ComBio e fecha a stack da empresa (Django + Django Ninja + MySQL), pelo mesmo critério da troca para o Django Ninja. O projeto não usa recursos exclusivos do PostgreSQL, e a troca é só de configuração (`MYSQL_HOST`) e de driver (`mysqlclient`).

## Status atual

Fase 1 em andamento. Concluídas: modelagem do domínio, extração de texto de escopo, geração de casos de teste via IA e persistência (com auditoria em `GeracaoIA`), já migradas para o ORM do Django. Próximo passo (Semana 4): regras de negócio de execução (rodadas, execuções, defeitos) e CRUD manual de casos de teste.

## Rodando os testes

```
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
pytest testes/ -q
```

## Banco local e Django Admin

```
cd api
python manage.py migrate          # cria casos_teste.db (SQLite) na raiz do projeto
python manage.py createsuperuser
python manage.py runserver        # admin em http://127.0.0.1:8000/admin/
```
