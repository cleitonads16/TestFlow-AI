# Guia de Uso da API — TestFlow AI

> Como usar a API do Gestor de Casos de Teste com Geração Assistida por IA: subir o ambiente, percorrer o fluxo completo e tratar os erros. A referência interativa, com todos os campos e exemplos, fica no Swagger (`/api/docs`). Decisões de arquitetura e regras de negócio em detalhe: [`arquitetura-e-cronograma.md`](arquitetura-e-cronograma.md).

**Versão da API:** 0.7.0 · **Atualizado em:** 02/10/2026

---

## 1. Subindo a API

**Com Docker (API + MySQL)**, na raiz do projeto:

```
cp docker/.env.exemplo docker/.env      # preencha as senhas e a DJANGO_SECRET_KEY
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d --build
```

**Sem Docker (SQLite, só para desenvolvimento)**:

```
cd api
python manage.py migrate
python manage.py runserver
```

Nos dois casos a API responde em `http://127.0.0.1:8000/api/` e o Swagger em **http://127.0.0.1:8000/api/docs**, onde todas as rotas podem ser testadas pelo navegador.

**Geração de casos via IA:** precisa da variável `ANTHROPIC_API_KEY` (no `docker/.env` ou no ambiente do `runserver`). Sem ela, só a rota de geração responde 503; todo o resto da API funciona.

## 2. Convenções

| Item | Regra |
|---|---|
| Autenticação | Nenhuma nesta versão (fora de escopo, ver seção 7 da arquitetura) |
| Formato | JSON em UTF-8 (`Content-Type: application/json`). O único envio em `multipart/form-data` é o do documento de escopo |
| Identificadores | Números inteiros gerados pela API (`id`); use o `id` devolvido na criação para as chamadas seguintes |
| Datas | `AAAA-MM-DD` (ex.: `2026-10-02`). Data e hora são devolvidas em UTC, no formato ISO 8601 |
| Textos obrigatórios | Não aceitam vazio nem só espaços; espaços nas pontas são removidos |
| Atualização parcial | Nos `PATCH`, só os campos enviados são alterados |

**Valores fixos (enums):**

| Campo | Valores |
|---|---|
| Categoria do caso | `funcional` (padrão), `integracao`, `regra_de_negocio`, `outro` |
| Prioridade do caso | `baixa`, `media` (padrão), `alta` |
| Origem do caso | `manual`, `ia` (definida pela API, não editável) |
| Status do escopo | `pendente`, `processado`, `erro` |
| Status da execução | `pendente`, `passou`, `falhou`, `bloqueado` |
| Severidade do defeito | `baixa`, `media` (padrão), `alta`, `critica` |
| Status do defeito | `aberto`, `em_analise`, `corrigido`, `fechado` |

## 3. Fluxo completo, passo a passo

Os exemplos usam `curl` com `B=http://127.0.0.1:8000/api`. Os ids mostrados (`1`, `2`…) são os de um banco vazio; use os que a sua API devolver.

### 3.1 Criar o projeto

```
curl -X POST $B/projetos -H "Content-Type: application/json" \
     -d '{"nome": "Portal RH", "descricao": "Portal de autoatendimento"}'
```

`201` → `{"id": 1, "nome": "Portal RH", "descricao": "Portal de autoatendimento"}`

O nome é único, sem diferenciar maiúsculas: um segundo "portal rh" é recusado com `409`.

### 3.2 Enviar o documento de escopo

```
curl -X POST $B/projetos/1/escopos -F "arquivo=@escopo-login.docx"
```

`201` → `{"id": 1, "projeto_id": 1, "nome_arquivo": "escopo-login.docx", "status": "pendente", "data_upload": "..."}`

Só `.docx`, até 10 MB. O documento é lido já no envio: arquivo em outro formato, vazio, corrompido, só renomeado para `.docx` ou sem texto (ex.: só imagens) é recusado com `400`. A API lê os parágrafos e as tabelas do documento; cabeçalho e rodapé não são lidos.

### 3.3 Gerar os casos de teste via IA

```
curl -X POST $B/escopos/1/gerar-casos
```

`201` → `{"escopo": {..., "status": "processado"}, "quantidade_casos_gerados": 12, "casos": [...]}`

- A chamada é síncrona e leva o tempo de a IA responder: de alguns segundos a poucos minutos, conforme o tamanho do escopo. Configure o cliente HTTP com timeout de pelo menos 5 minutos.
- Os casos nascem com `origem: "ia"`. O texto lido do documento fica em `GET /escopos/1` (`texto_extraido`).
- Um escopo já `processado` não é gerado de novo (`409`), para não duplicar os casos nem perder as revisões.
- Se a IA falhar (`502` ou `503`), o escopo fica com status `erro` e a geração pode ser pedida outra vez. Nenhum caso parcial é gravado.

