"""Avalia no conjunto de teste: modelo base, modelo afinado e um modelo da API, com as mesmas métricas.

Uso:
    uv run python avaliar.py --modelo base
    uv run python avaliar.py --modelo base --few-shot 3
    uv run python avaliar.py --modelo saidas/sft/final
    uv run python avaliar.py --modelo claude:claude-haiku-5-5
    uv run python avaliar.py --tabela          # compara todos os resultados guardados
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from comum import SYSTEM, exemplo_chat, ler_json, metricas

AQUI = Path(__file__).parent
RES = AQUI / "resultados"
PRECOS_API = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}   # USD por milhão de tokens


def ler(nome: str) -> list[dict]:
    return [json.loads(l) for l in (AQUI / "dados" / nome).read_text(encoding="utf-8").splitlines() if l.strip()]


def prompts_com_exemplos(textos: list[str], k: int) -> list[list[dict]]:
    if not k:
        return [exemplo_chat(t)["prompt"] for t in textos]
    treino = ler("treino_bruto.jsonl")
    exemplos = random.Random(0).sample(treino, k)
    shots = []
    for e in exemplos:
        shots += [{"role": "user", "content": e["texto"]}, {"role": "assistant", "content": json.dumps(e["rotulo"], ensure_ascii=False)}]
    return [[{"role": "system", "content": SYSTEM}, *shots, {"role": "user", "content": t}] for t in textos]


def correr_local(caminho: str, prompts):
    from modelo_local import BASE, carregar, gerar
    adaptador = None if caminho == "base" else caminho
    modelo, tok = carregar(BASE, adaptador=adaptador, quatro_bits=True)
    t0 = time.time()
    saidas = gerar(modelo, tok, prompts)
    seg = time.time() - t0
    return saidas, {"seg_por_pedido": seg / len(prompts), "usd_por_1000": None}


def correr_api(modelo: str, prompts):
    from anthropic import Anthropic
    from dotenv import load_dotenv
    load_dotenv()
    llm, saidas, ent, sai = Anthropic(), [], 0, 0
    t0 = time.time()
    for p in prompts:
        r = llm.messages.create(model=modelo, max_tokens=300, system=p[0]["content"], messages=p[1:])
        saidas.append("".join(b.text for b in r.content if b.type == "text"))
        ent, sai = ent + r.usage.input_tokens, sai + r.usage.output_tokens
    pe, ps = PRECOS_API.get(modelo, (0, 0))
    usd = (ent * pe + sai * ps) / 1e6
    return saidas, {"seg_por_pedido": (time.time() - t0) / len(prompts), "usd_por_1000": round(usd / len(prompts) * 1000, 3)}


def tabela():
    linhas = [json.loads(f.read_text()) for f in sorted(RES.glob("*.json"))]
    cols = ["json_valido", "exato_categoria", "exato_urgencia", "exato_numero_encomenda", "exato_produto", "exato_pedido", "tudo_certo", "f1_macro_categoria"]
    print(f"{'modelo':<34}" + "".join(f"{c.replace('exato_', '')[:12]:>13}" for c in cols) + f"{'s/pedido':>10}{'US$/1000':>10}")
    for l in linhas:
        m = l["metricas"]
        print(f"{l['nome'][:34]:<34}" + "".join(f"{m[c]:>13.1%}" for c in cols) +
              f"{l['custo']['seg_por_pedido']:>10.2f}{str(l['custo']['usd_por_1000'] or '-'):>10}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", help="base | caminho do adaptador | claude:<id>")
    ap.add_argument("--few-shot", type=int, default=0)
    ap.add_argument("--limite", type=int, default=0, help="avaliar só os primeiros N (para testes rápidos)")
    ap.add_argument("--tabela", action="store_true")
    args = ap.parse_args()
    if args.tabela or not args.modelo:
        tabela()
        raise SystemExit
    teste = ler("teste_bruto.jsonl")
    if args.limite:
        teste = teste[: args.limite]
    prompts = prompts_com_exemplos([x["texto"] for x in teste], args.few_shot)
    if args.modelo.startswith("claude:"):
        saidas, custo = correr_api(args.modelo.split(":", 1)[1], prompts)
    else:
        saidas, custo = correr_local(args.modelo, prompts)
    previstos = [ler_json(s) for s in saidas]
    m = metricas(previstos, [x["rotulo"] for x in teste])
    nome = args.modelo.replace("/", "_").replace(":", "_") + (f"_fs{args.few_shot}" if args.few_shot else "")
    RES.mkdir(exist_ok=True)
    erros = [{"texto": x["texto"], "esperado": x["rotulo"], "obtido": s} for x, s, p in zip(teste, saidas, previstos) if p != x["rotulo"]]
    (RES / f"{nome}.json").write_text(json.dumps({"nome": nome, "metricas": m, "custo": custo}, ensure_ascii=False, indent=1))
    (RES / f"{nome}_erros.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in erros), encoding="utf-8")
    print(json.dumps(m, indent=1), custo)
    tabela()
