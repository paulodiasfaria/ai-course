# M07 · Avaliação, observabilidade e guardrails

Medir a qualidade de um sistema com LLMs e saber quando ele falha.

| | |
|---|---|
| Fase | RAG |
| Duração estimada | 8 h |
| Complexidade | 4/5 |
| Ferramentas | RAGAS, DeepEval, Langfuse, Arize Phoenix |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Laboratório de avaliação do assistente jurídico

Criar 100 perguntas de teste para o assistente do módulo 6, medir cada versão do pipeline, encontrar as falhas mais frequentes com tracing e corrigi-las com números a provar a melhoria.

## Objetivos

- Construir um golden dataset e avaliar um sistema de forma reprodutível
- Usar LLM-as-judge com critérios claros e verificar o próprio juiz
- Instrumentar uma aplicação com tracing e analisar custos e latência
- Aplicar guardrails contra prompt injection, fugas de dados e alucinações

## Leituras de base

RAGAS (Es et al., 2023); Judging LLM-as-a-Judge (Zheng et al., 2023); OWASP Top 10 for LLM Applications
