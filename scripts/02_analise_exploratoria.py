"""Numeros-chave do projeto (base para o README e para validar o dashboard)."""
from pathlib import Path
import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
rd = dict(sep=";", decimal=",", dtype={"cod_ibge": str, "cnpj": str}, parse_dates=["data"])
f = pd.read_csv(P / "fato_acessos.csv", **rd)
d = pd.read_csv(P / "fato_densidade.csv", **rd)
m = pd.read_csv(P / "dim_municipio.csv", sep=";", dtype=str)
pr = pd.read_csv(P / "dim_prestadora.csv", sep=";", dtype=str)
f = f.merge(m, on="cod_ibge").merge(pr[["cnpj", "marca"]], on="cnpj")
INI, FIM = pd.Timestamp("2019-12-01"), f["data"].max()
pd.set_option("display.width", 200)

print("== Share por categoria (dez de cada ano + ultimo mes) ==")
datas = sorted({pd.Timestamp(f"{a}-12-01") for a in range(2019, FIM.year)} | {FIM})
x = f[f.data.isin(datas)].groupby(["uf", "data", "categoria"]).acessos.sum().unstack()
print((x.div(x.sum(axis=1), axis=0) * 100).round(1).assign(total=x.sum(axis=1)).to_string())

print("\n== Tecnologia (ultimo mes, %) ==")
t = f[f.data == FIM].groupby(["uf", "tecnologia"]).acessos.sum().unstack()
print((t.div(t.sum(axis=1), axis=0) * 100).round(1).to_string())

print("\n== Top 10 marcas (ultimo mes) e crescimento desde dez/2019 ==")
a = f[f.data == FIM].groupby(["marca", "categoria"]).acessos.sum()
b = f[f.data == INI].groupby(["marca", "categoria"]).acessos.sum()
top = pd.DataFrame({"hoje": a, "dez19": b}).fillna(0).sort_values("hoje", ascending=False).head(12)
print(top.astype(int).to_string())

print("\n== Municipios ==")
def share(dt):
    g = f[f.data == dt].groupby(["cod_ibge", "categoria"]).acessos.sum().unstack().fillna(0)
    return g.div(g.sum(axis=1), axis=0) * 100, g.sum(axis=1)
s1, tot1 = share(FIM); s0, _ = share(INI)
mm = m.set_index("cod_ibge").copy()
mm["acessos"] = tot1
mm["share_regional"] = s1["Provedor regional"]
mm["share_grande"] = s1["Grande operadora"]
mm["delta_regional_pp"] = s1["Provedor regional"] - s0["Provedor regional"].reindex(s1.index).fillna(0)
lider = f[f.data == FIM].groupby(["cod_ibge", "marca"]).acessos.sum().reset_index().sort_values("acessos")
lider = lider.groupby("cod_ibge").tail(1).set_index("cod_ibge")
mm["lider"] = lider["marca"]; mm["share_lider"] = lider["acessos"] / tot1 * 100
mm["n_prestadoras"] = f[f.data == FIM].groupby("cod_ibge").cnpj.nunique()
mm["dens_100hab"] = d[d.data == d.data.max()].set_index("cod_ibge")["densidade"]
mm = mm.round(1)
print("municipios onde regionais ja lideram (>50%):", (mm.share_regional > 50).sum(), "de", len(mm))
print("\nMaior ganho de share dos regionais (pp, municipios >= 5 mil acessos):")
print(mm[mm.acessos >= 5000].sort_values("delta_regional_pp", ascending=False).head(10).to_string())
print("\nOnde grandes ainda dominam (municipios >= 5 mil acessos):")
print(mm[mm.acessos >= 5000].sort_values("share_grande", ascending=False).head(10).to_string())
print("\nMenor densidade (acessos/100 hab):")
print(mm.sort_values("dens_100hab").head(10).to_string())
print("\nMediana densidade por UF:", mm.groupby("uf").dens_100hab.median().to_dict())
mm.to_csv(P / "resumo_municipios.csv", sep=";", decimal=",", encoding="utf-8-sig")
