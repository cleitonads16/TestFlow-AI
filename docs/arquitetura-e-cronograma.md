# Arquitetura e Cronograma — Gestor de Casos de Teste com Geração Assistida por IA

> Documento técnico de apoio ao desenvolvimento. Complementa `docs/escopo-projeto.docx` (visão de negócio/PDI) com decisões de arquitetura e o cronograma semana a semana até a apresentação de outubro/2026.

**Versão:** 2.11
**Data:** 02/10/2026
**Projeto:** todo-avancado (PDI 2026-2027 — Cleiton Ferreira)

> **Nota de revisão (v2.0):** o projeto foi replanejado. Em vez de um sistema de gestão de tarefas genérico, a base passa a ser uma ferramenta de gestão de casos de teste já construída pelo autor (uso interno, processo PM06 no Fluig), generalizada para qualquer processo de negócio e evoluída de um app local sem persistência para um sistema com API, banco de dados, Docker e geração automática de casos de teste via IA a partir de um documento de escopo. O nome do diretório do projeto (`todo-avancado`) é mantido por continuidade do repositório; o produto passa a se chamar **Gestor de Casos de Teste com IA**.

> **Nota de revisão (v2.1):** o framework de API passa de FastAPI para **Django + Django Ninja**, e a persistência do sistema core passa de SQLAlchemy para o **ORM do Django**. O banco de dados da Fase 3 passa de PostgreSQL para **MySQL**. Com isso, o projeto segue a stack padrão da ComBio (Django + Django Ninja + MySQL). Os motivos, as alternativas avaliadas e os custos de cada escolha estão registrados na seção 6 (Registro de Decisões).

### Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| 1.0 | — | Plano original (sistema de gestão de tarefas genérico) |
| 2.0 | 02/09/2026 | Replanejamento para Gestor de Casos de Teste com IA |
| 2.1 | 22/09/2026 | FastAPI → Django Ninja; SQLAlchemy → ORM do Django; PostgreSQL → MySQL; cronograma das Semanas 4 a 8 ajustado |
| 2.2 | 23/09/2026 | Semana 5 adiantada: API de projetos, escopos e casos de teste; regras de upload e de reprocessamento; tradução de erros para HTTP |
| 2.3 | 23/09/2026 | Semana 6 adiantada: API de rodadas, execuções e defeitos; formato único de erro com `codigo`; 409 para conflitos |
| 2.4 | 30/09/2026 | Semana 7 iniciada: revisão do Swagger/OpenAPI (resumos, tags na ordem do fluxo, exemplos de corpo, tabela de erros); documento de escopo ilegível passa a ser recusado com 400 no envio e na geração, em vez de 500 |
| 2.5 | 30/09/2026 | Escopo só em `.docx` (D4); extração passa a ler tabelas; documento sem texto recusado; resposta da IA cortada ou recusada tratada; chamada à IA via streaming |
| 2.6 | 02/10/2026 | Nome de projeto único (sem diferenciar maiúsculas); falta de credencial da IA vira 503; Dockerfile da API (`docker/Dockerfile`), validado também contra MySQL 8.4 |
| 2.7 | 02/10/2026 | Semana 8 iniciada: `docker-compose` (API + MySQL 8.4) com migrations na subida e suíte de testes contra o MySQL; corpo de requisição ilegível passa a seguir o formato padrão de erro (`corpo_invalido`) |
| 2.8 | 02/10/2026 | Mensagens de validação (422) em português; guia de uso da API (`docs/uso-da-api.md`); Semanas 7 e 8 concluídas |
| 2.9 | 02/10/2026 | Proteção da chave do provedor de IA (D5): leitura por arquivo via Docker secret, porta da API só em `127.0.0.1`, padrões de credencial no `.gitignore` e teste que barra chave dentro do projeto; Gemini fora por não ser ferramenta homologada |
| 2.10 | 02/10/2026 | Segundo provedor de IA: OpenAI (D6), selecionado por `LLM_PROVIDER`; prompt e schema dos casos compartilhados entre os provedores (`ia/esquema_casos.py`); mensagens próprias para conta sem crédito e limite de requisições |
| 2.11 | 02/10/2026 | Provedor gratuito: Ollama com modelo local (D7), que recusa modelos de nuvem e servidor fora da máquina; timeout do gunicorn de 300 s para 900 s |

---

## 1. Visão Geral da Arquitetura

O sistema é construído em camadas, evoluindo em fases, de forma que cada fase reaproveite a anterior:

```
┌───────────────────────────────────────────────────┐
│  Fase 3 — Docker / docker-compose                  │
│  ┌───────────────────────────────────────────────┐│
│  │  Fase 2 — API (Django Ninja)                   ││
│  │  ┌───────────────────────────────────────────┐ ││
│  │  │  Fase 1 — Sistema Core (Python + Django)   │ ││
│  │  │  (models do ORM + regras de negócio)       │ ││
│  │  │  ┌─────────────────────────────────────┐   │ ││
│  │  │  │ Camada de IA (interface LLMProvider) │   │ ││
│  │  │  │ + adaptador Claude (Anthropic SDK)   │   │ ││
│  │  │  └─────────────────────────────────────┘   │ ││
│  │  └───────────────────────────────────────────┘ ││
│  │  + schemas Ninja (Pydantic) + routers           ││
│  └───────────────────────────────────────────────┘│
│  + Dockerfile + MySQL                              │
└───────────────────────────────────────────────────┘
```

**Regra de ouro (revista na v2.1): a API não contém regra de negócio, e nem o core nem a API conhecem um provedor de IA específico.** Os routers do Django Ninja só validam a entrada, chamam os serviços do core e traduzem o resultado (ou o erro) para HTTP. Toda regra de negócio fica em `sistema-core/servicos/`. A geração de casos de teste via IA fica atrás de uma interface própria (`LLMProvider`), então dá para trocar de provedor sem mexer no resto do sistema.

