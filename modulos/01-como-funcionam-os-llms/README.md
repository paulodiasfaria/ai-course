# M01 · Como funcionam os LLMs

Da tokenização à geração: o que acontece entre o prompt e a resposta.

| | |
|---|---|
| Fase | Fundamentos |
| Duração estimada | 8 h |
| Complexidade | 1/5 |
| Ferramentas | PyTorch, transformers, tiktoken, tokenizers |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Mini-GPT e explorador de tokens

Treinar um GPT de caracteres com textos de autores portugueses em PyTorch e construir uma ferramenta que compara a tokenização e o custo do mesmo texto em vários modelos.

## Objetivos

- Explicar a arquitetura transformer e o mecanismo de atenção sem recorrer a analogias vagas
- Perceber o ciclo de vida de um modelo: pré-treino, instruction tuning e alinhamento (RLHF, DPO)
- Controlar a geração com temperatura, top-p e outros parâmetros de amostragem
- Estimar custos e limites a partir de tokens e da janela de contexto

## Leituras de base

Attention Is All You Need (Vaswani et al., 2017); nanoGPT e a série «Zero to Hero» de Andrej Karpathy
