"""Gera faturas e emails sintéticos em português com a resposta certa conhecida.

Cada documento é texto livre (com estilos variados e algum ruído) e vem acompanhado
dos valores corretos, para medir a taxa de acerto de um extrator.

Uso:
    uv run python gerar_dados.py --n 200 --saida dados.jsonl
"""
import argparse
import json
import random
from datetime import date, timedelta

FORNECEDORES = [
    "Papelaria Central, Lda.", "TecnoNorte Informática S.A.", "Padaria Flor do Minho",
    "Transportes Rápidos do Sul, Lda.", "Gráfica Atlântico", "Limpezas Brilho Total, Unipessoal",
    "Café Avenida", "EletroLis S.A.", "Consultoria Douro & Associados", "Farmácia Moderna",
]
ITENS = {
    23: [("Toner HP 59A", 89.9), ("Portátil 14''", 749.0), ("Serviço de consultoria (h)", 65.0), ("Resma papel A4", 4.2), ("Monitor 27''", 219.0)],
    13: [("Refeição de grupo", 14.5), ("Serviço de catering", 320.0)],
    6: [("Pão de forma", 1.8), ("Medicamento genérico", 7.9), ("Livro técnico", 32.0)],
}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def nif_valido():
    base = [random.choice([1, 2, 5])] + [random.randint(0, 9) for _ in range(7)]
    soma = sum(d * (9 - i) for i, d in enumerate(base))
    ctrl = 11 - soma % 11
    return "".join(map(str, base + [0 if ctrl >= 10 else ctrl]))


def euros(v, estilo):
    s = f"{v:,.2f}"
    if estilo == 0:
        return s.replace(",", " ").replace(".", ",") + " €"
    if estilo == 1:
        return "€" + s.replace(",", "")
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " EUR"


def documento():
    taxa = random.choice([23, 23, 23, 13, 6])
    forn = random.choice(FORNECEDORES)
    nif = nif_valido()
    d = date(2026, 1, 1) + timedelta(days=random.randint(0, 300))
    linhas = random.sample(ITENS[taxa], k=min(len(ITENS[taxa]), random.randint(1, 3)))
    qts = [random.randint(1, 10) for _ in linhas]
    base = round(sum(p * q for (_, p), q in zip(linhas, qts)), 2)
    iva = round(base * taxa / 100, 2)
    total = round(base + iva, 2)
    est = random.randint(0, 2)
    nif_txt = random.choice([nif, f"{nif[:3]} {nif[3:6]} {nif[6:]}", f"PT{nif}"])
    data_txt = random.choice([d.strftime("%d/%m/%Y"), d.isoformat(), f"{d.day} de {MESES[d.month - 1]} de {d.year}"])
    itens_txt = "\n".join(f"  {q} x {n} ... {euros(p * q, est)}" for (n, p), q in zip(linhas, qts))
    tipo = random.choice(["fatura", "email", "email_curto"])
    if tipo == "fatura":
        texto = (f"{forn}\nNIF: {nif_txt}\nFATURA FT 2026/{random.randint(100, 9999)}\nData de emissão: {data_txt}\n\n"
                 f"{itens_txt}\n\nIncidência: {euros(base, est)}\nIVA {taxa}%: {euros(iva, est)}\nTOTAL A PAGAR: {euros(total, est)}")
    elif tipo == "email":
        texto = (f"Assunto: Fatura de {MESES[d.month - 1]}\n\nBom dia,\n\nSegue a fatura referente aos serviços prestados, "
                 f"emitida em {data_txt}. O valor total é de {euros(total, est)} (IVA incluído à taxa de {taxa}%).\n"
                 f"Pedimos pagamento a 30 dias.\n\nCom os melhores cumprimentos,\n{forn}\nContribuinte {nif_txt}")
    else:
        texto = (f"olá, envio a fatura de {data_txt}, total {euros(total, est)} c/ iva {taxa}%. "
                 f"qualquer coisa disponham. {forn} (nif {nif_txt})")
    return {"texto": texto, "esperado": {"fornecedor": forn, "nif": nif, "data": d.isoformat(), "total": total, "taxa_iva": taxa}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--saida", default="dados.jsonl")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    random.seed(a.seed)
    with open(a.saida, "w", encoding="utf-8") as f:
        for i in range(a.n):
            f.write(json.dumps({"id": i, **documento()}, ensure_ascii=False) + "\n")
    print(f"{a.n} documentos em {a.saida}")


if __name__ == "__main__":
    main()
