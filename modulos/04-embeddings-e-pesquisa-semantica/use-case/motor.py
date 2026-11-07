"""Motor de pesquisa com BM25, pesquisa vetorial (Qdrant) e híbrida (RRF).

Reutilizável nos módulos de RAG:

    from motor import Motor
    m = Motor("noticias", path="qdrant_db")
    m.indexar(textos, metadados)
    m.pesquisar("inflação no Brasil", modo="hibrida", k=5)
"""
from __future__ import annotations

import pickle
import re
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

PREFIXOS = {"intfloat/multilingual-e5": ("query: ", "passage: ")}


def tokenizar(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def rrf(listas: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    pont: dict[int, float] = {}
    for lista in listas:
        for pos, doc in enumerate(lista):
            pont[doc] = pont.get(doc, 0) + 1 / (k + pos + 1)
    return sorted(pont.items(), key=lambda x: x[1], reverse=True)


class Motor:
    def __init__(self, colecao: str, path: str | None = "qdrant_db", modelo: str = "intfloat/multilingual-e5-base"):
        self.colecao = colecao
        self.qd = QdrantClient(path=path) if path else QdrantClient(":memory:")
        self.emb = SentenceTransformer(modelo)
        self.pq, self.pp = next((v for k, v in PREFIXOS.items() if modelo.startswith(k)), ("", ""))
        self.bm25_path = Path(path or ".") / f"{colecao}_bm25.pkl"
        self.textos: list[str] = []
        self.bm25: BM25Okapi | None = None
        if self.bm25_path.exists():
            self.textos, self.bm25 = pickle.loads(self.bm25_path.read_bytes())

    # ---------- indexação ----------
    def indexar(self, textos: list[str], metadados: list[dict] | None = None, batch: int = 64):
        metadados = metadados or [{} for _ in textos]
        dim = self.emb.get_sentence_embedding_dimension()
        if self.qd.collection_exists(self.colecao):
            self.qd.delete_collection(self.colecao)
        self.qd.create_collection(self.colecao, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
        for i in range(0, len(textos), batch):
            parte = textos[i:i + batch]
            vet = self.emb.encode([self.pp + t for t in parte], normalize_embeddings=True)
            self.qd.upload_points(self.colecao, [
                models.PointStruct(id=i + j, vector=v.tolist(), payload={"texto": t, **metadados[i + j]})
                for j, (t, v) in enumerate(zip(parte, vet))
            ])
        self.textos = list(textos)
        self.bm25 = BM25Okapi([tokenizar(t) for t in textos])
        self.bm25_path.parent.mkdir(parents=True, exist_ok=True)
        self.bm25_path.write_bytes(pickle.dumps((self.textos, self.bm25)))

    # ---------- pesquisa ----------
    def _vetorial(self, pergunta: str, k: int, filtro: models.Filter | None = None) -> list[tuple[int, float]]:
        q = self.emb.encode(self.pq + pergunta, normalize_embeddings=True)
        hits = self.qd.query_points(self.colecao, query=q.tolist(), limit=k, query_filter=filtro).points
        return [(h.id, h.score) for h in hits]

    def _bm25(self, pergunta: str, k: int) -> list[tuple[int, float]]:
        s = self.bm25.get_scores(tokenizar(pergunta))
        top = np.argsort(-s)[:k]
        return [(int(i), float(s[i])) for i in top]

    def pesquisar(self, pergunta: str, modo: str = "hibrida", k: int = 5, candidatos: int = 50,
                  filtro: models.Filter | None = None) -> list[dict]:
        if modo == "vetorial":
            res = self._vetorial(pergunta, k, filtro)
        elif modo == "bm25":
            res = self._bm25(pergunta, k)
        elif modo == "hibrida":
            res = rrf([[i for i, _ in self._bm25(pergunta, candidatos)],
                       [i for i, _ in self._vetorial(pergunta, candidatos, filtro)]])[:k]
        else:
            raise ValueError(f"modo desconhecido: {modo}")
        return [{"id": i, "score": round(s, 4), "texto": self.textos[i]} for i, s in res]