### 3.4 Revisar os casos e cadastrar casos manuais

Listar (filtros combináveis: `projeto_id`, `escopo_id`, `categoria`, `origem`):

```
curl "$B/casos-de-teste?escopo_id=1&origem=ia"
```

Revisar um caso (só os campos enviados mudam; a `origem` nunca muda):

```
curl -X PATCH $B/casos-de-teste/1 -H "Content-Type: application/json" \
     -d '{"prioridade": "alta", "resultado_esperado": "Usuario autenticado e redirecionado"}'
```

Cadastrar um caso manual (`codigo` e `titulo` obrigatórios; o código é único dentro do escopo):

```
curl -X POST $B/escopos/1/casos-de-teste -H "Content-Type: application/json" \
     -d '{"codigo": "CT-900", "titulo": "Login com senha expirada", "categoria": "regra_de_negocio",
          "pre_condicao": "Senha vencida ha 91 dias", "passos": "1. Informar e-mail\n2. Informar a senha",
          "resultado_esperado": "Sistema pede a troca da senha", "prioridade": "alta"}'
```

Excluir: `DELETE $B/casos-de-teste/{id}` → `204`. Um caso que já entrou em alguma rodada não pode ser excluído (`409`), para preservar o histórico.

### 3.5 Montar a rodada de execução

```
curl -X POST $B/projetos/1/rodadas -H "Content-Type: application/json" \
     -d '{"nome": "Homologacao 1", "data_inicio": "2026-10-05", "data_fim": "2026-10-09", "casos_ids": [1, 2, 3]}'
```

`201` → `{"id": 1, "projeto_id": 1, "nome": "Homologacao 1", ...}`

Cada caso vira uma **execução** com status `pendente`. A criação é tudo ou nada: se algum caso não existir (`400`) ou for de outro projeto (`400`), a rodada não é criada. Para incluir casos depois:

```
curl -X POST $B/rodadas/1/casos -H "Content-Type: application/json" -d '{"casos_ids": [4]}'
```

Um caso entra uma única vez por rodada (`409` se repetido).

### 3.6 Registrar os resultados

Listar as execuções da rodada (filtro opcional `status`) para obter os ids:

```
curl "$B/rodadas/1/execucoes?status=pendente"
```

Registrar o resultado (`passou`, `falhou` ou `bloqueado`; a data é gravada pela API):

```
curl -X PUT $B/execucoes/2/resultado -H "Content-Type: application/json" \
     -d '{"status": "falhou", "observacoes": "Conta nao foi bloqueada na 3a tentativa"}'
```

`bloqueado` exige `observacoes` (`400` sem elas), para registrar o impedimento. O resultado pode ser corrigido enviando outro `PUT`.

### 3.7 Abrir e acompanhar defeitos

Só em execução com status `falhou` (`400` nas demais). O defeito nasce `aberto`:

```
curl -X POST $B/execucoes/2/defeitos -H "Content-Type: application/json" \
     -d '{"descricao": "Conta nao e bloqueada apos 3 tentativas", "severidade": "critica"}'
```

Atualizar o andamento:

```
curl -X PATCH $B/defeitos/1 -H "Content-Type: application/json" -d '{"status": "corrigido"}'
```

Listar defeitos (filtros combináveis: `projeto_id`, `rodada_id`, `status`, `severidade`):

```
curl "$B/defeitos?projeto_id=1&status=aberto"
```

### 3.8 Acompanhar a rodada

```
curl $B/rodadas/1/resumo
```

`200` → `{"pendente": 1, "passou": 1, "falhou": 1, "bloqueado": 0, "total": 3}`

`GET $B/rodadas/1` devolve os dados da rodada com o mesmo resumo embutido.

## 4. Referência rápida das rotas

Todas sob `/api`.

