"""
gerar_planilha_perfil_estudantes.py
-----------------------------------
Gera a planilha de metadados (CSV) dos relatórios "Perfil dos Estudantes de
Graduação da UnB" a partir dos arquivos HTML, seguindo o mesmo modelo/cabeçalho
fornecido pela DAI.

O que o script faz, para cada arquivo Relatorio_Avalia_UnB_<UNID>_<Curso>_<data>.html:
  1. Lê o CABEÇALHO e os VALORES FIXOS a partir do arquivo-modelo (assim a
     planilha sai sempre idêntica ao template, mesmo que a ordem de colunas mude).
  2. Extrai do NOME DO ARQUIVO: o nome do curso e a data.
     (o nome do curso NÃO existe no texto do relatório — o título interno é genérico)
  3. Extrai do TEXTO do relatório: a Fonte dos Dados (SIGRA ou SIGAA) e o ano-base.
  4. Preenche as colunas segundo as regras combinadas (ver CONSTANTES abaixo).
  5. Gera o `special_document` = nome do arquivo "limpo" (sem acento) + .pdf,
     que precisa BATER com o nome final do PDF (é o que vira o link no site).
  6. Exporta a planilha em CSV e, opcionalmente, um de-para de nomes de arquivo.

Dependências:  pip install beautifulsoup4 lxml
Uso:           ajuste os caminhos em CONFIG e rode:  python gerar_planilha_perfil_estudantes.py
"""

import csv
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup


# CONFIG — ajuste estes caminhos

PASTA_HTML   = Path(__file__).resolve().parent
ARQUIVO_MODELO = Path("Modelo_planilha_perfil_estudantes_-_Modelo.csv") 
SAIDA_PLANILHA = Path("planilha_perfil_estudantes.csv")
SAIDA_DEPARA   = Path("de-para_nomes_arquivos.csv") 
GERAR_DEPARA   = True

# True  -> gera um CSV por ano (planilha_perfil_estudantes_AAAA.csv), agrupando
#          pelo ANO DA PASTA (mesma divisão que você já tem em "Anos").
# False -> gera um ÚNICO CSV com todos os anos juntos.
UMA_PLANILHA_POR_ANO = False

# CONSTANTES — regras de preenchimento combinadas

# Colunas copiadas TAL QUAL do arquivo-modelo (valores institucionais fixos):
COPIAR_DO_MODELO = [
    "Instituição",
    "Unidade Responsável",
    "Unidade do DPO responsável pelo documento",
    "Idioma",
    "Eixos de Atuação",
]

# Texto padrão da coluna Descrição — igual para todos, variando curso e ano.
# {curso} e {ano} são preenchidos automaticamente por relatório.
DESCRICAO_TEMPLATE = (
    "Este relatório apresenta o perfil dos estudantes de graduação do curso de "
    "{curso} da Universidade de Brasília (UnB), com base nos dados de {ano}. "
    "Reúne informações sobre o perfil sociodemográfico dos discentes, como sexo, "
    "faixa etária e raça/cor, além das formas de ingresso e de saída do curso, do "
    "ingresso por reserva de vagas (cotas), da assistência estudantil e dos "
    "indicadores de formatura. As informações subsidiam a avaliação institucional "
    "e o acompanhamento acadêmico do curso."
)

# Valores fixos definidos por regra (iguais para todos os relatórios):
TIPO_DOCUMENTO      = "Perfil de Estudantes por Curso"    # corrige o typo "Perifl" do modelo
POPULACAO_ANALISADA = "Estudantes"
NIVEL               = "Graduação"
# Assunto: o campo é 'taxonomy|multiple', então aceita vários temas.

ASSUNTO = ["Perfil dos Estudantes", "Acesso e Permanência", "Indicadores de Graduação"]
SEPARADOR_ASSUNTO = "||"   # separador entre temas (a orientadora usa barra dupla no scraping)
MODALIDADE_PADRAO   = "Presencial"                       

# Colunas que ficam SEMPRE em branco:
EM_BRANCO = ["special_item_id", "Grau"]   # Unidade agora é preenchida (ver UNIDADES)

