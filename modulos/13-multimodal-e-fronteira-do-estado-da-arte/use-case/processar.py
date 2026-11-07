"""Processador de documentos digitalizados: visão + validação + revisão + notas de voz.

Para cada imagem em entrada/:
  1. um modelo de visão extrai os campos para um esquema Pydantic;
  2. validações determinísticas (NIF, somas, IVA, datas);
  3. se falhar, uma segunda leitura focada nos problemas; se continuar a falhar, fica para revisão humana;
  4. se houver uma nota de voz com o mesmo nome (.wav, .mp3, .m4a), transcreve com Whisper e extrai instruções;
  5. grava tudo em documentos.db e exporta documentos.csv.

Uso:
    uv run python processar.py
    uv run python processar.py --whisper openai/whisper-small     # CPU
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from validacao import Documento, validar

load_dotenv()
AQUI = Path(__file__).parent
ENTRADA = AQUI / "entrada"
DB = AQUI / "documentos.db"
MODELO_VISAO = os.getenv("MODELO_FORTE", "claude-sonnet-5-5")
MODELO = os.getenv("MODELO", "claude-haiku-5-5")
AUDIO = (".wav", ".mp3", ".m4a", ".ogg")

PROMPT = """Extrai os dados desta fatura portuguesa digitalizada.
- Valores em euros como números (1 234,50 € → 1234.5). Preço unitário sem IVA.
- NIF só com os 9 dígitos. Data em AAAA-MM-DD.
- Copia os valores tal como estão impressos, mesmo que pareçam errados: não corrijas contas.
- Se algo estiver ilegível, marca legivel=false em vez de adivinhar."""


class Nota(BaseModel):
    centro_custo: Optional[str] = Field(description="Por exemplo marketing, administrativo, projeto Coimbra; null se não for dito")
    pagar_ate_dia: Optional[int] = Field(description="Dia do mês indicado para pagar, ou null")
    ja_pago: bool
    alerta: Optional[str] = Field(description="Qualquer aviso para quem processa (valor errado, confirmar, etc.), ou null")


def imagem(caminho: Path) -> dict:
    tipo = "image/png" if caminho.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": tipo, "data": base64.standard_b64encode(caminho.read_bytes()).decode()}}


def extrair(llm: Anthropic, caminho: Path, problemas: list[str] | None = None) -> Documento:
    texto = PROMPT
    if problemas:
        texto += ("\n\nUma primeira leitura teve estes problemas de validação. Volta a ler com atenção os campos envolvidos "
                  "(dígitos do NIF, quantidades, preços, totais). Se o próprio documento tiver um erro, mantém o valor impresso:\n- "
                  + "\n- ".join(problemas))
    r = llm.messages.parse(model=MODELO_VISAO, max_tokens=4000, output_format=Documento,
                           messages=[{"role": "user", "content": [imagem(caminho), {"type": "text", "text": texto}]}])
    return r.parsed_output


_asr = None


def transcrever(caminho: Path, modelo: str) -> str:
    global _asr
    if _asr is None:
        import torch
        from transformers import pipeline
        _asr = pipeline("automatic-speech-recognition", model=modelo, device=0 if torch.cuda.is_available() else -1)
    return _asr(str(caminho), generate_kwargs={"language": "portuguese", "task": "transcribe"})["text"].strip()


def interpretar_nota(llm: Anthropic, transcricao: str) -> Nota:
    r = llm.messages.parse(model=MODELO, max_tokens=1000, output_format=Nota, messages=[{"role": "user", "content":
        f"Nota de voz deixada por um colega sobre uma fatura. Extrai as instruções.\n\nTranscrição: {transcricao}"}])
    return r.parsed_output


def preparar_db(con: sqlite3.Connection):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS documentos (ficheiro TEXT PRIMARY KEY, tipo TEXT, emitente TEXT, nif_emitente TEXT, nif_cliente TEXT,
        numero TEXT, data TEXT, total_sem_iva REAL, total_iva REAL, total REAL, estado TEXT, problemas TEXT, leituras INT,
        transcricao TEXT, centro_custo TEXT, pagar_ate_dia INT, ja_pago INT, alerta TEXT, json TEXT);
    CREATE TABLE IF NOT EXISTS linhas (ficheiro TEXT, descricao TEXT, quantidade REAL, preco_unitario REAL, taxa_iva INT);""")


def processar(llm: Anthropic, caminho: Path, whisper: str) -> dict:
    doc = extrair(llm, caminho)
    problemas, leituras = validar(doc), 1
    if problemas:
        doc2 = extrair(llm, caminho, problemas)
        p2 = validar(doc2)
        leituras = 2
        if len(p2) <= len(problemas):
            doc, problemas = doc2, p2
    estado = "ok" if not problemas else "revisao"
    reg = {"ficheiro": caminho.name, **doc.model_dump(exclude={"linhas", "legivel"}), "estado": estado,
           "problemas": json.dumps(problemas, ensure_ascii=False), "leituras": leituras, "transcricao": None,
           "centro_custo": None, "pagar_ate_dia": None, "ja_pago": None, "alerta": None, "json": doc.model_dump_json()}
    audio = next((caminho.with_suffix(s) for s in AUDIO if caminho.with_suffix(s).exists()), None)
    if audio:
        reg["transcricao"] = transcrever(audio, whisper)
        nota = interpretar_nota(llm, reg["transcricao"])
        reg.update(centro_custo=nota.centro_custo, pagar_ate_dia=nota.pagar_ate_dia, ja_pago=int(nota.ja_pago), alerta=nota.alerta)
        if nota.alerta and estado == "ok":
            reg["estado"] = "revisao"      # uma pessoa pediu atenção: não automatizar
    return reg, doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--whisper", default="openai/whisper-large-v3-turbo")
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()
    llm = Anthropic()
    imagens = sorted(p for p in ENTRADA.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if args.limite:
        imagens = imagens[: args.limite]
    with sqlite3.connect(DB) as con:
        preparar_db(con)
        for i, img in enumerate(imagens, 1):
            reg, doc = processar(llm, img, args.whisper)
            con.execute("DELETE FROM documentos WHERE ficheiro = ?", (img.name,))
            con.execute("DELETE FROM linhas WHERE ficheiro = ?", (img.name,))
            con.execute(f"INSERT INTO documentos ({', '.join(reg)}) VALUES ({', '.join('?' * len(reg))})", list(reg.values()))
            con.executemany("INSERT INTO linhas VALUES (?, ?, ?, ?, ?)",
                            [(img.name, l.descricao, l.quantidade, l.preco_unitario, l.taxa_iva) for l in doc.linhas])
            icone = "✅" if reg["estado"] == "ok" else "👀"
            print(f"{icone} {i}/{len(imagens)} {img.name}: {doc.emitente[:30]} · {doc.total:.2f} € · {reg['leituras']} leitura(s)"
                  + (f" · {'; '.join(json.loads(reg['problemas']))}" if reg["estado"] != "ok" and reg["problemas"] != "[]" else "")
                  + (f" · nota: {reg['transcricao'][:60]}" if reg["transcricao"] else ""))
        linhas = con.execute("SELECT * FROM documentos ORDER BY ficheiro").fetchall()
        cols = [d[0] for d in con.execute("SELECT * FROM documentos LIMIT 0").description]
    with open(AQUI / "documentos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([c for c in cols if c != "json"])
        w.writerows([[v for c, v in zip(cols, l) if c != "json"] for l in linhas])
    rev = sum(l[cols.index("estado")] == "revisao" for l in linhas)
    print(f"\n{len(linhas)} documentos · {rev} para revisão humana · documentos.db e documentos.csv atualizados")
