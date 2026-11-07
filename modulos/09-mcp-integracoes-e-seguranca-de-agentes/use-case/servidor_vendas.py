"""Servidor MCP com acesso só de leitura à base de vendas da Loja Lusa.

Tools:     listar_tabelas, descrever_tabela, consultar_sql, preparar_envio_relatorio
Resources: schema://vendas
Prompts:   relatorio_mensal

Uso:
    uv run python criar_base.py              # cria vendas.db a partir dos dados do módulo 8
    uv run mcp dev servidor_vendas.py        # testar no MCP Inspector
    uv run python servidor_vendas.py         # servidor stdio (para Claude Desktop, Claude Code ou o cliente.py)
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB = Path(__file__).parent / "vendas.db"
PENDENTES = Path(__file__).parent / "envios_pendentes.jsonl"
MAX_LINHAS = 50
DOMINIOS_PERMITIDOS = ("lojalusa.pt",)

mcp = FastMCP("vendas-loja-lusa")


def ligar() -> sqlite3.Connection:
    # mode=ro: a própria base recusa escritas, mesmo que a validação abaixo falhe
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


PROIBIDAS = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace|vacuum)\b", re.I)


@mcp.tool()
def listar_tabelas() -> str:
    """Lista as tabelas da base de vendas."""
    with ligar() as con:
        return ", ".join(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))


@mcp.tool()
def descrever_tabela(tabela: str) -> str:
    """Colunas, tipos e 3 linhas de exemplo de uma tabela. Usa antes de escrever SQL."""
    with ligar() as con:
        nomes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tabela not in nomes:
            return f"Tabela '{tabela}' não existe. Tabelas: {', '.join(sorted(nomes))}"
        cols = con.execute(f'PRAGMA table_info("{tabela}")').fetchall()
        ex = con.execute(f'SELECT * FROM "{tabela}" LIMIT 3').fetchall()
        n = con.execute(f'SELECT COUNT(*) FROM "{tabela}"').fetchone()[0]
    return json.dumps({"tabela": tabela, "linhas": n, "colunas": [{"nome": c[1], "tipo": c[2]} for c in cols], "exemplo": ex},
                      ensure_ascii=False, default=str)


@mcp.tool()
def consultar_sql(query: str) -> str:
    """Executa UMA consulta SQL de leitura (SELECT ou WITH) em SQLite e devolve até 50 linhas em CSV.
    Agrega no SQL (GROUP BY, SUM, AVG) em vez de pedir linhas individuais.
    Datas estão em texto ISO (AAAA-MM-DD): usa strftime('%Y-%m', data) para agrupar por mês."""
    q = query.strip().rstrip(";")
    if ";" in q:
        return "Envia uma única consulta, sem ';' no meio."
    if not re.match(r"^\s*(select|with)\b", q, re.I) or PROIBIDAS.search(q):
        return "Só são permitidas consultas de leitura (SELECT/WITH)."
    try:
        with ligar() as con:
            cur = con.execute(q)
            linhas = cur.fetchmany(MAX_LINHAS + 1)
            cab = [d[0] for d in cur.description]
    except sqlite3.Error as e:
        return f"Erro de SQL: {e}. Confirma nomes de colunas com descrever_tabela."
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cab)
    w.writerows(linhas[:MAX_LINHAS])
    aviso = f"\n[cortado a {MAX_LINHAS} linhas; agrega ou filtra mais]" if len(linhas) > MAX_LINHAS else ""
    return buf.getvalue() + aviso


@mcp.tool()
def preparar_envio_relatorio(destinatario: str, assunto: str, corpo: str) -> str:
    """Prepara o envio de um relatório por email a um colega da Loja Lusa.
    NÃO envia: fica pendente até uma pessoa aprovar no cliente. Só aceita endereços @lojalusa.pt."""
    if not destinatario.lower().endswith(tuple("@" + d for d in DOMINIOS_PERMITIDOS)):
        return f"Recusado: só é possível enviar para endereços {', '.join('@' + d for d in DOMINIOS_PERMITIDOS)}."
    pedido = {"quando": datetime.now().isoformat(timespec="seconds"), "para": destinatario, "assunto": assunto, "corpo": corpo[:5000]}
    with open(PENDENTES, "a", encoding="utf-8") as f:
        f.write(json.dumps(pedido, ensure_ascii=False) + "\n")
    return "Envio registado como PENDENTE de aprovação humana. Informa o utilizador de que tem de aprovar."


@mcp.resource("schema://vendas")
def esquema() -> str:
    """Esquema completo da base de vendas."""
    with ligar() as con:
        return "\n".join(r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE type='table'") if r[0])


@mcp.prompt()
def relatorio_mensal(mes: str) -> str:
    """Relatório de vendas de um mês (formato AAAA-MM)."""
    return (f"Prepara um relatório de vendas de {mes}: total, totais por loja e por categoria, "
            f"variação face ao mês anterior e ao mesmo mês do ano anterior, e 3 conclusões para a direção.")


if __name__ == "__main__":
    mcp.run()
