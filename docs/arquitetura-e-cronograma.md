# Arquitetura e Cronograma — Gestor de Casos de Teste com Geração Assistida por IA

> Documento técnico de apoio ao desenvolvimento. Complementa `docs/escopo-projeto.docx` (visão de negócio/PDI) com decisões de arquitetura e o cronograma semana a semana até a apresentação de outubro/2026.

**Versão:** 2.0
**Data:** 02/09/2026
**Projeto:** todo-avancado (PDI 2026-2027 — Cleiton Ferreira)

> **Nota de revisão (v2.0):** o projeto foi replanejado. Em vez de um sistema de gestão de tarefas genérico, a base passa a ser uma ferramenta de gestão de casos de teste já construída pelo autor (uso interno, processo PM06 no Fluig), generalizada para qualquer processo de negócio e evoluída de um app local sem persistência para um sistema com API, banco de dados, Docker e geração automática de casos de teste via IA a partir de um documento de escopo. O nome do diretório do projeto (`todo-avancado`) é mantido por continuidade do repositório; o produto passa a se chamar **Gestor de Casos de Teste com IA**.

---

## 1. Visão Geral da Arquitetura

O sistema é construído em camadas, evoluindo em fases, de forma que cada fase reaproveite a anterior sem retrabalho:

```
┌───────────────────────────────────────────────────┐
│  Fase 3 — Docker / docker-compose                  │
│  ┌───────────────────────────────────────────────┐│
│  │  Fase 2 — API (FastAPI)                        ││
│  │  ┌───────────────────────────────────────────┐ ││
│  │  │  Fase 1 — Sistema Core (Python)            │ ││
│  │  │  (entidades + regras de negócio)           │ ││
│  │  │  ┌─────────────────────────────────────┐   │ ││
│  │  │  │ Camada de IA (interface LLMProvider) │   │ ││
│  │  │  │ + adaptador Claude (Anthropic SDK)   │   │ ││
│  │  │  └─────────────────────────────────────┘   │ ││
│  │  └───────────────────────────────────────────┘ ││
│  │  + schemas Pydantic + rotas                     ││
│  └───────────────────────────────────────────────┘│
│  + Dockerfile + banco de dados                     │
└───────────────────────────────────────────────────┘
```

A regra de ouro: **o sistema core (Fase 1) não conhece a API, o Docker nem um provedor de IA específico**. A geração de casos de teste via IA fica atrás de uma interface própria (`LLMProvider`), do mesmo jeito que a persistência fica atrás do repositório — troca-se a implementação sem tocar no resto do sistema. A API (Fase 2) só orquestra chamadas ao core e traduz para HTTP.

## 2. Estrutura de Diretórios

Conforme a skill `estrutura-projeto`, tudo vive dentro de `todo-avancado/`:

```
todo-avancado/
├── docs/                  # escopo, este documento, doc de uso da API
├── sistema-core/          # Fase 1 — entidades e regras de negócio
│   ├── modelos/           # Projeto, Escopo, CasoDeTeste, RodadaDeExecucao, ExecucaoDeCaso, Defeito
│   ├── repositorio/       # camada de persistência (SQLite/SQLAlchemy)
│   ├── servicos/          # regras de negócio (criar, listar, executar, etc.)
│   ├── documentos/        # extração de texto de escopo (docx/pdf)
│   └── ia/                # interface LLMProvider + adaptador Claude (Anthropic SDK)
├── api/                   # Fase 2 — camada HTTP sobre o core
│   ├── rotas/             # routers FastAPI (escopos, casos-de-teste, rodadas, execucoes, defeitos)
│   └── schemas/           # modelos Pydantic (entrada/saída)
├── docker/                # Fase 3 — Dockerfile, docker-compose.yml
└── testes/                # testes automatizados (pytest), espelhando core e api
```

## 3. Modelo de Domínio (Fase 1)

| Entidade | Atributos principais |
|---|---|
| **Projeto** | id, nome, descrição |
| **Escopo** | id, projeto_id, nome_arquivo, texto_extraido, status (`pendente`, `processado`, `erro`), data_upload |
| **CasoDeTeste** | id, escopo_id, código, título, categoria (`funcional`, `integração`, `regra_de_negócio`, `outro`), pré_condição, passos, resultado_esperado, prioridade, origem (`manual`, `ia`) |
| **RodadaDeExecucao** | id, projeto_id, nome, data_início, data_fim |
| **ExecucaoDeCaso** | id, rodada_id, caso_id, status (`pendente`, `passou`, `falhou`, `bloqueado`), observações, data_execução |
| **Defeito** | id, execucao_id, descrição, severidade, status |
| **GeracaoIA** *(log de auditoria)* | id, escopo_id, provedor, modelo, quantidade_casos_gerados, tokens_utilizados, data |

Operações do core (Fase 1): extrair texto de um documento de escopo; gerar casos de teste via IA a partir desse texto (um escopo por vez); criar, listar, atualizar e excluir casos de teste manualmente; organizar casos em rodadas de execução; registrar execução e defeitos.

## 4. Camada de IA — Geração de Casos de Teste

**Fluxo:**

```
Upload do escopo (docx/pdf)
   → extrair texto (sistema-core/documentos)
   → LLMProvider.gerar_casos_teste(texto)   [interface, Strategy Pattern]
   → adaptador concreto: ProvedorClaude (Anthropic SDK, output estruturado / JSON Schema)
   → casos de teste retornam já no formato de CasoDeTeste (origem="ia")
   → persistidos vinculados ao Escopo, sujeitos a revisão do usuário
```

