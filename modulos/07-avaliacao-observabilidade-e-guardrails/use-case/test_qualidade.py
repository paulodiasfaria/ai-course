"""Testes de qualidade para correr em CI: uv run pytest test_qualidade.py

Lê os resultados da última avaliação (resultados.csv) e falha se as métricas
descerem abaixo dos limites. Em CI, corre primeiro avaliar.py.
"""
from pathlib import Path

import pandas as pd
import pytest

LIMITES = {"acerto": 0.85, "faithfulness": 0.90, "context_recall": 0.80}
RES = Path(__file__).parent / "resultados.csv"


@pytest.fixture(scope="module")
def resultados():
    if not RES.exists():
        pytest.skip("corre primeiro: uv run python avaliar.py")
    return pd.read_csv(RES)


def test_acerto(resultados):
    assert resultados.correta.mean() >= LIMITES["acerto"]


def test_faithfulness(resultados):
    assert resultados.faithfulness.mean() >= LIMITES["faithfulness"]


def test_context_recall(resultados):
    assert resultados.context_recall.dropna().mean() >= LIMITES["context_recall"]


def test_recusa_sem_informacao(resultados):
    sem = resultados[resultados.sem_resposta.astype(bool)]
    assert sem.recusou.all(), sem[~sem.recusou].pergunta.tolist()
