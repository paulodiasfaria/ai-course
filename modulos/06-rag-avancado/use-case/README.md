# Use case: assistente de legislação portuguesa

Assistente sobre legislação laboral e fiscal portuguesa que cita o artigo exato, junta artigos relacionados e mostra o ganho de cada técnica de RAG avançado em relação ao RAG simples do módulo 5.

| Ficheiro | O que faz |
|---|---|
| [`legislacao.py`](legislacao.py) | Parsing de PDFs em artigos e números, pesquisa híbrida, reranking com `bge-reranker-v2-m3`, expansão por referências e geração com citações |
| [`perguntas_teste.jsonl`](perguntas_teste.jsonl) | 13 perguntas em linguagem comum com o artigo de referência |
| [`legislacao/`](legislacao/) | Pasta para os PDFs do Diário da República (não incluídos) |

```bash
uv run python legislacao.py indexar
uv run python legislacao.py perguntar "Como são pagas as horas extraordinárias?"
uv run python legislacao.py avaliar
```

Confirma os artigos de referência em `perguntas_teste.jsonl` na versão que descarregaste: a numeração pode mudar com alterações legislativas.

**Aviso:** é um projeto de aprendizagem. As respostas não substituem a consulta da lei em vigor nem aconselhamento jurídico.
