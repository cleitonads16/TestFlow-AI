---
name: estrutura-projeto
description: Regras de organização de arquivos e diretórios do projeto de PDI "Sistema de Gestão de Tarefas e Projetos (To-Do Avançado)" (pasta todo-avancado). Use sempre que for criar, salvar ou mover qualquer arquivo dentro desta pasta ou de suas subpastas — código Python do sistema core, a API, configuração Docker, documentação (incluindo documentos gerados com /word-combio), scripts ou testes. Garante que nada seja criado fora da raiz do projeto e que novos tipos de conteúdo ganhem subdiretório próprio em kebab-case, em vez de arquivos soltos na raiz.
---

# Estrutura do projeto todo-avancado

Este projeto é o PDI pessoal do usuário: um sistema de gestão de tarefas e
projetos em Python, evoluindo em três fases — sistema core, API sobre esse
core, e containerização com Docker + documentação — com apresentação da API
funcionando e da documentação em outubro/2026.

## Raiz do projeto

Tudo relacionado a este projeto vive dentro desta pasta (a que contém este
`.claude/skills/estrutura-projeto/`). Nunca crie arquivos ou pastas deste
projeto em diretórios irmãos ou em qualquer outro lugar de
`planejamento-2026`. Se precisar decidir "isso vai aqui ou em outro lugar?",
a resposta é: aqui dentro.

## Crescimento por subdiretório

Não deixe arquivos soltos se acumulando na raiz. Quando aparecer um tipo de
conteúdo novo, crie um subdiretório dedicado para ele antes de salvar o
arquivo. Exemplos de divisões que tendem a surgir ao longo das três fases:

- `docs/` — documentos de escopo, apresentações, documentação de uso da API
- `sistema-core/` — lógica de negócio em Python (fase 1)
- `api/` — camada de API sobre o core (fase 2)
- `docker/` — Dockerfile, docker-compose e arquivos de configuração de containers (fase 3)
- `testes/` — testes automatizados

Estes são exemplos, não uma lista fechada — crie o subdiretório que o
conteúdo realmente pedir, mesmo que não esteja nesta lista.

## Convenção de nomes

Nomes de diretórios seguem o padrão do usuário: kebab-case (separado por
hífen), curtos e intuitivos, em português quando fizer sentido. Antes de
criar um diretório novo, verifique se já existe um equivalente para não
duplicar (por exemplo, não crie `documentacao/` se `docs/` já existe).

## Por quê

Este projeto vai crescer em fases distintas ao longo de vários meses até a
apresentação de outubro. Manter tudo contido e organizado por tipo de
conteúdo desde o início evita que a raiz vire uma bagunça de arquivos soltos
e facilita retomar o trabalho em cada fase sem precisar reorganizar depois.
