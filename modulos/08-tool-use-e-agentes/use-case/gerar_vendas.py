"""Gera dados de vendas sintéticos da Loja Lusa (2024-2025) com padrões conhecidos.

Padrões inseridos de propósito, para verificares se o agente os encontra:
- sazonalidade forte em novembro e dezembro;
- a categoria "Cozinha" cresce ~25% em 2025, "Têxteis" cai ~5%;
- a loja online cresce mais do que as físicas;
- 0,5% de valores em falta e alguns valores negativos (devoluções).
"""
from pathlib import Path

import numpy as np
import pandas as pd


def gerar(n=50_000, seed=42):
    rng = np.random.default_rng(seed)
    datas = pd.to_datetime(rng.integers(pd.Timestamp("2024-01-01").value // 10**9, pd.Timestamp("2025-12-31").value // 10**9, n), unit="s").normalize()
    lojas = rng.choice(["Online", "Porto", "Lisboa", "Braga", "Faro"], n, p=[0.4, 0.2, 0.2, 0.1, 0.1])
    cats = rng.choice(["Têxteis", "Cozinha", "Decoração", "Banho", "Iluminação"], n, p=[0.3, 0.25, 0.2, 0.15, 0.1])
    base = {"Têxteis": 35, "Cozinha": 45, "Decoração": 28, "Banho": 22, "Iluminação": 60}
    valor = np.array([base[c] for c in cats]) * rng.lognormal(0, 0.5, n)
    mes = datas.month.values
    ano = datas.year.values
    valor *= np.where(np.isin(mes, [11, 12]), 1.6, 1.0)
    valor *= np.where((ano == 2025) & (cats == "Cozinha"), 1.25, 1.0)
    valor *= np.where((ano == 2025) & (cats == "Têxteis"), 0.95, 1.0)
    valor *= np.where((ano == 2025) & (lojas == "Online"), 1.15, 1.0)
    devol = rng.random(n) < 0.03
    valor = np.where(devol, -valor, valor).round(2)
    df = pd.DataFrame({"data": datas.strftime("%Y-%m-%d"), "loja": lojas, "categoria": cats,
                       "quantidade": rng.integers(1, 5, n), "valor_eur": valor})
    df.loc[rng.random(n) < 0.005, "valor_eur"] = np.nan
    return df.sort_values("data").reset_index(drop=True)


if __name__ == "__main__":
    Path("dados").mkdir(exist_ok=True)
    df = gerar()
    df.to_csv("dados/vendas.csv", index=False)
    print(df.head(), f"\n{len(df)} linhas em dados/vendas.csv")
