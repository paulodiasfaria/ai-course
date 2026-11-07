"""Equipa de pesquisa de mercado: um sistema multi-agente com LangGraph.

Planeador -> investigadores em paralelo (web e dados internos) -> revisor de fontes
-> aprovação humana -> redator. Estado gravado em SQLite: podes interromper e retomar.

Uso:
    uv run python equipa.py "Vale a pena a Loja Lusa abrir uma loja em Coimbra em 2026?"
    uv run python equipa.py --retomar <thread_id>
"""
from __future__ import annotations

import argparse
import json
import operator
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from anthropic import Anthropic
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt
from pydantic import BaseModel, Field

load_dotenv()
AQUI = Path(__file__).parent
MODELO = os.getenv("MODELO", "claude-haiku-5-5")              # analista de dados internos
MODELO_FORTE = os.getenv("MODELO_FORTE", "claude-sonnet-5-5")  # planeador, web, revisor, redator
MAX_RONDAS = 2           # rondas de revisão antes de seguir com o que houver
MAX_PASSOS_ANALISTA = 8
PRECOS = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}  # USD por milhão de tokens (entrada, saída)

# Dados internos: reutilizamos as ferramentas do servidor MCP do módulo 9
M09 = AQUI.parent.parent / "09-mcp-integracoes-e-seguranca-de-agentes" / "use-case"
sys.path.insert(0, str(M09))
if not (M09 / "vendas.db").exists():
    subprocess.run([sys.executable, str(M09 / "criar_base.py")], check=True)
from servidor_vendas import consultar_sql, descrever_tabela, listar_tabelas  # noqa: E402

_llm: Anthropic | None = None


def llm() -> Anthropic:
    global _llm
    if _llm is None:
        _llm = Anthropic()
    return _llm


# ---------------------------------------------------------------- esquemas
class Tarefa(BaseModel):
    id: str = Field(description="Identificador curto, por exemplo t1")
    pergunta: str = Field(description="Subpergunta autónoma: quem a ler sem mais contexto sabe o que procurar")
    fonte: Literal["web", "interno"] = Field(description="web para mercado, concorrência, demografia; interno para as vendas da Loja Lusa")


class Plano(BaseModel):
    tarefas: list[Tarefa] = Field(min_length=2, max_length=6)


class Problema(BaseModel):
    tarefa_id: str
    problema: str = Field(description="O que falta ou está mal e o que o investigador deve fazer")


class Revisao(BaseModel):
    aprovado: bool
    problemas: list[Problema] = Field(default_factory=list)


# ---------------------------------------------------------------- estado
def juntar(a: dict | None, b: dict | None) -> dict:
    """Reducer: junta achados por id de tarefa (uma nova versão substitui a anterior)."""
    return {**(a or {}), **(b or {})}


class Estado(TypedDict, total=False):
    pergunta: str
    tarefas: list[dict]
    achados: Annotated[dict, juntar]
    revisao: dict
    rondas: int
    auto_aprovar: bool
    decisao_humana: str
    relatorio: str
    uso: Annotated[list, operator.add]


def registo(no: str, modelo: str, r) -> dict:
    u = r.usage
    pesquisas = getattr(getattr(u, "server_tool_use", None), "web_search_requests", 0) or 0
    return {"no": no, "modelo": modelo, "entrada": u.input_tokens, "saida": u.output_tokens, "pesquisas": pesquisas}


# ---------------------------------------------------------------- agentes
SYSTEM_PLANEADOR = """És o coordenador de uma equipa de pesquisa de mercado da Loja Lusa, uma cadeia portuguesa de artigos para a casa
(lojas Online, Porto, Lisboa, Braga e Faro; categorias Têxteis, Cozinha, Decoração, Banho e Iluminação).
Divide a pergunta em 2 a 6 subperguntas independentes, que possam ser investigadas em paralelo.
- Usa fonte "interno" para o que se responde com as vendas da Loja Lusa (2024-2025): crescimento, categorias, lojas comparáveis.
- Usa fonte "web" para mercado, concorrência, demografia, rendas, tendências.
- Escala o esforço: uma pergunta factual simples precisa de 2 tarefas; uma decisão de investimento, de 4 a 6.
- Cada subpergunta tem de ser autónoma: o investigador não vê a pergunta original."""

