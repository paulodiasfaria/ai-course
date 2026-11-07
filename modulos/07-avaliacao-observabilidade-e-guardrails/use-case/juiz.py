"""Métricas de RAG com LLM-as-judge: faithfulness, correção e context recall.

Implementação própria, simples e transparente, para perceberes o que medem as
bibliotecas como RAGAS e DeepEval.
"""
from __future__ import annotations

import os

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()
MODELO_JUIZ = os.getenv("MODELO_JUIZ", "claude-sonnet-5-5")   # o juiz deve ser pelo menos tão forte como o sistema avaliado
_client = Anthropic()


def _pedir(modelo_resposta, prompt: str, max_tokens: int = 1500):
    # Structured outputs nativos (output_format): o Sonnet 5.5 não aceita tool_choice forçado, que o Instructor usa por omissão
    r = _client.messages.parse(model=MODELO_JUIZ, max_tokens=max_tokens, output_format=modelo_resposta,
                               messages=[{"role": "user", "content": prompt}])
    return r.parsed_output


# ---------- faithfulness ----------
class Afirmacao(BaseModel):
    texto: str
    suportada: bool = Field(description="True se o contexto suporta explicitamente a afirmação")
    justificacao: str


class AnaliseFidelidade(BaseModel):
    afirmacoes: list[Afirmacao]


def faithfulness(resposta: str, contextos: list[str]) -> tuple[float, list[Afirmacao]]:
    """Fração das afirmações factuais da resposta suportadas pelo contexto."""
    ctx = "\n\n".join(f"<excerto>{c}</excerto>" for c in contextos)
    r = _pedir(AnaliseFidelidade, f"""<contexto>
{ctx}
</contexto>

<resposta>
{resposta}
</resposta>

1. Parte a resposta em afirmações factuais atómicas (ignora cortesias, recusas e sugestões de contacto).
2. Para cada uma, decide se o contexto a suporta explicitamente. Conhecimento geral não conta como suporte.""")
    if not r.afirmacoes:
        return 1.0, []
    return sum(a.suportada for a in r.afirmacoes) / len(r.afirmacoes), r.afirmacoes


# ---------- correção face à referência ----------
class Veredicto(BaseModel):
    raciocinio: str
    correta: bool = Field(description="True se a resposta contém os factos essenciais da referência sem a contradizer")


def correcao(pergunta: str, resposta: str, referencia: str) -> Veredicto:
    return _pedir(Veredicto, f"""Avalias respostas de um assistente.
<pergunta>{pergunta}</pergunta>
<referencia>{referencia}</referencia>
<resposta>{resposta}</resposta>

A resposta está correta se contiver os factos essenciais da referência (valores, prazos, condições, exceções)
e não a contradisser. Detalhes extra corretos não penalizam. Se a referência diz que a informação não existe,
a resposta está correta se recusar responder. Explica em 1 ou 2 frases e decide.""", 600)


# ---------- context recall ----------
class Cobertura(BaseModel):
    factos_referencia: list[str]
    cobertos: list[bool] = Field(description="Para cada facto, True se está presente no contexto")


def context_recall(referencia: str, contextos: list[str]) -> float:
    ctx = "\n\n".join(f"<excerto>{c}</excerto>" for c in contextos)
    r = _pedir(Cobertura, f"""<referencia>{referencia}</referencia>
<contexto>
{ctx}
</contexto>

Parte a referência em factos atómicos e indica, para cada um, se o contexto contém essa informação.""")
    if not r.factos_referencia:
        return 1.0
    return sum(r.cobertos) / len(r.cobertos)


# ---------- concordância com humanos ----------
def kappa_cohen(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    p0 = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (p0 - pe) / (1 - pe)
