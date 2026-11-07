"""Funde o adaptador LoRA no modelo base (em 16 bits) e, opcionalmente, publica no Hugging Face Hub.

O resultado, em modelo_final/, é o que o módulo 12 quantiza e serve.
Uso:
    uv run python fundir.py --adaptador saidas/dpo/final
    uv run python fundir.py --adaptador saidas/sft/final --hub o-teu-utilizador/qwen2.5-1.5b-reclamacoes-pt
"""
from __future__ import annotations

import argparse
from pathlib import Path

from modelo_local import BASE, carregar

AQUI = Path(__file__).parent

CARTAO = """---
base_model: {base}
library_name: transformers
license: apache-2.0
language: [pt]
tags: [lora, qlora, classificacao, extracao, portugues]
---
# Classificador de reclamações (pt-PT)

Afinado a partir de `{base}` com QLoRA (SFT{dpo}) para classificar reclamações de clientes de uma loja de artigos para a casa
e extrair categoria, urgência, número de encomenda, produto e pedido, em JSON.

- **Dados:** reclamações sintéticas geradas e rotuladas por um modelo maior (destilação). Não contêm dados pessoais reais.
- **Métricas no teste:** ver `resultados/` no repositório do curso.
- **Limitações:** treinado só com dados sintéticos de um domínio; avalia com dados reais antes de usar em produção.
"""

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--adaptador", required=True)
    ap.add_argument("--saida", default=str(AQUI / "modelo_final"))
    ap.add_argument("--hub", help="repo_id no Hugging Face Hub (precisa de huggingface-cli login)")
    args = ap.parse_args()
    # Fundir sobre o modelo em 16 bits, não sobre a versão de 4 bits
    modelo, tok = carregar(BASE, adaptador=args.adaptador, quatro_bits=False)
    modelo = modelo.merge_and_unload()
    modelo.save_pretrained(args.saida, safe_serialization=True)
    tok.padding_side = "right"
    tok.save_pretrained(args.saida)
    Path(args.saida, "README.md").write_text(CARTAO.format(base=BASE, dpo=" + DPO" if "dpo" in args.adaptador else ""), encoding="utf-8")
    print("Modelo fundido em", args.saida)
    if args.hub:
        modelo.push_to_hub(args.hub)
        tok.push_to_hub(args.hub)
        from huggingface_hub import upload_file
        upload_file(path_or_fileobj=str(Path(args.saida, "README.md")), path_in_repo="README.md", repo_id=args.hub)
        print(f"Publicado em https://huggingface.co/{args.hub}")
