"""Execução de código Python num subprocesso com limites.

ATENÇÃO: isto protege contra erros (ciclos infinitos, memória a mais), NÃO contra código
malicioso. Para utilizadores externos usa um contentor sem rede (Docker) ou uma sandbox
gerida (E2B, Modal). Ver a lição do módulo 8.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

PRELUDIO = textwrap.dedent("""
    import warnings; warnings.filterwarnings("ignore")
    import pandas as pd, numpy as np
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pd.set_option("display.width", 120); pd.set_option("display.max_columns", 20)
""")


def _limites():  # só em Linux/macOS
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))   # 2 GB de memória
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))                     # 60 s de CPU
    except Exception:
        pass


class Sandbox:
    """Mantém o estado entre execuções reexecutando o histórico de células bem-sucedidas."""

    def __init__(self, pasta: str | Path, timeout: int = 60, max_saida: int = 4000):
        self.pasta = Path(pasta).resolve()
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.timeout, self.max_saida = timeout, max_saida
        self.historico: list[str] = []

    def executar(self, codigo: str) -> str:
        marcador = "### __SAIDA_NOVA__ ###"
        anterior = "\n".join(f"import contextlib, io\nwith contextlib.redirect_stdout(io.StringIO()):\n{textwrap.indent(c, '    ')}"
                             for c in self.historico)
        programa = f"{PRELUDIO}\n{anterior}\nprint({marcador!r})\n{codigo}\n"
        try:
            p = subprocess.run([sys.executable, "-I", "-c", programa], cwd=self.pasta, capture_output=True, text=True,
                               timeout=self.timeout, preexec_fn=_limites if os.name == "posix" else None,
                               env={"PATH": os.environ.get("PATH", ""), "MPLBACKEND": "Agg"})
        except subprocess.TimeoutExpired:
            return f"ERRO: o código excedeu {self.timeout} s. Simplifica ou trabalha com uma amostra."
        saida = p.stdout.split(marcador, 1)[-1].strip()
        if p.returncode != 0:
            erro = p.stderr.strip().splitlines()
            return f"ERRO (o código não foi guardado no estado):\n{saida[-1000:]}\n" + "\n".join(erro[-8:])
        self.historico.append(codigo)
        if len(saida) > self.max_saida:
            saida = saida[:self.max_saida] + f"\n... [saída cortada, {len(saida)} caracteres; mostra menos linhas]"
        return saida or "(sem output; usa print() para ver resultados)"