Na v2.0 a regra era mais forte: "o core não conhece a API nem a persistência concreta". Ao adotar o ORM do Django (seção 6, D2), o core passa a depender do Django para persistir. Esse acoplamento foi aceito de forma consciente. As camadas `documentos/` e `ia/` continuam sem nenhuma dependência de Django.

## 2. Estrutura de Diretórios

Conforme a skill `estrutura-projeto`, tudo vive dentro de `todo-avancado/`:

```
todo-avancado/
├── docs/                  # escopo, este documento, doc de uso da API
├── sistema-core/          # Fase 1 — entidades e regras de negócio
│   ├── modelos/           # app Django do domínio: models (Projeto, Escopo, CasoDeTeste,
│   │                      #   RodadaDeExecucao, ExecucaoDeCaso, Defeito, GeracaoIA) + migrations
│   ├── servicos/          # regras de negócio (criar, listar, executar, etc.)
│   ├── documentos/        # extração de texto de escopo (.docx) — sem dependência de Django
│   └── ia/                # interface LLMProvider + adaptador Claude — sem dependência de Django
├── api/                   # Fase 2 — camada HTTP sobre o core
│   ├── config/            # projeto Django: settings, urls, wsgi/asgi
│   ├── rotas/             # routers Django Ninja (escopos, casos-de-teste, rodadas, execucoes, defeitos)
│   └── schemas/           # Schemas Django Ninja (Pydantic) de entrada/saída
├── docker/                # Fase 3 — Dockerfile, docker-compose.yml
└── testes/                # testes automatizados (pytest + pytest-django), espelhando core e api
```

A pasta `sistema-core/repositorio/` (sessão/engine do SQLAlchemy) deixa de existir na v2.1: a configuração de banco passa para `DATABASES` em `api/config/settings.py`.

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

### Regras de negócio implementadas (Semana 4)

Os serviços ficam em `sistema-core/servicos/` (`casos_teste.py`, `execucoes.py`, `geracao_casos_teste.py`). Toda violação levanta `RegraDeNegocioViolada`, que a API da Fase 2 traduz para uma resposta HTTP 4xx padronizada. Valores de enum podem chegar como membro do enum ou como texto (ex.: `"alta"`), e valores fora do domínio são recusados com a lista de valores permitidos.

| Regra | Por quê |
|---|---|
| *(v2.6)* Nome do projeto é único, sem diferenciar maiúsculas de minúsculas e ignorando espaços nas pontas (validado no serviço e garantido no banco pela constraint `projeto_nome_unico`, sobre `LOWER(nome)`) | Dois projetos "Portal RH" deixam ambíguo onde enviar escopos e de quem são os resultados. A mensagem de conflito traz o nome do projeto que já existe |
| Código do caso de teste é obrigatório e único dentro do escopo | Os casos são referenciados pelo código nas rodadas e na comunicação da equipe; dois `CT-001` no mesmo escopo gerariam ambiguidade. Escopos diferentes podem repetir códigos |
| Campos de texto obrigatórios (código, título, nome da rodada, descrição do defeito) não aceitam vazio ou só espaços | Evita registros sem significado que atrapalham a leitura dos resultados |
| A edição de um caso não altera a `origem` | Um caso gerado por IA e revisado pelo usuário continua registrado como `ia`, preservando a rastreabilidade da geração (auditoria em `GeracaoIA`). Só os campos de conteúdo são editáveis |
| Caso que já entrou em alguma rodada não pode ser excluído | Excluir apagaria em cascata o histórico de execuções e defeitos, que é a evidência dos testes realizados |
| Rodada: data de fim não pode ser anterior à de início | Consistência do período de execução |
| Rodada só aceita casos do mesmo projeto | Uma rodada testa um projeto; misturar casos de outro projeto distorce os resultados |
| Cada caso entra uma única vez por rodada (validado no serviço e garantido no banco pela constraint `caso_unico_por_rodada`) | Reexecutar um caso na mesma rodada é registrar de novo o mesmo resultado, não criar uma segunda execução. A constraint protege mesmo contra gravações que não passem pelo serviço |
| Criação de rodada com casos é atômica | Se algum caso for recusado, nada é gravado; não fica rodada pela metade |
| Resultado de execução deve ser `passou`, `falhou` ou `bloqueado`; a data de execução é gravada automaticamente | `pendente` é só o estado inicial. A data automática garante que todo resultado tenha quando foi obtido |
| Execução `bloqueado` exige observação | Quem lê o resultado precisa saber qual é o impedimento para destravá-lo |
| Defeito só pode ser registrado em execução com status `falhou`, e nasce `aberto` | Defeito é consequência de uma falha observada; em execução que passou ou está pendente ele não tem origem rastreável |
| `resumo_rodada` conta execuções por status | Base para acompanhar o andamento de uma rodada (será exposto pela API) |
| *(Semana 5; revista na v2.5)* Documento de escopo só é aceito em `.docx` (D4), não vazio, com até 10 MB, legível e com texto, validado já no envio | O usuário descobre na hora que o arquivo não serve, e não só ao pedir a geração; o limite protege o servidor e o custo da chamada à IA. Sem a checagem de texto, um documento só com imagens chegaria vazio à IA, que poderia inventar casos |
| *(v2.5)* A extração lê parágrafos **e tabelas**, na ordem do documento; cada linha de tabela vira uma linha de texto com as células separadas por ` \| ` | Escopos costumam trazer os requisitos em tabela. Antes, só os parágrafos eram lidos, e o conteúdo das tabelas ficava de fora sem nenhum aviso. Cabeçalho e rodapé não são lidos: costumam repetir título e logotipo, não requisitos |
| *(Semana 5)* O documento é gravado com o id do escopo como nome (`uploads/escopos/<id>.<ext>`), e não com o nome enviado | Um nome de arquivo malicioso (ex.: `../../settings.py`) não consegue escolher onde o arquivo é salvo. O nome original fica só em `Escopo.nome_arquivo` |
| *(Semana 5)* Um escopo já `processado` não é gerado de novo; `pendente` e `erro` podem ser processados | Gerar de novo duplicaria os casos (e seus códigos) e descartaria as revisões do usuário. O status `erro` permite tentar outra vez depois de uma falha da IA |

