"""Interface Gradio do copiloto, pronta para um Space do Hugging Face.

Uso local:
    uv run python app.py
Variáveis: ANTHROPIC_API_KEY (obrigatória), SENHA_DEMO (opcional: protege a demo), MAX_PERGUNTAS_SESSAO (omissão 20).
"""
from __future__ import annotations

import inspect
import os

import gradio as gr

import copiloto
import pesquisa

MAX = int(os.getenv("MAX_PERGUNTAS_SESSAO", "20"))
EXEMPLOS = ["Tenho 12 anos de casa. Quantos dias de férias tenho?",
            "Que categoria mais cresceu de 2024 para 2025?",
            "Vou a Lisboa visitar a loja. Qual é o limite de hotel e quanto vendeu essa loja em 2025?",
            "O robô mostra o erro E4. O que faço?"]


FORMATO = {"type": "messages"} if "type" in inspect.signature(gr.Chatbot.__init__).parameters else {}   # Gradio 5; no 6 é o único


def so_texto(conteudo) -> str:
    """No Gradio 6 o conteúdo é uma lista de partes ({"type": "text", "text": ...}); no 5 é uma string."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        return "".join(p.get("text", "") for p in conteudo if isinstance(p, dict) and p.get("type") == "text")
    return str(conteudo)


def formatar_fontes(r: dict) -> str:
    linhas = []
    for c in r["citacoes"]:
        if c == "sql":
            for t in r["ferramentas"]:
                if t["ferramenta"] == "consultar_sql":
                    linhas.append(f"- **[sql]** `{t['args'].get('query', '')[:300]}`")
        elif (ex := pesquisa.por_id(c)):
            linhas.append(f"- **[{c}]** {ex['titulo']} › {ex['secao']}\n  > {ex['texto'][:300].replace(chr(10), ' ')}")
    rodape = f"\n\n<sub>{len(r['ferramentas'])} chamadas a ferramentas · {r['segundos']} s · US${r['usd']:.4f}</sub>"
    return ("\n".join(linhas) or "_Sem fontes citadas._") + rodape


async def responder(mensagem, historico, contador):
    contador = (contador or 0) + 1
    if contador > MAX:
        yield historico + [{"role": "user", "content": mensagem}, {"role": "assistant", "content": "Limite de perguntas desta demo atingido. Recarrega a página."}], "", contador
        return
    historico = historico + [{"role": "user", "content": mensagem}, {"role": "assistant", "content": "A pesquisar..."}]
    yield historico, "", contador
    # histórico curto em texto: o copiloto volta a consultar as fontes em cada pergunta
    anterior = [{"role": m["role"], "content": so_texto(m["content"])} for m in historico[:-2][-6:]]
    anterior = [m for m in anterior if m["content"]]
    while anterior and anterior[0]["role"] != "user":
        anterior = anterior[1:]
    r = await copiloto.perguntar(mensagem, historico=anterior)
    historico[-1] = {"role": "assistant", "content": r["resposta"]}
    yield historico, formatar_fontes(r), contador


with gr.Blocks(title="Copiloto Loja Lusa") as demo:
    gr.Markdown("## Copiloto Loja Lusa\nPerguntas sobre políticas internas, manuais e vendas. Cada resposta cita as fontes. "
                "Os dados são fictícios. Estás a falar com um assistente de IA.")
    contador = gr.State(0)
    with gr.Row():
        with gr.Column(scale=3):
            chat = gr.Chatbot(height=480, **FORMATO)
            caixa = gr.Textbox(placeholder="Escreve a tua pergunta", show_label=False)
            gr.Examples(EXEMPLOS, caixa)
        with gr.Column(scale=2):
            gr.Markdown("### Fontes")
            fontes = gr.Markdown()
    caixa.submit(responder, [caixa, chat, contador], [chat, fontes, contador]).then(lambda: "", None, caixa)

if __name__ == "__main__":
    senha = os.getenv("SENHA_DEMO")
    demo.queue(default_concurrency_limit=4).launch(auth=("demo", senha) if senha else None)
