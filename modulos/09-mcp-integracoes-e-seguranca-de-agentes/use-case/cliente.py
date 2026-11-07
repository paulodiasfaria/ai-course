"""Agente que usa o servidor MCP de vendas, com aprovação humana para envios.

Uso:
    uv run python cliente.py "Qual foi a loja com mais vendas em dezembro de 2025?"
    uv run python cliente.py "Envia à direção (direcao@lojalusa.pt) um resumo das vendas de novembro de 2025"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
MODELO = os.getenv("MODELO_AGENTE", "claude-sonnet-5-5")
AQUI = Path(__file__).parent
SERVIDOR = StdioServerParameters(command=sys.executable, args=[str(AQUI / "servidor_vendas.py")])
SENSIVEIS = {"preparar_envio_relatorio"}

SYSTEM = ("És um analista da Loja Lusa com acesso à base de vendas através de ferramentas. "
          "Descreve as tabelas antes de escrever SQL, agrega no SQL e responde em português de Portugal com números concretos. "
          "Valores negativos em valor_eur são devoluções.")


def aprovar(nome: str, args: dict) -> bool:
    print(f"\n⚠️  O agente quer usar '{nome}' com:\n{json.dumps(args, ensure_ascii=False, indent=2)}")
    return input("Aprovar? [s/N] ").strip().lower() == "s"


async def correr(pergunta: str, aprovador=aprovar, max_passos: int = 12, verbose: bool = True) -> str:
    async with stdio_client(SERVIDOR) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()
            ferramentas = [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                           for t in (await sessao.list_tools()).tools]
            if verbose:
                print("Ferramentas do servidor:", [f["name"] for f in ferramentas])
            llm = Anthropic()
            msgs = [{"role": "user", "content": pergunta}]
            for _ in range(max_passos):
                r = llm.messages.create(model=MODELO, max_tokens=2000, system=SYSTEM, tools=ferramentas, messages=msgs)
                msgs.append({"role": "assistant", "content": r.content})
                if r.stop_reason != "tool_use":
                    return "".join(b.text for b in r.content if b.type == "text")
                resultados = []
                for b in r.content:
                    if b.type != "tool_use":
                        continue
                    if b.name in SENSIVEIS and not aprovador(b.name, b.input):
                        texto = "O utilizador NÃO aprovou esta ação. Não tentes outra vez; explica o que farias."
                    else:
                        res = await sessao.call_tool(b.name, b.input)
                        texto = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
                    if verbose:
                        print(f"  🔧 {b.name}({json.dumps(b.input, ensure_ascii=False)[:150]})\n     → {texto[:300]}")
                    resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": texto})
                msgs.append({"role": "user", "content": resultados})
            return "Limite de passos atingido."


if __name__ == "__main__":
    print("\n" + asyncio.run(correr(" ".join(sys.argv[1:]) or "Que categoria vendeu mais em 2025?")))