| Método | Rota | O que faz | Sucesso |
|---|---|---|---|
| POST | `/projetos` | Cria projeto | 201 |
| GET | `/projetos` | Lista projetos (ordem alfabética) | 200 |
| GET | `/projetos/{id}` | Detalha projeto | 200 |
| POST | `/projetos/{id}/escopos` | Envia documento de escopo (campo `arquivo`) | 201 |
| GET | `/projetos/{id}/escopos` | Lista escopos do projeto | 200 |
| GET | `/escopos/{id}` | Detalha escopo, com `texto_extraido` | 200 |
| POST | `/escopos/{id}/gerar-casos` | Gera casos de teste via IA | 201 |
| GET | `/casos-de-teste` | Lista casos (filtros: `projeto_id`, `escopo_id`, `categoria`, `origem`) | 200 |
| POST | `/escopos/{id}/casos-de-teste` | Cria caso manual | 201 |
| GET | `/casos-de-teste/{id}` | Detalha caso | 200 |
| PATCH | `/casos-de-teste/{id}` | Revisa caso | 200 |
| DELETE | `/casos-de-teste/{id}` | Exclui caso sem histórico | 204 |
| POST | `/projetos/{id}/rodadas` | Cria rodada (com `casos_ids` opcional) | 201 |
| GET | `/projetos/{id}/rodadas` | Lista rodadas do projeto | 200 |
| GET | `/rodadas/{id}` | Detalha rodada, com resumo | 200 |
| GET | `/rodadas/{id}/resumo` | Execuções por status | 200 |
| POST | `/rodadas/{id}/casos` | Inclui casos na rodada | 201 |
| GET | `/rodadas/{id}/execucoes` | Lista execuções (filtro: `status`) | 200 |
| GET | `/execucoes/{id}` | Detalha execução | 200 |
| PUT | `/execucoes/{id}/resultado` | Registra resultado | 200 |
| POST | `/execucoes/{id}/defeitos` | Abre defeito | 201 |
| GET | `/execucoes/{id}/defeitos` | Lista defeitos da execução | 200 |
| GET | `/defeitos` | Lista defeitos (filtros: `projeto_id`, `rodada_id`, `status`, `severidade`) | 200 |
| GET | `/defeitos/{id}` | Detalha defeito | 200 |
| PATCH | `/defeitos/{id}` | Atualiza status do defeito | 200 |

## 5. Erros

Todo erro sai no mesmo formato. Use `codigo` para decidir o que fazer no cliente; `detail` é a mensagem em português para mostrar ao usuário.

```json
{"detail": "Já existe um projeto com o nome 'Portal RH'.", "codigo": "conflito"}
```

Nos erros de validação (`422`), `erros` traz um item por campo recusado. `campo` usa ponto para itens de lista (`casos_ids.0` é o primeiro item) e `origem` diz de onde o campo veio (`body`, `query`, `path` ou `file`):

```json
{"detail": "Dados de entrada inválidos.", "codigo": "dados_invalidos",
 "erros": [{"campo": "titulo", "origem": "body", "mensagem": "Campo obrigatório."},
           {"campo": "prioridade", "origem": "body", "mensagem": "Valor inválido. Permitidos: baixa, media, alta."}]}
```

| HTTP | `codigo` | Quando | O que fazer |
|---|---|---|---|
| 400 | `corpo_invalido` | O corpo não é um JSON legível (sintaxe errada ou texto fora de UTF-8) | Corrigir o JSON ou a codificação |
| 400 | `regra_de_negocio` | A entrada tem o formato certo, mas uma regra recusa a operação | Mostrar o `detail` ao usuário |
| 404 | `nao_encontrado` | O registro do caminho da URL não existe | Conferir o id |
| 409 | `conflito` | A operação duplicaria um registro ou apagaria histórico | Mostrar o `detail`; não adianta repetir |
| 422 | `dados_invalidos` | Campo faltando, tipo errado ou valor fora da lista | Corrigir os campos listados em `erros` |
| 502 | `ia_resposta_invalida` | A IA respondeu fora do formato, cortou a resposta ou recusou o pedido | Tentar de novo; persistindo, revisar o escopo |
| 503 | `ia_indisponivel` | A IA não respondeu ou falta a `ANTHROPIC_API_KEY` | Tentar mais tarde ou configurar a credencial |
| 500 | `erro_interno` | Falha inesperada (detalhe só no log do servidor) | Avisar o responsável pela API |

**Id inexistente no corpo** (ex.: um `casos_ids` com id que não existe) é `400`, não `404`: o `404` fica reservado ao registro da URL.

## 6. Dicas para testar pelo terminal no Windows

- **Acentos com `curl`:** no Windows, o texto passado direto em `-d` não chega em UTF-8, e a API recusa o corpo (`400`, `corpo_invalido`). Grave o JSON num arquivo UTF-8 e envie com `--data-binary @arquivo.json`, ou use o Swagger.
- **PowerShell 5.1:** o `Invoke-RestMethod` também não manda UTF-8 por padrão. Envie o corpo em bytes:

  ```powershell
  $corpo = [Text.Encoding]::UTF8.GetBytes('{"nome": "Homologação"}')
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/projetos `
      -ContentType "application/json; charset=utf-8" -Body $corpo
  ```

- **`curl` no PowerShell 5.1:** lá `curl` é apelido do `Invoke-WebRequest`, que tem outra sintaxe. Chame `curl.exe` explicitamente. Os exemplos da seção 3 quebram linha com `\` (bash/Git Bash); no PowerShell, escreva o comando numa linha só ou quebre com `` ` ``.
