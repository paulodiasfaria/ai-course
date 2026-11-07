# M04 · Embeddings e pesquisa semântica

Representar significado como vetores e pesquisar por semelhança.

| | |
|---|---|
| Fase | RAG |
| Duração estimada | 6 h |
| Complexidade | 2/5 |
| Ferramentas | sentence-transformers, FAISS, Qdrant, rank_bm25 |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Motor de pesquisa semântica de notícias

Indexar alguns milhares de notícias em português e comparar BM25, pesquisa vetorial e híbrida com um conjunto de perguntas de teste e métricas recall@k.

## Objetivos

- Gerar embeddings e escolher modelos adequados ao português (MTEB)
- Comparar pesquisa lexical (BM25) com pesquisa vetorial
- Perceber índices ANN como HNSW e IVF e os seus compromissos
- Usar uma base de dados vetorial com filtros de metadados

## Leituras de base

Sentence-BERT (Reimers e Gurevych, 2019); leaderboard MTEB
