# Use case: mini-GPT e explorador de tokens

1. **Mini-GPT de caracteres**: treinado na secção 3 do notebook [`pratica.ipynb`](../pratica.ipynb) com *Os Lusíadas*.
2. **Explorador de tokens**: [`explorador_tokens.py`](explorador_tokens.py) compara a contagem de tokens e o custo de um texto em vários modelos.

```bash
uv run python explorador_tokens.py contrato.txt --saida 500 --pedidos 10000
```

Atualiza a tabela `PRECOS` no início do script com os preços atuais antes de usar os números para decisões.