# Mapa código da unidade -> nome por extenso. O código vem do nome do arquivo
# (Relatorio_Avalia_UnB_<CODIGO>_<Curso>_<data>). Códigos não listados aqui saem
# com o próprio código e são apontados no fim para conferência.

UNIDADES = {
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
    # códigos históricos/antigos
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

# Correção de cursos com acento comido em anos antigos (chave = curso extraído):
CORRECOES_CURSO = {
    "Nutricao": "Nutrição",
}


# (o parsing agora é feito por parse_grad, mais abaixo)

# Conectivos que ficam em minúsculo no nome do curso:
CONECTIVOS = {"de", "da", "do", "das", "dos", "e"}

# Correções pontuais no nome de exibição do curso:
def corrigir_nome_curso(curso: str) -> str:
    curso = curso.replace("Teoria Crítica e História da Arte",
                          "Teoria, Crítica e História da Arte")     
    curso = re.sub(r"\bMsi\b", "MSI", curso)                        
    return curso


# FUNÇÕES AUXILIARES

# Prefixos/rótulos que aparecem antes do código da unidade em vários anos:
_PREFIXOS_GRAD = {"relatorio", "avalia", "perfil", "unb", "graduacao", "graduação",
                  "graduando", "graduandos", "mestrado", "doutorado"}


def parse_grad(stem: str):
    """Deriva (curso, data_iso, unidade_cod) de qualquer um dos formatos usados
    ao longo dos anos. Retorna None se não houver data no fim do nome.
    Formatos aceitos, ex.:
       Relatorio_Avalia_UnB_<UNID>_<Curso>_DATA
       Perfil_Graduacao_<UNID>_<Curso>_DATA
       Relatorio_Avalia_Graduacao_UnB_<UNID>_<Curso>_DATA
    """
    m = re.search(r"(\d{4}-\d{2}-\d{2})$", stem)
    if not m:
        return None
    data_iso = m.group(1)
    toks = stem[:m.start()].rstrip("_").split("_")
    i = 0
    while i < len(toks) and (toks[i] == "" or toks[i].lower() in _PREFIXOS_GRAD
                             or toks[i].lower().startswith("pos")):
        i += 1
    unidade = ""
    if i < len(toks):                      # próximo token é o código da unidade
        unidade = toks[i]; i += 1
    curso = "_".join(toks[i:]).replace("_-_", " - ").replace("_-", " - ").replace("_", " ")
    curso = re.sub(r"\s+", " ", curso).strip()
    if not curso:
        return None
    if curso == curso.upper():             # nomes ALLCAPS dos anos antigos (2020)
        curso = curso.title()              # -> Caixa Normal (acentos ainda faltam)
    curso = " ".join(w.lower() if w.lower() in CONECTIVOS else w for w in curso.split())
    curso = CORRECOES_CURSO.get(curso, curso)
    curso = corrigir_nome_curso(curso)
    return curso, data_iso, unidade


def data_br(data_iso: str) -> str:
    """2025-11-19 -> 19/11/2025"""
    ano, mes, dia = data_iso.split("-")
    return f"{dia}/{mes}/{ano}"


def texto_visivel(caminho: Path) -> str:
    """Extrai apenas o texto legível do HTML (descarta script/style)."""
    soup = BeautifulSoup(caminho.read_text(encoding="utf-8"), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(" ")


def extrair_fonte(texto: str) -> str:
    """Retorna 'SIGAA', 'SIGRA' ou 'VERIFICAR' conforme o que aparece no texto."""
    low = texto.lower()
    tem_sigaa = "sigaa" in low
    tem_sigra = "sigra" in low
    if tem_sigaa and not tem_sigra:
        return "SIGAA"
    if tem_sigra and not tem_sigaa:
        return "SIGRA"
    return "VERIFICAR"   # nenhum ou ambos -> conferir manualmente


def extrair_ano_base(texto: str) -> str:
    """Ano-base = ANO DOS DADOS, indicado no relatório como 'Perfil Geral - AAAA'
    (equivale ao ano de publicação menos 1). O ano da pasta é o ano de publicação,
    NÃO serve para o ano-base. Retorna 'VERIFICAR' se não encontrar."""
    anos = re.findall(r"perfil geral\s*-\s*(20\d{2})", texto, re.I)
    if anos:
        return max(anos)
    return "VERIFICAR"


def detectar_modalidade(nome_arquivo: str) -> str:
    """Padrão Presencial; marca 'A Distância' se o nome indicar EaD.
    (útil para os anos futuros que podem ter cursos EaD)"""
    if re.search(r"\b(ead|a[_ ]dist[aâ]ncia)\b", nome_arquivo, re.I):
        return "A Distância"
    return MODALIDADE_PADRAO


def sem_acentos(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(ch))


def limpar_nome_arquivo(stem: str) -> str:
    """Remove acentos, troca caracteres estranhos por _, colapsa __ e apara bordas.
    Mantém maiúsculas/minúsculas e hífens. É o nome que vira o link -> precisa
    ser idêntico ao PDF final."""
    s = sem_acentos(stem)
    s = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# GERAÇÃO DA PLANILHA

def ano_da_pasta(caminho: Path) -> str:
    """Ano de publicação para agrupar as planilhas: procura AAAA nas pastas
    (ex.: '... - 2022/graduacao'); se não achar, usa a data do nome do arquivo."""
    for parte in reversed(caminho.parent.parts):
        m = re.search(r"(20\d{2})", parte)
        if m:
            return m.group(1)
    m = re.search(r"_(\d{4})-\d{2}-\d{2}$", caminho.stem)
    return m.group(1) if m else "sem_ano"


def carregar_modelo(caminho_modelo: Path):
    with caminho_modelo.open(newline="", encoding="utf-8") as fh:
        linhas = list(csv.reader(fh))
    cabecalho = linhas[0]
    linha_ref = linhas[1] if len(linhas) > 1 else [""] * len(cabecalho)
    # mapa nome-da-coluna -> índice (nome = tudo antes do primeiro '|')
    indice = {col.split("|")[0].strip(): i for i, col in enumerate(cabecalho)}
    return cabecalho, linha_ref, indice


def montar_linha(caminho, parsed, cabecalho, linha_ref, idx):
    curso, data_iso, unidade_cod = parsed
    nome_arquivo_sem_ext = caminho.stem
    texto = texto_visivel(caminho)

    linha = [""] * len(cabecalho)

    # 1) colunas copiadas do modelo
    for nome in COPIAR_DO_MODELO:
        if nome in idx:
            linha[idx[nome]] = linha_ref[idx[nome]]

    ano_base = extrair_ano_base(texto)   # ano dos dados (do texto), não da pasta

    # 2) colunas calculadas
    linha[idx["Título"]]              = f"Perfil de Estudantes por Curso - {curso}"
    linha[idx["Descrição"]]           = DESCRICAO_TEMPLATE.format(curso=curso, ano=ano_base)
    linha[idx["Tipo de Documento"]]   = TIPO_DOCUMENTO
    linha[idx["População Analisada"]] = POPULACAO_ANALISADA
    linha[idx["Ano-base dos dados"]]  = ano_base
    linha[idx["Fonte dos Dados"]]     = extrair_fonte(texto)
    linha[idx["Curso"]]               = curso
    linha[idx["Unidade"]]             = UNIDADES.get(unidade_cod, unidade_cod)
    linha[idx["Nível"]]               = NIVEL
    linha[idx["Modalidade"]]          = detectar_modalidade(nome_arquivo_sem_ext)
    linha[idx["Data de Publicação"]]  = data_br(data_iso)
    linha[idx["Assunto"]]             = (SEPARADOR_ASSUNTO.join(ASSUNTO)
                                         if isinstance(ASSUNTO, (list, tuple)) else ASSUNTO)
    linha[idx["special_document"]]    = limpar_nome_arquivo(nome_arquivo_sem_ext) + ".pdf"

    # 3) colunas em branco (já estão "", mas deixamos explícito)
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
            print("  -> Ajuste ARQUIVO_MODELO para o caminho completo do modelo,")
            print("     ou copie o arquivo do modelo para a mesma pasta deste script.")
            return
    cabecalho, linha_ref, idx = carregar_modelo(modelo)

    arquivos = sorted(PASTA_HTML.rglob("*.html")) 
    print(f"Arquivos .html encontrados: {len(arquivos)}")
    if not arquivos:
        print(f"\nNENHUM .html encontrado em:\n  {PASTA_HTML}")
        print("Verifique se este script está DENTRO da pasta dos relatórios "
              "(ou ajuste PASTA_HTML para o caminho completo).")
        return

    linhas = []
    anos_pub = []
    depara = []
    fontes_para_conferir = []
    docs_gerados = []   # para checar nomes duplicados entre anos
    unidades_desconhecidas = {}   # codigo -> exemplo de arquivo
    ignorados = []                # arquivos .html sem data no nome (fora de padrão)

    for caminho in arquivos:
        stem = caminho.stem
        parsed = parse_grad(stem)
        if parsed is None:
            ignorados.append(caminho.name)
            continue
        linha = montar_linha(caminho, parsed, cabecalho, linha_ref, idx)
        linhas.append(linha)
        anos_pub.append(ano_da_pasta(caminho))
        docs_gerados.append(linha[idx["special_document"]])

        cod_unid = parsed[2]
        if cod_unid and cod_unid not in UNIDADES_COD:   # código fora do mapa UNIDADES
            unidades_desconhecidas.setdefault(cod_unid, caminho.name)

        novo = limpar_nome_arquivo(stem)
        depara.append((caminho.name, novo + ".html", novo + ".pdf"))

        if linha[idx["Fonte dos Dados"]] == "VERIFICAR":
            fontes_para_conferir.append(caminho.name)
        if linha[idx["Ano-base dos dados"]] == "VERIFICAR":
            fontes_para_conferir.append(caminho.name + "  (ano-base)")

    print(f"Relatórios processados: {len(linhas)}")
    from collections import Counter
    cont_ano = Counter(anos_pub)
    print("Por ano (ano da pasta/publicação):",
          "  ".join(f"{a}:{n}" for a, n in sorted(cont_ano.items())))

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

    # grava o de-para
    if GERAR_DEPARA and SAIDA_DEPARA:
      
        from collections import Counter
        colisoes = [n for n, c in Counter(x[2] for x in depara).items() if c > 1]
        if colisoes:
            print("ATENÇÃO — nomes finais duplicados:", colisoes)
        with SAIDA_DEPARA.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["nome_atual_html", "nome_novo_html", "nome_final_pdf"])
            w.writerows(depara)
        print(f"De-para gerado:  {SAIDA_DEPARA}")

    if fontes_para_conferir:
        print("\nConferir a fonte (SIGRA/SIGAA) manualmente nestes arquivos:")
        for n in fontes_para_conferir:
            print("  -", n)

    if unidades_desconhecidas:
        print("\nATENÇÃO — códigos de UNIDADE não reconhecidos (saíram com o próprio "
              "código na coluna Unidade). Adicione-os ao mapa UNIDADES:")
        for cod, exemplo in sorted(unidades_desconhecidas.items()):
            print(f"  - {cod}  (ex.: {exemplo})")

    repetidos = [d for d, c in Counter(docs_gerados).items() if c > 1]
    if repetidos:
        print(f"\nATENÇÃO — {len(repetidos)} nome(s) de 'special_document' repetido(s) "
              f"entre anos (o link/PDF colidiria). Exemplos:")
        for d in repetidos[:10]:
            print("  -", d)

    if ignorados:
        print(f"\nATENÇÃO — {len(ignorados)} arquivo(s) .html sem data no nome "
              "(não processados). Me mande esses nomes para eu ajustar o parser:")
        for n in ignorados:
            print("  -", n)


if __name__ == "__main__":
    main()
