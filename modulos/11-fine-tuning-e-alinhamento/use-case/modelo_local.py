"""Carregar o modelo base (opcionalmente em 4 bits) e gerar respostas em lote."""
from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

BASE = "Qwen/Qwen2.5-1.5B-Instruct"


def dtype_gpu() -> torch.dtype:
    # As T4 do Colab não suportam bf16: usamos fp16 nessas GPUs
    return torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16


def carregar(base: str = BASE, adaptador: str | None = None, quatro_bits: bool = True, treinavel: bool = False):
    tok = AutoTokenizer.from_pretrained(base)
    tok.padding_side = "left"          # geração em lote: preencher à esquerda
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    kw = {"device_map": "auto", "dtype": dtype_gpu()}
    if quatro_bits:
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=dtype_gpu(), bnb_4bit_use_double_quant=True)
    modelo = AutoModelForCausalLM.from_pretrained(base, **kw)
    if adaptador:
        from peft import PeftModel
        modelo = PeftModel.from_pretrained(modelo, adaptador, is_trainable=treinavel)
    if not treinavel:
        modelo.eval()
    return modelo, tok


@torch.no_grad()
def gerar(modelo, tok, prompts: list[list[dict]], max_new_tokens: int = 128, lote: int = 16) -> list[str]:
    saidas = []
    for i in range(0, len(prompts), lote):
        textos = [tok.apply_chat_template(p, tokenize=False, add_generation_prompt=True) for p in prompts[i:i + lote]]
        enc = tok(textos, return_tensors="pt", padding=True).to(modelo.device)
        out = modelo.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.pad_token_id)
        saidas += tok.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    return saidas