SYSTEM_WEB = """És um investigador de mercado. Responde à subpergunta com pesquisas na web (no máximo 4).
Prefere fontes oficiais e recentes (INE, Pordata, Banco de Portugal, câmaras municipais, imprensa económica).
Responde em português de Portugal, em 5 a 10 linhas, com números concretos e o ano a que se referem.
Se não encontrares dados fiáveis, diz exatamente o que falta em vez de estimar."""

SYSTEM_ANALISTA = """És analista de dados da Loja Lusa. Responde à subpergunta com consultas SQL à base de vendas.
Descreve as tabelas antes de escrever SQL e agrega no SQL. Valores negativos em valor_eur são devoluções.
Termina com 3 a 8 linhas em português de Portugal, com os números que encontraste."""

SYSTEM_REVISOR = """És o revisor de uma equipa de pesquisa. Verifica cada achado:
- responde à subpergunta?
- os números têm fonte (URL para a web, consulta SQL para dados internos) e ano?
- há afirmações sem suporte ou contradições entre achados?
Aprova se os achados chegam para responder à pergunta principal, mesmo com lacunas menores.
Aponta problemas só quando uma nova investigação os pode resolver, com instruções concretas."""

SYSTEM_REDATOR = """Escreves relatórios de pesquisa de mercado para a direção da Loja Lusa, em português de Portugal.
Estrutura: Resposta curta (2-3 frases), Evidência (por tema), Riscos e lacunas, Recomendação.
Cada número ou afirmação factual leva a citação [n] da lista de fontes. Não uses fontes que não estão na lista.
Se as instruções do revisor humano mandarem ignorar uma fonte, não a uses."""


def planear(s: Estado) -> dict:
    r = llm().messages.parse(model=MODELO_FORTE, max_tokens=4000, system=SYSTEM_PLANEADOR,
                             messages=[{"role": "user", "content": s["pergunta"]}], output_format=Plano)
    tarefas = [t.model_dump() for t in r.parsed_output.tarefas]
    return {"tarefas": tarefas, "rondas": 0, "uso": [registo("planear", MODELO_FORTE, r)]}


def investigar_web(pergunta: str) -> tuple[str, list[dict], list[dict]]:
    msgs = [{"role": "user", "content": pergunta}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 4, "user_location":
              {"type": "approximate", "country": "PT"}}]
    uso = []
    for _ in range(4):     # pause_turn: o servidor pede para continuar uma pesquisa longa
        r = llm().messages.create(model=MODELO_FORTE, max_tokens=8000, system=SYSTEM_WEB, tools=tools, messages=msgs)
        uso.append(registo("investigar_web", MODELO_FORTE, r))
        if r.stop_reason != "pause_turn":
            break
        msgs.append({"role": "assistant", "content": r.content})
    texto, fontes = "", {}
    for b in r.content:
        if b.type == "text":
            texto += b.text
            for c in getattr(b, "citations", None) or []:
                if getattr(c, "url", None):
                    fontes.setdefault(c.url, {"url": c.url, "titulo": getattr(c, "title", "") or c.url})
    return texto.strip(), list(fontes.values()), uso


