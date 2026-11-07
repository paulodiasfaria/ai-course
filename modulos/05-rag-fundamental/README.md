# M05 · RAG fundamental

O pipeline clássico de Retrieval-Augmented Generation, construído do zero.

| | |
|---|---|
| Fase | RAG |
| Duração estimada | 8 h |
| Complexidade | 3/5 |
| Ferramentas | Docling, Qdrant, LlamaIndex, LangChain |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Assistente de documentação interna

Um assistente que responde a perguntas sobre um conjunto de manuais em PDF de uma empresa fictícia, indica a página de onde tirou cada afirmação e recusa responder quando a informação não existe.

## Objetivos

- Construir um pipeline RAG completo sem frameworks, para perceber cada peça
- Escolher estratégias de chunking adequadas ao tipo de documento
- Gerar respostas fundamentadas com citações das fontes
- Reconstruir o mesmo pipeline com LlamaIndex ou LangChain e comparar

## Leituras de base

Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)
