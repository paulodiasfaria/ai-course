# Use case: laboratório de avaliação

Mede a qualidade de um assistente RAG com métricas reprodutíveis, encontra as falhas mais frequentes e testa a robustez a ataques. Funciona com o assistente interno do módulo 5 (sem preparação) e com o assistente jurídico do módulo 6.

| Ficheiro | O que faz |
|---|---|
| [`juiz.py`](juiz.py) | Faithfulness (afirmação a afirmação), correção face à referência, context recall e kappa de Cohen |
| [`avaliar.py`](avaliar.py) | Corre o dataset contra o sistema escolhido, em paralelo, e escreve `resultados.csv` |
| [`dataset.jsonl`](dataset.jsonl) | 20 casos com resposta de referência, incluindo 2 sem resposta nos documentos |
| [`ataques.jsonl`](ataques.jsonl) | 8 ataques: injeção, fora do âmbito, extração de dados, alucinação induzida, autoridade falsa |
| [`test_qualidade.py`](test_qualidade.py) | Testes pytest com limites mínimos, para CI |

```bash
uv run python avaliar.py --dataset dataset.jsonl
uv run python avaliar.py --ataques ataques.jsonl
uv run pytest test_qualidade.py
```

A deteção de sucesso dos ataques usa palavras-chave e serve só como primeira triagem: revê os resultados à mão ou substitui por um juiz LLM.

## Resultados

| Versão | Acerto | Faithfulness | Context recall | Latência p95 |
|---|---|---|---|---|
| M05 base | | | | |
| M05 + guardrail de entrada | | | | |