FERRAMENTAS_SQL = [
    {"name": "listar_tabelas", "description": "Lista as tabelas da base de vendas.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "descrever_tabela", "description": "Colunas, tipos e 3 linhas de exemplo de uma tabela.",
     "input_schema": {"type": "object", "properties": {"tabela": {"type": "string"}}, "required": ["tabela"]}},
    {"name": "consultar_sql", "description": "Executa UMA consulta SELECT em SQLite e devolve até 50 linhas em CSV. Datas em texto AAAA-MM-DD.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]
FUNCOES_SQL = {"listar_tabelas": listar_tabelas, "descrever_tabela": descrever_tabela, "consultar_sql": consultar_sql}


def investigar_interno(pergunta: str) -> tuple[str, list[dict], list[dict]]:
    msgs, uso, consultas = [{"role": "user", "content": pergunta}], [], []
    for _ in range(MAX_PASSOS_ANALISTA):
        r = llm().messages.create(model=MODELO, max_tokens=3000, system=SYSTEM_ANALISTA, tools=FERRAMENTAS_SQL, messages=msgs)
        uso.append(registo("investigar_interno", MODELO, r))
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            break
        res = []
        for b in r.content:
            if b.type == "tool_use":
                out = FUNCOES_SQL[b.name](**b.input)
                if b.name == "consultar_sql" and not out.startswith(("Erro", "Só", "Envia")):
                    consultas.append(b.input["query"])
                res.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        msgs.append({"role": "user", "content": res})
    texto = "".join(b.text for b in r.content if b.type == "text").strip()
    fontes = [{"url": "vendas.db", "titulo": "SQL: " + " ".join(q.split())[:200]} for q in consultas[-3:]]
    return texto, fontes, uso


def investigar(entrada: dict) -> dict:
    """Recebe só a sua tarefa (via Send), não o estado todo: contexto limpo."""
    t, feedback = entrada["tarefa"], entrada.get("feedback")
    pergunta = t["pergunta"] + (f"\n\nUma primeira tentativa foi rejeitada pelo revisor: {feedback}" if feedback else "")
    fazer = investigar_web if t["fonte"] == "web" else investigar_interno
    texto, fontes, uso = fazer(pergunta)
    return {"achados": {t["id"]: {**t, "resposta": texto, "fontes": fontes}}, "uso": uso}


def distribuir(s: Estado) -> list[Send]:
    return [Send("investigar", {"tarefa": t}) for t in s["tarefas"]]


def rever(s: Estado) -> dict:
    achados = s.get("achados", {})
    # 1) verificações determinísticas: não gastam tokens e não falham por distração
    problemas = [{"tarefa_id": i, "problema": "Sem fontes. Volta a pesquisar e cita de onde vêm os números."}
                 for i, a in achados.items() if not a["fontes"]]
    # 2) revisão pelo modelo
    r = llm().messages.parse(model=MODELO_FORTE, max_tokens=3000, system=SYSTEM_REVISOR, output_format=Revisao, messages=[
        {"role": "user", "content": f"Pergunta principal: {s['pergunta']}\n\nAchados:\n{json.dumps(achados, ensure_ascii=False, indent=1)}"}])
    rev = r.parsed_output
    ids = {p["tarefa_id"] for p in problemas}
    problemas += [p.model_dump() for p in rev.problemas if p.tarefa_id in achados and p.tarefa_id not in ids]
    aprovado = rev.aprovado and not ids
    return {"revisao": {"aprovado": aprovado, "problemas": problemas}, "rondas": s.get("rondas", 0) + 1,
            "uso": [registo("rever", MODELO_FORTE, r)]}


def depois_da_revisao(s: Estado):
    rev = s["revisao"]
    if rev["aprovado"] or not rev["problemas"] or s["rondas"] >= MAX_RONDAS:
        return "aprovar"
    return [Send("investigar", {"tarefa": s["achados"][p["tarefa_id"]], "feedback": p["problema"]}) for p in rev["problemas"]]


def aprovar(s: Estado) -> dict:
    if s.get("auto_aprovar"):
        return {"decisao_humana": "ok"}
    decisao = interrupt({"pergunta": s["pergunta"], "achados": s["achados"], "revisao": s["revisao"]})
    return {"decisao_humana": str(decisao)}


def lista_fontes(achados: dict) -> list[dict]:
    vistas, out = set(), []
    for a in achados.values():
        for f in a["fontes"]:
            chave = f["url"] + f["titulo"]
            if chave not in vistas:
                vistas.add(chave)
                out.append(f)
    return out


def escrever(s: Estado) -> dict:
    fontes = lista_fontes(s["achados"])
    numeradas = "\n".join(f"[{i}] {f['titulo']} ({f['url']})" for i, f in enumerate(fontes, 1))
    achados = "\n\n".join(f"### {a['pergunta']}\n{a['resposta']}\nFontes: " +
                          ", ".join(f"[{fontes.index(f) + 1}]" for f in a["fontes"]) for a in s["achados"].values())
    instr = "" if s.get("decisao_humana", "ok").strip().lower() in ("ok", "s", "sim", "") else \
        f"\n\nInstruções do revisor humano: {s['decisao_humana']}"
    r = llm().messages.create(model=MODELO_FORTE, max_tokens=6000, system=SYSTEM_REDATOR, messages=[{"role": "user", "content":
        f"Pergunta: {s['pergunta']}\n\nAchados:\n{achados}\n\nFontes:\n{numeradas}{instr}"}])
    texto = "".join(b.text for b in r.content if b.type == "text").strip()
    relatorio = f"# {s['pergunta']}\n\n{texto}\n\n## Fontes\n\n" + "\n".join(
        f"{i}. {f['titulo']} — {f['url']}" for i, f in enumerate(fontes, 1))
    return {"relatorio": relatorio, "uso": [registo("escrever", MODELO_FORTE, r)]}


# ---------------------------------------------------------------- grafo
def construir(checkpointer=None):
    g = StateGraph(Estado)
    g.add_node("planear", planear)
    g.add_node("investigar", investigar)
    g.add_node("rever", rever)
    g.add_node("aprovar", aprovar)
    g.add_node("escrever", escrever)
    g.add_edge(START, "planear")
    g.add_conditional_edges("planear", distribuir, ["investigar"])
    g.add_edge("investigar", "rever")        # o revisor corre uma vez, depois de todos os investigadores
    g.add_conditional_edges("rever", depois_da_revisao, ["investigar", "aprovar"])
    g.add_edge("aprovar", "escrever")
    g.add_edge("escrever", END)
    return g.compile(checkpointer=checkpointer)


def custo(uso: list[dict]) -> dict:
    usd = sum(u["entrada"] / 1e6 * PRECOS.get(u["modelo"], (0, 0))[0] + u["saida"] / 1e6 * PRECOS.get(u["modelo"], (0, 0))[1] for u in uso)
    pesquisas = sum(u["pesquisas"] for u in uso)
    return {"chamadas": len(uso), "tokens_entrada": sum(u["entrada"] for u in uso), "tokens_saida": sum(u["saida"] for u in uso),
            "pesquisas_web": pesquisas, "usd_tokens": round(usd, 4), "usd_pesquisas": round(pesquisas * 0.01, 4)}


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]


def mostrar_achados(valor: dict) -> None:
    print("\n" + "=" * 70 + "\nACHADOS PARA APROVAÇÃO\n" + "=" * 70)
    for i, a in valor["achados"].items():
        print(f"\n[{i} · {a['fonte']}] {a['pergunta']}\n{a['resposta'][:700]}")
        for f in a["fontes"]:
            print(f"   - {f['titulo'][:90]} ({f['url'][:80]})")
    if valor["revisao"]["problemas"]:
        print("\nProblemas que o revisor ainda aponta:", *[f"- {p['tarefa_id']}: {p['problema']}" for p in valor["revisao"]["problemas"]], sep="\n")


def correr(app, entrada, cfg) -> dict:
    while True:
        for evento in app.stream(entrada, cfg, stream_mode="updates"):
            for no in evento:
                if no != "__interrupt__":
                    print(f"  ✓ {no}")
        estado = app.get_state(cfg)
        if not estado.next:
            return estado.values
        pendente = estado.tasks[0].interrupts[0].value
        mostrar_achados(pendente)
        resposta = input("\nEscreve 'ok' para aprovar, ou instruções para o redator (ex.: 'ignora a fonte sobre rendas'): ")
        entrada = Command(resume=resposta or "ok")


if __name__ == "__main__":
    from langgraph.checkpoint.sqlite import SqliteSaver

    ap = argparse.ArgumentParser()
    ap.add_argument("pergunta", nargs="*")
    ap.add_argument("--retomar", help="thread_id de uma execução interrompida")
    args = ap.parse_args()
    con = sqlite3.connect(AQUI / "checkpoints.db", check_same_thread=False)
    app = construir(SqliteSaver(con))
    if args.retomar:
        cfg = {"configurable": {"thread_id": args.retomar}}
        if not app.get_state(cfg).values:
            sys.exit(f"Não há execução com thread_id {args.retomar}")
        entrada = None      # None retoma do último checkpoint
    else:
        pergunta = " ".join(args.pergunta) or "Vale a pena a Loja Lusa abrir uma loja em Coimbra em 2026?"
        cfg = {"configurable": {"thread_id": f"{slug(pergunta)}-{datetime.now():%Y%m%d-%H%M%S}"}, "recursion_limit": 40}
        entrada = {"pergunta": pergunta}
    print(f"thread_id: {cfg['configurable']['thread_id']}  (usa --retomar com este id se interromperes)")
    final = correr(app, entrada, cfg)
    Path(AQUI / "relatorios").mkdir(exist_ok=True)
    destino = AQUI / "relatorios" / f"{cfg['configurable']['thread_id']}.md"
    destino.write_text(final["relatorio"], encoding="utf-8")
    print("\n" + final["relatorio"] + f"\n\nGuardado em {destino}\nCusto: {json.dumps(custo(final['uso']), ensure_ascii=False)}")
