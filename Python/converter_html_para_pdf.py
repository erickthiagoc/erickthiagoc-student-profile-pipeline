"""
converter_html_para_pdf.py
--------------------------
Converte em lote os relatórios .html em .pdf usando Playwright (navegador real),
para renderizar corretamente as tabelas e gráficos feitos em JavaScript.

Serve para graduação, mestrado e doutorado: ele lê a pasta ONDE o script está
(recursivamente), então basta colocar uma cópia dentro da pasta de cada nível.

  * Nomeia cada PDF com o nome "LIMPO" (sem acento), igual ao que vai na coluna
    special_document da planilha -> o link no site bate com o arquivo.
  * Processa vários arquivos EM PARALELO (CONCORRENCIA).
  * SIMULAR = True mostra o que faria, sem converter nada.

Instalação (uma vez):
    pip install playwright
    playwright install chromium
Uso:
    coloque este arquivo na pasta dos relatórios e rode:  python converter_html_para_pdf.py
"""

import asyncio
import csv
import re
import unicodedata
from pathlib import Path

from playwright.async_api import async_playwright

# ==========================================================================
# CONFIG
# ==========================================================================
# Pasta de entrada = a pasta onde ESTE script está (busca recursiva).
PASTA_ENTRADA = Path(__file__).resolve().parent
PASTA_SAIDA   = PASTA_ENTRADA / "PDFs_convertidos"
LOG_CONVERSAO = PASTA_SAIDA / "log_conversao.csv"

CONCORRENCIA  = 4          # quantos arquivos converter ao mesmo tempo (4-6 é seguro)
ESPERA_MS     = 4000       # espera após carregar, para os gráficos assentarem
TIMEOUT_MS    = 120000     # timeout de carregamento por página

# Como organizar os PDFs de saída:
#   "por_ano"  -> uma subpasta por ano (2020, 2021, ...)  [recomendado]
#   "espelhar" -> replica as pastas de entrada
#   "unica"    -> tudo numa pasta só
ESTRUTURA_SAIDA = "por_ano"

# True = SIMULAÇÃO (só lista o que faria). False = converte de verdade.
# Dica: rode com True primeiro; depois mude para False e SALVE (Ctrl+S).
SIMULAR = True

if not SIMULAR:
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)


# ==========================================================================
# Nome de saída "limpo" (mesma regra usada na planilha -> special_document)
# ==========================================================================
def sem_acentos(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(ch))


def _ano_da_entrada(html_path: Path) -> str:
    """Ano de publicação: procura AAAA nas pastas de entrada; se não achar,
    usa a data no nome do arquivo (..._AAAA-MM-DD)."""
    for parte in reversed(html_path.parent.parts):
        m = re.search(r"(20\d{2})", parte)
        if m:
            return m.group(1)
    m = re.search(r"_(\d{4})-\d{2}-\d{2}$", html_path.stem)
    return m.group(1) if m else "sem_ano"


