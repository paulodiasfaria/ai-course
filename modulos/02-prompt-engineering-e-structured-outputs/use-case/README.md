# Use case: extração de dados de faturas e emails

Transforma faturas e emails em texto livre numa tabela pandas validada (fornecedor, NIF, data, total, taxa de IVA) e mede a taxa de acerto contra a resposta certa.

| Ficheiro | O que faz |
|---|---|
| [`gerar_dados.py`](gerar_dados.py) | Gera documentos sintéticos com estilos variados e a resposta certa (NIFs com dígito de controlo válido) |
| [`extrator.py`](extrator.py) | Extrai com Instructor + Pydantic, em paralelo, e calcula o acerto por campo |

```bash
uv run python gerar_dados.py --n 200
uv run python extrator.py dados.jsonl --modelo claude-haiku-5-5 --saida resultados.csv
```

**Objetivo:** 99% de acerto em todos os campos. Analisa os erros em `resultados.csv` e itera no prompt e nas descrições dos campos.
