# M10 · Sistemas multi-agente

Coordenar vários agentes especializados numa tarefa longa.

| | |
|---|---|
| Fase | Agentes |
| Duração estimada | 10 h |
| Complexidade | 5/5 |
| Ferramentas | LangGraph, CrewAI, OpenAI Agents SDK, Langfuse |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Equipa de pesquisa de mercado

Um sistema em que um orquestrador divide uma pergunta de mercado em subtarefas, agentes pesquisam na web e em dados internos em paralelo, um revisor verifica as fontes e o resultado é um relatório com citações.

## Objetivos

- Desenhar arquiteturas orquestrador-trabalhadores, supervisor e handoffs
- Incluir aprovação humana e retomar execuções interrompidas
- Avaliar agentes pela trajetória e pelo resultado
- Controlar custos e falhas em execuções longas

## Leituras de base

How we built our multi-agent research system (Anthropic, 2025); documentação do LangGraph
