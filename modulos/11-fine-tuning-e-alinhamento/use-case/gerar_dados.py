"""Gera um conjunto de reclamações rotuladas por destilação de um modelo grande.

Cada pedido ao modelo fixa uma combinação de categoria, canal, tom e particularidades, para forçar variedade.
Uso:
    uv run python gerar_dados.py --n 1500
Saída: dados/treino.jsonl, dados/validacao.jsonl, dados/teste.jsonl (formato prompt/completion)
       dados/teste_bruto.jsonl (texto + rótulo, para avaliar)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from comum import CATEGORIAS, Extracao, exemplo_chat

load_dotenv()
MODELO_PROFESSOR = os.getenv("MODELO_FORTE", "claude-sonnet-5-5")
AQUI = Path(__file__).parent
POR_PEDIDO = 10
PESOS = {"entrega_atrasada": 0.24, "produto_danificado": 0.18, "produto_errado": 0.10, "faturacao": 0.12,
         "devolucao": 0.16, "atendimento": 0.12, "outro": 0.08}
CANAIS = ["email", "formulário do site", "chat do site", "comentário no Facebook", "mensagem de Instagram", "transcrição de chamada"]
TONS = ["calmo e educado", "irritado", "muito irritado, com maiúsculas e pontos de exclamação", "confuso", "formal", "sarcástico", "apressado e telegráfico"]
EXTRAS = ["com erros ortográficos e sem acentos", "sem número de encomenda", "o número de encomenda vem com # ou espaços",
          "menciona dois produtos mas só um tem problema", "mistura duas questões (a principal deve ser clara)",
          "muito curta (uma frase)", "longa, com contexto pessoal", "ambígua entre duas categorias", "ameaça ir ao Livro de Reclamações",
          "pede só informação", "escrita por um cliente idoso", ""]
PRODUTOS = "toalhas, lençóis, edredão, frigideira, panela de pressão, faqueiro, taças, copos, candeeiro, abajur, espelho, tapete, cortinados, almofadas, cesto de roupa, organizador, vela aromática, jarra, serviço de jantar, cafeteira"


class Item(BaseModel):
    texto: str = Field(description="A reclamação tal como o cliente a escreveu, em português de Portugal")
    rotulo: Extracao


class Lote(BaseModel):
    itens: list[Item]


def pedir_lote(llm: Anthropic, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    cats = rnd.choices(list(PESOS), weights=list(PESOS.values()), k=POR_PEDIDO)
    specs = "\n".join(f"{i + 1}. categoria={c}; canal={rnd.choice(CANAIS)}; tom={rnd.choice(TONS)}; {rnd.choice(EXTRAS)}"
                      for i, c in enumerate(cats))
    prompt = (f"Gera {POR_PEDIDO} reclamações realistas e diferentes entre si de clientes da Loja Lusa, uma cadeia portuguesa de artigos para a casa "
              f"(lojas Online, Porto, Lisboa, Braga, Faro). Produtos possíveis: {PRODUTOS}. Números de encomenda têm 5 ou 6 dígitos.\n"
              f"Segue estas especificações, uma por reclamação:\n{specs}\n\n"
              "Para cada uma, dá o rótulo correto. A categoria do rótulo pode diferir da especificação se o texto que escreveste o justificar. "
              "Não uses nomes nem dados pessoais reais.")
    r = llm.messages.parse(model=MODELO_PROFESSOR, max_tokens=8000, output_format=Lote, messages=[{"role": "user", "content": prompt}])
    return [{"texto": it.texto.strip(), "rotulo": it.rotulo.model_dump()} for it in r.parsed_output.itens]


def chave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()[:80]


def dividir(itens: list[dict], seed=0) -> tuple[list, list, list]:
    """Divisão estratificada por categoria: 80/10/10."""
    rnd = random.Random(seed)
    tr, va, te = [], [], []
    for cat in CATEGORIAS:
        grupo = [x for x in itens if x["rotulo"]["categoria"] == cat]
        rnd.shuffle(grupo)
        n = len(grupo)
        te += grupo[: n // 10]
        va += grupo[n // 10: n // 5]
        tr += grupo[n // 5:]
    for parte in (tr, va, te):
        rnd.shuffle(parte)
    return tr, va, te


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--paralelo", type=int, default=6)
    args = ap.parse_args()
    llm = Anthropic()
    itens, vistos = [], set()
    with ThreadPoolExecutor(args.paralelo) as ex:
        futuros = [ex.submit(pedir_lote, llm, s) for s in range(-(-args.n // POR_PEDIDO))]
        for i, f in enumerate(as_completed(futuros), 1):
            try:
                for it in f.result():
                    k = chave(it["texto"])
                    if k not in vistos and len(it["texto"]) > 15:
                        vistos.add(k)
                        itens.append(it)
            except Exception as e:  # um lote falhado não deve parar a geração
                print("lote falhou:", e)
            print(f"\r{i}/{len(futuros)} lotes, {len(itens)} exemplos únicos", end="")
    print("\nCategorias:", dict(Counter(x["rotulo"]["categoria"] for x in itens)))
    tr, va, te = dividir(itens)
    d = AQUI / "dados"
    d.mkdir(exist_ok=True)
    for nome, parte in [("treino", tr), ("validacao", va), ("teste", te)]:
        with open(d / f"{nome}.jsonl", "w", encoding="utf-8") as f:
            for x in parte:
                f.write(json.dumps(exemplo_chat(x["texto"], x["rotulo"]), ensure_ascii=False) + "\n")
    with open(d / "teste_bruto.jsonl", "w", encoding="utf-8") as f:
        for x in te:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with open(d / "treino_bruto.jsonl", "w", encoding="utf-8") as f:
        for x in tr:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"treino {len(tr)}, validação {len(va)}, teste {len(te)} em {d}")
