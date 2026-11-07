"""Painel simples (Gradio) com as métricas que a API grava em SQLite. Atualiza a cada 5 segundos.

Uso:
    uv run python painel.py            # http://localhost:7860
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import gradio as gr
import pandas as pd

DB = Path(os.getenv("METRICAS_DB", Path(__file__).parent / "metricas.db"))
CUSTO_GPU_HORA = float(os.getenv("CUSTO_GPU_HORA", "0.80"))


def ler(minutos: int) -> pd.DataFrame:
    if not DB.exists():
        return pd.DataFrame(columns=["ts", "origem", "latencia_ms", "valido", "categoria", "usd_api"])
    with sqlite3.connect(DB) as con:
        df = pd.read_sql("SELECT * FROM pedidos WHERE ts > ?", con, params=(time.time() - minutos * 60,))
    df["hora"] = pd.to_datetime(df["ts"], unit="s")
    return df


def atualizar(minutos):
    df = ler(int(minutos))
    if df.empty:
        vazio = pd.DataFrame({"hora": [], "valor": []})
        return "Ainda não há pedidos. Corre o carga.py ou faz pedidos à API.", vazio, vazio, pd.DataFrame({"categoria": [], "pedidos": []})
    por_min = df.set_index("hora").resample("10s")
    lat = por_min["latencia_ms"].quantile(0.95).rename("valor").reset_index().dropna()
    rps = (por_min.size() / 10).rename("valor").reset_index()
    dur = max(1.0, df["ts"].max() - df["ts"].min())
    ritmo = len(df) / dur
    usd_gpu_1000 = CUSTO_GPU_HORA / max(ritmo * 3600, 1) * 1000
    usd_api_1000 = df["usd_api"].sum() / len(df) * 1000
    resumo = (f"**{len(df)} pedidos** · {ritmo:.1f} ped/s · p50 {df.latencia_ms.median():.0f} ms · p95 {df.latencia_ms.quantile(.95):.0f} ms  \n"
              f"cache {(df.origem == 'cache').mean():.0%} · fallback {(df.origem == 'fallback').mean():.1%} · inválidos {(1 - df.valido.mean()):.2%}  \n"
              f"custo por 1000 pedidos: GPU US${usd_gpu_1000:.3f} + API de fallback US${usd_api_1000:.3f}")
    cats = df["categoria"].value_counts().rename_axis("categoria").reset_index(name="pedidos")
    return resumo, lat, rps, cats


with gr.Blocks(title="Classificador · métricas") as demo:
    gr.Markdown("## Classificador de reclamações · produção")
    minutos = gr.Slider(5, 24 * 60, value=60, step=5, label="Janela (minutos)")
    resumo = gr.Markdown()
    with gr.Row():
        g_lat = gr.LinePlot(x="hora", y="valor", title="Latência p95 (ms)")
        g_rps = gr.LinePlot(x="hora", y="valor", title="Pedidos por segundo")
    g_cat = gr.BarPlot(x="categoria", y="pedidos", title="Categorias previstas (drift)")
    saidas = [resumo, g_lat, g_rps, g_cat]
    gr.Timer(5).tick(atualizar, minutos, saidas)
    minutos.change(atualizar, minutos, saidas)
    demo.load(atualizar, minutos, saidas)

if __name__ == "__main__":
    demo.launch()
