"""Assistente de legislação portuguesa com RAG avançado.

Pipeline: artigos como unidades (parent) e números como chunks (child), pesquisa híbrida
(BM25 + vetorial com RRF), reranking com cross-encoder, expansão por referências entre
artigos e geração com citação do artigo exato.

Prepara os textos (ver README): descarrega do Diário da República os PDFs consolidados
para a pasta legislacao/ com os nomes <SIGLA>.pdf, por exemplo CT.pdf e CIVA.pdf.

Uso:
    uv run python legislacao.py indexar
    uv run python legislacao.py perguntar "Quantos dias de férias tenho?"
    uv run python legislacao.py avaliar perguntas_teste.jsonl
"""
from __future__ import annotations

import json
import os
import pickle
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from anthropic import Anthropic
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

load_dotenv()
AQUI = Path(__file__).parent
PASTA = AQUI / "legislacao"
CACHE = AQUI / "indice.pkl"
MODELO = os.getenv("MODELO", "claude-haiku-5-5")
NOMES = {"CT": "Código do Trabalho", "CIVA": "Código do IVA", "CIRS": "Código do IRS", "CSC": "Código das Sociedades Comerciais"}

RE_ARTIGO = re.compile(r"^\s*Artigo\s+(\d+)\.?\s*º\s*(-[A-Z])?\s*$", re.M)
RE_REF = re.compile(r"artigos?\s+(\d+)\.?\s*º", re.I)


@dataclass
class Artigo:
    diploma: str
    numero: str
    titulo: str
    texto: str
    refs: list[str] = field(default_factory=list)

    @property
    def chave(self) -> str:
        return f"{self.diploma}:{self.numero}"

    def cabecalho(self) -> str:
        return f"{NOMES.get(self.diploma, self.diploma)}, artigo {self.numero}.º ({self.titulo})"


def texto_pdf(caminho: Path) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(str(caminho)).pages)


def partir_artigos(texto: str, diploma: str) -> list[Artigo]:
    marcas = list(RE_ARTIGO.finditer(texto))
    artigos: dict[str, Artigo] = {}
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        corpo = texto[m.end():fim].strip()
        linhas = [l.strip() for l in corpo.splitlines() if l.strip()]
        if not linhas:
            continue
        numero = m.group(1) + (m.group(2) or "")
        titulo, resto = linhas[0], "\n".join(linhas[1:])
        refs = sorted({r for r in RE_REF.findall(resto) if r != m.group(1)})
        # versões consolidadas repetem às vezes o artigo (redações anteriores): fica a mais longa
        if numero not in artigos or len(resto) > len(artigos[numero].texto):
            artigos[numero] = Artigo(diploma, numero, titulo[:150], resto, refs)
    return list(artigos.values())


def partir_numeros(art: Artigo, max_chars: int = 900) -> list[str]:
    """Filhos: números do artigo ('1 - ...', '2 - ...'), agrupados até max_chars."""
    partes = re.split(r"\n(?=\d+\s*[-–]\s)", art.texto)
    filhos, bloco = [], ""
    for p in partes:
        if bloco and len(bloco) + len(p) > max_chars:
            filhos.append(bloco.strip()); bloco = ""
        bloco += p + "\n"
    if bloco.strip():
        filhos.append(bloco.strip())
    return filhos or [art.texto[:max_chars]]


