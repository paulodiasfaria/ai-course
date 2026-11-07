# Use case: chatbot de apoio ao cliente

Assistente da Loja Lusa, uma loja online fictícia. Responde com base em [`faq.md`](faq.md), mantém o contexto da conversa (resumindo mensagens antigas quando a conversa fica longa) e troca entre um modelo na nuvem e um modelo local com uma variável de ambiente.

```bash
uv run python app.py                                   # nuvem (Claude Haiku)
MODELO_CHAT=ollama/qwen2.5:7b uv run python app.py     # local, com Ollama
```

Ideias para ir mais longe:
- Publicar num Hugging Face Space.
- Registar cada conversa num CSV e rever as respostas erradas.
- Medir a taxa de respostas corretas com 20 perguntas de teste nos dois modelos.
