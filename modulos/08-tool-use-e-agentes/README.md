# M08 · Tool use e agentes

Dar ferramentas a um modelo e deixá-lo decidir como as usar.

| | |
|---|---|
| Fase | Agentes |
| Duração estimada | 8 h |
| Complexidade | 3/5 |
| Ferramentas | LangGraph, PydanticAI, Claude Agent SDK, E2B ou Docker |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Agente analista de dados

Um agente que recebe um CSV e uma pergunta de negócio, escreve e executa código pandas numa sandbox, corrige os próprios erros e devolve a resposta com um gráfico.

## Objetivos

- Implementar function calling e o ciclo de um agente sem frameworks
- Desenhar ferramentas com descrições e esquemas que o modelo usa bem
- Comparar frameworks de agentes e escolher conforme o problema
- Distinguir workflows determinísticos de agentes autónomos

## Leituras de base

ReAct (Yao et al., 2022); Building Effective Agents (Anthropic, 2024)
