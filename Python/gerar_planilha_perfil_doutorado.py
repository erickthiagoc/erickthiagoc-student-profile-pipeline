"""
gerar_planilha_perfil_doutorado.py

Gerador de planilha para os relatórios de DOUTORADO (pós-graduação).
  * Entende os vários formatos de nome de arquivo usados ao longo dos anos
    (ver comentário em parse_nome).
  * O NÍVEL é lido do título interno do relatório ("...de Doutorado da UnB").
  * O NOME DO PROGRAMA vem do nome do arquivo; acentos comidos são corrigidos
    via CORRECOES_PROGRAMA. A Descrição é adaptada para pós-graduação.

Dependências:  pip install beautifulsoup4 lxml
Uso:           ajuste os caminhos em CONFIG e rode:  python gerar_planilha_perfil_doutorado.py
"""

import csv
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup


# CONFIG

# Pasta base dos relatórios. Por padrão, a pasta onde ESTE script está
# (deixe o script dentro da pasta do doutorado e rode dali). Para fixar outra
# pasta, troque por um caminho completo, ex.: Path(r"C:\...\Estágio\Doutorado").
PASTA_HTML     = Path(__file__).resolve().parent
# Caminho COMPLETO do modelo (o mesmo arquivo usado na graduação).
# AJUSTE para onde o modelo realmente está no seu PC:
ARQUIVO_MODELO = Path(r"C:\Users\01969472600\Downloads\Modelo_planilha_perfil_estudantes_-_Modelo.csv")
SAIDA_PLANILHA = Path("planilha_perfil_doutorado.csv")
SAIDA_DEPARA   = Path("de-para_nomes_doutorado.csv")       # None para não gerar
GERAR_DEPARA   = True

# True -> um CSV por ano; False -> um único CSV com tudo.
# (o doutorado TEM pastas por ano; mude para True se quiser um CSV por ano, como na graduação)
UMA_PLANILHA_POR_ANO = False

# CONSTANTES — regras de preenchimento (iguais à graduação, salvo indicado)

COPIAR_DO_MODELO = [
    "Instituição",
    "Unidade Responsável",
    "Unidade do DPO responsável pelo documento",
    "Idioma",
    "Eixos de Atuação",
]

# {nivel} (ex.: "mestrado"), {programa} e {ano} são preenchidos automaticamente.
DESCRICAO_TEMPLATE = (
    "Este relatório apresenta o perfil dos estudantes de {nivel} do programa de "
    "pós-graduação em {programa} da Universidade de Brasília (UnB), com base nos "
    "dados de {ano}. Reúne informações sobre o perfil sociodemográfico dos "
    "discentes, como sexo, faixa etária e raça/cor, além das formas de ingresso "
    "e de saída e dos indicadores de titulação. As informações subsidiam a "
    "avaliação institucional e o acompanhamento acadêmico do programa."
)

TITULO_PREFIXO      = "Perfil de Estudantes por Curso - "  # mantém o mesmo termo da graduação
TIPO_DOCUMENTO      = "Perfil de Estudantes por Curso"     # termo da taxonomia (igual à graduação)
POPULACAO_ANALISADA = "Estudantes"
# NÍVEL: lido do título do relatório (Mestrado). Se não achar, usa este padrão:
NIVEL_PADRAO        = "Doutorado"
GRAU                = ""                                   # em branco (como na graduação)

ASSUNTO = ["Perfil dos Estudantes", "Pós-Graduação", "Acesso e Permanência"]
SEPARADOR_ASSUNTO = "||"    # barra dupla, como no scraping

MODALIDADE_PADRAO = "Presencial"

EM_BRANCO = ["special_item_id"]   # Grau vem de GRAU; Unidade é preenchida (ver UNIDADES)

CONECTIVOS = {"de", "da", "do", "das", "dos", "e", "em"}



# FUNÇÕES AUXILIARES