def nome_pdf_limpo(html_path: Path) -> Path:
    stem = sem_acentos(html_path.stem)
    stem = re.sub(r"[^A-Za-z0-9_.-]", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")

    if ESTRUTURA_SAIDA == "por_ano":
        destino_dir = PASTA_SAIDA / _ano_da_entrada(html_path)
    elif ESTRUTURA_SAIDA == "espelhar":
        try:
            destino_dir = PASTA_SAIDA / html_path.parent.relative_to(PASTA_ENTRADA)
        except ValueError:
            destino_dir = PASTA_SAIDA
    else:  # "unica"
        destino_dir = PASTA_SAIDA

    return destino_dir / (stem + ".pdf")


# ==========================================================================
# Ações na página
# ==========================================================================
async def carregar_imagens(page):
    await page.evaluate("""
        async () => {
            const imgs = Array.from(document.images);
            await Promise.all(imgs.map(img => {
                if (img.complete) return Promise.resolve();
                return new Promise(resolve => { img.onload = resolve; img.onerror = resolve; });
            }));
        }
    """)


async def rolar_pagina(page):
    await page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let total = 0; const distancia = 500;
                const timer = setInterval(() => {
                    window.scrollBy(0, distancia); total += distancia;
                    if (total >= document.body.scrollHeight) {
                        clearInterval(timer); window.scrollTo(0, 0); resolve();
                    }
                }, 250);
            });
        }
    """)


async def converter_um(context, html: Path, i: int, total: int, sem: asyncio.Semaphore):
    async with sem:                       # limita a concorrência
        pdf_saida = nome_pdf_limpo(html)
        status, erro = "OK", ""
        page = None
        try:
            print(f"[{i}/{total}] {html.name}")
            page = await context.new_page()
            await page.goto(html.resolve().as_uri(),
                            wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            await page.wait_for_timeout(ESPERA_MS)
            await carregar_imagens(page)
            await rolar_pagina(page)
            await page.emulate_media(media="screen")

            texto = await page.locator("body").inner_text(timeout=30000)
            if len(texto.strip()) < 50:
                status = "SUSPEITO: pouco texto renderizado"

            pdf_saida.parent.mkdir(parents=True, exist_ok=True)
            await page.pdf(
                path=str(pdf_saida), format="A4", print_background=True,
                prefer_css_page_size=True,
                margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"},
            )
            if pdf_saida.stat().st_size < 10_000:
                status = "SUSPEITO: PDF pequeno ou possivelmente em branco"
        except Exception as e:
            status, erro = "ERRO", str(e)
            print(f"  ERRO: {html.name} -> {e}")
        finally:
            if page:
                await page.close()

        return {"html": str(html), "pdf": str(pdf_saida), "status": status, "erro": erro}


async def converter():
    htmls = sorted(list(PASTA_ENTRADA.rglob("*.html")) + list(PASTA_ENTRADA.rglob("*.htm")))
    print(f"Entrada: {PASTA_ENTRADA}")
    print(f"MODO   : {'SIMULACAO (nao converte nada)' if SIMULAR else 'REAL (vai converter)'}")
    print(f"Saida  : {PASTA_SAIDA}  (estrutura: {ESTRUTURA_SAIDA})")
    print("-" * 60)
    print(f"Arquivos HTML encontrados: {len(htmls)}")

    # --- MODO SIMULAÇÃO: só mostra o plano, sem abrir o navegador ---
    if SIMULAR:
        contagem = {}
        exemplos = []
        for h in htmls:
            destino = nome_pdf_limpo(h)
            pasta = destino.parent.name
            contagem[pasta] = contagem.get(pasta, 0) + 1
            if len(exemplos) < 5:
                exemplos.append(f"  {h.name}\n    -> {destino.relative_to(PASTA_SAIDA)}")
        print("\nExemplos (nome de entrada -> PDF de saida):")
        print("\n".join(exemplos))
        print("\nQuantos PDFs por pasta:")
        for pasta in sorted(contagem):
            print(f"  {pasta}: {contagem[pasta]}")
        print("\n>> Isto foi uma SIMULACAO. Para converter de verdade: "
              "mude SIMULAR = False, salve (Ctrl+S) e rode de novo.")
        return

    sem = asyncio.Semaphore(CONCORRENCIA)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = await browser.new_context(viewport={"width": 1366, "height": 1800})

        tarefas = [converter_um(context, h, i, len(htmls), sem)
                   for i, h in enumerate(htmls, start=1)]
        log = await asyncio.gather(*tarefas)

        await context.close()
        await browser.close()

    with open(LOG_CONVERSAO, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["html", "pdf", "status", "erro"])
        w.writeheader()
        w.writerows(log)

    ok = sum(1 for r in log if r["status"] == "OK")
    print(f"\nFinalizado. OK: {ok}/{len(log)}  |  conferir os demais no log.")
    print(f"PDFs em: {PASTA_SAIDA}\nLog em:  {LOG_CONVERSAO}")


if __name__ == "__main__":
    asyncio.run(converter())
