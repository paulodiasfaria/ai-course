"""API de produção para o classificador de reclamações.

À frente do vLLM: autenticação por chave, limite de pedidos, cache exata, saída JSON com esquema,
validação, fallback para um modelo da API e registo de métricas em SQLite.

Uso local (com o vLLM a correr em localhost:8000):
    uv run uvicorn servidor:app --port 8080
    curl -s localhost:8080/classificar -H 'X-API-Key: dev' -H 'Content-Type: application/json' \
         -d '{"texto": "A encomenda 51234 nunca chegou e já passaram 3 semanas!"}'
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:
    from comum import SYSTEM, Extracao, ler_json   # no contentor, copiado para junto deste ficheiro
except ImportError:                                  # localmente, vem do módulo 11
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "11-fine-tuning-e-alinhamento" / "use-case"))
    from comum import SYSTEM, Extracao, ler_json   # o mesmo prompt usado no treino

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1")
MODELO_SERVIDO = os.getenv("MODELO_SERVIDO", "reclamacoes")
CHAVES = set(os.getenv("API_KEYS", "dev").split(","))
LIMITE_POR_MINUTO = int(os.getenv("LIMITE_POR_MINUTO", "600"))
FALLBACK = os.getenv("MODELO_FALLBACK", "claude-haiku-5-5")       # vazio para desligar
CUSTO_GPU_HORA = float(os.getenv("CUSTO_GPU_HORA", "0.80"))       # USD, para o painel
DB = Path(os.getenv("METRICAS_DB", Path(__file__).parent / "metricas.db"))
ESQUEMA = Extracao.model_json_schema()


class Pedido(BaseModel):
    texto: str = Field(min_length=3, max_length=4000)


class Resposta(Extracao):
    origem: str = Field(description="cache, modelo ou fallback")
    latencia_ms: int


# ---------------------------------------------------------------- infraestrutura
class CacheLRU:
    def __init__(self, maximo=10_000):
        self.d: OrderedDict[str, dict] = OrderedDict()
        self.maximo = maximo

    def get(self, k):
        if k in self.d:
            self.d.move_to_end(k)
            return self.d[k]

    def set(self, k, v):
        self.d[k] = v
        self.d.move_to_end(k)
        if len(self.d) > self.maximo:
            self.d.popitem(last=False)


cache = CacheLRU()
janelas: dict[str, list[float]] = defaultdict(list)


def autenticar(x_api_key: str = Header(default="")) -> str:
    if x_api_key not in CHAVES:
        raise HTTPException(401, "Chave inválida")
    agora = time.time()
    janelas[x_api_key] = [t for t in janelas[x_api_key] if agora - t < 60] + [agora]
    if len(janelas[x_api_key]) > LIMITE_POR_MINUTO:
        raise HTTPException(429, "Limite de pedidos por minuto excedido", headers={"Retry-After": "10"})
    return x_api_key


def chave_cache(texto: str) -> str:
    return hashlib.sha256(" ".join(texto.lower().split()).encode()).hexdigest()


def registar(**m):
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS pedidos (ts REAL, cliente TEXT, origem TEXT, latencia_ms INT,
                       tokens_in INT, tokens_out INT, valido INT, categoria TEXT, usd_api REAL)""")
        con.execute("INSERT INTO pedidos VALUES (:ts, :cliente, :origem, :latencia_ms, :tokens_in, :tokens_out, :valido, :categoria, :usd_api)", m)


@asynccontextmanager
async def ciclo_de_vida(app):
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=3.0))
    yield
    await app.state.http.aclose()


app = FastAPI(title="Classificador de reclamações Loja Lusa", lifespan=ciclo_de_vida)


# ---------------------------------------------------------------- chamadas aos modelos
async def chamar_vllm(texto: str) -> tuple[str, int, int]:
    corpo = {"model": MODELO_SERVIDO, "temperature": 0, "max_tokens": 160,
             "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": texto}],
             "response_format": {"type": "json_schema", "json_schema": {"name": "extracao", "schema": ESQUEMA}}}
    r = await app.state.http.post(f"{VLLM_URL}/chat/completions", json=corpo)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"], j["usage"]["prompt_tokens"], j["usage"]["completion_tokens"]


