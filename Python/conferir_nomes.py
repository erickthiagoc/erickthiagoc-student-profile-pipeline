"""
conferir_nomes.py
-----------------
Compara os nomes dos PDFs gerados com a coluna 'special_document' da(s)
planilha(s), apontando divergências:
  - linha da planilha SEM PDF correspondente
  - PDF SEM linha na planilha
  - diferença só de MAIÚSCULA/minúscula (o link no site pode ser sensível a caixa)

Ajuste PLANILHAS e PASTA_PDFS e rode:  python conferir_nomes.py
"""
import csv
from pathlib import Path

# Uma ou mais planilhas (graduação/mestrado/doutorado):
PLANILHAS = [
    Path(__file__).resolve().parent / "planilha_perfil_estudantes.csv",
]
# Pasta onde estão os PDFs convertidos (procura em subpastas também):
PASTA_PDFS = Path(__file__).resolve().parent / "PDFs_convertidos"


def ler_special_documents(csvs):
    docs = {}
    for cam in csvs:
        if not cam.exists():
            print(f"AVISO: planilha não encontrada: {cam}")
            continue
        with cam.open(newline="", encoding="utf-8-sig") as fh:
            linhas = list(csv.reader(fh))
        if not linhas:
            continue
        idx = {c.split("|")[0].strip(): i for i, c in enumerate(linhas[0])}
        if "special_document" not in idx:
            print(f"AVISO: coluna 'special_document' não encontrada em {cam.name}")
            continue
        j = idx["special_document"]
        for row in linhas[1:]:
            if j < len(row) and row[j].strip():
                docs[row[j].strip()] = cam.name
    return docs


def main():
    if not PASTA_PDFS.exists():
        print("ERRO: pasta de PDFs não existe:", PASTA_PDFS)
        return
    docs = ler_special_documents(PLANILHAS)
    pdfs = {p.name for p in PASTA_PDFS.rglob("*.pdf")}
    print(f"special_document na planilha : {len(docs)}")
    print(f"PDFs na pasta                : {len(pdfs)}")

    set_docs = set(docs)
    exatos = set_docs & pdfs
    faltando = sorted(set_docs - pdfs)
    sobrando = sorted(pdfs - set_docs)
    print(f"Batem exatamente             : {len(exatos)}")

    if not faltando and not sobrando:
        print("\nTUDO BATE ✔  (todo special_document tem PDF e todo PDF tem linha)")
        return

    low_pdfs = {p.lower(): p for p in pdfs}
    caixa = [(d, low_pdfs[d.lower()]) for d in faltando if d.lower() in low_pdfs]
    faltando_reais = [d for d in faltando if d.lower() not in low_pdfs]

    if caixa:
        print(f"\n[!] Diferença só de MAIÚSCULA/minúscula ({len(caixa)}):")
        for d, p in caixa[:30]:
            print(f"    planilha: {d}")
            print(f"    pdf     : {p}")
    if faltando_reais:
        print(f"\n[!] Na planilha mas SEM PDF ({len(faltando_reais)}):")
        for d in faltando_reais[:40]:
            print("    -", d)
    if sobrando:
        print(f"\n[!] PDF SEM linha na planilha ({len(sobrando)}):")
        for p in sobrando[:40]:
            print("    -", p)

    print("\nResumo: exatos={} | so_caixa={} | sem_pdf={} | pdf_extra={}".format(
        len(exatos), len(caixa), len(faltando_reais), len(sobrando)))


if __name__ == "__main__":
    main()
