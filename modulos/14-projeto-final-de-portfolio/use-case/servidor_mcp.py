"""Servidor MCP do copiloto: documentos internos (pesquisa híbrida) e base de vendas (só leitura, do módulo 9).

Qualquer cliente MCP o pode usar: o copiloto.py, o Claude Desktop ou o Claude Code.
    uv run mcp dev servidor_mcp.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import pesquisa

AQUI = Path(__file__).parent
# Base de vendas: variável DADOS_COPILOTO_DIR, senão vendas/ ao lado deste ficheiro (num Space), senão o módulo 9
M09 = Path(os.getenv("DADOS_COPILOTO_DIR") or (AQUI / "vendas" if (AQUI / "vendas").is_dir() else AQUI.parent.parent / "09-mcp-integracoes-e-seguranca-de-agentes" / "use-case"))
sys.path.insert(0, str(M09))
if not (M09 / "vendas.db").exists():
    subprocess.run([sys.executable, str(M09 / "criar_base.py")], check=True, stdout=subprocess.DEVNULL)
import servidor_vendas  # noqa: E402

mcp = FastMCP("copiloto-loja-lusa")


@mcp.tool()
def pesquisar_documentos(pergunta: str, k: int = 5) -> str:
    """Pesquisa nos documentos internos da Loja Lusa (manuais, políticas de RH, despesas, TI, manuais de produto).
    Devolve excertos com um id (por exemplo politica_despesas#3) que deves citar entre parênteses retos."""
    res = pesquisa.procurar(pergunta, k=max(1, min(k, 8)))
    return json.dumps([{"id": r["id"], "documento": r["titulo"], "secao": r["secao"], "texto": r["texto"]} for r in res], ensure_ascii=False)


@mcp.tool()
def ler_excerto(id: str) -> str:
    """Texto completo de um excerto pelo id devolvido por pesquisar_documentos."""
    c = pesquisa.por_id(id)
    return json.dumps(c, ensure_ascii=False) if c else f"Excerto {id} não existe."


# As ferramentas de dados são as mesmas do servidor do módulo 9: reutilizar em vez de copiar
for f in (servidor_vendas.listar_tabelas, servidor_vendas.descrever_tabela, servidor_vendas.consultar_sql):
    mcp.tool()(f)


@mcp.resource("docs://indice")
def indice() -> str:
    """Lista de documentos e secções indexados."""
    chunks = pesquisa.carregar()[0]
    return "\n".join(sorted({f"{c['titulo']} › {c['secao']}" for c in chunks}))


if __name__ == "__main__":
    mcp.run()