# Formatos de nome observados ao longo dos anos (todos suportados):
#   Relatorio_Avalia_UnB__NOME_..._DATA          (nome por extenso, unidade vazia)
#   Relatorio_Avalia_UnB_<UNID>_NOME_..._DATA    (com código de unidade)
#   Relatorio_Avalia_(Mestrado|Doutorado)_UnB_<UNID>_NOME_..._DATA
#   Perfil_(Doutorado|PosMestrado|...)_<UNID>_NOME_..._DATA
#   SIGLA_-_(MESTRADO|DOUTORADO)_DATA            (só a sigla do programa)
# OBS.: em vários arquivos os ACENTOS viraram "_" no nome (Administra__o =
#       Administração, M_SICA = MÚSICA). Isso NÃO é recuperável do nome; use
#       CORRECOES_PROGRAMA para arrumar a EXIBIÇÃO. O special_document continua
#       igual ao nome real do arquivo/PDF (o link não é afetado).

UNIDADES = {   # código -> nome por extenso
    "CET":  "Centro de Excelência em Turismo",
    "FACE": "Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas",
    "FAC":  "Faculdade de Comunicação",
    "FAU":  "Faculdade de Arquitetura e Urbanismo",
    "FAV":  "Faculdade de Agronomia e Medicina Veterinária",
    "FCI":  "Faculdade de Ciência da Informação",
    "FD":   "Faculdade de Direito",
    "FE":   "Faculdade de Educação",
    "FEF":  "Faculdade de Educação Física",
    "FM":   "Faculdade de Medicina",
    "FS":   "Faculdade de Ciências da Saúde",
    "FT":   "Faculdade de Tecnologia",
    "IdA":  "Instituto de Artes",
    "ICB":  "Instituto de Ciências Biológicas",
    "ICH":  "Instituto de Ciências Humanas",
    "ICS":  "Instituto de Ciências Sociais",
    "IE":   "Instituto de Ciências Exatas",
    "IF":   "Instituto de Física",
    "IG":   "Instituto de Geociências",
    "IL":   "Instituto de Letras",
    "IP":   "Instituto de Psicologia",
    "IPOL": "Instituto de Ciência Política",
    "IQ":   "Instituto de Química",
    "IREL": "Instituto de Relações Internacionais",
    "FCE":  "Faculdade de Ceilândia",
    "FGA":  "Faculdade do Gama",
    "FUP":  "Faculdade de Planaltina",
    "CEAM": "Centro de Estudos Avançados Multidisciplinares",
    "ADM":  "Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas",
    "ILD":  "Instituto de Letras",
}
# Códigos de DEPARTAMENTO usados nos anos antigos (2020-2023) -> faculdade.

DEPARTAMENTOS = {
    'ADM': 'Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas',
    'CCA': 'Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas',
    'ECO': 'Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas',
    'GPP': 'Faculdade de Economia, Administração, Contabilidade e Gestão de Políticas Públicas',
    'CEN': 'Instituto de Artes',
    'DIN': 'Instituto de Artes',
    'MUS': 'Instituto de Artes',
    'VIS': 'Instituto de Artes',
    'COM': 'Faculdade de Comunicação',
    'DAP': 'Faculdade de Comunicação',
    'JOR': 'Faculdade de Comunicação',
    'DAN': 'Instituto de Ciências Sociais',
    'SOL': 'Instituto de Ciências Sociais',
    'CIC': 'Instituto de Ciências Exatas',
    'EST': 'Instituto de Ciências Exatas',
    'MAT': 'Instituto de Ciências Exatas',
    'DSC': 'Faculdade de Ciências da Saúde',
    'ENF': 'Faculdade de Ciências da Saúde',
    'FCS': 'Faculdade de Ciências da Saúde',
    'NUT': 'Faculdade de Ciências da Saúde',
    'ODT': 'Faculdade de Ciências da Saúde',
    'EFL': 'Faculdade de Tecnologia',
    'ENC': 'Faculdade de Tecnologia',
    'ENE': 'Faculdade de Tecnologia',
    'ENM': 'Faculdade de Tecnologia',
    'FTD': 'Faculdade de Tecnologia',
    'FDD': 'Faculdade de Direito',
    'FED': 'Faculdade de Educação',
    'FMD': 'Faculdade de Medicina',
    'FIL': 'Instituto de Ciências Humanas',
    'GEA': 'Instituto de Ciências Humanas',
    'HIS': 'Instituto de Ciências Humanas',
    'SER': 'Instituto de Ciências Humanas',
    'IFD': 'Instituto de Física',
    'IGD': 'Instituto de Geociências',
    'IPD': 'Instituto de Psicologia',
    'IQD': 'Instituto de Química',
    'LET': 'Instituto de Letras',
    'LIP': 'Instituto de Letras',
    'CET': 'Centro de Excelência em Turismo',
}
UNIDADES.update(DEPARTAMENTOS)
UNIDADES.update({"IB": "Instituto de Ciências Biológicas", "IH": "Instituto de Ciências Humanas", "CDS": "Centro de Desenvolvimento Sustentável"})
UNIDADES_COD = set(UNIDADES)

