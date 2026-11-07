# Use case: equipa de pesquisa de mercado

Um sistema multi-agente em LangGraph que responde a perguntas de negócio da Loja Lusa com pesquisa na web e nos dados internos de vendas, e entrega um relatório com citações.

```
planear ─┬─> investigar (web) ──┐
         ├─> investigar (web) ──┼─> rever ──(falta fonte)──> investigar
         └─> investigar (SQL) ──┘     │
                                      └─> aprovar (pessoa) ─> escrever ─> relatório
```

| Ficheiro | O que faz |
|---|---|
| [`equipa.py`](equipa.py) | O grafo: planeador (Pydantic), investigadores em paralelo com `Send` (pesquisa web do Claude ou SQL na base do módulo 9), revisor com verificações determinísticas e do modelo, aprovação humana com `interrupt`, redator com citações; checkpoints em SQLite |
| [`avaliar.py`](avaliar.py) | Avaliação da trajetória e do resultado com k repetições por pergunta (taxa de sucesso e pass^k), juiz opcional |
| [`perguntas.jsonl`](perguntas.jsonl) | Perguntas de teste com as fontes exigidas e o orçamento máximo |

```bash
uv sync --extra agentes
uv run python equipa.py "Vale a pena a Loja Lusa abrir uma loja em Coimbra em 2026?"
uv run python equipa.py --retomar <thread_id>     # depois de interromper (Ctrl+C) ou fechar o terminal
uv run python avaliar.py --k 2
```

Os relatórios ficam em `relatorios/` e os checkpoints em `checkpoints.db`. A base de vendas vem do módulo 9 e é criada automaticamente se não existir.

**Custos:** uma pergunta típica faz 8 a 15 chamadas ao modelo e 8 a 20 pesquisas web (cada pesquisa custa US$0,01 além dos tokens). O script mostra o custo no fim; a avaliação com `--k 2` sobre as 4 perguntas custa alguns dólares.

**Requisitos:** `ANTHROPIC_API_KEY` com a pesquisa web ativa na organização (Console → Settings → Privacy/Web search).
