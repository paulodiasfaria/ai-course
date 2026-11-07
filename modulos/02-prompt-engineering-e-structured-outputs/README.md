# M02 · Prompt engineering e structured outputs

Obter respostas previsíveis, validadas e prontas a entrar num DataFrame.

| | |
|---|---|
| Fase | Fundamentos |
| Duração estimada | 6 h |
| Complexidade | 1/5 |
| Ferramentas | SDK da Anthropic e da OpenAI, Pydantic, Instructor, pandas |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Extração de dados de faturas e emails

Transformar 200 emails e faturas em texto livre numa tabela pandas validada (fornecedor, NIF, valor, IVA, data), com uma taxa de acerto medida contra anotações manuais.

## Objetivos

- Escrever prompts de sistema, few-shot e chain-of-thought com intenção clara
- Forçar saídas estruturadas com JSON Schema e Pydantic
- Medir a qualidade de um prompt com um pequeno conjunto de testes em vez de intuição
- Reduzir custo e latência com prompt caching e batching

## Leituras de base

Guias de prompt engineering da Anthropic e da OpenAI; documentação do Instructor