def tokenizar(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def rrf(listas, k=60):
    p: dict[int, float] = {}
    for l in listas:
        for pos, d in enumerate(l):
            p[d] = p.get(d, 0) + 1 / (k + pos + 1)
    return sorted(p, key=p.get, reverse=True)


SYSTEM = """És um assistente de legislação laboral e fiscal portuguesa para profissionais de RH e contabilidade.
Respondes usando EXCLUSIVAMENTE os artigos em <legislacao>.

Regras:
- Cita o diploma e o artigo de cada afirmação, por exemplo (Código do Trabalho, art. 238.º, n.º 1).
- Se a pergunta depender de vários artigos, combina-os e explica a relação.
- Se os artigos fornecidos não respondem, diz "Os artigos encontrados não respondem a esta pergunta." e não especules.
- Termina com uma nota: "Informação geral, não dispensa a consulta da versão em vigor e de um jurista."
- Português de Portugal, claro e direto."""


class Assistente:
    def __init__(self, reranker: bool = True):
        self.emb = SentenceTransformer("intfloat/multilingual-e5-base")
        self.rr = CrossEncoder("BAAI/bge-reranker-v2-m3") if reranker else None
        self.llm = Anthropic()
        self.artigos: list[Artigo] = []
        self.filhos: list[tuple[int, str]] = []   # (índice do artigo pai, texto)
        if CACHE.exists():
            self.artigos, self.filhos, self.V = pickle.loads(CACHE.read_bytes())
            self._bm25()

    def _bm25(self):
        self.bm25 = BM25Okapi([tokenizar(self.artigos[p].cabecalho() + " " + t) for p, t in self.filhos])
        self.por_chave = {a.chave: i for i, a in enumerate(self.artigos)}

    def indexar(self, pasta: Path = PASTA):
        self.artigos = []
        for f in sorted(pasta.glob("*")):
            sigla = f.stem.upper()
            texto = texto_pdf(f) if f.suffix.lower() == ".pdf" else f.read_text(encoding="utf-8")
            arts = partir_artigos(texto, sigla)
            print(f"{f.name}: {len(arts)} artigos")
            self.artigos += arts
        self.filhos = [(i, t) for i, a in enumerate(self.artigos) for t in partir_numeros(a)]
        self.V = self.emb.encode([f"passage: {self.artigos[p].cabecalho()}\n{t}" for p, t in self.filhos],
                                 normalize_embeddings=True, batch_size=32, show_progress_bar=True)
        self._bm25()
        CACHE.write_bytes(pickle.dumps((self.artigos, self.filhos, self.V)))

    def recuperar(self, pergunta: str, k: int = 5, candidatos: int = 50, expandir: bool = True) -> list[Artigo]:
        q = self.emb.encode("query: " + pergunta, normalize_embeddings=True)
        vet = list(np.argsort(-(self.V @ q))[:candidatos])
        lex = list(np.argsort(-self.bm25.get_scores(tokenizar(pergunta)))[:candidatos])
        cand = rrf([vet, lex])[:candidatos]
        if self.rr is not None:
            s = self.rr.predict([(pergunta, self.artigos[self.filhos[c][0]].cabecalho() + "\n" + self.filhos[c][1]) for c in cand])
            cand = [c for _, c in sorted(zip(s, cand), key=lambda x: -x[0])]
        pais: list[int] = []
        for c in cand:                         # parent-child: devolve o artigo, sem repetidos
            p = self.filhos[c][0]
            if p not in pais:
                pais.append(p)
            if len(pais) == k:
                break
        if expandir:                           # grafo de referências: acrescenta até 2 artigos citados
            extra = []
            for p in pais[:2]:
                a = self.artigos[p]
                for r in a.refs[:2]:
                    j = self.por_chave.get(f"{a.diploma}:{r}")
                    if j is not None and j not in pais and j not in extra:
                        extra.append(j)
            pais += extra[:2]
        return [self.artigos[p] for p in pais]

    def responder(self, pergunta: str, k: int = 5) -> dict:
        arts = self.recuperar(pergunta, k)
        ctx = "\n\n".join(f'<artigo diploma="{NOMES.get(a.diploma, a.diploma)}" numero="{a.numero}.º" titulo="{a.titulo}">\n{a.texto[:4000]}\n</artigo>' for a in arts)
        r = self.llm.messages.create(model=MODELO, max_tokens=800, system=SYSTEM,
                                     messages=[{"role": "user", "content": f"<legislacao>\n{ctx}\n</legislacao>\n\nPergunta: {pergunta}"}])
        return {"resposta": r.content[0].text, "artigos": [a.chave for a in arts]}


def avaliar(a: Assistente, ficheiro: str):
    import pandas as pd
    testes = [json.loads(l) for l in open(ficheiro, encoding="utf-8")]
    linhas = []
    for t in testes:
        for nome, kw in [("híbrida", dict(expandir=False)), ("híbrida+grafo", dict(expandir=True))]:
            arts = [x.chave for x in a.recuperar(t["pergunta"], k=5, **kw)]
            alvo = f"{t['diploma']}:{t['artigo']}"
            linhas.append({"config": nome, "pergunta": t["pergunta"], "alvo": alvo,
                           "top1": arts[:1] == [alvo], "top5": alvo in arts})
    df = pd.DataFrame(linhas)
    print(df.groupby("config")[["top1", "top5"]].mean().round(2))
    print("\nFalhas no top 5:\n", df[(df.config == "híbrida") & ~df.top5][["pergunta", "alvo"]].to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "indexar":
        Assistente(reranker=False).indexar()
    elif cmd == "perguntar":
        r = Assistente().responder(" ".join(sys.argv[2:]))
        print(r["resposta"], "\n\nArtigos usados:", ", ".join(r["artigos"]))
    elif cmd == "avaliar":
        avaliar(Assistente(), sys.argv[2] if len(sys.argv) > 2 else str(AQUI / "perguntas_teste.jsonl"))
    else:
        print(__doc__)
