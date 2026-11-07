"""Teste de carga: débito, latência e qualidade a vários níveis de concorrência.

Usa o conjunto de teste do módulo 11 (com rótulos), por isso mede também se a qualidade se mantém sob carga.
Uso:
    uv run python carga.py --url http://localhost:8080 --nome w4a16
    uv run python carga.py --comparar
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

import httpx

AQUI = Path(__file__).parent
M11 = AQUI.parent.parent / "11-fine-tuning-e-alinhamento" / "use-case"
sys.path.insert(0, str(M11))
from comum import CAMPOS, normalizar  # noqa: E402


async def um_nivel(url: str, chave: str, casos: list[dict], concorrencia: int, n: int) -> dict:
    sem = asyncio.Semaphore(concorrencia)
    lat, erros, certos = [], 0, 0
    # textos únicos com um sufixo aleatório, para a cache não falsear o teste
    amostra = [{**c, "texto": c["texto"] + f" (ref {random.randint(10**6, 10**7)})"} for c in random.choices(casos, k=n)]

    async with httpx.AsyncClient(timeout=60) as cli:
        async def um(c):
            nonlocal erros, certos
            async with sem:
                t0 = time.perf_counter()
                try:
                    r = await cli.post(f"{url}/classificar", json={"texto": c["texto"]}, headers={"X-API-Key": chave})
                    r.raise_for_status()
                    j = r.json()
                    lat.append((time.perf_counter() - t0) * 1000)
                    certos += all(normalizar(j[k]) == normalizar(c["rotulo"][k]) for k in CAMPOS if k != "numero_encomenda")
                except httpx.HTTPError:
                    erros += 1
        t0 = time.perf_counter()
        await asyncio.gather(*(um(c) for c in amostra))
        dur = time.perf_counter() - t0
    lat.sort()
    q = lambda p: round(lat[min(len(lat) - 1, int(p * len(lat)))]) if lat else None
    return {"concorrencia": concorrencia, "pedidos": n, "pedidos_por_seg": round(n / dur, 1), "p50_ms": q(0.5), "p95_ms": q(0.95),
            "erros": erros, "exatidao": round(certos / max(1, n - erros), 3)}


def comparar():
    for f in sorted(AQUI.glob("resultados/carga_*.json")):
        d = json.loads(f.read_text())
        print(f"\n{d['nome']}")
        print(f"{'conc.':>6}{'ped/s':>8}{'p50 ms':>8}{'p95 ms':>8}{'erros':>7}{'exatidão':>10}")
        for r in d["niveis"]:
            print(f"{r['concorrencia']:>6}{r['pedidos_por_seg']:>8}{r['p50_ms']:>8}{r['p95_ms']:>8}{r['erros']:>7}{r['exatidao']:>10.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--chave", default="dev")
    ap.add_argument("--nome", default="modelo")
    ap.add_argument("--niveis", default="1,4,16,64")
    ap.add_argument("--n", type=int, default=200, help="pedidos por nível")
    ap.add_argument("--comparar", action="store_true")
    args = ap.parse_args()
    if args.comparar:
        comparar()
        raise SystemExit
    casos = [json.loads(l) for l in (M11 / "dados" / "teste_bruto.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    niveis = []
    for c in map(int, args.niveis.split(",")):
        r = asyncio.run(um_nivel(args.url, args.chave, casos, c, args.n))
        print(r)
        niveis.append(r)
    (AQUI / "resultados").mkdir(exist_ok=True)
    (AQUI / "resultados" / f"carga_{args.nome}.json").write_text(json.dumps({"nome": args.nome, "niveis": niveis}, indent=1))
    comparar()
