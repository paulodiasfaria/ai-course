"""Cria vendas.db (SQLite) com as vendas sintéticas do módulo 8 e uma tabela de lojas."""
import sqlite3
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent.parent / "08-tool-use-e-agentes" / "use-case"))
from gerar_vendas import gerar  # noqa: E402

df = gerar()
lojas = [("Online", "—", "2019-03-01"), ("Porto", "Rua de Santa Catarina", "2015-06-10"), ("Lisboa", "Avenida de Roma", "2016-09-01"),
         ("Braga", "Avenida da Liberdade", "2021-04-15"), ("Faro", "Rua de Santo António", "2022-05-20")]
db = AQUI / "vendas.db"
db.unlink(missing_ok=True)
with sqlite3.connect(db) as con:
    df.to_sql("vendas", con, index=False)
    con.execute("CREATE TABLE lojas (loja TEXT PRIMARY KEY, morada TEXT, abertura TEXT)")
    con.executemany("INSERT INTO lojas VALUES (?, ?, ?)", lojas)
    con.execute("CREATE INDEX idx_data ON vendas(data)")
print(f"{db}: {len(df)} vendas, {len(lojas)} lojas")
