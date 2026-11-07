"""Avalia a equipa de pesquisa pela trajetória e pelo resultado, repetindo cada pergunta k vezes.

Uso:
    uv run python avaliar.py                 # k=2, só verificações determinísticas
    uv run python avaliar.py --k 3 --juiz    # acrescenta um LLM como juiz do relatório
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel, Field

import equipa

AQUI = Path(__file__).parent
MODELO_JUIZ = os.getenv("MODELO_JUIZ", "claude-sonnet-5-5")


class Nota(BaseModel):
    responde: bool = Field(description="O relatório responde diretamente à pergunta")
    suportado: int = Field(ge=1, le=5, description="1 = afirmações sem suporte nos achados; 5 = tudo suportado e citado")
    justificacao: str


def executar(pergunta: str, i: int) -> tuple[list[str], dict]:
    app = equipa.construir(InMemorySaver())
    cfg = {"configurable": {"thread_id": f"aval-{i}"}, "recursion_limit": 40}
    trajetoria = []
    for evento in app.stream({"pergunta": pergunta, "auto_aprovar": True}, cfg, stream_mode="updates"):
        trajetoria += [no for no in evento if no != "__interrupt__"]
    return trajetoria, app.get_state(cfg).values


def verificar(caso: dict, trajetoria: list[str], estado: dict) -> dict[str, bool]:
    tarefas, achados, rel = estado.get("tarefas", []), estado.get("achados", {}), estado.get("relatorio", "")
    fontes = equipa.lista_fontes(achados) if achados else []
    citadas = {int(n) for n in re.findall(r"\[(\d+)\]", rel.split("## Fontes")[0])}
    custo = equipa.custo(estado.get("uso", []))
    return {
        "ordem_da_trajetoria": trajetoria[:1] == ["planear"] and trajetoria[-2:] == ["aprovar", "escrever"] and "rever" in trajetoria,
        "plano_com_fontes_exigidas": set(caso["exige"]) <= {t["fonte"] for t in tarefas},
        "esforco_proporcional": len(tarefas) <= caso.get("max_tarefas", 6),
        "todos_os_achados_com_fonte": bool(achados) and all(a["fontes"] for a in achados.values()),
        "citacoes_validas": bool(citadas) and citadas <= set(range(1, len(fontes) + 1)),
        "dentro_do_orcamento": custo["usd_tokens"] + custo["usd_pesquisas"] <= caso["max_usd"],
    }


def julgar(pergunta: str, estado: dict) -> Nota:
    achados = json.dumps(estado["achados"], ensure_ascii=False)
    r = equipa.llm().messages.parse(model=MODELO_JUIZ, max_tokens=2000, output_format=Nota, messages=[{"role": "user", "content":
        f"Pergunta: {pergunta}\n\nAchados da equipa (a única evidência disponível):\n{achados}\n\nRelatório:\n{estado['relatorio']}\n\n"
        "Avalia se o relatório responde à pergunta e se cada afirmação está suportada pelos achados."}])
    return r.parsed_output


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--juiz", action="store_true")
    ap.add_argument("--so", help="id de uma pergunta")
    args = ap.parse_args()
    casos = [json.loads(l) for l in (AQUI / "perguntas.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    casos = [c for c in casos if not args.so or c["id"] == args.so]
    resumo = []
    for caso in casos:
        sucessos = []
        for i in range(args.k):
            traj, estado = executar(caso["pergunta"], i)
            checks = verificar(caso, traj, estado)
            if args.juiz and estado.get("relatorio"):
                nota = julgar(caso["pergunta"], estado)
                checks["juiz_responde_e_suporta"] = nota.responde and nota.suportado >= 4
            ok = all(checks.values())
            sucessos.append(ok)
            c = equipa.custo(estado.get("uso", []))
            print(f"{caso['id']} #{i + 1}: {'✅' if ok else '❌'}  passos={len(traj)}  tarefas={len(estado.get('tarefas', []))}  "
                  f"rondas={estado.get('rondas')}  US${c['usd_tokens'] + c['usd_pesquisas']:.3f}")
            for nome, v in checks.items():
                if not v:
                    print(f"     falhou: {nome}")
        resumo.append((caso["id"], sum(sucessos) / args.k, all(sucessos)))
    print(f"\n{'pergunta':<10} {'taxa':>6}  pass^{args.k}")
    for cid, taxa, todos in resumo:
        print(f"{cid:<10} {taxa:>6.0%}  {'sim' if todos else 'não'}")
    print(f"\npass^{args.k} global: {sum(t for *_, t in resumo)}/{len(resumo)} perguntas")
