"""Compara o que o processador extraiu com os valores verdadeiros dos documentos gerados.

Mede a exatidão por campo e se as validações apanham os documentos com erros inseridos.
Uso:
    uv run python avaliar.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

AQUI = Path(__file__).parent
CAMPOS = ["tipo", "nif_emitente", "nif_cliente", "numero", "data", "total_sem_iva", "total_iva", "total"]


def igual(a, b) -> bool:
    if isinstance(b, float) or isinstance(a, float):
        return a is not None and b is not None and abs(float(a) - float(b)) < 0.011
    return (a or None) == (b or None)


if __name__ == "__main__":
    verdade = {json.loads(l)["ficheiro"]: json.loads(l) for l in (AQUI / "entrada/verdade.jsonl").read_text(encoding="utf-8").splitlines()}
    with sqlite3.connect(AQUI / "documentos.db") as con:
        con.row_factory = sqlite3.Row
        docs = {r["ficheiro"]: dict(r) for r in con.execute("SELECT * FROM documentos")}
        linhas = {}
        for r in con.execute("SELECT ficheiro, COUNT(*) n FROM linhas GROUP BY ficheiro"):
            linhas[r["ficheiro"]] = r["n"]
    comuns = [f for f in verdade if f in docs]
    print(f"{len(comuns)} documentos avaliados\n")
    for c in CAMPOS:
        ok = sum(igual(docs[f][c], verdade[f]["documento"][c]) for f in comuns)
        print(f"{c:<15} {ok / len(comuns):6.1%}")
    ok = sum(linhas.get(f, 0) == len(verdade[f]["documento"]["linhas"]) for f in comuns)
    print(f"{'n.º de linhas':<15} {ok / len(comuns):6.1%}")
    tudo = sum(all(igual(docs[f][c], verdade[f]["documento"][c]) for c in CAMPOS) for f in comuns)
    print(f"{'tudo certo':<15} {tudo / len(comuns):6.1%}")

    com_erro = [f for f in comuns if verdade[f]["erros_inseridos"]]
    sem_erro = [f for f in comuns if not verdade[f]["erros_inseridos"] and not verdade[f].get("nota")]
    apanhados = sum(docs[f]["estado"] == "revisao" for f in com_erro)
    falsos = sum(docs[f]["estado"] == "revisao" for f in sem_erro)
    print(f"\nDocumentos com erros inseridos enviados para revisão: {apanhados}/{len(com_erro)}")
    print(f"Documentos corretos enviados para revisão (falsos alarmes): {falsos}/{len(sem_erro)}")
    print(f"Segunda leitura usada em {sum(docs[f]['leituras'] == 2 for f in comuns)} documentos")
    errados = [f for f in sem_erro if docs[f]["estado"] == "ok" and not all(igual(docs[f][c], verdade[f]["documento"][c]) for c in CAMPOS)]
    print(f"Documentos aceites automaticamente com algum campo errado: {len(errados)} (o erro mais caro: ninguém revê)")
    for f in errados[:5]:
        dif = {c: (docs[f][c], verdade[f]["documento"][c]) for c in CAMPOS if not igual(docs[f][c], verdade[f]["documento"][c])}
        print(f"  {f}: {dif}")
