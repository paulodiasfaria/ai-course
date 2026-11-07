"""DPO sobre o modelo afinado com SFT, usando os erros do próprio modelo como respostas rejeitadas.

1. O modelo SFT responde a exemplos de treino.
2. Onde erra, cria um par: escolhida = rótulo correto, rejeitada = resposta do modelo.
3. Treina o mesmo adaptador com DPO (o modelo de referência é o SFT, com o adaptador desligado pelo TRL).

Uso:
    uv run python treinar_dpo.py --sft saidas/sft/final
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from trl import DPOConfig, DPOTrainer

from comum import exemplo_chat, ler_json, normalizar, CAMPOS
from modelo_local import BASE, carregar, gerar

AQUI = Path(__file__).parent


def pares_on_policy(modelo, tok, n: int) -> list[dict]:
    treino = [json.loads(l) for l in (AQUI / "dados/treino_bruto.jsonl").read_text(encoding="utf-8").splitlines()][:n]
    saidas = gerar(modelo, tok, [exemplo_chat(x["texto"])["prompt"] for x in treino])
    pares = []
    for x, s in zip(treino, saidas):
        p = ler_json(s)
        certo = p is not None and all(normalizar(p[c]) == normalizar(x["rotulo"][c]) for c in CAMPOS)
        if not certo:
            ex = exemplo_chat(x["texto"], x["rotulo"])
            pares.append({"prompt": ex["prompt"], "chosen": ex["completion"], "rejected": [{"role": "assistant", "content": s.strip()}]})
    return pares


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sft", default=str(AQUI / "saidas/sft/final"))
    ap.add_argument("--n", type=int, default=800, help="exemplos de treino a usar para encontrar erros")
    ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--lora16", action="store_true")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--saida", default=str(AQUI / "saidas" / "dpo"))
    args = ap.parse_args()

    modelo, tok = carregar(args.base, adaptador=args.sft, quatro_bits=not args.lora16, treinavel=True)
    modelo.eval()
    pares = pares_on_policy(modelo, tok, args.n)
    print(f"{len(pares)} pares a partir de {args.n} exemplos ({len(pares) / args.n:.0%} de erros no treino)")
    if len(pares) < 20:
        raise SystemExit("Poucos erros para um DPO útil: o SFT já acerta quase tudo no treino. Tenta exemplos mais difíceis.")
    modelo.train()
    modelo.enable_input_require_grads()   # necessário com gradient checkpointing sobre um modelo de 4 bits
    tok.padding_side = "right"
    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    fp16 = torch.cuda.is_available() and not bf16   # T4: fp16; CPU (só para testes): nenhum
    cfg = DPOConfig(output_dir=args.saida, beta=args.beta, learning_rate=5e-6, num_train_epochs=1,
                    per_device_train_batch_size=4, gradient_accumulation_steps=4, max_length=768,
                    logging_steps=5, bf16=bf16, fp16=fp16, gradient_checkpointing=True, report_to="none")
    trainer = DPOTrainer(model=modelo, ref_model=None, args=cfg, train_dataset=Dataset.from_list(pares), processing_class=tok)
    trainer.train()
    final = Path(args.saida) / "final"
    trainer.save_model(str(final))
    tok.save_pretrained(str(final))
    print("Adaptador DPO em", final)
