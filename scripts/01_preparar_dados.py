"""
Prepara a base de acessos de banda larga fixa (Anatel / SCM) para RO e MT.

Entrada : data/raw/acessos_banda_larga_fixa.zip   (Anatel - Dados Abertos, ~1 GB)
Saidas  : data/processed/fato_acessos.csv      acessos por mes x municipio x prestadora x tecnologia
          data/processed/fato_densidade.csv    acessos por 100 domicilios, por municipio e mes
          data/processed/dim_municipio.csv
          data/processed/dim_prestadora.csv

O zip tem ~8 GB descompactado, entao o script le em streaming, linha a linha,
e so guarda as linhas de RO e MT. Roda com pouca memoria.

Uso: python scripts/01_preparar_dados.py
"""
import csv
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "interim"   # recorte RO/MT de cada arquivo (permite retomar se interromper)
UFS = {"RO", "MT"}
ANO_INICIAL = 2019

# Classificacao principal: campo oficial "Porte da Prestadora" da Anatel.
# A lista so e usada se o porte vier vazio.
GRANDES_REGEX = r"\b(?:CLARO|TELEFONICA|VIVO|TIM|OI|NIO|SKY)\b"

MARCAS = {"TELECOM AMERICAS": "Claro", "TELEFONICA": "Vivo", "TELECOM ITALIA": "TIM",
          "OI": "Oi", "SKY/AT&T": "Sky", "BRASIL TECPAR": "Brasil TecPar"}

MEIOS = {"Fibra": "Fibra óptica", "Cabo Coaxial": "Cabo coaxial", "Cabo Metálico": "Cabo metálico (DSL)",
         "Rádio": "Rádio", "Satélite": "Satélite"}
SUFIXOS = r"\s*[-,]?\s*\b(LTDA|LTD|ME|EPP|EIRELI|S/?A|S\.A\.?|SOCIEDADE ANONIMA)\b\.?"


def limpar_nome(nome: str) -> str:
    """'FULANO TELECOM LTDA - ME' -> 'Fulano Telecom'"""
    n = re.sub(SUFIXOS, "", str(nome).upper()).strip(" -.,")
    return n.title() if n else str(nome).title()


RENOMEAR = {
    "Ano": "ano", "Mês": "mes", "Grupo Econômico": "grupo_economico", "Empresa": "empresa",
    "CNPJ": "cnpj", "Porte da Prestadora": "porte", "UF": "uf", "Município": "municipio",
    "Código IBGE Município": "cod_ibge", "Código IBGE": "cod_ibge", "Tecnologia": "tecnologia",
    "Meio de Acesso": "meio_acesso", "Acessos": "acessos", "Densidade": "densidade",
    "Nível Geográfico Densidade": "nivel",
}
MANTER = ["ano", "mes", "grupo_economico", "empresa", "cnpj", "porte", "uf",
          "municipio", "cod_ibge", "tecnologia", "meio_acesso", "acessos"]


def filtrar(zf: zipfile.ZipFile, nome: str, manter: list[str]) -> pd.DataFrame:
    """Le um CSV do zip em streaming e devolve so as linhas de RO/MT."""
    with zf.open(nome) as fb:
        texto = io.TextIOWrapper(fb, encoding="utf-8-sig", newline="")
        leitor = csv.reader(texto, delimiter=";")
        cab = [RENOMEAR.get(c.strip(), c.strip()) for c in next(leitor)]
        i_uf = cab.index("uf")
        idx = [cab.index(c) for c in manter if c in cab]
        linhas = [[l[i] for i in idx] for l in leitor if len(l) > i_uf and l[i_uf] in UFS]
    return pd.DataFrame(linhas, columns=[cab[i] for i in idx])


URL_COORDS = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"


def coordenadas():
    """Latitude/longitude dos municipios (repositorio aberto kelvins/municipios-brasileiros)."""
    arq = RAW / "municipios_coordenadas.csv"
    try:
        if not arq.exists():
            from urllib.request import urlretrieve
            urlretrieve(URL_COORDS, arq)
        c = pd.read_csv(arq, dtype={"codigo_ibge": str})
        return c.rename(columns={"codigo_ibge": "cod_ibge"})[["cod_ibge", "latitude", "longitude"]]
    except Exception as e:  # sem internet: segue sem coordenadas
        print(f"aviso: sem coordenadas ({e})")
        return None


def arquivos_acessos(zf: zipfile.ZipFile) -> list[str]:
    nomes = []
    for n in zf.namelist():
        m = re.match(r"Acessos_Banda_Larga_Fixa_(\d{4})(?:[-_](\d{4}))?\.csv$", n)
        if m and int(m.group(2) or m.group(1)) >= ANO_INICIAL:
            nomes.append(n)
    return sorted(nomes)


