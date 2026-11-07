"""Agente analista de dados: recebe um CSV e uma pergunta de negócio, escreve e executa
código pandas numa sandbox, corrige os próprios erros e responde com um gráfico.

Uso:
    uv run python gerar_vendas.py                     # cria dados/vendas.csv de exemplo
    uv run python agente_dados.py dados/vendas.csv "Que categoria cresceu mais em 2025 face a 2024?"
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from sandbox import Sandbox

load_dotenv()
MODELO = os.getenv("MODELO_AGENTE", "claude-sonnet-5-5")

SYSTEM = """És um analista de dados sénior. Respondes a perguntas de negócio sobre o ficheiro de dados disponível, \
escrevendo e executando código Python (pandas, numpy, matplotlib) com a ferramenta executar_python.

Método:
1. Começa por perceber os dados (colunas, tipos, valores em falta, intervalo de datas).
2. Faz a análise em passos pequenos e verifica os resultados intermédios.
3. Se um passo der erro, lê a mensagem e corrige.
4. Quando ajudar, guarda UM gráfico com plt.savefig("grafico.png", dpi=120, bbox_inches="tight").
5. Termina com uma resposta em português de Portugal: conclusão principal primeiro, números concretos, \
e limitações dos dados se existirem. Não inventes números que não calculaste."""

FERRAMENTAS = [
    {
        "name": "executar_python",
        "description": ("Executa código Python. As variáveis persistem entre chamadas. pandas (pd), numpy (np) e "
                        "matplotlib.pyplot (plt) já estão importados. O ficheiro de dados está na pasta atual. "
                        "Usa print() para ver resultados; mostra só o necessário (head, describe, agregados)."),
        "input_schema": {"type": "object", "properties": {"codigo": {"type": "string"}}, "required": ["codigo"]},
    },
]


def analisar(csv: str | Path, pergunta: str, pasta_trabalho: str | Path = "trabalho", max_passos: int = 12, verbose: bool = True) -> dict:
    csv = Path(csv)
    pasta = Path(pasta_trabalho)
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    shutil.copy(csv, pasta / csv.name)
    sb = Sandbox(pasta)
    client = Anthropic()
    msgs = [{"role": "user", "content": f"Ficheiro de dados: {csv.name}\n\nPergunta: {pergunta}"}]
    uso = {"input": 0, "output": 0}
    for passo in range(1, max_passos + 1):
        r = client.messages.create(model=MODELO, max_tokens=3000, system=SYSTEM, tools=FERRAMENTAS, messages=msgs)
        uso["input"] += r.usage.input_tokens
        uso["output"] += r.usage.output_tokens
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            texto = "".join(b.text for b in r.content if b.type == "text")
            grafico = pasta / "grafico.png"
            return {"resposta": texto, "passos": passo, "grafico": str(grafico) if grafico.exists() else None, "uso": uso, "mensagens": msgs}
        resultados = []
        for b in r.content:
            if b.type == "tool_use":
                saida = sb.executar(b.input["codigo"])
                if verbose:
                    print(f"\n── passo {passo} ──\n{b.input['codigo']}\n→ {saida[:600]}")
                resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": saida,
                                   "is_error": saida.startswith("ERRO")})
        msgs.append({"role": "user", "content": resultados})
    return {"resposta": "Não consegui concluir a análise dentro do limite de passos.", "passos": max_passos,
            "grafico": None, "uso": uso, "mensagens": msgs}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    out = analisar(sys.argv[1], " ".join(sys.argv[2:]))
    print("\n" + "=" * 60 + "\n" + out["resposta"])
    print(f"\n{out['passos']} passos | tokens: {out['uso']} | gráfico: {out['grafico']}")
