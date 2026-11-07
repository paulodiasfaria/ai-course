# Use case: assistente de documentação interna

Assistente que responde a perguntas de colaboradores da Loja Lusa (empresa fictícia) com base nos documentos internos, cita a fonte de cada afirmação e recusa responder quando a informação não existe.

| Ficheiro | O que faz |
|---|---|
| [`docs/`](docs/) | Manual do colaborador, política de despesas, política de TI e manual de um robô aspirador |
| [`rag.py`](rag.py) | Pipeline completo: ingestão (Markdown, ou PDF e Word via Docling), chunking por secção, Qdrant, geração com citações |
| [`perguntas_teste.jsonl`](perguntas_teste.jsonl) | 20 perguntas com a fonte e a resposta esperadas, incluindo 2 sem resposta nos documentos |

```bash
uv run python rag.py indexar docs/
uv run python rag.py perguntar "Quem aprova uma despesa de 800 euros?"
uv run python rag.py avaliar perguntas_teste.jsonl
```

A avaliação mede o recall da pesquisa, as recusas corretas e indevidas e se as respostas têm citações. No módulo 6 este assistente serve de linha de base para medir o ganho das técnicas avançadas.