def main():
    zips = sorted(RAW.glob("*.zip")) or sorted(ROOT.glob("*.zip"))
    if not zips:
        sys.exit("Coloque acessos_banda_larga_fixa.zip em data/raw/")
    CACHE.mkdir(parents=True, exist_ok=True)

    def recorte(zf, nome, manter):
        alvo = CACHE / nome
        if not alvo.exists():
            print(f"lendo {nome} ...", flush=True)
            tmp = alvo.with_suffix(".tmp")
            filtrar(zf, nome, manter).to_csv(tmp, index=False, sep=";")
            tmp.replace(alvo)
        return pd.read_csv(alvo, sep=";", dtype=str, keep_default_na=False)

    with zipfile.ZipFile(zips[0]) as zf:
        frames = [recorte(zf, n, MANTER) for n in arquivos_acessos(zf)]
        dens = recorte(zf, "Densidade_Banda_Larga_Fixa.csv",
                       ["ano", "mes", "uf", "municipio", "cod_ibge", "densidade", "nivel"])

    df = pd.concat(frames, ignore_index=True)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df = df[df["ano"] >= ANO_INICIAL]
    df["acessos"] = pd.to_numeric(df["acessos"], errors="coerce").fillna(0).astype(int)
    for c in ["grupo_economico", "empresa", "municipio", "tecnologia", "meio_acesso", "porte"]:
        df[c] = df[c].fillna("").str.strip().replace("", "Nao informado")

    df["grupo_economico"] = df["grupo_economico"].str.replace("TELEFÔNICA", "TELEFONICA")
    df["data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))

    # --- Classificacao -------------------------------------------------------------
    # 1) Porte: a Anatel publica o porte linha a linha e ha inconsistencias
    #    (ex.: em 2021 a Oi aparece como "Pequeno Porte"). Por isso usamos o porte
    #    MAIS RECENTE de cada CNPJ e aplicamos a todo o historico.
    ultimo_porte = (df.sort_values("data").drop_duplicates("cnpj", keep="last")
                      .set_index("cnpj")["porte"].str.upper())
    porte_cnpj = df["cnpj"].map(ultimo_porte)
    por_grupo = df["grupo_economico"].str.upper().str.contains(GRANDES_REGEX, regex=True)
    eh_grande = porte_cnpj.str.contains("GRANDE") | (~porte_cnpj.str.contains("GRANDE|PEQUENO") & por_grupo)
    # 2) Satelite (Starlink, Hughes, Viasat...) e outro mercado: vira categoria propria,
    #    senao infla os "provedores regionais" (a Anatel classifica a Starlink como pequeno porte).
    eh_sat = df["meio_acesso"].str.lower().str.startswith("sat")
    df["categoria"] = "Provedor regional"
    df.loc[eh_grande, "categoria"] = "Grande operadora"
    df.loc[eh_sat, "categoria"] = "Satélite"
    df["marca"] = df["grupo_economico"].map(MARCAS).fillna(df["empresa"].map(limpar_nome))
    df.loc[df["empresa"].str.upper().str.contains("STARLINK"), "marca"] = "Starlink"

    # O campo "Tecnologia" muda de nomenclatura entre os anos (ex.: "Fibra" x "FTTH");
    # o "Meio de Acesso" e estavel, entao ele vira a tecnologia do dashboard.
    df["tecnologia"] = df["meio_acesso"].map(MEIOS).fillna("Outros")

    chaves = ["data", "cod_ibge", "cnpj", "categoria", "tecnologia"]
    fato = df.groupby(chaves, as_index=False)["acessos"].sum()
    fato = fato[fato["acessos"] > 0]
    ult = df.sort_values("data")

    dens = dens[dens["nivel"].str.lower().str.startswith("munic")].copy()
    dens["ano"] = dens["ano"].astype(int)
    dens["mes"] = dens["mes"].astype(int)
    dens = dens[dens["ano"] >= ANO_INICIAL]
    dens["densidade"] = pd.to_numeric(dens["densidade"].str.replace(",", "."), errors="coerce").round(2)
    dens["data"] = pd.to_datetime(dict(year=dens["ano"], month=dens["mes"], day=1))
    dens = dens[["data", "cod_ibge", "densidade"]]

    OUT.mkdir(parents=True, exist_ok=True)
    kw = dict(index=False, encoding="utf-8-sig", sep=";", decimal=",")
    fato.to_csv(OUT / "fato_acessos.csv", date_format="%Y-%m-%d", **kw)
    dens.to_csv(OUT / "fato_densidade.csv", date_format="%Y-%m-%d", **kw)
    dim_mun = (ult.drop_duplicates("cod_ibge", keep="last")[["cod_ibge", "municipio", "uf"]]
                 .sort_values(["uf", "municipio"]))
    dim_mun["local_mapa"] = dim_mun["municipio"] + ", " + dim_mun["uf"] + ", Brasil"
    coords = coordenadas()
    if coords is not None:
        dim_mun = dim_mun.merge(coords, on="cod_ibge", how="left")
    dim_mun.to_csv(OUT / "dim_municipio.csv", **kw)
    (ult.drop_duplicates("cnpj", keep="last")
        [["cnpj", "empresa", "marca", "grupo_economico", "porte"]]
        .assign(porte_atual=lambda d: d["cnpj"].map(ultimo_porte).str.title())
        .drop(columns="porte")
        .to_csv(OUT / "dim_prestadora.csv", **kw))

    fim = fato["data"].max()
    print(f"\nPeriodo: {fato['data'].min():%m/%Y} a {fim:%m/%Y} | linhas fato: {len(fato):,}")
    print(df[df["data"] == fim].groupby(["uf", "categoria"])["acessos"].sum().unstack())


if __name__ == "__main__":
    main()
