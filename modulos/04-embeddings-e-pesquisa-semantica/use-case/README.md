# Use case: motor de pesquisa semântica de notícias

Indexa milhares de notícias em português e compara BM25, pesquisa vetorial e híbrida com recall@k e MRR.

| Ficheiro | O que faz |
|---|---|
| [`motor.py`](motor.py) | Classe `Motor`: Qdrant (persistente ou em memória), BM25 e fusão RRF. Reutilizada nos módulos 5 e 6. |
| [`avaliar.py`](avaliar.py) | Avaliação no XL-Sum português: o título de cada notícia é a pergunta e o artigo é a resposta. |

```bash
uv run python avaliar.py --n 5000 --perguntas 1000
uv run python avaliar.py --modelo BAAI/bge-m3
```

## Resultados

Preenche com os teus números:

| Modelo | Modo | recall@5 | MRR@10 | ms/pergunta |
|---|---|---|---|---|
| multilingual-e5-base | bm25 | | | |
| multilingual-e5-base | vetorial | | | |
| multilingual-e5-base | hibrida | | | |
