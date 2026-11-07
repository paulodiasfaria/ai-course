# Use case: modelo pequeno especialista em português

Afinar o `Qwen/Qwen2.5-1.5B-Instruct` com QLoRA para classificar reclamações de clientes da Loja Lusa e extrair campos em JSON, e compará-lo com o modelo base e com um modelo grande na API.

| Ficheiro | O que faz |
|---|---|
| [`comum.py`](comum.py) | Esquema da extração (Pydantic), prompt de sistema, formato prompt/completion e métricas |
| [`gerar_dados.py`](gerar_dados.py) | Gera ~1500 reclamações rotuladas por destilação (Claude), com variedade forçada de categoria, canal, tom e particularidades; divide 80/10/10 estratificado |
| [`modelo_local.py`](modelo_local.py) | Carrega o modelo (4 bits, com ou sem adaptador) e gera em lote |
| [`treinar_sft.py`](treinar_sft.py) | SFT com QLoRA (TRL + PEFT), guarda o melhor checkpoint pela perda de validação |
| [`avaliar.py`](avaliar.py) | Mesmas métricas para modelo base, few-shot, afinado e API: JSON válido, exatidão por campo, F1 macro, latência, custo |
| [`treinar_dpo.py`](treinar_dpo.py) | DPO com pares on-policy (erros do modelo SFT como rejeitadas) |
| [`fundir.py`](fundir.py) | Funde o adaptador no modelo em 16 bits, gera o model card e publica no Hub (opcional) |

```bash
uv sync --extra finetuning
uv run python gerar_dados.py --n 1500
uv run python avaliar.py --modelo base
uv run python avaliar.py --modelo claude:claude-haiku-5-5
uv run python treinar_sft.py
uv run python avaliar.py --modelo saidas/sft/final
uv run python treinar_dpo.py
uv run python avaliar.py --modelo saidas/dpo/final
uv run python fundir.py --adaptador saidas/sft/final      # usa o melhor dos dois
uv run python avaliar.py --tabela
```

**Hardware:** GPU NVIDIA com 16 GB (T4 do Colab gratuito, com fp16) ou mais. Em GPUs com bf16 (A10, L4, A100, RTX 30xx/40xx) o treino é mais rápido e estável.

**Saídas** (ignoradas pelo Git): `dados/`, `saidas/` (adaptadores e checkpoints), `resultados/` (métricas e erros), `modelo_final/` (modelo fundido, usado no módulo 12).
