"""SFT com QLoRA (TRL + PEFT) do modelo base sobre as reclamações geradas.

Uso (GPU com 16 GB chega; numa T4 do Colab demora ~20 min com 1200 exemplos e 2 épocas):
    uv run python treinar_sft.py
    uv run python treinar_sft.py --base Qwen/Qwen2.5-3B-Instruct --r 32
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from trl import SFTConfig, SFTTrainer

from modelo_local import BASE, carregar

AQUI = Path(__file__).parent

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--epocas", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--saida", default=str(AQUI / "saidas" / "sft"))
    args = ap.parse_args()

    modelo, tok = carregar(args.base, quatro_bits=True, treinavel=True)
    tok.padding_side = "right"         # no treino, preenchimento à direita
    modelo = prepare_model_for_kbit_training(modelo, use_gradient_checkpointing=True)
    dados = load_dataset("json", data_files={"train": str(AQUI / "dados/treino.jsonl"),
                                             "validation": str(AQUI / "dados/validacao.jsonl")})
    lora = LoraConfig(r=args.r, lora_alpha=2 * args.r, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    cfg = SFTConfig(
        output_dir=args.saida, num_train_epochs=args.epocas, learning_rate=args.lr, lr_scheduler_type="cosine", warmup_ratio=0.05,
        per_device_train_batch_size=8, gradient_accumulation_steps=2, per_device_eval_batch_size=16,
        max_length=768, eval_strategy="steps", eval_steps=25, save_strategy="steps", save_steps=25, save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="eval_loss", logging_steps=5,
        bf16=bf16, fp16=not bf16, gradient_checkpointing=True, report_to="none",
    )
    trainer = SFTTrainer(model=modelo, args=cfg, train_dataset=dados["train"], eval_dataset=dados["validation"],
                         processing_class=tok, peft_config=lora)
    trainer.model.print_trainable_parameters()
    trainer.train()
    final = Path(args.saida) / "final"
    trainer.save_model(str(final))     # guarda só o adaptador (dezenas de MB)
    tok.save_pretrained(str(final))
    print("Adaptador em", final, "| melhor eval_loss:", trainer.state.best_metric)
