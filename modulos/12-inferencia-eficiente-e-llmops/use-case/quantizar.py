"""Quantiza o modelo afinado do módulo 11 com o llm-compressor, num formato que o vLLM carrega diretamente.

Uso (GPU necessária):
    uv run python quantizar.py --esquema w4a16      # GPTQ 4 bits, com calibração
    uv run python quantizar.py --esquema fp8        # FP8 dinâmico, sem calibração (GPUs Ada/Hopper para tirar partido)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

AQUI = Path(__file__).parent
M11 = AQUI.parent.parent / "11-fine-tuning-e-alinhamento" / "use-case"

if __name__ == "__main__":
    from llmcompressor import oneshot
    from llmcompressor.modifiers.quantization import GPTQModifier, QuantizationModifier

    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=str(M11 / "modelo_final"))
    ap.add_argument("--esquema", choices=["w4a16", "fp8"], default="w4a16")
    ap.add_argument("--amostras", type=int, default=256)
    args = ap.parse_args()
    saida = AQUI / "modelos" / f"reclamacoes-{args.esquema}"

    tok = AutoTokenizer.from_pretrained(args.modelo)
    modelo = AutoModelForCausalLM.from_pretrained(args.modelo, dtype="auto", device_map="auto")

    if args.esquema == "fp8":
        receita = QuantizationModifier(targets="Linear", scheme="FP8_DYNAMIC", ignore=["lm_head"])
        oneshot(model=modelo, recipe=receita)
    else:
        # Calibração com prompts reais da tarefa: o GPTQ ajusta-se às ativações que vai ver em produção
        linhas = [json.loads(l) for l in (M11 / "dados" / "treino.jsonl").read_text(encoding="utf-8").splitlines()][: args.amostras]
        textos = [tok.apply_chat_template(x["prompt"] + x["completion"], tokenize=False) for x in linhas]
        calib = Dataset.from_dict({"text": textos}).map(
            lambda x: tok(x["text"], max_length=512, truncation=True, add_special_tokens=False), remove_columns=["text"])
        receita = GPTQModifier(targets="Linear", scheme="W4A16", ignore=["lm_head"])
        oneshot(model=modelo, dataset=calib, recipe=receita, max_seq_length=512, num_calibration_samples=len(linhas))

    modelo.save_pretrained(saida, save_compressed=True)
    tok.save_pretrained(saida)
    tamanho = sum(f.stat().st_size for f in saida.glob("*.safetensors")) / 1e9
    print(f"Modelo quantizado em {saida} ({tamanho:.2f} GB)")