async def chamar_fallback(texto: str) -> tuple[str, float]:
    from anthropic import AsyncAnthropic
    r = await AsyncAnthropic().messages.create(model=FALLBACK, max_tokens=300, system=SYSTEM,
                                               messages=[{"role": "user", "content": texto}])
    usd = (r.usage.input_tokens * 0.10 + r.usage.output_tokens * 0.50) / 1e6
    return "".join(b.text for b in r.content if b.type == "text"), usd


# ---------------------------------------------------------------- endpoints
@app.post("/classificar", response_model=Resposta)
async def classificar(pedido: Pedido, cliente: str = Depends(autenticar)):
    t0 = time.perf_counter()
    k = chave_cache(pedido.texto)
    if (hit := cache.get(k)) is not None:
        ms = int((time.perf_counter() - t0) * 1000)
        registar(ts=time.time(), cliente=cliente, origem="cache", latencia_ms=ms, tokens_in=0, tokens_out=0,
                 valido=1, categoria=hit["categoria"], usd_api=0.0)
        return {**hit, "origem": "cache", "latencia_ms": ms}
    origem, tin, tout, usd, extracao = "modelo", 0, 0, 0.0, None
    try:
        saida, tin, tout = await chamar_vllm(pedido.texto)
        extracao = ler_json(saida)
    except httpx.HTTPError:
        extracao = None          # vLLM em baixo ou lento: segue para o fallback
    if extracao is None and FALLBACK:
        origem = "fallback"
        saida, usd = await chamar_fallback(pedido.texto)
        extracao = ler_json(saida)
    ms = int((time.perf_counter() - t0) * 1000)
    registar(ts=time.time(), cliente=cliente, origem=origem, latencia_ms=ms, tokens_in=tin, tokens_out=tout,
             valido=int(extracao is not None), categoria=(extracao or {}).get("categoria"), usd_api=usd)
    if extracao is None:
        raise HTTPException(502, "O modelo não devolveu uma extração válida")
    cache.set(k, extracao)
    return {**extracao, "origem": origem, "latencia_ms": ms}


@app.get("/saude")
async def saude():
    try:
        r = await app.state.http.get(VLLM_URL.removesuffix("/v1") + "/health", timeout=2)
        return {"api": "ok", "vllm": "ok" if r.status_code == 200 else f"http {r.status_code}"}
    except httpx.HTTPError:
        return {"api": "ok", "vllm": "indisponível"}


@app.get("/metricas")
def metricas(minutos: int = 60):
    if not DB.exists():
        return {"pedidos": 0}
    with sqlite3.connect(DB) as con:
        linhas = con.execute("SELECT ts, origem, latencia_ms, valido, usd_api FROM pedidos WHERE ts > ?",
                             (time.time() - minutos * 60,)).fetchall()
    if not linhas:
        return {"pedidos": 0}
    lat = sorted(l[2] for l in linhas)
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
    duracao = max(1.0, linhas[-1][0] - linhas[0][0])
    rps = len(linhas) / duracao
    return {"pedidos": len(linhas), "pedidos_por_seg": round(rps, 2), "p50_ms": q(0.5), "p95_ms": q(0.95), "p99_ms": q(0.99),
            "taxa_cache": round(sum(l[1] == "cache" for l in linhas) / len(linhas), 3),
            "taxa_fallback": round(sum(l[1] == "fallback" for l in linhas) / len(linhas), 3),
            "taxa_invalidos": round(sum(not l[3] for l in linhas) / len(linhas), 4),
            "usd_api": round(sum(l[4] for l in linhas), 4),
            # custo da GPU repartido pelos pedidos servidos ao ritmo atual
            "usd_gpu_por_1000": round(CUSTO_GPU_HORA / max(rps * 3600, 1) * 1000, 4)}
