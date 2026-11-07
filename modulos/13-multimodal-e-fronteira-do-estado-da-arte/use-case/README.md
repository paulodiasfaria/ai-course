# Use case: processador de documentos digitalizados

Um pipeline que recebe faturas digitalizadas (e notas de voz associadas), extrai os campos com um modelo de visão, valida-os com código, pede uma segunda leitura quando a validação falha, manda para revisão humana o que continuar duvidoso e grava tudo em SQLite e CSV.

```
imagem ─> VLM (esquema Pydantic) ─> validação (NIF, somas, IVA, data) ─┬─ ok ──────────────> documentos.db
                                         │ falha                        │
                                         └─> segunda leitura focada ────┴─ ainda falha ─> revisão humana
nota de voz ─> Whisper ─> instruções (centro de custo, prazo, alertas) ─┘
```

| Ficheiro | O que faz |
|---|---|
| [`gerar_documentos.py`](gerar_documentos.py) | Faturas sintéticas «digitalizadas» (rotação, ruído, desfoque, JPEG), algumas com erros de propósito, mais notas de voz opcionais com TTS aberto |
| [`validacao.py`](validacao.py) | Esquema Pydantic e validações: dígito de controlo do NIF, somas das linhas, IVA, taxas válidas, datas |
| [`processar.py`](processar.py) | O pipeline completo, com Claude (visão) e Whisper (voz) |
| [`avaliar.py`](avaliar.py) | Exatidão por campo, documentos com erro apanhados, falsos alarmes e erros aceites sem revisão |

```bash
uv sync --extra multimodal
uv run python gerar_documentos.py --n 30 --notas
uv run python processar.py                                  # GPU para o Whisper large; em CPU: --whisper openai/whisper-small
uv run python avaliar.py
```

Para usar faturas tuas, põe as imagens (JPG ou PNG) em `entrada/`. O `avaliar.py` só funciona com as geradas, porque precisa dos valores verdadeiros.

**Custo:** uma leitura com o Claude Sonnet custa cerca de um cêntimo por página; os documentos com problemas fazem duas leituras.

**Privacidade:** faturas reais têm dados pessoais. Antes de enviar documentos verdadeiros para uma API, confirma o enquadramento RGPD com o fornecedor, ou troca o `extrair()` por um VLM aberto local (desafio no notebook).