### Tradução de erros para HTTP (Semanas 5 e 6)

Os routers não tratam erros. Os exception handlers registrados em `api/config/api.py` fazem a tradução, e **todo erro sai no mesmo formato** (`schemas.ErroSaida`):

```json
{"detail": "Mensagem legível", "codigo": "conflito"}
{"detail": "Dados de entrada inválidos.", "codigo": "dados_invalidos",
 "erros": [{"campo": "categoria", "origem": "body", "mensagem": "Valor inválido. Permitidos: funcional, integracao, regra_de_negocio, outro."}]}
```

`detail` é para a pessoa ler; `codigo` é estável e serve para quem consome a API decidir o que fazer sem depender do texto da mensagem; `erros` só aparece no 422, com um item por campo inválido.

| Exceção | HTTP | `codigo` | Quando |
|---|---|---|---|
| Validação dos Schemas do Ninja (tipo errado, enum fora do domínio, campo faltando) | 422 | `dados_invalidos` | Antes de chegar ao core. As mensagens do Pydantic, só em inglês, são traduzidas pelo `type` do erro (estável entre versões) em `api/config/traducao_validacao.py`; um tipo sem tradução mantém a mensagem original |
| `HttpError` do Ninja (corpo que não é JSON legível: sintaxe errada ou texto fora de UTF-8) | 400 | `corpo_invalido` | Antes da validação dos Schemas. Sem esse handler, o Ninja respondia `{"detail": "Cannot parse request body"}`, em inglês, sem `codigo` e, com `DEBUG`, com o erro interno do parser |
| `RegraDeNegocioViolada`, `FormatoDocumentoNaoSuportado`, `DocumentoIlegivel`, `DocumentoSemTexto` | 400 | `regra_de_negocio` | Uma regra da seção 3 recusou a operação (texto vazio, datas invertidas, status inválido, defeito em execução que não falhou, id de caso inexistente no corpo, documento de escopo corrompido, só renomeado para .docx ou sem texto) |
| `OperacaoEmConflito` (subclasse de `RegraDeNegocioViolada`) e `IntegrityError` do banco | 409 | `conflito` | O pedido é válido, mas colide com um registro existente: nome de projeto repetido, código repetido no escopo, caso já na rodada, escopo já processado, exclusão de caso com histórico. O `IntegrityError` cobre gravações simultâneas que passem pela validação do serviço e esbarrem na constraint do banco |
| `Http404` (`rotas.comum.obter_ou_404`) | 404 | `nao_encontrado` | Recurso do caminho da URL inexistente, com mensagem em português e o id buscado (ex.: "Rodada de execução 42 não encontrada.") |
| `RespostaIAInvalida` | 502 | `ia_resposta_invalida` | O provedor de IA respondeu fora do formato esperado, cortou a resposta por tamanho (`stop_reason` `max_tokens`) ou recusou o pedido (`refusal`); cada caso tem mensagem própria, e nenhum caso parcial é gravado |
| `ProvedorIAIndisponivel` | 503 | `ia_indisponivel` | Falha ao chamar o provedor (rede, credencial, limite de uso). Cada adaptador traduz os erros do seu SDK para essa exceção, então a API não conhece o SDK da Anthropic |
| Qualquer outra exceção | 500 | `erro_interno` | Mensagem genérica; o detalhe (traceback) vai só para o log, para não expor informação interna |

**Por que 400 e não 404 para id inexistente no corpo:** o 404 fica reservado ao recurso da URL. Um `casos_ids` com um id que não existe torna o corpo do pedido inválido, então é 400, e a mensagem lista os ids não encontrados.

### Endpoints entregues (Semanas 5 e 6)

Swagger em `/api/docs` e OpenAPI em `/api/openapi.json`. As seções do Swagger seguem a ordem do fluxo de uso (projeto → escopo → casos → rodada → execução → defeito). Cada operação tem um resumo próprio em português, e os corpos de entrada vêm com um exemplo preenchido. O topo da página explica o fluxo e a tabela de códigos de erro. O teste `testes/test_api_documentacao.py` garante que essas regras continuem valendo quando um endpoint novo for criado, e também que cada exemplo seja aceito pelo próprio schema.

| Método | Caminho | O que faz |
|---|---|---|
| POST / GET | `/api/projetos` | Cria / lista projetos |
| GET | `/api/projetos/{projeto_id}` | Detalha um projeto |
| POST | `/api/projetos/{projeto_id}/escopos` | Envia o documento de escopo (multipart, campo `arquivo`); o escopo nasce `pendente` |
| GET | `/api/projetos/{projeto_id}/escopos` | Lista os escopos do projeto (mais recentes primeiro) |
| GET | `/api/escopos/{escopo_id}` | Detalha o escopo, com o texto extraído |
| POST | `/api/escopos/{escopo_id}/gerar-casos` | Extrai o texto, gera os casos via IA e devolve os casos criados (chamada síncrona) |
| POST | `/api/escopos/{escopo_id}/casos-de-teste` | Cria um caso manual |
| GET | `/api/casos-de-teste` | Lista casos; filtros opcionais `projeto_id`, `escopo_id`, `categoria`, `origem` |
| GET / PATCH / DELETE | `/api/casos-de-teste/{caso_id}` | Detalha / revisa (só os campos enviados) / exclui um caso |
| POST / GET | `/api/projetos/{projeto_id}/rodadas` | *(Semana 6)* Cria uma rodada (com `casos_ids` opcionais, agendados como `pendente`, tudo ou nada) / lista as rodadas do projeto |
| GET | `/api/rodadas/{rodada_id}` | *(Semana 6)* Detalha a rodada, já com o resumo por status |
| GET | `/api/rodadas/{rodada_id}/resumo` | *(Semana 6)* Quantidade de execuções por status, mais o total |
| POST | `/api/rodadas/{rodada_id}/casos` | *(Semana 6)* Inclui mais casos na rodada |
| GET | `/api/rodadas/{rodada_id}/execucoes` | *(Semana 6)* Lista as execuções da rodada, com código e título do caso; filtro opcional `status` |
| GET | `/api/execucoes/{execucao_id}` | *(Semana 6)* Detalha uma execução |
| PUT | `/api/execucoes/{execucao_id}/resultado` | *(Semana 6)* Registra ou corrige o resultado (`passou`, `falhou`, `bloqueado`); a data é gravada automaticamente |
| POST / GET | `/api/execucoes/{execucao_id}/defeitos` | *(Semana 6)* Abre um defeito numa execução que falhou / lista os defeitos da execução |
| GET | `/api/defeitos` | *(Semana 6)* Lista defeitos; filtros opcionais `projeto_id`, `rodada_id`, `status`, `severidade` |
| GET / PATCH | `/api/defeitos/{defeito_id}` | *(Semana 6)* Detalha / muda o status do defeito |