**Decisão de arquitetura:** a interface `LLMProvider` define o contrato (`gerar_casos_teste(texto_escopo: str) -> list[CasoDeTeste]`) e não conhece detalhes de nenhum provedor. A primeira implementação (`ProvedorClaude`) usa o SDK oficial `anthropic`, com **structured outputs** (`output_config.format`) para garantir que a resposta já venha validada no schema de `CasoDeTeste`, sem depender de parsing de texto livre. Essa abstração é o que permite, no futuro, adicionar outro provedor (ex.: OpenAI) implementando a mesma interface — sem exigir isso para a entrega de outubro/2026 (ver seção 5, Fora de Escopo).

**MCP (Model Context Protocol):** avaliado e descartado para esta necessidade — MCP serve para conectar um LLM a ferramentas/dados externos, direção oposta à necessidade aqui (a própria API chama o LLM diretamente via SDK). Fica registrado como possível extensão futura (expor a geração de casos como uma tool MCP), fora do escopo de outubro/2026.

## 5. Decisões Técnicas (Stack)

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3 | Alinhado à formação em andamento (Python 3 do Zero ao Avançado) |
| ORM / Persistência | SQLAlchemy + SQLite (arquivo local) desde a Fase 1 | Permite trocar SQLite → Postgres na Fase 3 (docker-compose) trocando só a connection string |
| Extração de documentos | `python-docx` (Word) + `pypdf` (PDF) | Cobre os formatos mais prováveis de documento de escopo |
| Integração com IA | SDK oficial `anthropic`, atrás da interface `LLMProvider` | Ferramenta homologada; structured outputs elimina parsing frágil |
| Framework de API | FastAPI | Gera documentação interativa OpenAPI/Swagger automaticamente |
| Validação | Pydantic (nativo do FastAPI) | Validação de entrada e serialização de saída |
| Testes | pytest | Padrão de mercado, cobre core, IA e API |
| Containerização | Docker + docker-compose (API + banco) | Conforme escopo Fase 3 |

**Novas variáveis de ambiente:** `ANTHROPIC_API_KEY` (credencial do provedor de IA — nunca versionada, via `.env`/segredo do Docker), `LLM_PROVIDER` (seleciona o adaptador ativo).

## 6. Fora de Escopo (reforçando o escopo-projeto.docx)

Autenticação multiusuário, frontend, deploy em nuvem, filas/mensageria, suporte simultâneo a múltiplos provedores de IA no dia 1 (só a interface fica pronta para isso), armazenamento do conteúdo de evidências (imagens/PDF, só metadados) — nada disso entra nesta primeira versão.

---

## 7. Cronograma Semanal (02/set a 31/out/2026)

Base: apresentação final em outubro/2026 (API funcionando + geração de casos via IA + documentação), com os prazos intermediários do `plano-de-acoes.docx` (métodos REST, tratamento de erros e Git até outubro/2026). Cronograma replanejado a partir da data de hoje (02/09/2026), já considerando o pivô de escopo.

| Semana | Período | Fase | Entregas da semana |
|---|---|---|---|
| 1 | 02–08/set | Fase 1 | Remodelagem do domínio (Projeto, Escopo, CasoDeTeste, RodadaDeExecucao, ExecucaoDeCaso, Defeito), ajuste do SQLAlchemy/SQLite já existente |
| 2 | 09–15/set | Fase 1 | Extração de texto de documentos (docx/pdf); interface `LLMProvider`; adaptador `ProvedorClaude` (chamada simples via SDK) |
| 3 | 16–22/set | Fase 1 | Geração estruturada de casos de teste via IA (output estruturado/JSON Schema); persistência; testes automatizados do core |
| 4 | 23–29/set | Fase 1 | Regras de negócio de execução (rodadas, execução de casos, defeitos); fechamento da Fase 1 (revisão de código com dev mais experiente — 20%) |
| 5 | 30/set–06/out | Fase 2 | Setup FastAPI, schemas Pydantic; endpoints de escopos (upload + gerar-casos) e casos de teste |
| 6 | 07–13/out | Fase 2 | Endpoints de rodadas/execuções/defeitos, tratamento de erros padronizado, testes de integração |
| 7 | 14–20/out | Fase 2 | Revisão do Swagger/OpenAPI, repositório Git versionado, Dockerfile da API |
| 8 | 21–27/out | Fase 3 | `docker-compose` (API + banco), testes end-to-end containerizados, documentação de uso da API |
| 9 | 28–31/out | — | Buffer + **apresentação final (outubro/2026)** |

**Riscos já sinalizados no plano de ações:** se o tempo apertar, a estrutura de logs e a documentação de endpoints têm prazo formal até novembro/2026 — não comprometem a meta principal de outubro (API funcionando + geração de casos via IA). O cronograma ficou mais apertado (9 semanas em vez das 11 originais) por ter iniciado o replanejamento em setembro; se a Semana 3 (geração via IA) atrasar, ela tem prioridade sobre a Semana 4 (fechamento formal da Fase 1), que pode se estender para dentro da Fase 2 sem risco à meta de outubro.

## 8. Próximo Passo Imediato

Semanas 1 a 3 concluídas: remodelagem das entidades, extração de texto de documentos (docx/pdf), interface `LLMProvider` + adaptador `ProvedorClaude` (geração estruturada via tool call), e o serviço `servicos.processar_escopo` que orquestra extração + geração via IA + persistência (`CasoDeTeste` e `GeracaoIA`), com testes automatizados cobrindo o caminho feliz e os erros de extração/IA.

Semana 4 (23–29/set): regras de negócio de execução — criar rodadas de execução, registrar execução de casos (`ExecucaoDeCaso`) e defeitos (`Defeito`) vinculados a uma execução, com os respectivos testes. Fecha a Fase 1 (sistema core).
