# Student Profile Reports — Cataloging & PDF Pipeline

A small Python toolkit that turns a large, multi-year collection of
institutional **"student profile"** reports (published as web pages) into:

1. a clean **metadata catalog** (CSV), and
2. a matching set of **PDF** files, ready to be linked from a public page.

It was built to automate what was previously manual work for a university's
institutional-evaluation office, across six publication cycles and three
academic levels (undergraduate, master's, doctorate) — roughly **1,800
reports** in total.

> **Note:** this repository contains only the code. It does **not** include any
> report, spreadsheet or student data. See [Data & privacy](#data--privacy).

---

## What it does

- **HTML → PDF conversion at scale.** The reports are web pages whose tables and
  charts are rendered by JavaScript, so a plain HTML-to-PDF converter loses the
  visuals. The converter drives a real headless browser (Playwright/Chromium),
  waits for images and lazy charts to render, and prints faithful PDFs — in
  parallel, with a per-file log and a dry-run mode.
- **Metadata extraction.** For every report it fills a fixed template (title,
  course/program, unit, level, data year, source system, publication date,
  subject tags, etc.), reading what it can from the page text and the file name.
- **Robust, multi-format file-name parsing.** File-naming conventions changed
  across years (different prefixes, department vs. faculty codes, acronym-only
  names, legacy names with accents stripped). The parser understands all the
  observed formats and reports anything it doesn't recognize instead of silently
  dropping it.
- **Unit-code mapping.** Short institutional codes (faculty/department/center)
  are expanded to full names via a lookup table that is easy to review and extend.
- **Normalization.** Course/program names are tidied (connector words
  lower-cased, all-caps legacy names converted to title case) and a small
  correction map fixes known cases.
- **Name reconciliation.** A checker confirms that every catalog entry has a
  matching PDF and vice-versa (and flags case-only differences), so the links
  built from the catalog never break.
- **Diagnostics & reporting.** Each run prints a per-year count and lists files
  it skipped or codes it couldn't map, making data-quality gaps visible.

---

## Tech stack

- **Python 3**
- [Playwright](https://playwright.dev/python/) (headless Chromium) + `asyncio`
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) + `lxml`
- Standard library (`csv`, `re`, `pathlib`, `unicodedata`)

---

## Repository layout

| File | Purpose |
|------|---------|
| `gerar_planilha_perfil_estudantes.py` | Build the metadata CSV for **undergraduate** reports |
| `gerar_planilha_perfil_mestrado.py`   | Build the metadata CSV for **master's** reports |
| `gerar_planilha_perfil_doutorado.py`  | Build the metadata CSV for **doctorate** reports |
| `converter_html_para_pdf.py`          | Convert the HTML reports to PDF (Playwright). Reads the folder it sits in, so one copy works for any level |
| `conferir_nomes.py`                   | Reconcile catalog entries against the actual PDF files |
| `diagnostico_2020.py`                 | Diagnostic: list files per year and flag unparsable names |

*(File and column names are kept in Portuguese to match the source material.)*

Each script reads the folder it is placed in (recursively), so the usual setup
is to drop the relevant scripts inside each level's report folder and run them
there.

---

## How it works

```
HTML reports ──► converter_html_para_pdf.py ──► PDFs (clean, link-safe names)
            └───► gerar_planilha_*.py        ──► metadata.csv  (+ name map)
                                                    │
                        conferir_nomes.py ◄─────────┘  (verify PDF ↔ CSV match)
```

- **Data year vs. publication year.** Each report's *data year* is read from the
  page; the *publication date* comes from the file name. These differ (a report
  about year *N* is typically published in *N+1*), which the pipeline handles
  explicitly.
- **Link-safe names.** The PDF file name and the catalog's document-reference
  column are produced by the *same* normalization routine (accents stripped,
  spaces/odd characters collapsed), so they always match.

---

## Usage

> Requires Python 3 and, for the converter, a one-time
> `pip install playwright && playwright install chromium`.
> The CSV generators only need `pip install beautifulsoup4 lxml`.

Each script has a small **CONFIG** block at the top (input folder, template
path, output names, options). By default the scripts operate on the folder they
are placed in and search it recursively. Typical flow per level:

```bash
# 1) convert HTML to PDF (dry-run first, then set SIMULAR = False)
python converter_html_para_pdf.py

# 2) build the metadata catalog
python gerar_planilha_perfil_estudantes.py   # or _mestrado / _doutorado

# 3) verify names line up
python conferir_nomes.py
```

Key options include a single combined CSV vs. one per year, the output folder
structure (per-year / mirror / flat), and the subject-tag separator — all set as
constants at the top of the files.

---

## Design notes & limitations

- **Legacy accents are unrecoverable.** In older cycles, accented characters in
  file names were replaced by underscores (e.g. `M_SICA` → "Música"). Those
  accents can't be restored from the file name; a small correction map handles
  the known cases, and the display name stays independent from the link.
- **Missing metadata is reported, not guessed.** When the source system or a
  unit code can't be determined, the field is marked for review rather than
  filled with a guess.
- **Unit lookup tables should be confirmed** against the institution's official
  list before publishing.

---

## Possible improvements

- A program → unit lookup to fill units for files whose names carry no unit code.
- A configurable correction map loaded from an external file.
- Tests and CI around the file-name parser.

---

## Data & privacy

This repo is **code only**. The reports contain aggregated institutional data
and must not be committed. A `.gitignore` is provided to keep report folders,
generated PDFs and CSVs out of version control. Review any sample before
publishing.

## License

Add a license of your choice (e.g. MIT) before publishing.
