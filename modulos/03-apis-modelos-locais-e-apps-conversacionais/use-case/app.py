"""Chatbot de apoio ao cliente da Loja Lusa (Gradio).

- Responde com base em faq.md
- Streaming de respostas
- Memória por resumo quando a conversa fica longa
- Modelo configurável: MODELO_CHAT=anthropic/claude-haiku-5-5 (padrão) ou ollama/qwen2.5:7b

Uso:
    uv run python app.py
"""
import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
MODELO = os.getenv("MODELO_CHAT", "anthropic/claude-haiku-5-5")
FAQ = (Path(__file__).parent / "faq.md").read_text(encoding="utf-8")
LIMITE_TOKENS_APROX = 1500   # acima disto, as mensagens antigas são resumidas
MANTER = 4                   # mensagens recentes que nunca são resumidas

SYSTEM = f"""És o assistente de apoio ao cliente da Loja Lusa. Respondes em português de Portugal, \
de forma simpática e breve (no máximo 4 frases), usando só a informação em <faq>.

<faq>
{FAQ}
</faq>"""


def tokens_aprox(msgs):
    return sum(len(m["content"]) for m in msgs) // 4


def resumir(antigas, resumo_atual):
    texto = "\n".join(f"{m['role']}: {m['content']}" for m in antigas)
    r = completion(model=MODELO, max_tokens=250, messages=[{"role": "user", "content":
        f"Resumo anterior: {resumo_atual or '(nenhum)'}\n\nMensagens:\n{texto}\n\n"
        "Escreve um resumo atualizado em até 5 frases. Mantém nome do cliente, números de encomenda, datas, problemas e o que já foi respondido."}])
    return r.choices[0].message.content


_resumos = {}   # cache: mensagens antigas -> resumo (evita voltar a resumir a cada volta)


def contexto(msgs):
    """Devolve (resumo, mensagens ativas). Resume em blocos para o resumo ser reutilizado."""
    if tokens_aprox(msgs) <= LIMITE_TOKENS_APROX or len(msgs) <= MANTER:
        return "", msgs
    corte = (len(msgs) - MANTER) // 4 * 4 or len(msgs) - MANTER   # corta em múltiplos de 4 mensagens
    chave = tuple(m["content"] for m in msgs[:corte])
    if chave not in _resumos:
        anterior = ""
        for k in range(4, corte, 4):           # reaproveita o resumo do bloco anterior, se existir
            anterior = _resumos.get(tuple(m["content"] for m in msgs[:k]), anterior)
        _resumos[chave] = resumir(msgs[:corte], anterior)
    return _resumos[chave], msgs[corte:]


def responder(mensagem, historico):
    # historico chega no formato [{"role": ..., "content": ...}] (type="messages")
    msgs = [{"role": m["role"], "content": m["content"]} for m in historico]
    resumo, ativas = contexto(msgs)
    while ativas and ativas[0]["role"] != "user":
        ativas = ativas[1:]
    system = SYSTEM + (f"\n\nResumo da conversa até agora: {resumo}" if resumo else "")
    pedido = [{"role": "system", "content": system}] + ativas + [{"role": "user", "content": mensagem}]
    texto = ""
    for pedaco in completion(model=MODELO, messages=pedido, stream=True, max_tokens=400, temperature=0.3):
        texto += pedaco.choices[0].delta.content or ""
        yield texto


demo = gr.ChatInterface(
    responder,
    type="messages",
    title="Loja Lusa · Apoio ao cliente",
    description=f"Modelo: `{MODELO}`",
    examples=["Fazem entregas nos Açores?", "Posso devolver uns lençóis que já abri?", "Como peço fatura com NIF?"],
)

if __name__ == "__main__":
    demo.launch()
