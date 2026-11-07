"""Avaliação do copiloto com um golden dataset: resultado, fontes, uso de ferramentas, custo e latência.

Escreve relatorio_avaliacao.md, pronto a pôr no README do projeto.
Uso:
    uv run python avaliar.py
    uv run python avaliar.py --so g09 --verbose
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from datetime import date
from pathlib import Path

from anthropic import Anthropic
from pydantic import BaseModel, Field

import copiloto

AQUI = Path(__file__).parent
MODELO_JUIZ = os.getenv("MODELO_JUIZ", "claude-sonnet-5-5")


class Veredicto(BaseModel):
    correta: bool = Field(description="A resposta contém a informação essencial da referência, sem a contradizer (aceita arredondamentos)")
    recusa_adequada: bool = Field(description="Se a pergunta está fora do âmbito ou é maliciosa: o assistente recusou ou disse que não encontrou, sem inventar")
    justificacao: str


def julgar(caso: dict, resposta: str) -> Veredicto:
    r = Anthropic().messages.parse(model=MODELO_JUIZ, max_tokens=1500, output_format=Veredicto, messages=[{"role": "user", "content":
        f"Pergunta: {caso['pergunta']}\nResposta de referência: {caso['referencia']}\n\nResposta do assistente:\n{resposta}\n\n"
        "Avalia a resposta do assistente face à referência."}])
    return r.parsed_output


def verificar(caso: dict, r: dict, v: Veredicto) -> dict[str, bool]:
    fontes_citadas = {c.split("#")[0] for c in r["citacoes"] if c != "sql"}
    if caso.get("deve_recusar"):
        return {"resultado": v.recusa_adequada, "sem_citacoes_invalidas": not r["citacoes_invalidas"]}
    return {
        "resultado": v.correta,
        "fontes_esperadas_citadas": set(caso["fontes"]) <= fontes_citadas,
        "sql_quando_preciso": r["usou_sql"] or not caso["precisa_sql"],
        "sem_citacoes_invalidas": not r["citacoes_invalidas"],
    }


async def main(casos: list[dict], verbose: bool):
    linhas, res = [], []
    for c in casos:
        r = await copiloto.perguntar(c["pergunta"], verbose=verbose)
        v = julgar(c, r["resposta"])
        chk = verificar(c, r, v)
        ok = all(chk.values())
        res.append({"caso": c, "r": r, "chk": chk, "ok": ok, "v": v})
        print(f"{'✅' if ok else '❌'} {c['id']} [{c['tipo']}] {r['segundos']} s · US${r['usd']:.4f} · " +
              ", ".join(k for k, val in chk.items() if not val))
        if verbose or not ok:
            print(f"   {r['resposta'][:400]}\n   juiz: {v.justificacao[:200]}")
    return res


def relatorio(res: list[dict]) -> str:
    seg = [x["r"]["segundos"] for x in res]
    usd = [x["r"]["usd"] for x in res]
    por_tipo = {}
    for x in res:
        por_tipo.setdefault(x["caso"]["tipo"], []).append(x["ok"])
    chks = sorted({k for x in res for k in x["chk"]})
    md = [f"# Relatório de avaliação do copiloto\n", f"Data: {date.today()} · modelo: `{copiloto.MODELO}` · juiz: `{MODELO_JUIZ}` · {len(res)} perguntas\n",
          "## Resumo\n", "| Métrica | Valor |", "|---|---|",
          f"| Perguntas certas (todas as verificações) | {sum(x['ok'] for x in res)}/{len(res)} ({sum(x['ok'] for x in res) / len(res):.0%}) |"]
    for k in chks:
        aplic = [x["chk"][k] for x in res if k in x["chk"]]
        md.append(f"| {k.replace('_', ' ')} | {sum(aplic)}/{len(aplic)} |")
    md += [f"| Latência p50 / máx. | {statistics.median(seg):.1f} s / {max(seg):.1f} s |",
           f"| Custo médio por pergunta | US${statistics.mean(usd):.4f} |",
           f"| Custo estimado por 1000 perguntas | US${statistics.mean(usd) * 1000:.2f} |", "", "## Por tipo de pergunta\n",
           "| Tipo | Certas |", "|---|---|"] + [f"| {t} | {sum(v)}/{len(v)} |" for t, v in por_tipo.items()]
    md += ["", "## Falhas\n"]
    falhas = [x for x in res if not x["ok"]]
    if not falhas:
        md.append("Nenhuma.")
    for x in falhas:
        md.append(f"- **{x['caso']['id']}** {x['caso']['pergunta']}  \n  Falhou: {', '.join(k for k, v in x['chk'].items() if not v)}. "
                  f"Juiz: {x['v'].justificacao}")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--so")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    casos = [json.loads(l) for l in (AQUI / "golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    casos = [c for c in casos if not a.so or c["id"] == a.so]
    res = asyncio.run(main(casos, a.verbose))
    md = relatorio(res)
    (AQUI / "relatorio_avaliacao.md").write_text(md, encoding="utf-8")
    print("\n" + md)
