"""Pesquisa híbrida sobre documentos: chunking por secção, embeddings densos (e5), BM25 e fusão RRF.

O índice fica em indice/ (numpy + JSON), sem servidor: chega para centenas de documentos e corre num Space gratuito.
Para milhões de chunks, troca por Qdrant (módulos 4 a 6).

Uso:
    uv run python pesquisa.py indexar                 # usa os documentos do módulo 5 por omissão
    uv run python pesquisa.py indexar --docs a/minha/pasta
    uv run python pesquisa.py procurar "limite de hotel em Lisboa"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
# Documentos: variável DOCS_COPILOTO, senão docs/ ao lado deste ficheiro (num Space), senão os documentos do módulo 5
DOCS = Path(os.getenv("DOCS_COPILOTO") or (AQUI / "docs" if (AQUI / "docs").is_dir() else AQUI.parent.parent / "05-rag-fundamental" / "use-case" / "docs"))
INDICE = AQUI / "indice"
MODELO_EMB = "intfloat/multilingual-e5-base"


def chunks_markdown(texto: str, fonte: str, max_chars: int = 1500) -> list[dict]:
    titulo = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), fonte)
    out = []
    for parte in re.split(r"\n(?=## )", texto):
        linhas = parte.strip().splitlines()
        if not linhas:
            continue
        secao = linhas[0].lstrip("# ").strip() if linhas[0].startswith("#") else "Introdução"
        corpo = "\n".join(linhas[1:]).strip() if linhas[0].startswith("#") else parte.strip()
        bloco = ""
        for par in corpo.split("\n\n"):
            if bloco and len(bloco) + len(par) > max_chars:
                out.append({"texto": bloco.strip(), "fonte": fonte, "titulo": titulo, "secao": secao})
                bloco = ""
            bloco += par + "\n\n"
        if bloco.strip():
            out.append({"texto": bloco.strip(), "fonte": fonte, "titulo": titulo, "secao": secao})
    for i, c in enumerate(out):
        c["id"] = f"{Path(fonte).stem}#{i + 1}"
    return out


def ler(caminho: Path) -> str:
    if caminho.suffix.lower() in {".md", ".txt"}:
        return caminho.read_text(encoding="utf-8")
    from docling.document_converter import DocumentConverter   # PDF, Word, HTML (módulo 5)
    return DocumentConverter().convert(str(caminho)).document.export_to_markdown()


def tokens(t: str) -> list[str]:
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", t)


@lru_cache(maxsize=1)
def embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELO_EMB)


def indexar(pasta: Path = DOCS) -> int:
    chunks = []
    for f in sorted(pasta.glob("*")):
        if f.suffix.lower() in {".md", ".txt", ".pdf", ".docx", ".html"}:
            chunks += chunks_markdown(ler(f), f.name)
    vet = embedder().encode([f"passage: {c['titulo']} › {c['secao']}\n{c['texto']}" for c in chunks], normalize_embeddings=True)
    INDICE.mkdir(exist_ok=True)
    np.save(INDICE / "vetores.npy", vet.astype(np.float32))
    (INDICE / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    carregar.cache_clear()
    return len(chunks)


@lru_cache(maxsize=1)
def carregar():
    from rank_bm25 import BM25Okapi
    if not (INDICE / "chunks.json").exists():
        indexar()
    chunks = json.loads((INDICE / "chunks.json").read_text(encoding="utf-8"))
    vet = np.load(INDICE / "vetores.npy")
    bm25 = BM25Okapi([tokens(f"{c['secao']} {c['texto']}") for c in chunks])
    return chunks, vet, bm25


def procurar(pergunta: str, k: int = 5, rrf_k: int = 60) -> list[dict]:
    """Híbrida: ordena por embeddings e por BM25 e funde as duas listas com Reciprocal Rank Fusion."""
    chunks, vet, bm25 = carregar()
    q = embedder().encode("query: " + pergunta, normalize_embeddings=True)
    denso = np.argsort(-(vet @ q))[:30]
    lexical = np.argsort(-bm25.get_scores(tokens(pergunta)))[:30]
    pontos: dict[int, float] = {}
    for lista in (denso, lexical):
        for pos, i in enumerate(lista):
            pontos[int(i)] = pontos.get(int(i), 0) + 1 / (rrf_k + pos + 1)
    melhores = sorted(pontos, key=pontos.get, reverse=True)[:k]
    return [{**chunks[i], "rrf": round(pontos[i], 4)} for i in melhores]


def por_id(cid: str) -> dict | None:
    return next((c for c in carregar()[0] if c["id"] == cid), None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["indexar", "procurar"])
    ap.add_argument("texto", nargs="*")
    ap.add_argument("--docs", type=Path, default=DOCS)
    a = ap.parse_args()
    if a.acao == "indexar":
        print(f"{indexar(a.docs)} chunks indexados de {a.docs}")
    else:
        for r in procurar(" ".join(a.texto)):
            print(f"{r['rrf']:.4f}  {r['id']:<28} {r['secao'][:40]:<40} {r['texto'][:80]!r}")