O resultado da execução usa `PUT` porque registrar o mesmo resultado duas vezes deixa a execução no mesmo estado (é idempotente), e corrigir um resultado é substituí-lo.

Os endpoints de projetos não estavam no plano da Semana 5, mas foram incluídos porque, sem eles, não havia como criar pelo HTTP o projeto ao qual o escopo pertence.

## 4. Camada de IA — Geração de Casos de Teste

**Fluxo:**

```
Upload do escopo (.docx)
   → extrair texto: parágrafos e tabelas (sistema-core/documentos)
   → LLMProvider.gerar_casos_teste(texto)   [interface, Strategy Pattern]
   → adaptador concreto: ProvedorClaude (Anthropic SDK, tool call forçada com schema estrito)
   → casos retornam como CasoTesteGerado (dataclass, sem dependência de ORM)
   → o serviço processar_escopo persiste como CasoDeTeste (origem="ia") + registro GeracaoIA
   → casos ficam sujeitos a revisão do usuário
```

**Decisão de arquitetura:** a interface `LLMProvider` define o contrato (`gerar_casos_teste(texto_escopo: str) -> list[CasoTesteGerado]`) e não conhece detalhes de nenhum provedor nem do banco. A primeira implementação (`ProvedorClaude`) usa o SDK oficial `anthropic` com uma **tool call forçada** (`tool_choice`) e schema estrito (`strict: true`). Assim a resposta já chega validada no formato de `CasoTesteGerado`, sem parsing de texto livre. O provedor devolve um tipo simples (dataclass) e não um model do ORM. Por isso a troca de SQLAlchemy para o ORM do Django não afeta a camada de IA. Essa abstração permite, no futuro, adicionar outro provedor (ex.: OpenAI) implementando a mesma interface, sem exigir isso para a entrega de outubro/2026 (ver seção 7, Fora de Escopo).

**Chamada à IA (v2.5):** via streaming (`messages.stream` + `get_final_message`), com até 64 mil tokens de resposta, para que um escopo grande não seja cortado; antes era uma chamada simples limitada a 16 mil. O `stop_reason` é conferido antes de ler os casos: resposta cortada ou recusada vira `RespostaIAInvalida` com mensagem própria, em vez de gravar uma lista incompleta. O modelo segue `claude-opus-5`, que aceita a tool call forçada; os modelos 5.5 não aceitam `tool_choice` forçado, então migrar para eles exige trocar para `tool_choice` `auto` + instrução no prompt.

*(Correção na v2.1: a v2.0 citava structured outputs via `output_config.format`; a implementação entregue na Semana 2 usa tool call com schema estrito, que dá a mesma garantia de formato.)*

**MCP (Model Context Protocol):** avaliado e descartado para esta necessidade. O MCP serve para conectar um LLM a ferramentas e dados externos, que é a direção oposta ao que precisamos aqui (a própria aplicação chama o LLM diretamente via SDK). Fica registrado como possível extensão futura (expor a geração de casos como uma tool MCP), fora do escopo de outubro/2026.

## 5. Decisões Técnicas (Stack)

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3 | Alinhado à formação em andamento (Python 3 do Zero ao Avançado) |
| Framework web / API | Django + Django Ninja | Alinhado ao padrão de backend da ComBio (Django + Django Ninja); gera OpenAPI/Swagger automaticamente; ver D1 |
| ORM / Persistência | ORM do Django (models + migrations) | Integração nativa com o Django Ninja, migrations versionadas e Django Admin para inspeção dos dados; ver D2 |
| Banco de dados | MySQL 8.4 (docker-compose, Fase 3); SQLite só no desenvolvimento local e nos testes | Padrão de banco da ComBio; troca feita só pela configuração `DATABASES`, sem alterar código; ver D3 |
| Extração de documentos | `python-docx` (Word) | Os escopos do projeto são .docx; ver D4 |
| Integração com IA | SDK oficial `anthropic`, atrás da interface `LLMProvider` | Ferramenta homologada; saída estruturada via tool call elimina parsing frágil |
| Validação | Schemas do Django Ninja (Pydantic) | Validação de entrada e serialização de saída, com os mesmos type hints usados no FastAPI |
| Testes | pytest + pytest-django | Padrão de mercado; o `pytest-django` cria um banco de testes isolado por execução |
| Containerização | Docker + docker-compose (API + MySQL) | Conforme escopo Fase 3 |

