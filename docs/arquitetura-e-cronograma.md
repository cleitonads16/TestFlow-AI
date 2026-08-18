# Arquitetura e Cronograma — Sistema de Gestão de Tarefas e Projetos (To-Do Avançado)

> Documento técnico de apoio ao desenvolvimento. Complementa `docs/escopo-projeto.docx` (visão de negócio/PDI) com decisões de arquitetura e o cronograma semana a semana até a apresentação de outubro/2026.

**Versão:** 1.0
**Data:** 18/08/2026
**Projeto:** todo-avancado (PDI 2026-2027 — Cleiton Ferreira)

---

## 1. Visão Geral da Arquitetura

O sistema é construído em 3 camadas, evoluindo em fases (conforme o escopo), de forma que cada fase reaproveite a anterior sem retrabalho:

```
┌─────────────────────────────────────────┐
│  Fase 3 — Docker / docker-compose        │
│  ┌─────────────────────────────────────┐│
│  │  Fase 2 — API (FastAPI)              ││
│  │  ┌───────────────────────────────┐  ││
│  │  │  Fase 1 — Sistema Core (Python)│  ││
│  │  │  (entidades + regras de negócio)│ ││
│  │  └───────────────────────────────┘  ││
│  │  + schemas Pydantic + rotas          ││
│  └─────────────────────────────────────┘│
│  + Dockerfile + banco de dados           │
└─────────────────────────────────────────┘
```

A regra de ouro: **o sistema core (Fase 1) não conhece a API nem o Docker**. A API (Fase 2) só orquestra chamadas ao core e traduz para HTTP. Isso permite testar as regras de negócio sem subir servidor nenhum, e trocar a camada de persistência sem tocar na API.

## 2. Estrutura de Diretórios

Conforme a skill `estrutura-projeto`, tudo vive dentro de `todo-avancado/`:

```
todo-avancado/
├── docs/                  # escopo, este documento, doc de uso da API
├── sistema-core/          # Fase 1 — entidades e regras de negócio
│   ├── modelos/           # Task, Project, Status, Priority
│   ├── repositorio/       # camada de persistência (SQLite/SQLAlchemy)
│   └── servicos/          # regras de negócio (criar, listar, concluir, etc.)
├── api/                   # Fase 2 — camada HTTP sobre o core
│   ├── rotas/             # routers FastAPI (tarefas, projetos)
│   └── schemas/           # modelos Pydantic (entrada/saída)
├── docker/                # Fase 3 — Dockerfile, docker-compose.yml
└── testes/                # testes automatizados (pytest), espelhando core e api
```

## 3. Modelo de Domínio (Fase 1)

Entidades principais definidas no escopo:

| Entidade | Atributos principais |
|---|---|
| **Task** (tarefa) | id, título, descrição, status, prioridade, prazo, projeto_id |
| **Project** (projeto) | id, nome, descrição, tarefas (relação) |
| **Status** | enum: `pendente`, `em_andamento`, `concluida` |
| **Priority** (prioridade) | enum: `baixa`, `media`, `alta` |

Operações do core (Fase 1): criar, listar, atualizar, concluir e excluir tarefas; organizar tarefas em projetos.

## 4. Decisões Técnicas (Stack)

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3 | Alinhado à formação em andamento (Python 3 do Zero ao Avançado) |
| ORM / Persistência | SQLAlchemy + SQLite (arquivo local) desde a Fase 1 | Permite trocar SQLite → Postgres na Fase 3 (docker-compose) trocando só a connection string, sem reescrever repositório |
| Framework de API | FastAPI | Gera documentação interativa OpenAPI/Swagger automaticamente — atende ao requisito de "documentação completa" do escopo |
| Validação | Pydantic (nativo do FastAPI) | Validação de entrada e serialização de saída |
| Testes | pytest | Padrão de mercado, cobre core e API |
| Containerização | Docker + docker-compose (API + banco) | Conforme escopo Fase 3 |

Essas escolhas são meu ponto de partida sugerido — se você já tiver preferência diferente (ex.: persistência em arquivo JSON puro na Fase 1, sem ORM), ajusto o documento antes de começar a codar.

## 5. Fora de Escopo (reforçando o escopo-projeto.docx)

Autenticação multiusuário, frontend, deploy em nuvem, filas/mensageria — nada disso entra nesta primeira versão.

---

## 6. Cronograma Semanal (18/ago a 31/out/2026)

Base: apresentação final em outubro/2026 (API funcionando + documentação), com os prazos intermediários do `plano-de-acoes.docx` (métodos REST, tratamento de erros e Git até outubro/2026).

| Semana | Período | Fase | Entregas da semana |
|---|---|---|---|
| 1 | 18–24/ago | Fase 1 | Estrutura de pastas, `git init`, modelagem das entidades (Task, Project, Status, Priority), setup SQLAlchemy + SQLite |
| 2 | 25–31/ago | Fase 1 | CRUD de tarefas (criar, listar, atualizar, concluir, excluir); organização de tarefas em projetos |
| 3 | 1–7/set | Fase 1 | Regras de negócio (prazos, prioridades, validações); início dos testes automatizados (pytest) |
| 4 | 8–14/set | Fase 1 | Fechamento da Fase 1: cobertura de testes, revisão de código com dev mais experiente (conversa poderosa — 20%) |
| 5 | 15–21/set | Fase 2 | Setup FastAPI, schemas Pydantic, primeiro endpoint (tarefas) |
| 6 | 22–28/set | Fase 2 | Endpoints completos (tarefas + projetos), tratamento de erros e retornos padronizados |
| 7 | 29/set–5/out | Fase 2 | Revisão do Swagger/OpenAPI, testes de integração da API, repositório Git versionado |
| 8 | 6–12/out | Fase 3 | Dockerfile da API, ajuste de persistência para o `docker-compose` |
| 9 | 13–19/out | Fase 3 | `docker-compose` (API + banco), testes end-to-end containerizados |
| 10 | 20–26/out | Fase 3 | Documentação de uso da API, estrutura de logs, roteiro da apresentação |
| 11 | 27–31/out | — | Buffer + **apresentação final (outubro/2026)** |

**Riscos já sinalizados no plano de ações:** se o tempo apertar, a estrutura de logs e a documentação de endpoints têm prazo formal até novembro/2026 — ou seja, a Semana 10 pode estourar sem comprometer a meta principal de outubro (API funcionando).

## 7. Próximo Passo Imediato

Iniciar a Semana 1: criar a estrutura de diretórios acima dentro de `todo-avancado/` e modelar as entidades do sistema core.
