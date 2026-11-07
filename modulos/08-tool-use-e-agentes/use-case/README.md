# Use case: agente analista de dados

Um agente que recebe um CSV e uma pergunta de negócio, escreve e executa código pandas numa sandbox, corrige os próprios erros e responde com números concretos e um gráfico.

| Ficheiro | O que faz |
|---|---|
| [`agente_dados.py`](agente_dados.py) | Ciclo do agente (sem frameworks) com a ferramenta `executar_python` |
| [`sandbox.py`](sandbox.py) | Execução em subprocesso com timeout e limites de memória e CPU, com estado entre chamadas |
| [`gerar_vendas.py`](gerar_vendas.py) | 50 000 vendas sintéticas com padrões conhecidos para verificar as conclusões do agente |

```bash
uv run python gerar_vendas.py
uv run python agente_dados.py dados/vendas.csv "Que categoria cresceu mais em 2025 face a 2024?"
```

**Segurança:** a sandbox protege contra erros, não contra código malicioso. Antes de expor o agente a terceiros, corre o código num contentor sem rede ou numa sandbox gerida (E2B, Modal).