**Variáveis de ambiente:** `LLM_PROVIDER` (`claude`, padrão, `openai` ou `ollama`; ver D6 e D7), `OLLAMA_URL` e `OLLAMA_MODEL` (servidor local e modelo do Ollama, padrão `gemma3:4b`), `OPENAI_API_KEY_FILE` e `OPENAI_MODEL` (chave e modelo da OpenAI, padrão `gpt-5.5`), `ANTHROPIC_API_KEY_FILE` (caminho do arquivo com a chave do provedor de IA; no Docker, o secret em `/run/secrets/anthropic_api_key`; ver D5), `ANTHROPIC_API_KEY` (alternativa só para desenvolvimento local, nunca versionada) `DJANGO_SECRET_KEY` (nunca versionada), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, e as variáveis de conexão com o MySQL usadas na Fase 3 (`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, nunca versionada, `MYSQL_HOST`, `MYSQL_PORT`). Sem `MYSQL_HOST`, o `settings.py` usa SQLite.

## 6. Registro de Decisões

Cada decisão registra o contexto, a escolha, as alternativas avaliadas e o que se perde com ela, para que a escolha possa ser revista no futuro com base no que foi pensado.

### D1 — Framework de API: Django Ninja no lugar de FastAPI (22/09/2026)

- **Contexto:** a v2.0 previa FastAPI para a Fase 2. A troca foi **solicitada pelo Tech Lead que avaliará o projeto**, que indicou o Django Ninja como padrão de API usado na empresa. Até esta data nenhum código de API tinha sido escrito (`api/` ainda vazio), então trocar agora não custa retrabalho na camada HTTP.
- **Decisão:** usar **Django + Django Ninja**.
- **Motivos:**
  - **Solicitação do Tech Lead avaliador, por ser o padrão da empresa.** O Django Ninja é o framework de API adotado na ComBio. Construir o PDI sobre ele faz com que o projeto seja avaliado na mesma stack que o time usa e mantém, que o aprendizado seja aplicável no dia a dia e que uma eventual evolução do projeto para uso interno fique mais fácil.
  - **Mantém o que motivou a escolha do FastAPI.** O Django Ninja também gera documentação OpenAPI/Swagger automática (`/api/docs`) e valida entrada e saída com Pydantic usando type hints. Os objetivos do PDI ligados a documentação de API e validação continuam atendidos.
  - **Ecossistema do Django.** Settings, gestão de configuração, Django Admin, migrations e suporte de testes (`pytest-django`) vêm prontos, sem precisar montar essas peças separadamente como no FastAPI.
- **Alternativa descartada:** FastAPI. É leve e muito popular, mas fora do padrão da empresa e exigiria montar à parte o que o Django já oferece (migrations, admin, settings).
- **Custo:** o Django é mais pesado e opinativo que o FastAPI; há uma curva de aprendizado do framework dentro de um cronograma já apertado.

### D2 — Persistência: ORM do Django no lugar de SQLAlchemy (22/09/2026)

- **Contexto:** o Django Ninja roda dentro do Django. As Semanas 1 a 3 já tinham entregado 7 modelos, a conexão e o serviço `processar_escopo` em SQLAlchemy.
- **Alternativas avaliadas:**
  1. **Manter SQLAlchemy** e usar o Django só como camada HTTP, sem o ORM. Não teria retrabalho e manteria o core independente de framework, mas é um uso pouco comum do Django: perde migrations e Admin e mantém duas formas de configurar banco no mesmo projeto.
  2. **Migrar para o ORM do Django** (escolhida).
- **Motivos da escolha:**
  - **Coerência de stack.** Um único framework cuida de HTTP, configuração e persistência, que é o uso padrão do Django e o esperado no padrão da ComBio.
  - **Integração com o Django Ninja.** Os Schemas do Ninja podem ser derivados dos models (`ModelSchema`), o que reduz código duplicado entre banco e API.
  - **Migrations versionadas** (`makemigrations`/`migrate`) no lugar de criar tabelas com `create_all`. Isso é essencial para evoluir o esquema com segurança quando o banco passar a ser o MySQL.
  - **Django Admin** para inspecionar e corrigir dados durante o desenvolvimento e na apresentação.
  - **Custo baixo nesta etapa.** São 7 modelos pequenos e um serviço. Migrar agora custa bem menos do que migrar depois que a API estiver construída sobre o SQLAlchemy.
- **Custo:** cerca de 2 dias de retrabalho na Semana 4 (modelos, serviço e testes); o core passa a depender do Django (regra de ouro revista na seção 1).

### D3 — Banco de dados: MySQL no lugar de PostgreSQL (22/09/2026)

- **Contexto:** a v2.0 previa PostgreSQL na Fase 3. Depois da D1, que foi motivada pelo padrão da empresa a pedido do Tech Lead avaliador, o autor decidiu aplicar o mesmo critério ao banco: o padrão de desenvolvimento da ComBio define **MySQL**. Até esta data nenhum banco de servidor tinha sido configurado (só SQLite local), então a troca não gera retrabalho.
- **Decisão:** usar **MySQL (8.4 LTS)** no docker-compose da Fase 3, com o driver `mysqlclient`, que é o recomendado pela documentação do Django.
- **Motivos:**
  - **Padrão da empresa.** Com o Django Ninja (D1), o PDI fica inteiro na stack de backend da ComBio (Django + Django Ninja + MySQL). É a mesma régua usada pelo Tech Lead na avaliação e pelo time que mantém os sistemas internos.
  - **Nenhuma restrição técnica.** O projeto não usa nenhum recurso exclusivo do PostgreSQL (como `django.contrib.postgres`), então a vantagem que motivava o PostgreSQL na v2.0 (melhor suporte no ORM) não pesa para este domínio.
  - **Troca sem código.** O ORM do Django abstrai o banco: basta trocar a configuração `DATABASES` (ativada pela variável `MYSQL_HOST`) e o driver no `requirements.txt`. Models, migrations e serviços não mudam.
- **Alternativa descartada:** manter o PostgreSQL, como estava na v2.0. Tecnicamente atenderia, mas deixaria o projeto fora do padrão da empresa e exigiria uma exceção formal (ADR) para uma aplicação interna.
- **Configuração adotada:** charset `utf8mb4`, para suportar qualquer caractere (acentuação e emojis vindos de documentos de escopo), e `sql_mode` `STRICT_TRANS_TABLES`, para que o MySQL rejeite dados inválidos em vez de truncá-los em silêncio.
- **Custo e atenção:**
  - O `mysqlclient` depende de bibliotecas nativas do MySQL. No Windows há wheel pronto; na imagem Docker da Fase 3, o Dockerfile precisará instalar os pacotes de build (`default-libmysqlclient-dev`, `pkg-config`).
  - O SQLite continua em uso **só como conveniência de desenvolvimento local e nos testes automatizados** (não precisa de servidor e deixa os testes rápidos). Ele não faz parte do padrão da empresa e não é usado em nenhum ambiente além da máquina do desenvolvedor. Diferenças de comportamento entre SQLite e MySQL (tipos, ordenação, collation, constraints) serão cobertas pelos testes end-to-end da Semana 8, que rodam contra o MySQL no container.

### D4 — Documento de escopo: só .docx (30/09/2026)

- **Contexto:** desde a Semana 2 o sistema aceitava .docx e .pdf. Antes dos primeiros testes com escopos reais, o autor definiu que o projeto vai trabalhar apenas com documentos .docx.
- **Decisão:** aceitar só `.docx`; o suporte a PDF e a dependência `pypdf` foram removidos.
- **Motivos:**
  - **Um formato só, extraído com fidelidade.** O .docx guarda a estrutura do documento (parágrafos e tabelas), o que permite enviar os requisitos à IA na ordem e com as colunas das tabelas. No PDF essa estrutura se perde, e um PDF digitalizado nem tem texto.
  - **Menos código e menos casos de erro** para testar e manter no prazo do PDI.
- **Alternativa descartada:** manter o PDF. Exigiria tratar PDF digitalizado (OCR) e tabelas quebradas para ter a mesma qualidade de extração, sem necessidade no uso previsto.
- **Custo:** quem tiver o escopo só em PDF precisa convertê-lo para .docx antes de enviar.

### D5 — Chave do provedor de IA: arquivo via Docker secret, nunca variável nem repositório (02/10/2026)

- **Decisão:** a chave da Anthropic fica num arquivo **fora do repositório** e chega à API como **Docker secret**, montado em `/run/secrets/anthropic_api_key`. O `ProvedorClaude` lê o caminho em `ANTHROPIC_API_KEY_FILE`. O `docker/.env` guarda só o caminho do arquivo (`ANTHROPIC_API_KEY_ARQUIVO`), nunca a chave.
- **Por quê, camada por camada:**
  - *GitHub:* o arquivo está fora do projeto; o `.gitignore` recusa nomes típicos de credencial (`*apikey*`, `*api-key*`, `*.key`, `secrets/`…); e `testes/test_seguranca_credenciais.py` falha a suíte se encontrar uma chave da Anthropic ou do Google em qualquer arquivo do projeto, citando só o nome do arquivo. O histórico do Git foi verificado: nenhuma chave.
  - *Imagem Docker:* a chave não é copiada no build (`docker/Dockerfile.dockerignore`); a imagem foi varrida e não tem chave.
  - *Ambiente do container:* como variável, a chave apareceria em `docker inspect`, nos processos filhos e nos relatórios de erro. Como secret, o ambiente só tem o caminho.
  - *Container de testes:* não recebe o secret; os testes nunca chamam a IA real.
  - *Respostas e logs:* as mensagens de erro da API são fixas, sem texto do SDK; o log registra o tipo do erro (ex.: `authentication_error`), nunca a chave. Chave recusada (401) tem mensagem própria.
  - *Rede:* a porta da API é publicada só em `127.0.0.1`, sem acesso por outras máquinas.
  - *Frontend:* o projeto não tem frontend (seção 7); a chave só existe no backend, e nenhuma rota a devolve.
- **Alternativa descartada:** provedor Gemini como reserva da Claude. O Gemini não é ferramenta homologada pela ComBio, e a reserva enviaria documentos de escopo (dados internos) para fora das ferramentas homologadas, o que a política de IA da empresa bloqueia. Um novo provedor depende de exceção aprovada pelo ServiceUP; a interface `LLMProvider` já permite adicioná-lo sem mudar o resto do sistema.
- **Custo:** quem roda localmente sem Docker precisa definir `ANTHROPIC_API_KEY_FILE` (ou `ANTHROPIC_API_KEY`) no próprio ambiente.

### D6 — Segundo provedor de IA: OpenAI, atrás da mesma interface (02/10/2026)

- **Decisão:** adicionar o adaptador `ProvedorOpenAI` (`sistema-core/ia/provedor_openai.py`), escolhido por `LLM_PROVIDER=openai`. Ele usa *structured output* (`response_format` com `json_schema` estrito), o equivalente da OpenAI à tool call forçada da Anthropic. O prompt, o schema dos casos e a conversão para `CasoTesteGerado` ficam em `ia/esquema_casos.py`, compartilhados pelos dois provedores, para a troca de provedor não mudar o que é pedido nem o formato do resultado. O modelo padrão é o `gpt-5.5`, configurável por `OPENAI_MODEL`.
- **Por quê:** a chave da Anthropic disponível não é válida (D5), e o ChatGPT é ferramenta homologada na ComBio. A interface `LLMProvider`, prevista desde a Semana 2 para isso, permitiu adicionar o provedor sem mudar serviços, API nem banco: só a fábrica `obter_provedor_llm` ganhou um registro. A auditoria em `GeracaoIA` passa a registrar `openai` e o modelo usado.
- **Regras de uso:** só chave de **conta corporativa** (política de IA da ComBio). A chave segue a D5: arquivo fora do repositório, secret `openai_api_key` no Docker, `OPENAI_API_KEY_FILE` no ambiente. Os mesmos casos de erro do `ProvedorClaude` (resposta cortada, recusada ou fora do formato; chave recusada) têm tratamento equivalente; o 429 diferencia **conta sem crédito**, que esperar não resolve, de **limite de requisições**, que passa sozinho.
- **Alternativa descartada:** troca automática de provedor quando um falha. Esconderia o problema (chave inválida, falta de crédito) e misturaria resultados de modelos diferentes no mesmo projeto sem decisão de ninguém; o provedor ativo é uma escolha explícita de configuração.
- **Custo:** mais um SDK (`openai`) nas dependências e um adaptador para manter.

### D7 — Provedor gratuito: Ollama com modelo local (02/10/2026)

- **Decisão:** adicionar o adaptador `ProvedorOllama` (`sistema-core/ia/provedor_ollama.py`), escolhido por `LLM_PROVIDER=ollama`, como opção gratuita enquanto não há crédito nos provedores pagos. O modelo roda na própria máquina (padrão `gemma3:4b`, configurável por `OLLAMA_MODEL`). O adaptador usa a API nativa do Ollama (`/api/chat`) com o mesmo JSON Schema dos outros provedores no campo `format`, que restringe a geração ao formato de `CasoTesteGerado`, e não precisa de biblioteca nova (só `urllib`).
- **Por quê:** é a única opção sem custo que mantém o documento de escopo dentro do computador. A política de IA da ComBio bloqueia enviar dado interno a ferramenta não homologada; com o modelo local, nada é enviado. O Ollama em si não está na lista de ferramentas homologadas, então o uso fica restrito a protótipo e PDI. Uso oficial depende de exceção pelo ServiceUP.
- **Travas:** o adaptador recusa, **antes de enviar qualquer coisa**, modelos de nuvem do Ollama (nome com `cloud`, ex.: `gpt-oss:120b-cloud`, que rodam fora da máquina) e servidores que não sejam a própria máquina (`localhost`, `127.0.0.1`, `::1` ou `host.docker.internal`, que é o Windows visto de dentro do Docker).
- **Medido nesta máquina (16 GB, sem GPU):** um escopo pequeno gerou 9 a 10 casos válidos em cerca de 3 min 20 s. A qualidade é inferior à dos provedores pagos (códigos fora do padrão `CT-NNN`, quase tudo `funcional`), o que reforça a revisão dos casos antes de usar. Por isso o timeout do gunicorn subiu de 300 s para 900 s, e o adaptador desiste em 840 s com mensagem própria. O contexto do modelo foi ampliado para 16 mil tokens (`num_ctx`), porque o padrão do Ollama cortaria escopos maiores sem aviso.
- **Alternativa descartada:** o Gemini no plano gratuito. É gratuito, mas não é homologado, e o escopo seria enviado para fora da empresa (ver D5).
- **Custo:** a geração é lenta e ocupa a CPU da máquina enquanto roda; escopos grandes devem ser divididos. O Ollama precisa estar aberto no Windows.

## 7. Fora de Escopo (reforçando o escopo-projeto.docx)

Autenticação multiusuário, frontend, deploy em nuvem, filas/mensageria, suporte simultâneo a múltiplos provedores de IA no dia 1 (só a interface fica pronta para isso), armazenamento do conteúdo de evidências (imagens/PDF, só metadados): nada disso entra nesta primeira versão. O Django Admin é usado só como ferramenta de apoio ao desenvolvimento e não é considerado um frontend do produto.

---

## 8. Cronograma Semanal (02/set a 31/out/2026)

Base: apresentação final em outubro/2026 (API funcionando + geração de casos via IA + documentação), com os prazos intermediários do `plano-de-acoes.docx` (métodos REST, tratamento de erros e Git até outubro/2026). Replanejado em 02/09/2026 (v2.0) e ajustado em 22/09/2026 (v2.1) para a troca de stack.

| Semana | Período | Fase | Entregas da semana |
|---|---|---|---|
| 1 | 02–08/set | Fase 1 | ✅ Remodelagem do domínio (Projeto, Escopo, CasoDeTeste, RodadaDeExecucao, ExecucaoDeCaso, Defeito), ajuste do SQLAlchemy/SQLite já existente |
| 2 | 09–15/set | Fase 1 | ✅ Extração de texto de documentos (docx/pdf); interface `LLMProvider`; adaptador `ProvedorClaude` |
| 3 | 16–22/set | Fase 1 | ✅ Geração estruturada de casos de teste via IA; persistência; testes automatizados do core |
| 4 | 23–29/set | Fase 1 | ✅ Migração para Django: projeto Django, models + migrations, `processar_escopo` e testes existentes no ORM do Django (pytest-django). Regras de negócio de execução (rodadas, execução de casos, defeitos) e CRUD manual de casos de teste. Fechamento da Fase 1 (revisão de código com dev mais experiente, 20%) |
| 5 | 30/set–06/out | Fase 2 | ✅ Setup do Django Ninja (`NinjaAPI`, routers), Schemas; endpoints de escopos (upload + gerar-casos) e casos de teste |
| 6 | 07–13/out | Fase 2 | ✅ Endpoints de rodadas/execuções/defeitos, tratamento de erros padronizado (exception handlers do Ninja), testes de integração |
| 7 | 14–20/out | Fase 2 | ✅ Revisão do Swagger/OpenAPI (`/api/docs`), repositório Git versionado (branch `main` só no deploy final, por decisão do autor), Dockerfile da API |
| 8 | 21–27/out | Fase 3 | ✅ `docker-compose` (API + MySQL 8.4), migrations aplicadas no container, testes end-to-end containerizados, documentação de uso da API |
| 9 | 28–31/out | — | Buffer + **apresentação final (outubro/2026)** |

**Riscos:**
- Os riscos já sinalizados no plano de ações continuam valendo. Se o tempo apertar, a estrutura de logs e a documentação de endpoints têm prazo formal até novembro/2026 e não comprometem a meta principal de outubro (API funcionando + geração de casos via IA).
- **Novo na v2.1: a Semana 4 ficou mais carregada** por causa da migração para o Django. Se ela não couber, o fechamento das regras de execução e o CRUD manual podem avançar para a Semana 5, rodando em paralelo com o setup do Django Ninja. A geração de casos via IA, que é a entrega mais importante, já está pronta e só será portada, não reescrita.
- **Curva de aprendizado do Django**, mitigada pela revisão de código com dev mais experiente já prevista na Semana 4.

## 9. Próximo Passo Imediato

Semanas 1 a 3 concluídas (sobre SQLAlchemy): remodelagem das entidades, extração de texto de documentos (docx/pdf), interface `LLMProvider` + adaptador `ProvedorClaude` (geração estruturada via tool call), e o serviço `servicos.processar_escopo` que orquestra extração + geração via IA + persistência (`CasoDeTeste` e `GeracaoIA`), com testes automatizados cobrindo o caminho feliz e os erros de extração/IA.

Migração para o Django concluída em 22/09/2026, adiantando o início da Semana 4: projeto Django em `api/config/`, `sistema-core/modelos/` como app Django (7 models + migration `0001_initial`, Django Admin registrado), `processar_escopo` portado para o ORM do Django com gravação atômica (`transaction.atomic`), e testes rodando com `pytest-django`. São 13 testes passando: os 12 anteriores e um novo que confere se as migrations estão em dia com os models. Os enums continuam Python puro, então `ia/` e `documentos/` seguem sem dependência de Django.

Regras de negócio da Semana 4 concluídas em 22/09/2026: CRUD manual de casos de teste (`servicos/casos_teste.py`) e rodadas, execuções e defeitos (`servicos/execucoes.py`), com as regras descritas na seção 3 e a migration `0002_caso_unico_por_rodada`. São 36 testes passando.

Semana 5 adiantada e concluída em 23/09/2026, para abrir mais tempo de testes antes da apresentação: Django Ninja configurado (`api/config/api.py`), Schemas em `api/schemas/`, routers em `api/rotas/` e os endpoints listados na seção 3. O core ganhou `servicos/projetos.py`, `servicos/escopos.py` (upload do documento), a recusa de reprocessar um escopo já processado e a exceção `ProvedorIAIndisponivel` na camada de IA. São 74 testes passando, 26 deles pela camada HTTP (cliente de teste do Django, com a IA substituída por um dublê).

Revisão de código com o dev mais experiente realizada em 23/09/2026, fechando formalmente a Fase 1. Os pontos levantados foram o banco MySQL e o Django Ninja (NinjaAPI), que já estavam aplicados (decisões D1 e D3). 

Semana 6 adiantada e concluída em 23/09/2026: endpoints de rodadas, execuções e defeitos (seção 3), formato único de erro com `codigo` estável, `OperacaoEmConflito` (409) para as regras de duplicidade e de histórico, mensagens 404 em português e erro 500 sem vazar detalhes internos. O teste de integração `testes/test_api_fluxo_completo.py` percorre o produto inteiro só pela API, do envio do escopo à correção do defeito. São 110 testes passando.

Semana 7 iniciada em 30/09/2026 com a revisão do Swagger (ver "Endpoints entregues" na seção 3). No mesmo dia foi corrigido o erro 500 com documento de escopo ilegível (corrompido ou só renomeado): o conteúdo agora é lido já no envio (`documentos.validar_documento`), e uma falha de leitura na geração vira `DocumentoIlegivel` (400). São 130 testes passando. Os commits das Semanas 5 e 6 foram enviados para `origin/develop` no mesmo dia.

Ainda em 30/09/2026, preparando os testes com escopos reais: escopo só em .docx (D4), leitura das tabelas do documento, recusa de documento sem texto e tratamento de resposta da IA cortada ou recusada (seção 4). São 136 testes passando.

Em 02/10/2026: teste manual de todas as rotas da API com `curl` (sem falhas); falta de credencial do provedor de IA passa a responder 503 em vez de 500; nome de projeto único (seção 3); Dockerfile da API em `docker/Dockerfile` (multi-stage, Python 3.13, usuário não-root com código só leitura, `gunicorn` com timeout de 300 s por causa da geração via IA). A imagem foi validada rodando sozinha (SQLite) e contra um MySQL 8.4 temporário, com as migrations aplicadas. São 140 testes passando. A branch `main` só será criada no deploy final, com o projeto concluído.

Semana 8 iniciada em 02/10/2026: `docker/docker-compose.yml` com a API e o MySQL 8.4. A API só sobe quando o MySQL aceita conexões do usuário da aplicação (healthcheck), as migrations são aplicadas a cada subida (`docker/entrypoint.sh`), e os dados do MySQL e os uploads ficam em volumes. O serviço `testes` (perfil `testes`) roda a suíte inteira contra o MySQL; para isso, `docker/mysql-init/` dá ao usuário da aplicação permissão no banco `test_casos_teste`, que o pytest-django cria a cada execução. Um fluxo ponta a ponta pelo HTTP (projeto → escopo → casos → rodada → execuções → defeito), com derrubada e nova subida dos containers no meio, confirmou que os dados persistem. Nesse teste apareceu o corpo ilegível fora do formato padrão de erro, corrigido com o código `corpo_invalido`. São 142 testes passando, no SQLite e no MySQL.

Ainda em 02/10/2026, fechando a Semana 8: mensagens de validação (422) em português e o guia de uso da API em `docs/uso-da-api.md` (subida do ambiente, convenções, fluxo completo com exemplos, referência das rotas, erros e dicas para o terminal do Windows). Os exemplos do guia foram executados contra a API antes de entrar no documento. São 146 testes passando.

Ainda em 02/10/2026: proteção da chave do provedor de IA (D5). No primeiro teste real, a Anthropic recusou o arquivo recebido (401, `authentication_error`): o conteúdo não tem o formato de uma chave da API da Anthropic. São 151 testes passando.

Ainda em 02/10/2026: segundo provedor, a OpenAI (D6). A chave da OpenAI é válida (autenticou e listou os modelos), mas a conta está sem créditos: a geração real respondeu 429 `insufficient_quota`, que agora tem mensagem própria. As verificações da D5 foram repetidas com a chave da OpenAI: nenhuma ocorrência nos logs, no `docker inspect` nem na imagem. São 163 testes passando.

Ainda em 02/10/2026: provedor gratuito com Ollama local (D7). Primeira geração real de ponta a ponta: pela API no Docker, o `gemma3:4b` gerou 9 casos do escopo de exemplo em 3 min 22 s, gravados com origem `ia` e auditados em `GeracaoIA`. São 178 testes passando, no SQLite e no MySQL.

Próximo passo (até a apresentação): testes com escopos reais pelo Ollama; quando houver crédito na conta corporativa da OpenAI (ou uma chave válida da Anthropic), comparar a qualidade dos casos; branch `main` e deploy final com o projeto concluído.
