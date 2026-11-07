"""Explorador de tokens e custos.

Compara a contagem de tokens de um texto em vários tokenizadores e estima o custo
de o enviar a diferentes modelos.

Uso:
    uv run python explorador_tokens.py ficheiro.txt [--saida 500] [--pedidos 1000]

Os preços (USD por milhão de tokens) mudam com frequência. Atualiza a tabela PRECOS
com os valores atuais das páginas de cada fornecedor antes de tomar decisões.
"""
import argparse
import sys

import pandas as pd
import tiktoken
from transformers import AutoTokenizer

USD_EUR = 0.92

# modelo: (tokenizador usado para contar, preço entrada, preço saída)
# Para modelos fechados sem tokenizador público usamos o200k_base como aproximação.
PRECOS = {
    "Claude Sonnet": ("o200k_base", 3.00, 15.00),
    "Claude Haiku": ("o200k_base", 1.00, 5.00),
    "GPT (gama média)": ("o200k_base", 2.50, 10.00),
    "Qwen2.5-7B (self-hosted, custo de GPU estimado)": ("Qwen/Qwen2.5-7B-Instruct", 0.20, 0.20),
    "Llama 3.1 8B (fornecedor de inferência)": ("unsloth/Meta-Llama-3.1-8B-Instruct", 0.18, 0.18),
}

_cache = {}


def tokenizador(nome):
    if nome not in _cache:
        if nome in tiktoken.list_encoding_names():
            enc = tiktoken.get_encoding(nome)
            _cache[nome] = lambda s, e=enc: len(e.encode(s))
        else:
            tok = AutoTokenizer.from_pretrained(nome)
            _cache[nome] = lambda s, t=tok: len(t.encode(s, add_special_tokens=False))
    return _cache[nome]


def analisar(texto, tokens_saida, pedidos):
    palavras = len(texto.split())
    linhas = []
    for modelo, (tok, p_in, p_out) in PRECOS.items():
        n = tokenizador(tok)(texto)
        custo = (n * p_in + tokens_saida * p_out) / 1e6 * USD_EUR
        linhas.append({
            "modelo": modelo,
            "tokens": n,
            "tokens/palavra": round(n / max(palavras, 1), 2),
            "custo/pedido (€)": round(custo, 5),
            f"custo {pedidos} pedidos (€)": round(custo * pedidos, 2),
        })
    return pd.DataFrame(linhas).sort_values("custo/pedido (€)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ficheiro", nargs="?", help="ficheiro de texto (omite para ler do stdin)")
    ap.add_argument("--saida", type=int, default=300, help="tokens de resposta esperados por pedido")
    ap.add_argument("--pedidos", type=int, default=1000, help="número de pedidos para a projeção")
    a = ap.parse_args()
    texto = open(a.ficheiro, encoding="utf-8").read() if a.ficheiro else sys.stdin.read()
    print(f"{len(texto.split())} palavras, {len(texto)} caracteres\n")
    print(analisar(texto, a.saida, a.pedidos).to_string(index=False))


if __name__ == "__main__":
    main()
