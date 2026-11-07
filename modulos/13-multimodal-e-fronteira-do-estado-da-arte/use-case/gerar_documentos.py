"""Gera faturas sintéticas «digitalizadas» (imagens com ruído, rotação e compressão) e os valores corretos.

Algumas faturas têm erros de propósito (um total mal somado, um NIF inválido) para testar as validações.
Uso:
    uv run python gerar_documentos.py --n 30
    uv run python gerar_documentos.py --n 30 --notas      # também notas de voz (TTS aberto, facebook/mms-tts-por)
Saída: entrada/doc_XXX.jpg, entrada/doc_XXX.wav (opcional), entrada/verdade.jsonl
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = Path(__file__).parent
ENTRADA = AQUI / "entrada"
EMITENTES = [("Têxteis do Ave, Lda.", "Rua da Fábrica 45, 4760-123 Vila Nova de Famalicão"),
             ("Cerâmicas Bordalo & Filhos, S.A.", "Zona Industrial, 2500-000 Caldas da Rainha"),
             ("Vidros da Marinha, Lda.", "Av. Industrial 12, 2430-000 Marinha Grande"),
             ("Transportes Rápidos do Norte, Lda.", "Rua do Porto 300, 4470-000 Maia"),
             ("Papelaria Central", "Praça da República 3, 3000-343 Coimbra"),
             ("Luz & Forma Iluminação, Lda.", "Rua das Indústrias 8, 3810-000 Aveiro")]
ARTIGOS = [("Toalha de banho 70x140", 6.90, 23), ("Lençol 180x200 algodão", 14.50, 23), ("Serviço de jantar 18 peças", 39.00, 23),
           ("Copo de vidro 33cl (cx 6)", 7.20, 23), ("Candeeiro de mesa", 24.90, 23), ("Transporte de mercadorias", 85.00, 23),
           ("Resma papel A4", 3.95, 23), ("Livro técnico", 18.00, 6), ("Almofada decorativa", 9.80, 23), ("Taça de cerâmica", 4.30, 23),
           ("Refeição de equipa", 12.50, 13), ("Água mineral (pack 6)", 2.10, 6)]


def nif_aleatorio(rnd: random.Random, valido=True) -> str:
    base = [rnd.choice([5, 5, 5, 2, 1])] + [rnd.randint(0, 9) for _ in range(7)]
    soma = sum(d * (9 - i) for i, d in enumerate(base))
    c = 11 - soma % 11
    c = 0 if c >= 10 else c
    if not valido:
        c = (c + rnd.randint(1, 9)) % 10
    return "".join(map(str, base)) + str(c)


def fonte(tamanho: int, negrito=False):
    nomes = ["DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf", "Arial Bold.ttf" if negrito else "Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"]
    for n in nomes:
        try:
            return ImageFont.truetype(n, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanho)


def euros(v: float) -> str:
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def fatura(rnd: random.Random, i: int) -> tuple[dict, list[str]]:
    emitente, morada = rnd.choice(EMITENTES)
    erro = rnd.choice([None] * 6 + ["total", "nif"])
    tipo = rnd.choice(["fatura", "fatura-recibo", "fatura simplificada"])
    d = date(2025, 1, 1) + timedelta(days=rnd.randint(0, 300))
    linhas = []
    for art, preco, taxa in rnd.sample(ARTIGOS, rnd.randint(1, 5)):
        linhas.append({"descricao": art, "quantidade": float(rnd.randint(1, 12)), "preco_unitario": round(preco * rnd.uniform(0.9, 1.1), 2), "taxa_iva": taxa})
    base = round(sum(l["quantidade"] * l["preco_unitario"] for l in linhas), 2)
    iva = round(sum(l["quantidade"] * l["preco_unitario"] * l["taxa_iva"] / 100 for l in linhas), 2)
    total = round(base + iva, 2)
    if erro == "total":
        total = round(total + rnd.choice([-10, 10, 1, -1]) * rnd.randint(1, 3), 2)
    doc = {"tipo": tipo, "emitente": emitente, "nif_emitente": nif_aleatorio(rnd, valido=erro != "nif"),
           "nif_cliente": None if tipo == "fatura simplificada" and rnd.random() < 0.5 else "515123455",
           "numero": f"{'FR' if tipo == 'fatura-recibo' else 'FS' if tipo == 'fatura simplificada' else 'FT'} {d.year}/{rnd.randint(1, 2400)}",
           "data": d.isoformat(), "linhas": linhas, "total_sem_iva": base, "total_iva": iva, "total": total, "legivel": True}
    return doc, ([] if erro is None else [erro])


def desenhar(doc: dict, rnd: random.Random) -> Image.Image:
    W, H = 1240, 1754                         # A4 a 150 dpi
    im = Image.new("L", (W, H), 250)
    dr = ImageDraw.Draw(im)
    f, fb, fg, fp = fonte(26), fonte(26, True), fonte(40, True), fonte(21)
    y = 90
    dr.text((90, y), doc["emitente"], font=fg, fill=20); y += 60
    dr.text((90, y), next(m for e, m in EMITENTES if e == doc["emitente"]), font=f, fill=40); y += 40
    dr.text((90, y), f"NIF {doc['nif_emitente'][:3]} {doc['nif_emitente'][3:6]} {doc['nif_emitente'][6:]}", font=f, fill=40); y += 90
    dr.text((90, y), doc["tipo"].upper(), font=fg, fill=10)
    dr.text((760, y + 8), doc["numero"], font=fb, fill=10); y += 70
    dr.text((90, y), f"Data: {date.fromisoformat(doc['data']).strftime('%d-%m-%Y')}", font=f, fill=30)
    dr.text((760, y), f"NIF cliente: {doc['nif_cliente'] or 'Consumidor final'}", font=f, fill=30); y += 80
    cols = [90, 640, 780, 930, 1050]
    for x, t in zip(cols, ["Descrição", "Qtd.", "Preço", "IVA", "Total"]):
        dr.text((x, y), t, font=fb, fill=10)
    y += 42
    dr.line((90, y, 1150, y), fill=60, width=2); y += 18
    for l in doc["linhas"]:
        vals = [l["descricao"], f"{l['quantidade']:g}", euros(l["preco_unitario"]), f"{l['taxa_iva']}%", euros(l["quantidade"] * l["preco_unitario"])]
        for x, t in zip(cols, vals):
            dr.text((x, y), t, font=f, fill=25)
        y += 44
    y += 20
    dr.line((640, y, 1150, y), fill=60, width=2); y += 25
    for rot, v in [("Total sem IVA", doc["total_sem_iva"]), ("IVA", doc["total_iva"]), ("TOTAL", doc["total"])]:
        dr.text((640, y), rot, font=fb if rot == "TOTAL" else f, fill=10)
        dr.text((960, y), euros(v), font=fb if rot == "TOTAL" else f, fill=10)
        y += 46
    dr.text((90, H - 140), "Processado por programa certificado n.º 0000/AT · Documento sintético para fins de formação", font=fp, fill=90)
    # «digitalização»: rotação, manchas, desfoque e compressão
    im = im.rotate(rnd.uniform(-2.5, 2.5), expand=False, fillcolor=235, resample=Image.BICUBIC)
    dr = ImageDraw.Draw(im)
    for _ in range(rnd.randint(200, 900)):
        x, yy = rnd.randint(0, W - 1), rnd.randint(0, H - 1)
        dr.point((x, yy), fill=rnd.randint(80, 200))
    return im.filter(ImageFilter.GaussianBlur(rnd.uniform(0.3, 1.1)))


NOTAS = ["Esta fatura é do centro de custo marketing. Pagar até ao dia quinze.",
         "Atenção, a fatura do transporte veio com o valor errado, confirmar com o fornecedor antes de pagar.",
         "Lançar no projeto da loja de Coimbra. Já está paga por transferência.",
         "Fatura de material de escritório, centro de custo administrativo."]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--notas", action="store_true", help="gera notas de voz para algumas faturas")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    ENTRADA.mkdir(exist_ok=True)
    tts = None
    if args.notas:
        from transformers import pipeline
        tts = pipeline("text-to-speech", model="facebook/mms-tts-por")
    with open(ENTRADA / "verdade.jsonl", "w", encoding="utf-8") as fv:
        for i in range(args.n):
            doc, erros = fatura(rnd, i)
            nome = f"doc_{i:03d}"
            desenhar(doc, rnd).save(ENTRADA / f"{nome}.jpg", quality=rnd.randint(45, 80))
            nota = None
            if tts and rnd.random() < 0.4:
                import numpy as np
                import soundfile as sf
                nota = rnd.choice(NOTAS)
                audio = tts(nota)
                sf.write(ENTRADA / f"{nome}.wav", np.asarray(audio["audio"]).squeeze(), audio["sampling_rate"])
            fv.write(json.dumps({"ficheiro": f"{nome}.jpg", "documento": doc, "erros_inseridos": erros, "nota": nota}, ensure_ascii=False) + "\n")
    print(f"{args.n} documentos em {ENTRADA}")
