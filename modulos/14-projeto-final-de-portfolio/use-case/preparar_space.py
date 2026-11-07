"""Monta a pasta space/ com tudo o que um Space do Hugging Face precisa para correr a demo.

Uso:
    uv run python pesquisa.py indexar          # o índice vai pronto, para o Space arrancar depressa
    uv run python preparar_space.py
    huggingface-cli upload o-teu-utilizador/copiloto-loja-lusa space . --repo-type space
Depois, nas definições do Space: Secrets → ANTHROPIC_API_KEY; opcional SENHA_DEMO.
"""
from __future__ import annotations

import shutil
from importlib.metadata import version
from pathlib import Path

import pesquisa
import servidor_mcp

AQUI = Path(__file__).parent
DESTINO = AQUI / "space"

LEIA_ME = """---
title: Copiloto Loja Lusa
emoji: 📚
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: {gradio}
app_file: app.py
pinned: false
---

# Copiloto de análise de documentos empresariais

Agente Claude ligado por MCP a documentos internos (pesquisa híbrida) e a uma base de vendas (SQL só de leitura).
Cada resposta cita as fontes; as citações são verificadas por código. Dados fictícios.

Código e avaliação: https://github.com/paulodiasfaria/ai-course/tree/main/modulos/14-projeto-final-de-portfolio
"""

REQUISITOS = """anthropic
mcp>=1.10,<2
sentence-transformers
rank-bm25
numpy
pandas
python-dotenv
pydantic
"""

if __name__ == "__main__":
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir()
    for f in ["app.py", "copiloto.py", "pesquisa.py", "servidor_mcp.py"]:
        shutil.copy(AQUI / f, DESTINO / f)
    shutil.copytree(pesquisa.DOCS, DESTINO / "docs")
    if not (pesquisa.INDICE / "chunks.json").exists():
        pesquisa.indexar()
    shutil.copytree(pesquisa.INDICE, DESTINO / "indice")
    (DESTINO / "vendas").mkdir()
    for f in ["servidor_vendas.py", "vendas.db"]:
        shutil.copy(servidor_mcp.M09 / f, DESTINO / "vendas" / f)
    (DESTINO / "requirements.txt").write_text(REQUISITOS, encoding="utf-8")
    (DESTINO / "README.md").write_text(LEIA_ME.format(gradio=version("gradio")), encoding="utf-8")
    print(f"Pasta pronta em {DESTINO}:")
    for p in sorted(DESTINO.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(DESTINO)}  ({p.stat().st_size / 1024:.0f} KB)")
