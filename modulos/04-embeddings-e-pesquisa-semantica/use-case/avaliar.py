"""Avalia BM25, vetorial e híbrida no XL-Sum português (título -> artigo).

Uso:
    uv run python avaliar.py --n 5000 --perguntas 1000 [--modelo BAAI/bge-m3]
"""
import argparse
import time

import numpy as np
import pandas as pd
from datasets import load_dataset

from motor import Motor


def metricas(resultados, alvos, ks=(1, 5, 10)):
    r = {f"recall@{k}": np.mean([a in res[:k] for res, a in zip(resultados, alvos)]) for k in ks}
    r["MRR@10"] = np.mean([1 / (res[:10].index(a) + 1) if a in res[:10] else 0 for res, a in zip(resultados, alvos)])
    return {k: round(float(v), 3) for k, v in r.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--perguntas", type=int, default=1000)
    ap.add_argument("--modelo", default="intfloat/multilingual-e5-base")
    a = ap.parse_args()

    ds = load_dataset("csebuetnlp/xlsum", "portuguese", split="test").select(range(a.n)).to_pandas()
    textos = ds.text.str.slice(0, 2000).tolist()
    m = Motor("xlsum_pt", path=None, modelo=a.modelo)
    t0 = time.time()
    m.indexar(textos, [{"titulo": t} for t in ds.title])
    print(f"Indexação: {time.time() - t0:.0f}s")

    linhas = []
    for modo in ("bm25", "vetorial", "hibrida"):
        t0 = time.time()
        res = [[r["id"] for r in m.pesquisar(q, modo=modo, k=10)] for q in ds.title[:a.perguntas]]
        linhas.append({"modo": modo, **metricas(res, list(range(a.perguntas))),
                       "ms/pergunta": round((time.time() - t0) / a.perguntas * 1000, 1)})
    tabela = pd.DataFrame(linhas).set_index("modo")
    print(f"\nModelo: {a.modelo}\n{tabela.to_string()}")
    tabela.to_csv(f"resultados_{a.modelo.split('/')[-1]}.csv")


if __name__ == "__main__":
    main()
