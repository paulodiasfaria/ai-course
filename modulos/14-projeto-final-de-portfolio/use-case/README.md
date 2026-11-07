# Use case: copiloto de análise de documentos empresariais

O projeto final junta o curso num produto pequeno e completo: um agente Claude que responde a colaboradores da Loja Lusa sobre políticas internas e dados de vendas, com citações verificáveis, avaliado com um golden dataset e publicado numa demo pública.

```
pergunta ─> agente (Claude Sonnet) ─ MCP stdio ─> servidor_mcp.py ─┬─ pesquisar_documentos / ler_excerto ─> pesquisa híbrida (e5 + BM25 + RRF)
                │                                                  └─ listar_tabelas / descrever_tabela / consultar_sql ─> vendas.db (M09)
                └─> verificação das citações por código ─> resposta com [doc#n] e [sql]
```

| Ficheiro | O que faz |
|---|---|
| [`pesquisa.py`](pesquisa.py) | Chunking por secção, embeddings e5, BM25 e fusão RRF; índice em numpy em `indice/` |
| [`servidor_mcp.py`](servidor_mcp.py) | Servidor MCP com as ferramentas de documentos e as de SQL do módulo 9 |
| [`copiloto.py`](copiloto.py) | O agente: ciclo de ferramentas, citações validadas por código, custo e latência por pergunta |
| [`golden.jsonl`](golden.jsonl) | 13 casos: documentos, dados, mistos, fora de âmbito e segurança |
| [`avaliar.py`](avaliar.py) | Juiz LLM mais verificações de código; escreve `relatorio_avaliacao.md` |
| [`app.py`](app.py) | Demo Gradio com painel de fontes, limite por sessão e senha opcional |
| [`preparar_space.py`](preparar_space.py) | Monta a pasta `space/` para publicar num Space do Hugging Face |
| [`PROJETO.md`](PROJETO.md) | Modelo de README para o teu projeto de portfólio |

```bash
uv sync --extra rag --extra agentes             # a vendas.db do módulo 9 é criada sozinha na primeira execução
uv run python pesquisa.py indexar
uv run python pesquisa.py procurar "limite de hotel em Lisboa"
uv run python copiloto.py "Qual é o limite de hotel em Lisboa e quanto vendeu a loja de Lisboa em 2025?"
uv run python avaliar.py                      # cerca de US$0,30 para os 13 casos
uv run python app.py                          # http://localhost:7860
uv run python preparar_space.py
huggingface-cli upload o-teu-utilizador/copiloto-loja-lusa space . --repo-type space
```

No Space, define o segredo `ANTHROPIC_API_KEY` e, se a demo for pública, `SENHA_DEMO` e um limite de gastos na consola da Anthropic.

**Para o teu projeto:** troca os documentos (`DOCS_COPILOTO=a/tua/pasta`), os dados (`DADOS_COPILOTO_DIR`) e o golden dataset pelos do teu domínio, e preenche o `PROJETO.md`.
