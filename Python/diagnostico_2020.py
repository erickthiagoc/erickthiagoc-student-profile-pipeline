"""
diagnostico_2020.py
-------------------
Diagnóstico de leitura: lista os arquivos .html por ano de pasta e diz se o
parser aceitaria cada um (se têm data AAAA-MM-DD no fim do nome). Útil quando
algum ano "não aparece" na planilha. NÃO gera nada.

Coloque na mesma pasta de onde você roda o gerador e rode:
    python diagnostico_2020.py
"""
import re
from pathlib import Path
from collections import Counter

BASE = Path(__file__).resolve().parent
DATA_RE = re.compile(r"(\d{4}-\d{2}-\d{2})$")

htmls = sorted(BASE.rglob("*.html")) + sorted(BASE.rglob("*.htm"))
print(f"Pasta base: {BASE}")
print(f"Total de arquivos .html/.htm encontrados (recursivo): {len(htmls)}")
print("-" * 70)

por_pasta = Counter()
sem_data = []
amostra_por_pasta = {}

for h in htmls:
    ano_pasta = "?"
    for parte in reversed(h.parent.parts):
        m = re.search(r"(20\d{2})", parte)
        if m:
            ano_pasta = m.group(1); break
    por_pasta[ano_pasta] += 1
    stem = h.stem
    tem_data = bool(DATA_RE.search(stem))
    if not tem_data:
        sem_data.append(str(h.relative_to(BASE)))
    amostra_por_pasta.setdefault(ano_pasta, (stem, tem_data, stem[-16:]))

print("Arquivos por ano de pasta:")
for ano, n in sorted(por_pasta.items()):
    ex, td, tail = amostra_por_pasta[ano]
    print(f"  {ano}: {n:4}   exemplo: {ex[:60]}")
    print(f"          termina em: ...{tail!r}  | tem data AAAA-MM-DD no fim? {td}")

print("-" * 70)
if sem_data:
    print(f"Arquivos SEM data AAAA-MM-DD no fim do nome ({len(sem_data)}) — NÃO entram:")
    for s in sem_data[:40]:
        print("  -", s)
else:
    print("Todos os arquivos têm data no fim do nome (o parser aceitaria todos).")
