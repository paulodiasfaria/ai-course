# Use case: API de produção para o modelo afinado

Pegar no classificador de reclamações do módulo 11, quantizá-lo, servi-lo com vLLM atrás de uma API FastAPI em Docker, testar carga e acompanhar latência, custo e qualidade num painel.

```
clientes ──X-API-Key──> API FastAPI ──> vLLM (modelo quantizado)
                          │  cache, limites, validação
                          ├──> fallback: Claude Haiku (se a resposta for inválida ou o vLLM falhar)
                          └──> metricas.db ──> painel Gradio
```

| Ficheiro | O que faz |
|---|---|
| [`quantizar.py`](quantizar.py) | Quantiza `modelo_final/` do módulo 11 com o `llm-compressor`: GPTQ W4A16 (calibrado com prompts da tarefa) ou FP8 |
| [`servidor.py`](servidor.py) | API: autenticação, limite por minuto, cache exata, JSON com esquema no vLLM, validação Pydantic, fallback, métricas em SQLite, `/saude` e `/metricas` |
| [`carga.py`](carga.py) | Teste de carga a vários níveis de concorrência, com exatidão medida contra os rótulos do teste do módulo 11 |
| [`painel.py`](painel.py) | Painel Gradio: p95, pedidos por segundo, custo por 1000 pedidos, taxa de cache, fallback e distribuição das categorias |
| [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml) | Dois serviços: `vllm` (imagem oficial, GPU) e `api` |

## Passos

```bash
# 1. Quantizar (GPU; precisa do modelo_final/ do módulo 11)
uv sync --extra deploy
uv run python quantizar.py --esquema w4a16
uv run python quantizar.py --esquema fp8

# 2a. Servir sem Docker
uv run vllm serve modelos/reclamacoes-w4a16 --served-model-name reclamacoes --max-model-len 2048
uv run uvicorn servidor:app --port 8080           # noutro terminal

# 2b. Ou com Docker Compose (precisa do nvidia-container-toolkit)
MODELO=reclamacoes-w4a16 docker compose up --build

# 3. Testar
curl -s localhost:8080/classificar -H 'X-API-Key: dev' -H 'Content-Type: application/json' \
     -d '{"texto": "A encomenda 51234 nunca chegou e já passaram 3 semanas!"}'
uv run python carga.py --nome w4a16
uv run python painel.py                            # http://localhost:7860

# 4. Comparar variantes: repete 2 e 3 com o modelo em 16 bits e com FP8
uv run python carga.py --comparar
```

## Sem GPU

- **Ollama:** converte para GGUF com o llama.cpp (`python convert_hf_to_gguf.py ../../11-fine-tuning-e-alinhamento/use-case/modelo_final --outfile reclamacoes.gguf` e `llama-quantize reclamacoes.gguf reclamacoes-q4.gguf Q4_K_M`), cria um `Modelfile` com `FROM ./reclamacoes-q4.gguf` e corre `ollama create reclamacoes -f Modelfile`. O Ollama expõe uma API compatível com a da OpenAI em `http://localhost:11434/v1`: arranca a API com `VLLM_URL=http://localhost:11434/v1`.
- **GPU na nuvem à hora:** Modal, RunPod ou um Space do Hugging Face com GPU servem para o teste de carga sem comprar hardware.

## Variáveis de ambiente da API

| Variável | Omissão | Para quê |
|---|---|---|
| `VLLM_URL` | `http://localhost:8000/v1` | Servidor compatível com a API da OpenAI |
| `API_KEYS` | `dev` | Chaves aceites, separadas por vírgulas |
| `LIMITE_POR_MINUTO` | `600` | Pedidos por minuto por chave |
| `MODELO_FALLBACK` | `claude-haiku-5-5` | Vazio desliga o fallback |
| `CUSTO_GPU_HORA` | `0.80` | Para estimar o custo por pedido no painel |
