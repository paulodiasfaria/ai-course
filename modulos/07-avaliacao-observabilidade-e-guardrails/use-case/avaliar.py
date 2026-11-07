"""Laboratório de avaliação de um assistente RAG.

Avalia qualquer sistema que exponha `responder(pergunta) -> {"resposta": str, "contextos": [str]}`.
Por omissão usa o assistente interno do módulo 5 (funciona sem preparação);
com --sistema legislacao usa o assistente jurídico do módulo 6 (precisa dos PDFs).

Uso:
    uv run python avaliar.py --dataset dataset.jsonl --saida resultados.csv
    uv run python avaliar.py --sistema legislacao --dataset dataset_legislacao.jsonl
    uv run python avaliar.py --ataques ataques.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from juiz import context_recall, correcao, faithfulness

MODULOS = Path(__file__).resolve().parents[2]


def carregar_sistema(nome: str):
    if nome == "interno":
        sys.path.insert(0, str(MODULOS / "05-rag-fundamental" / "use-case"))
        from rag import RAG
        rag = RAG(db=None)
        rag.indexar(MODULOS / "05-rag-fundamental" / "use-case" / "docs")

        def responder(p):
            recs = rag.recuperar(p)
            r = rag.responder(p)
            return {"resposta": r["resposta"], "contextos": [c.texto for c, _ in recs]}
        return responder
    if nome == "legislacao":
        sys.path.insert(0, str(MODULOS / "06-rag-avancado" / "use-case"))
        from legislacao import Assistente
        a = Assistente()

        def responder(p):
            arts = a.recuperar(p)
            r = a.responder(p)
            return {"resposta": r["resposta"], "contextos": [x.cabecalho() + "\n" + x.texto[:4000] for x in arts]}
        return responder
    raise ValueError(nome)


def avaliar_caso(responder, caso: dict) -> dict:
    t0 = time.time()
    out = responder(caso["pergunta"])
    lat = time.time() - t0
    f, afirm = faithfulness(out["resposta"], out["contextos"])
    v = correcao(caso["pergunta"], out["resposta"], caso["referencia"])
    sem_resp = caso.get("sem_resposta", False)
    return {
        **caso,
        "resposta": out["resposta"],
        "latencia_s": round(lat, 2),
        "faithfulness": round(f, 3),
        "afirmacoes_nao_suportadas": [a.texto for a in afirm if not a.suportada],
        "correta": v.correta,
        "justificacao_juiz": v.raciocinio,
        "context_recall": None if sem_resp else round(context_recall(caso["referencia"], out["contextos"]), 3),
        "recusou": any(s in out["resposta"] for s in ("Não encontrei", "não respondem")),
    }


def resumo(df: pd.DataFrame) -> pd.Series:
    r = {
        "casos": len(df),
        "acerto": df.correta.mean(),
        "faithfulness": df.faithfulness.mean(),
        "context_recall": df.context_recall.dropna().mean(),
        "latencia_p50_s": df.latencia_s.median(),
        "latencia_p95_s": df.latencia_s.quantile(0.95),
    }
    if "sem_resposta" in df:
        r["recusas_corretas"] = df[df.sem_resposta.fillna(False).astype(bool)].recusou.mean()
    return pd.Series(r).round(3)


def correr_ataques(responder, ficheiro: str) -> pd.DataFrame:
    linhas = []
    for l in open(ficheiro, encoding="utf-8"):
        a = json.loads(l)
        resp = responder(a["ataque"])["resposta"]
        falhou = any(s.lower() in resp.lower() for s in a["sinais_de_sucesso"])
        linhas.append({"tipo": a["tipo"], "ataque": a["ataque"][:80], "ataque_teve_sucesso": falhou, "resposta": resp})
    df = pd.DataFrame(linhas)
    print(df.groupby("tipo").ataque_teve_sucesso.mean().rename("taxa de sucesso dos ataques"))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sistema", default="interno", choices=["interno", "legislacao"])
    ap.add_argument("--dataset", default="dataset.jsonl")
    ap.add_argument("--ataques")
    ap.add_argument("--saida", default="resultados.csv")
    ap.add_argument("--paralelo", type=int, default=3)
    a = ap.parse_args()
    responder = carregar_sistema(a.sistema)
    if a.ataques:
        correr_ataques(responder, a.ataques).to_csv("ataques_resultados.csv", index=False)
        return
    casos = [json.loads(l) for l in open(a.dataset, encoding="utf-8")]
    with ThreadPoolExecutor(a.paralelo) as ex:
        res = list(ex.map(lambda c: avaliar_caso(responder, c), casos))
    df = pd.DataFrame(res)
    df.to_csv(a.saida, index=False)
    print(resumo(df).to_string())
    print(f"\nDetalhe em {a.saida}. Lê primeiro os casos com correta=False e as afirmações não suportadas.")


if __name__ == "__main__":
    main()
