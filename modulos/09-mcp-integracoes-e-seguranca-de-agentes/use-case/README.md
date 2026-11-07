# Use case: servidor MCP para a base de vendas

Um servidor MCP que dá acesso só de leitura à base de vendas da Loja Lusa (criada a partir dos dados do módulo 8) e um agente que o usa, com aprovação humana antes de qualquer envio.

| Ficheiro | O que faz |
|---|---|
| [`criar_base.py`](criar_base.py) | Cria `vendas.db` (SQLite) com as tabelas `vendas` e `lojas` |
| [`servidor_vendas.py`](servidor_vendas.py) | Servidor MCP (FastMCP): ferramentas `listar_tabelas`, `descrever_tabela`, `consultar_sql`, `preparar_envio_relatorio`; resource `schema://vendas`; prompt `relatorio_mensal` |
| [`cliente.py`](cliente.py) | Agente Claude que liga ao servidor por stdio e pede aprovação para ações sensíveis |

```bash
uv sync --extra agentes
uv run python criar_base.py
uv run mcp dev servidor_vendas.py          # MCP Inspector no browser
uv run python cliente.py "Que loja teve mais devoluções em 2025?"
```

**Defesas em camadas:** a ligação SQLite abre em `mode=ro`, a ferramenta só aceita `SELECT`/`WITH` e corta o resultado a 50 linhas, os envios só aceitam `@lojalusa.pt` e ficam pendentes em `envios_pendentes.jsonl` até uma pessoa aprovar.

**Versão do SDK:** o código usa o SDK `mcp` 1.x (`mcp.server.fastmcp.FastMCP`). Na versão 2 a classe chama-se `MCPServer`; o `pyproject.toml` fixa `mcp<2`.
