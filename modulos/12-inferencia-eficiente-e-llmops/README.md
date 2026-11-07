# M12 · Inferência eficiente e LLMOps

Servir modelos de forma rápida, barata e monitorizada.

| | |
|---|---|
| Fase | Modelos e produção |
| Duração estimada | 8 h |
| Complexidade | 4/5 |
| Ferramentas | vLLM, llama.cpp, FastAPI, Docker, LiteLLM |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: API de produção para o modelo afinado

Quantizar o modelo do módulo 11, servi-lo com vLLM atrás de uma API FastAPI em Docker, testar carga e construir um painel com latência, custo por pedido e qualidade.

## Objetivos

- Quantizar modelos e medir o impacto na qualidade
- Servir um modelo com vLLM e expô-lo numa API
- Containerizar e fazer deploy de uma aplicação LLM
- Monitorizar custos, latência e qualidade em produção

## Leituras de base

Efficient Memory Management for LLM Serving with PagedAttention (Kwon et al., 2023)
