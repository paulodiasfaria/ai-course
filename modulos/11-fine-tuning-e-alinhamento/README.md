# M11 · Fine-tuning e alinhamento

Adaptar um modelo aberto a uma tarefa ou estilo concretos.

| | |
|---|---|
| Fase | Modelos e produção |
| Duração estimada | 12 h |
| Complexidade | 5/5 |
| Ferramentas | PyTorch, transformers, PEFT, TRL, Unsloth, bitsandbytes |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Modelo pequeno especialista em português

Afinar um modelo de 1 a 4 mil milhões de parâmetros (Qwen ou Llama) para classificar e extrair informação de reclamações de clientes em português, superar o modelo base e aproximar-se de um modelo grande a uma fração do custo.

## Objetivos

- Decidir com critério entre prompting, RAG e fine-tuning
- Preparar e gerar dados de treino de qualidade
- Afinar com LoRA e QLoRA numa única GPU
- Alinhar preferências com DPO e perceber o RL com recompensas verificáveis (GRPO)

## Leituras de base

LoRA (Hu et al., 2021); QLoRA (Dettmers et al., 2023); DPO (Rafailov et al., 2023); DeepSeekMath e GRPO (Shao et al., 2024)
