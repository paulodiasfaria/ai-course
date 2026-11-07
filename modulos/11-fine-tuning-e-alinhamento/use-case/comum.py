"""Definições partilhadas: esquema da extração, prompt de sistema, formato dos exemplos e métricas."""
from __future__ import annotations

import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

CATEGORIAS = ["entrega_atrasada", "produto_danificado", "produto_errado", "faturacao", "devolucao", "atendimento", "outro"]
PEDIDOS = ["reembolso", "troca", "reenvio", "informacao", "cancelamento", "outro"]
CAMPOS = ["categoria", "urgencia", "numero_encomenda", "produto", "pedido"]


class Extracao(BaseModel):
    categoria: Literal["entrega_atrasada", "produto_danificado", "produto_errado", "faturacao", "devolucao", "atendimento", "outro"]
    urgencia: Literal["baixa", "media", "alta"] = Field(description="alta: cliente ameaça cancelar, reclamar no Livro de Reclamações ou há prejuízo; baixa: só pede informação")
    numero_encomenda: Optional[str] = Field(description="Só os dígitos, sem # nem espaços; null se não houver")
    produto: Optional[str] = Field(description="Nome curto do produto em minúsculas, no singular; null se não houver")
    pedido: Literal["reembolso", "troca", "reenvio", "informacao", "cancelamento", "outro"]


SYSTEM = (
    "Classificas reclamações de clientes da Loja Lusa (artigos para a casa) e extrais campos. "
    "Responde só com um objeto JSON com as chaves categoria, urgencia, numero_encomenda, produto e pedido.\n"
    f"categoria: {', '.join(CATEGORIAS)}\n"
    "urgencia: baixa, media, alta (alta se o cliente ameaça cancelar, recorrer ao Livro de Reclamações ou tem prejuízo)\n"
    "numero_encomenda: só dígitos, ou null\n"
    "produto: nome curto em minúsculas no singular, ou null\n"
    f"pedido: {', '.join(PEDIDOS)}"
)


def exemplo_chat(texto: str, rotulo: dict | None = None) -> dict:
    """Formato prompt/completion conversacional do TRL: a perda conta só a completion."""
    ex = {"prompt": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": texto}]}
    if rotulo is not None:
        ex["completion"] = [{"role": "assistant", "content": json.dumps(rotulo, ensure_ascii=False)}]
    return ex


def ler_json(saida: str) -> dict | None:
    """Extrai e valida o primeiro objeto JSON da saída do modelo. None se inválido."""
    m = re.search(r"\{.*\}", saida, re.S)
    if not m:
        return None
    try:
        return Extracao.model_validate(json.loads(m.group(0))).model_dump()
    except (json.JSONDecodeError, ValidationError):
        return None


def normalizar(v):
    return None if v in (None, "", "null") else str(v).strip().lower()


def metricas(previstos: list[dict | None], referencia: list[dict]) -> dict:
    n = len(referencia)
    validos = [p is not None for p in previstos]
    res = {"n": n, "json_valido": sum(validos) / n}
    for c in CAMPOS:
        res[f"exato_{c}"] = sum(p is not None and normalizar(p[c]) == normalizar(r[c]) for p, r in zip(previstos, referencia)) / n
    res["tudo_certo"] = sum(p is not None and all(normalizar(p[c]) == normalizar(r[c]) for c in CAMPOS)
                            for p, r in zip(previstos, referencia)) / n
    # F1 macro da categoria (as classes estão desequilibradas)
    f1s = []
    for cat in CATEGORIAS:
        tp = sum(p is not None and p["categoria"] == cat and r["categoria"] == cat for p, r in zip(previstos, referencia))
        fp = sum(p is not None and p["categoria"] == cat and r["categoria"] != cat for p, r in zip(previstos, referencia))
        fn = sum(r["categoria"] == cat and (p is None or p["categoria"] != cat) for p, r in zip(previstos, referencia))
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    res["f1_macro_categoria"] = sum(f1s) / len(f1s) if f1s else 0.0
    return res
