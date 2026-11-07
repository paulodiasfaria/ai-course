"""Esquema dos documentos e validações determinísticas (NIF, somas, taxas de IVA, datas)."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

TAXAS_IVA = {0, 6, 13, 23}          # continente; Madeira e Açores têm taxas próprias


class Linha(BaseModel):
    descricao: str
    quantidade: float
    preco_unitario: float = Field(description="Sem IVA, em euros")
    taxa_iva: int = Field(description="Percentagem: 0, 6, 13 ou 23")


class Documento(BaseModel):
    tipo: Literal["fatura", "fatura-recibo", "fatura simplificada", "outro"]
    emitente: str
    nif_emitente: str = Field(description="9 dígitos, sem espaços nem prefixo PT")
    nif_cliente: Optional[str] = Field(description="9 dígitos, ou null se for consumidor final")
    numero: str = Field(description="Número do documento tal como aparece, por exemplo FT 2025/123")
    data: str = Field(description="AAAA-MM-DD")
    linhas: list[Linha]
    total_sem_iva: float
    total_iva: float
    total: float
    legivel: bool = Field(description="false se partes importantes estão ilegíveis")


def nif_valido(nif: str | None) -> bool:
    """Dígito de controlo do NIF português (módulo 11)."""
    if not nif or len(nif) != 9 or not nif.isdigit() or nif[0] not in "1235689":
        return False
    soma = sum(int(d) * (9 - i) for i, d in enumerate(nif[:8]))
    controlo = 11 - soma % 11
    return int(nif[8]) == (0 if controlo >= 10 else controlo)


def validar(doc: Documento) -> list[str]:
    """Devolve a lista de problemas. Lista vazia = documento coerente."""
    p = []
    if doc.tipo == "outro":
        p.append("Não parece uma fatura")
    if not nif_valido(doc.nif_emitente):
        p.append(f"NIF do emitente inválido: {doc.nif_emitente}")
    if doc.nif_cliente and not nif_valido(doc.nif_cliente):
        p.append(f"NIF do cliente inválido: {doc.nif_cliente}")
    try:
        d = date.fromisoformat(doc.data)
        if not date(2000, 1, 1) <= d <= date.today():
            p.append(f"Data fora do intervalo plausível: {doc.data}")
    except ValueError:
        p.append(f"Data inválida: {doc.data}")
    for l in doc.linhas:
        if l.taxa_iva not in TAXAS_IVA:
            p.append(f"Taxa de IVA inesperada ({l.taxa_iva}%) em '{l.descricao}'")
    base = sum(l.quantidade * l.preco_unitario for l in doc.linhas)
    iva = sum(l.quantidade * l.preco_unitario * l.taxa_iva / 100 for l in doc.linhas)
    if abs(base - doc.total_sem_iva) > 0.02 * max(1, len(doc.linhas)):
        p.append(f"Soma das linhas ({base:.2f}) difere do total sem IVA ({doc.total_sem_iva:.2f})")
    if abs(iva - doc.total_iva) > 0.02 * max(1, len(doc.linhas)):
        p.append(f"IVA calculado ({iva:.2f}) difere do IVA indicado ({doc.total_iva:.2f})")
    if abs(doc.total_sem_iva + doc.total_iva - doc.total) > 0.02:
        p.append(f"Total sem IVA + IVA ({doc.total_sem_iva + doc.total_iva:.2f}) difere do total ({doc.total:.2f})")
    if not doc.legivel:
        p.append("O modelo indica partes ilegíveis")
    return p
