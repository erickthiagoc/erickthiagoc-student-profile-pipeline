"""
organizar_pdfs_por_ano.py
--------------------------
Move PDFs JÁ convertidos (que ficaram todos juntos numa pasta) para subpastas
por ano, SEM reconverter nada. O ano vem da data no nome (..._AAAA-MM-DD.pdf).

Use só se você converteu com ESTRUTURA_SAIDA = "unica". Se já converteu com
"por_ano", não precisa deste script.

COMO USAR:
  Ajuste PASTA_PDFS, rode com SIMULAR = True para conferir, depois mude para
  SIMULAR = False e rode de novo para mover de verdade.
"""
import re
import shutil
from pathlib import Path

PASTA_PDFS = Path(__file__).resolve().parent / "PDFs_convertidos"
SIMULAR = True   # True = só mostra o que faria | False = move de verdade


def ano_do_nome(pdf: Path) -> str:
    m = re.search(r"_(\d{4})-\d{2}-\d{2}$", pdf.stem)
    return m.group(1) if m else "sem_ano"


def main():
    print(f"Pasta : {PASTA_PDFS}")
    print(f"MODO  : {'SIMULACAO (nao move nada)' if SIMULAR else 'REAL (vai mover os arquivos)'}")
    print("-" * 60)
    if not PASTA_PDFS.exists():
        print("ERRO: a pasta acima nao existe. Confira o caminho em PASTA_PDFS.")
        return

    pdfs = [p for p in PASTA_PDFS.glob("*.pdf")]   # só os soltos na raiz
    print(f"PDFs soltos na raiz: {len(pdfs)}")
    if not pdfs:
        subpastas = [d.name for d in PASTA_PDFS.iterdir() if d.is_dir()]
        if subpastas:
            print("Nao ha PDFs soltos. Parece que ja foram organizados:",
                  ", ".join(sorted(subpastas)))
        else:
            print("Nenhum PDF encontrado na pasta.")
        return

    movidos, pulados, contagem = 0, 0, {}
    for pdf in pdfs:
        ano = ano_do_nome(pdf)
        contagem[ano] = contagem.get(ano, 0) + 1
        if SIMULAR:
            continue
        destino_dir = PASTA_PDFS / ano
        destino_dir.mkdir(exist_ok=True)
        destino = destino_dir / pdf.name
        if destino.exists():
            print(f"  JA EXISTE, pulando: {ano}/{pdf.name}")
            pulados += 1
            continue
        shutil.move(str(pdf), str(destino))
        movidos += 1

    print("\nResumo por ano:")
    for ano in sorted(contagem):
        print(f"  {ano}: {contagem[ano]} arquivos")
    if SIMULAR:
        print("\n>> SIMULACAO. Para mover de verdade: mude SIMULAR = False e rode de novo.")
    else:
        print(f"\nPronto. Movidos: {movidos} | Pulados (ja existiam): {pulados}")


if __name__ == "__main__":
    main()