# Programa por SIGLA (formato SIGLA_-_MESTRADO/DOUTORADO):
PROGRAMAS = {
    "PGAP": "Administração Pública",
    # "PPGXXX": "Nome do programa",
}

# Correção de nomes com acento comido (chave = nome extraído, antes do titlecase):
CORRECOES_PROGRAMA = {
    "Administra o": "Administração",
    "Administracao": "Administração",
    "Bio tica": "Bioética",
    "M SICA": "Música",
    "Ci ncias Cont beis": "Ciências Contábeis",
    "Ciencias e Tecnologias em Saude": "Ciências e Tecnologias em Saúde",
    "Regulacao e Gestao de Negocios": "Regulação e Gestão de Negócios",
    "Desenvolvimento Sociedade e Cooperacao Internacional":
        "Desenvolvimento, Sociedade e Cooperação Internacional",
}

_DESCARTE = {"relatorio", "avalia", "perfil", "unb"}


def titlecase_programa(s: str) -> str:
    s = s.title()
    return " ".join(w.lower() if w.lower() in CONECTIVOS else w for w in s.split())


def parse_nome(stem: str):
    """Retorna dict(programa, data, nivel_nome, sigla, unidade_cod) ou None."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", stem)
    if not m:
        return None
    data = m.group(1)
    corpo = stem[:m.start()].rstrip("_")

    ms = re.match(r"(.+?)_-_(MESTRADO|DOUTORADO)$", corpo, re.I)   # formato SIGLA
    if ms:
        sigla = ms.group(1).strip()
        return {"programa": PROGRAMAS.get(sigla.upper(), sigla), "data": data,
                "nivel_nome": ms.group(2).title(), "sigla": sigla, "unidade_cod": ""}

    toks = corpo.split("_")
    nivel = None; unidade = ""; i = 0
    while i < len(toks):
        t = toks[i]; low = t.lower()
        if t == "":                         i += 1; continue
        if low in _DESCARTE:                i += 1; continue
        if low in ("mestrado", "doutorado"): nivel = t.title(); i += 1; continue
        if low.startswith("pos"):
            nivel = "Doutorado" if "doutorado" in low else ("Mestrado" if "mestrado" in low else nivel)
            i += 1; continue
        if t in UNIDADES_COD and not unidade: unidade = t; i += 1; continue
        break
    raw = "_".join(toks[i:]).replace("_-_", " - ").replace("_", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return None
    prog = CORRECOES_PROGRAMA.get(raw, titlecase_programa(raw))
    return {"programa": prog, "data": data, "nivel_nome": nivel,
            "sigla": None, "unidade_cod": unidade}


def data_br(data_iso: str) -> str:
    ano, mes, dia = data_iso.split("-")
    return f"{dia}/{mes}/{ano}"


def ler_html(caminho: Path):
    """Retorna (nivel, texto_visivel). O nível vem do <title> do relatório."""
    soup = BeautifulSoup(caminho.read_text(encoding="utf-8"), "lxml")
    titulo = soup.title.string if soup.title else ""
    m = re.search(r"(Mestrado|Doutorado)", titulo or "", re.I)
    nivel = m.group(1).title() if m else NIVEL_PADRAO
    for tag in soup(["script", "style"]):
        tag.decompose()
    return nivel, soup.get_text(" ")


def extrair_fonte(texto: str) -> str:
    low = texto.lower()
    tem_sigaa, tem_sigra = "sigaa" in low, "sigra" in low
    if tem_sigaa and not tem_sigra:
        return "SIGAA"
    if tem_sigra and not tem_sigaa:
        return "SIGRA"
    return "VERIFICAR"


def extrair_ano_base(texto: str) -> str:
    anos = re.findall(r"perfil geral\s*-\s*(20\d{2})", texto, re.I)
    return max(anos) if anos else "VERIFICAR"


def detectar_modalidade(nome_arquivo: str) -> str:
    if re.search(r"\b(ead|a[_ ]dist[aâ]ncia)\b", nome_arquivo, re.I):
        return "A Distância"
    return MODALIDADE_PADRAO


def sem_acentos(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(ch))


def limpar_nome_arquivo(stem: str) -> str:
    s = sem_acentos(stem)
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def ano_da_pasta(caminho: Path) -> str:
    for parte in reversed(caminho.parent.parts):
        m = re.search(r"(20\d{2})", parte)
        if m:
            return m.group(1)
    m = re.search(r"_(\d{4})-\d{2}-\d{2}$", caminho.stem)
    return m.group(1) if m else "sem_ano"


# GERAÇÃO

def carregar_modelo(caminho_modelo: Path):
    with caminho_modelo.open(newline="", encoding="utf-8") as fh:
        linhas = list(csv.reader(fh))
    cabecalho = linhas[0]
    linha_ref = linhas[1] if len(linhas) > 1 else [""] * len(cabecalho)
    indice = {col.split("|")[0].strip(): i for i, col in enumerate(cabecalho)}
    return cabecalho, linha_ref, indice


def montar_linha(caminho, parsed, cabecalho, linha_ref, idx):
    programa  = parsed["programa"]
    data_iso  = parsed["data"]
    nivel_titulo, texto = ler_html(caminho)
    nivel = nivel_titulo
    if (not nivel_titulo or nivel_titulo == NIVEL_PADRAO) and parsed["nivel_nome"]:
        nivel = parsed["nivel_nome"]
    ano_base = extrair_ano_base(texto)

    linha = [""] * len(cabecalho)

    for nome in COPIAR_DO_MODELO:
        if nome in idx:
            linha[idx[nome]] = linha_ref[idx[nome]]

    linha[idx["Título"]]              = TITULO_PREFIXO + programa
    linha[idx["Descrição"]]           = DESCRICAO_TEMPLATE.format(
                                            nivel=nivel.lower(), programa=programa, ano=ano_base)
    linha[idx["Tipo de Documento"]]   = TIPO_DOCUMENTO
    linha[idx["População Analisada"]] = POPULACAO_ANALISADA
    linha[idx["Ano-base dos dados"]]  = ano_base
    linha[idx["Fonte dos Dados"]]     = extrair_fonte(texto)
    linha[idx["Curso"]]               = programa
    linha[idx["Unidade"]]             = UNIDADES.get(parsed["unidade_cod"], parsed["unidade_cod"])
    linha[idx["Grau"]]                = GRAU
    linha[idx["Nível"]]               = nivel
    linha[idx["Modalidade"]]          = detectar_modalidade(caminho.stem)
    linha[idx["Data de Publicação"]]  = data_br(data_iso)
    linha[idx["Assunto"]]             = (SEPARADOR_ASSUNTO.join(ASSUNTO)
                                         if isinstance(ASSUNTO, (list, tuple)) else ASSUNTO)
    linha[idx["special_document"]]    = limpar_nome_arquivo(caminho.stem) + ".pdf"

    for nome in EM_BRANCO:
        if nome in idx:
            linha[idx[nome]] = ""

    return linha


def main():
    modelo = ARQUIVO_MODELO
    if not modelo.exists():
        alt = Path(__file__).with_name(ARQUIVO_MODELO.name)   # tenta ao lado do script
        if alt.exists():
            modelo = alt
        else:
            print("ERRO: modelo não encontrado.")
            print(f"  Procurei em: {ARQUIVO_MODELO}")
            print(f"  e também em: {alt}")
            print("  -> Ajuste a constante ARQUIVO_MODELO para o caminho COMPLETO do modelo,")
            print("     ou copie o arquivo do modelo para a mesma pasta deste script.")
            return

    cabecalho, linha_ref, idx = carregar_modelo(modelo)
    arquivos = sorted(PASTA_HTML.rglob("*.html"))   # pega TODOS os .html (os 2 formatos)
    print(f"Arquivos .html encontrados: {len(arquivos)}")
    if not arquivos:
        print(f"\nNENHUM .html encontrado em:\n  {PASTA_HTML}")
        print("Verifique se este script está DENTRO da pasta dos relatórios "
              "(ou ajuste PASTA_HTML para o caminho completo).")
        return

    linhas, anos_pub, depara, conferir, docs, ignorados = [], [], [], [], [], []
    for caminho in arquivos:
        parsed = parse_nome(caminho.stem)
        if parsed is None:                       # não encaixa em nenhum formato
            ignorados.append(caminho.name)
            continue
        linha = montar_linha(caminho, parsed, cabecalho, linha_ref, idx)
        linhas.append(linha)
        anos_pub.append(ano_da_pasta(caminho))
        docs.append(linha[idx["special_document"]])
        novo = limpar_nome_arquivo(caminho.stem)
        depara.append((caminho.name, novo + ".html", novo + ".pdf"))
        if linha[idx["Fonte dos Dados"]] == "VERIFICAR":
            conferir.append(caminho.name + "  (fonte)")
        if linha[idx["Ano-base dos dados"]] == "VERIFICAR":
            conferir.append(caminho.name + "  (ano-base)")
        sigla = parsed["sigla"]
        if sigla and parsed["programa"] == sigla:          # sigla sem nome no mapa PROGRAMAS
            conferir.append(caminho.name + f"  (programa = sigla '{sigla}', preencha PROGRAMAS)")

    print(f"Relatórios processados: {len(linhas)}")

    def gravar(caminho_saida, subset):
        with caminho_saida.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(cabecalho)
            w.writerows(subset)

    if UMA_PLANILHA_POR_ANO:
        por_ano = {}
        for ano, linha in zip(anos_pub, linhas):
            por_ano.setdefault(ano, []).append(linha)
        for ano in sorted(por_ano):
            saida = SAIDA_PLANILHA.with_name(f"{SAIDA_PLANILHA.stem}_{ano}{SAIDA_PLANILHA.suffix}")
            gravar(saida, por_ano[ano])
            print(f"Planilha {ano}: {saida.name}  ({len(por_ano[ano])} linhas)")
    else:
        gravar(SAIDA_PLANILHA, linhas)
        print(f"Planilha gerada: {SAIDA_PLANILHA}  ({len(linhas)} linhas)")

    if GERAR_DEPARA and SAIDA_DEPARA:
        with SAIDA_DEPARA.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["nome_atual_html", "nome_novo_html", "nome_final_pdf"])
            w.writerows(depara)
        print(f"De-para gerado:  {SAIDA_DEPARA}")

    if conferir:
        print("\nConferir manualmente:")
        for n in conferir:
            print("  -", n)

    if ignorados:
        print(f"\nATENÇÃO — {len(ignorados)} arquivo(s) .html NÃO reconhecido(s) "
              "(fora dos formatos A e B). Me mande esses nomes para eu ajustar o parser:")
        for n in ignorados:
            print("  -", n)


if __name__ == "__main__":
    main()
