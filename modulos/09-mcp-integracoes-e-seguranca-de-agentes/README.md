# M09 · MCP, integrações e segurança de agentes

Ligar agentes a sistemas reais através de protocolos abertos.

| | |
|---|---|
| Fase | Agentes |
| Duração estimada | 6 h |
| Complexidade | 4/5 |
| Ferramentas | SDK Python do MCP (FastMCP), Playwright, SQLite ou Postgres |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Servidor MCP para uma base de dados de vendas

Um servidor MCP que dá acesso só de leitura a uma base de dados de vendas, usado por um agente que responde a perguntas em linguagem natural e pede confirmação antes de qualquer ação sensível.

## Objetivos

- Construir um servidor e um cliente Model Context Protocol (MCP)
- Expor bases de dados e APIs internas de forma controlada
- Perceber agentes de browser e computer use e os seus limites
- Proteger agentes contra prompt injection indireta e ações destrutivas

## Leituras de base

Especificação do Model Context Protocol (modelcontextprotocol.io)
