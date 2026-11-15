"""Construye los dos notebooks del AED (aed/) y los ejecuta.

Notebook 1: baterias individuales (P001_1 calendario, P058_1 ciclica).
Notebook 2: conjunto de 228 baterias (desde datos/consolidado_capacidad.csv).

Los notebooks se ejecutan con el kernel 'baterias' y quedan con las
salidas guardadas, para no tener que ejecutarlos a mano.
"""
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

REPO = Path(__file__).resolve().parent
AED = REPO / "aed"


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


def build_nb1():
    nb = nbf.v4.new_notebook(metadata={"kernelspec": {"display_name": "Python (baterias)",
                                                      "language": "python", "name": "baterias"},
                                       "language_info": {"name": "python", "version": "3.12"}})
    cells = []
    cells.append(md(r"""
# AED 01 — Baterías individuales

Análisis exploratorio de **una celda cada vez**: qué hay dentro de un archivo
de resultados (EOC), cómo se mide la capacidad en cada check-up (CU) y qué
columnas no se pueden usar como variables (fuga de información).

**Dataset:** Luh & Blank (2024), *Comprehensive battery aging dataset*,
RADAR4KIT v2, *result data*, DOI [10.35097/1969](https://doi.org/10.35097/1969).
Celdas LG INR18650HG2 (NMC/C-SiO, 3000 mAh nominales). Licencia CC BY 4.0.

**Cómo reproducirlo:** desde la raíz del repo, `python descarga_dataset.py`
descarga los 10 archivos de RADAR4KIT y los descomprime en `dataset/`.
Este notebook lee de `../dataset/extraido/`.
"""))
    cells.append(code(r"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA = Path("../dataset/extraido")
EOC = DATA / "cell_eocv2"
EIS = DATA / "cell_eisv2"
PLS = DATA / "cell_plsv2"
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 200)
print("archivos EOC:", len(list(EOC.glob("*.csv"))))
print("archivos EIS:", len(list(EIS.glob("*.csv"))))
print("archivos PLS:", len(list(PLS.glob("*.csv"))))
"""))
    cells.append(md(r"""
## 1. Una celda de calendario: P001_1

P001 es calendario a 0 °C y 10 % de SoC. La celda 1 es `cell_eocv2_P001_1_S01_C10.csv`.
Primero, el archivo crudo: forma, columnas y qué filas traen capacidad.
"""))
    cells.append(code(r"""
f = EOC / "cell_eocv2_P001_1_S01_C10.csv"
df = pd.read_csv(f, sep=";")
print("forma:", df.shape, "(filas, columnas)")
print("columnas:", list(df.columns))
cols = ["timestamp_s", "cyc_condition", "cyc_charged", "num_cycles_op",
        "num_cycles_checkup", "cap_aged_est_Ah", "soh_cap"]
print(df[cols].head(8).to_string())
"""))
    cells.append(code(r"""
print("filas por cyc_condition (0 = operacion, 1 = ciclado, 2 = check-up):")
print(df["cyc_condition"].value_counts().sort_index().to_string())
print()
print("filas con capacidad/SoH no nulos, por cyc_condition:")
print(df[df["soh_cap"].notna()]["cyc_condition"].value_counts().sort_index().to_string())
print()
print("NaN en cap_aged_est_Ah:", df["cap_aged_est_Ah"].isna().sum(), "de", len(df))
"""))
    cells.append(md(r"""
**Lectura:** el archivo tiene 430 filas (una por ciclo o evento), pero la
capacidad y el SoH solo aparecen en **58 filas, todas con `cyc_condition = 2`**
(check-up). Las demás filas son operación entre check-ups y no traen medida
de capacidad. El análisis de SoH usa solo las filas de check-up.
"""))
    cells.append(md(r"""
## 2. Dos medidas por check-up: carga y descarga

Cada CU aporta **dos filas**: una con `cyc_charged = 1` (carga) y otra con
`cyc_charged = 0` (descarga). Son dos estimaciones de la misma capacidad.
"""))
    cells.append(code(r"""
cu = df[(df["cyc_condition"] == 2) & df["soh_cap"].notna()].copy()
print("filas CU:", len(cu), "| CU distintos:", cu["num_cycles_checkup"].nunique())
print("filas por CU:", cu.groupby("num_cycles_checkup").size().value_counts().to_dict())
piv = cu.pivot(index="num_cycles_checkup", columns="cyc_charged",
               values="cap_aged_est_Ah")
piv.columns = ["q_dischg_Ah", "q_chg_Ah"]
piv["dif_Ah"] = piv["q_chg_Ah"] - piv["q_dischg_Ah"]
piv["dif_pct"] = 100 * piv["dif_Ah"] / piv["q_dischg_Ah"]
print(piv.head(10).round(4).to_string())
print()
print("diferencia carga-descarga: media %.4f Ah (%.2f %%), max %.4f Ah"
      % (piv["dif_Ah"].mean(), piv["dif_pct"].mean(), piv["dif_Ah"].max()))
"""))
    cells.append(code(r"""
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(piv.index, piv["q_chg_Ah"], "o-", ms=4, label="carga")
ax.plot(piv.index, piv["q_dischg_Ah"], "s-", ms=4, label="descarga")
ax.set_xlabel("Check-up (CU)")
ax.set_ylabel("Capacidad estimada [Ah]")
ax.set_title("P001_1 (calendario, 0 °C, 10 % SoC): capacidad por CU")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
**Decisión:** la diferencia carga–descarga es pequeña (media 0,017 Ah, ~0,6 %)
y no tiene tendencia. Para tener **un valor por CU** se usa la **media de
ambas**; así se construye también el consolidado (`datos/consolidado_capacidad.csv`).
"""))
    cells.append(md(r"""
## 3. La fuga: `soh_cap` y `cap_aged_est_Ah` son la misma columna

En el archivo van lado a lado `cap_aged_est_Ah` (capacidad en Ah) y `soh_cap`
(SoH en %). La documentación oficial (*Data Structure v05.3*, hoja EOCV2)
define `soh_cap` así:

> *estimated capacity SoH of the cell (100 = 100%), SoH = 0 if cap_aged_est_Ah
> is 40% (50%) of the nominal capacity when cycling (when in checkups).*

Es decir, `soh_cap` **no se mide**: se calcula a partir de la capacidad, con
un piso del 50 % de la nominal en check-ups (y del 40 % en ciclado). Si una
de las dos entra como variable y la otra es el objetivo, el modelo no aprende
nada: ya tiene la respuesta. Lo verificamos.
"""))
    cells.append(code(r"""
cu = df[(df["cyc_condition"] == 2) & df["soh_cap"].notna()]
print("correlacion soh_cap vs cap_aged_est_Ah (filas CU):",
      round(cu["soh_cap"].corr(cu["cap_aged_est_Ah"]), 12))
a, b = np.polyfit(cu["cap_aged_est_Ah"], cu["soh_cap"], 1)
print("ajuste: soh_cap = %.4f * cap_aged_est_Ah %+.4f" % (a, b))
print("formula del piso 50%%: soh_cap = (cap - 1.5) / 1.5 * 100")
err = ((cu["cap_aged_est_Ah"] - 1.5) / 1.5 * 100 - cu["soh_cap"]).abs().max()
print("desviacion maxima de esa formula: %.2e (redondeo float)" % err)
"""))
    cells.append(code(r"""
fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(cu["cap_aged_est_Ah"], cu["soh_cap"], s=30)
xs = np.linspace(cu["cap_aged_est_Ah"].min(), cu["cap_aged_est_Ah"].max(), 10)
ax.plot(xs, (xs - 1.5) / 1.5 * 100, "r--", label="(cap - 1.5)/1.5 * 100")
ax.set_xlabel("cap_aged_est_Ah [Ah]")
ax.set_ylabel("soh_cap [%]")
ax.set_title("P001_1, filas CU: soh_cap es funcion exacta de la capacidad")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
**Confirmado: correlación 1,0 y fórmula exacta.** `cap_aged_est_Ah` determina
`soh_cap` por completo en las filas de check-up. **Decisión: se elimina
`cap_aged_est_Ah` de las variables** y se conserva `soh_cap` como objetivo.
Lo mismo vale al revés: si el objetivo fuera la capacidad en Ah, habría que
quitar `soh_cap`.

**Ojo con la escala:** `soh_cap` no es Q/Q_nom. Es un SoH reescalado con piso
en el 50 % de la nominal: `soh_cap = 0` equivale a Q = 1,5 Ah (50 % nominal)
y `soh_cap = 100` a Q = 3,0 Ah. El SoH del diseño experimental es
`SoH_nominal = Q / 3,0 * 100`, y la conversión entre ambas escalas es:

$$SoH_{nominal} = 50 + soh_{cap}/2 \qquad (soh_{cap}=60 \iff 80\% \ nominal;\ soh_{cap}=0 \iff 50\% \ nominal)$$
"""))
    cells.append(code(r"""
piv["q_Ah"] = piv[["q_chg_Ah", "q_dischg_Ah"]].mean(axis=1)
piv["soh_cap"] = cu.groupby("num_cycles_checkup")["soh_cap"].mean()
piv["soh_nominal"] = piv["q_Ah"] / 3.0 * 100
print(piv[["q_Ah", "soh_cap", "soh_nominal"]].round(2).head(8).to_string())
print("...")
print(piv[["q_Ah", "soh_cap", "soh_nominal"]].round(2).tail(3).to_string())
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(piv.index, piv["soh_nominal"], "o-", ms=4, label="SoH nominal (Q/3,0)")
ax.plot(piv.index, piv["soh_cap"], "s-", ms=4, label="soh_cap (dataset)")
ax.axhline(80, color="r", ls="--", lw=1, label="80 % nominal (= soh_cap 60)")
ax.axhline(50, color="r", ls=":", lw=1, label="50 % nominal (= soh_cap 0)")
ax.set_xlabel("Check-up (CU)")
ax.set_ylabel("SoH [%]")
ax.set_title("P001_1: las dos escalas de SoH")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
## 4. Una celda cíclica: P058_1 y los dos pisos

P058 es cíclica a 40 °C (carga 0,33C, descarga 1C). En las celdas cíclicas la
capacidad también se estima **en cada ciclo de operación** (`cyc_condition = 1`),
no solo en los check-ups. Y ahí el piso es otro: **40 %** en vez de 50 %.
"""))
    cells.append(code(r"""
f2 = EOC / "cell_eocv2_P058_1_S15_C07.csv"
d2 = pd.read_csv(f2, sep=";")
print("forma:", d2.shape, "| filas con SoH:", d2["soh_cap"].notna().sum())
print("filas con SoH por cyc_condition:")
print(d2[d2["soh_cap"].notna()]["cyc_condition"].value_counts().sort_index().to_string())
s2 = d2.dropna(subset=["soh_cap"])
for cond, g in s2.groupby("cyc_condition"):
    a, b = np.polyfit(g["cap_aged_est_Ah"], g["soh_cap"], 1)
    e50 = ((g["cap_aged_est_Ah"] - 1.5) / 1.5 * 100 - g["soh_cap"]).abs().max()
    e40 = ((g["cap_aged_est_Ah"] - 1.2) / 1.8 * 100 - g["soh_cap"]).abs().max()
    print("cyc_condition=%d n=%d: soh = %.4f*cap %+.4f | desv. piso50%%: %.1e | desv. piso40%%: %.1e"
          % (cond, len(g), a, b, e50, e40))
cu2 = s2[s2["cyc_condition"] == 2]
print("filas CU:", len(cu2), "| CU distintos:", cu2["num_cycles_checkup"].nunique(),
      "| num_cycles_op max:", d2["num_cycles_op"].max())
"""))
    cells.append(code(r"""
fig, ax = plt.subplots(figsize=(6, 5))
for cond, g in s2.groupby("cyc_condition"):
    ax.scatter(g["cap_aged_est_Ah"], g["soh_cap"], s=8, alpha=0.5,
               label=f"cyc_condition={cond} (n={len(g)})")
xs = np.linspace(1.2, 3.0, 10)
ax.plot(xs, (xs - 1.5) / 1.5 * 100, "r--", label="piso 50% (check-up)")
ax.plot(xs, (xs - 1.2) / 1.8 * 100, "g--", label="piso 40% (ciclado)")
ax.set_xlabel("cap_aged_est_Ah [Ah]")
ax.set_ylabel("soh_cap [%]")
ax.set_title("P058_1 (ciclica, 40 °C): dos rectas, dos pisos")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
**Lectura:** en la misma columna conviven **dos definiciones de SoH** según
el tipo de fila: piso 50 % en check-ups y piso 40 % en ciclado. Por eso el
consolidado usa **solo las filas de check-up** (`cyc_condition = 2`): son las
medidas comparables (25 °C, 1/3C) del diseño experimental, y ahí la fórmula
es única. Las estimaciones por ciclo son útiles para diagnóstico, no para el
modelo de SoH por CU.
"""))
    cells.append(md(r"""
## 5. Las celdas P000: archivos vacíos

Los zips traen 240 archivos EOC, pero solo 228 celdas son P001_1–P076_3.
Los 12 restantes son P000_0 (esclavo 20, puestos C00–C11).
"""))
    cells.append(code(r"""
import glob
vacio = []
for f in sorted(glob.glob(str(EOC / "cell_eocv2_P000_*.csv"))):
    d = pd.read_csv(f, sep=";")
    vacio.append((Path(f).name, d.shape))
print("archivos P000:", len(vacio))
print("formas:", sorted(set(s for _, s in vacio)))
print("ejemplo:", vacio[0][0], "->", vacio[0][1])
print("P000 no tiene filas: son puestos sin datos y se excluyen del analisis.")
"""))
    cells.append(md(r"""
## 6. Un vistazo a EIS y PLS (misma celda)

La impedancia (EIS) y la resistencia de pulso (PLS) son las otras dos
medidas de cada check-up. No entran en el consolidado de capacidad, pero
conviene ver su forma: son la "primera mejora" del diseño.
"""))
    cells.append(code(r"""
eis = pd.read_csv(EIS / "cell_eisv2_P001_1_S01_C10.csv", sep=";")
print("EIS forma:", eis.shape)
print("columnas:", list(eis.columns))
print("espectros (timestamps distintos):", eis["timestamp_s"].nunique(),
      "| frecuencias por espectro:", eis.groupby("timestamp_s")["freq_Hz"].nunique().iloc[0])
print("SoC medidos:", sorted(eis["soc_nom"].unique()),
      "| RT vs OT:", eis["is_rt"].value_counts().to_dict())
sp = eis.groupby("timestamp_s")["soh_imp"].first()
print("soh_imp por espectro: media %.1f %%, min %.1f, max %.1f"
      % (sp.mean(), sp.min(), sp.max()))
"""))
    cells.append(code(r"""
def espectro(t):
    g = eis[eis["timestamp_s"] == t].dropna(subset=["z_re_comp_mOhm"])
    return g.sort_values("freq_Hz")
t0, t1 = sorted(eis["timestamp_s"].unique())[0], sorted(eis["timestamp_s"].unique())[-1]
g0, g1 = espectro(t0), espectro(t1)
fig, ax = plt.subplots(figsize=(6, 5))
ax.plot(g0["z_re_comp_mOhm"], -g0["z_im_comp_mOhm"], "o-", ms=4, label="primer espectro")
ax.plot(g1["z_re_comp_mOhm"], -g1["z_im_comp_mOhm"], "s-", ms=4, label="ultimo espectro")
ax.set_xlabel("Z' [mOhm]")
ax.set_ylabel("-Z'' [mOhm]")
ax.set_title("P001_1: Nyquist (SoC 10 %, RT) — primero vs ultimo")
ax.legend(); ax.grid(True, alpha=0.3); ax.set_aspect("equal", adjustable="datalim")
plt.show()
"""))
    cells.append(code(r"""
pls = pd.read_csv(PLS / "cell_plsv2_P001_1_S01_C10.csv", sep=";")
print("PLS forma:", pls.shape)
print("columnas:", list(pls.columns))
r = pls.groupby("timestamp_s")[["r_ref_10ms_mOhm", "r_ref_1s_mOhm"]].first()
print(r.describe().round(2).to_string())
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(len(r)), r["r_ref_1s_mOhm"], "o-", ms=3, label="R 1 s")
ax.plot(range(len(r)), r["r_ref_10ms_mOhm"], "s-", ms=3, label="R 10 ms")
ax.set_xlabel("Medida de pulso (orden temporal)")
ax.set_ylabel("Resistencia [mOhm]")
ax.set_title("P001_1: resistencia de pulso por medida")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(code(r"""
res = pd.DataFrame({
    "CU": [0, piv.index.max()],
    "Q_Ah": [piv["q_Ah"].iloc[0], piv["q_Ah"].iloc[-1]],
    "SoH_nominal": [piv["soh_nominal"].iloc[0], piv["soh_nominal"].iloc[-1]],
    "soh_cap": [piv["soh_cap"].iloc[0], piv["soh_cap"].iloc[-1]],
    "ciclos_op": [0, 0]})
print("P001_1 (calendario, 0 °C, 10 % SoC): primera y ultima CU")
print(res.round(2).to_string(index=False))
print()
print("caida total de SoH nominal: %.1f puntos en %d CU (%.2f puntos/CU)"
      % (res["SoH_nominal"].iloc[0] - res["SoH_nominal"].iloc[-1],
         piv.index.max(), (res["SoH_nominal"].iloc[0] - res["SoH_nominal"].iloc[-1]) / piv.index.max()))
"""))
    cells.append(md(r"""
**Conclusiones del AED 01**
1. La capacidad solo se mide en los check-ups (2 filas por CU: carga y descarga, diferencia ~0,6 %); un valor por CU = media de ambas.
2. `soh_cap` es función exacta de `cap_aged_est_Ah` (correlación 1,0): **fuga**. Se elimina la capacidad en Ah de las variables; el objetivo es `soh_cap` (o su equivalente `SoH_nominal`).
3. Hay **dos pisos**: 50 % en check-ups y 40 % en ciclado. El modelo usa solo check-ups.
4. Las 12 celdas P000 están vacías y se excluyen. Quedan **228 celdas**.
5. EIS (291 espectros × 29 frecuencias) y PLS (resistencia de pulso) existen por celda: son la primera mejora del modelo.
"""))
    nb["cells"] = cells
    return nb


def build_nb2():
    nb = nbf.v4.new_notebook(metadata={"kernelspec": {"display_name": "Python (baterias)",
                                                      "language": "python", "name": "baterias"},
                                       "language_info": {"name": "python", "version": "3.12"}})
    cells = []
    cells.append(md(r"""
# AED 02 — Conjunto de baterías

Análisis exploratorio de las **228 celdas juntas**: cobertura, degradación por
condición, variabilidad entre réplicas y qué implican los datos para el
diseño experimental (partición por celda y por condición, corte temporal).

**Dataset:** Luh & Blank (2024), RADAR4KIT v2, *result data*,
DOI [10.35097/1969](https://doi.org/10.35097/1969).
Trabaja sobre `../datos/consolidado_capacidad.csv` (una fila por celda y CU,
construido con `build_datos.py` desde las filas de check-up).
"""))
    cells.append(code(r"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path("..")
cons = pd.read_csv(REPO / "datos" / "consolidado_capacidad.csv")
print("forma:", cons.shape)
print("columnas:", list(cons.columns))
print(cons.head(3).to_string())
print()
print("celdas:", cons["cell_id"].nunique(),
      "| condiciones:", cons["condicion"].nunique(),
      "| CU max:", cons["cu"].max())
"""))
    cells.append(md(r"""
## 1. Cobertura: celdas, condiciones y check-ups

76 condiciones × 3 réplicas = 228 celdas. Cada celda tiene un número distinto
de check-ups: las que envejecen rápido llegan a menos CU.
"""))
    cells.append(code(r"""
por_celda = cons.groupby("cell_id").agg(
    cu_max=("cu", "max"), n_cu=("cu", "count"),
    soh_ini=("soh_nominal", "first"), soh_fin=("soh_nominal", "last"),
    cond=("condicion", "first"), tipo=("age_type", "first"),
    temp=("age_temp", "first"))
print(por_celda["n_cu"].describe().round(2).to_string())
print()
print("celdas con menos de 6 CU (no llegan a la historia minima del diseno):",
      (por_celda["n_cu"] < 6).sum())
print("celdas con menos de 8 CU (no llegan al corte C1):",
      (por_celda["n_cu"] < 8).sum())
print()
print(por_celda.nsmallest(8, "n_cu")[["cond", "tipo", "temp", "n_cu", "soh_fin"]].round(1).to_string())
"""))
    cells.append(code(r"""
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(por_celda["n_cu"], bins=range(0, 31), edgecolor="white")
ax.axvline(6, color="r", ls="--", label="historia minima (6 CU)")
ax.axvline(8, color="r", ls=":", label="corte C1 (8 CU)")
ax.set_xlabel("Check-ups por celda")
ax.set_ylabel("Celdas")
ax.set_title("Distribucion de CU por celda (228 celdas)")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
## 2. Verificación de la fuga a escala

El AED 01 mostró la fuga en dos celdas. Aquí se verifica en una muestra del
conjunto completo, siempre sobre filas de check-up.
"""))
    cells.append(code(r"""
import glob, random
random.seed(7)
files = sorted(glob.glob(str(REPO / "dataset" / "extraido" / "cell_eocv2" / "cell_eocv2_P0*.csv")))
muestra = random.sample(files, 24)
rows = []
for f in muestra:
    d = pd.read_csv(f, sep=";")
    cu = d[(d["cyc_condition"] == 2) & d["soh_cap"].notna()]
    rows.append(cu[["cap_aged_est_Ah", "soh_cap"]])
m = pd.concat(rows)
print("filas CU en la muestra:", len(m), "| celdas:", len(muestra))
print("correlacion soh_cap vs cap_aged_est_Ah:",
      round(m["soh_cap"].corr(m["cap_aged_est_Ah"]), 12))
a, b = np.polyfit(m["cap_aged_est_Ah"], m["soh_cap"], 1)
print("ajuste: soh_cap = %.4f * cap %+.4f" % (a, b))
err = ((m["cap_aged_est_Ah"] - 1.5) / 1.5 * 100 - m["soh_cap"]).abs().max()
print("desviacion maxima de (cap - 1.5)/1.5*100: %.2e" % err)
print("Conclusion: la fuga se confirma a escala. cap_aged_est_Ah queda fuera de las variables.")
"""))
    cells.append(code(r"""
fig, ax = plt.subplots(figsize=(6, 5))
ax.scatter(m["cap_aged_est_Ah"], m["soh_cap"], s=6, alpha=0.4)
xs = np.linspace(m["cap_aged_est_Ah"].min(), m["cap_aged_est_Ah"].max(), 10)
ax.plot(xs, (xs - 1.5) / 1.5 * 100, "r--", label="(cap - 1.5)/1.5 * 100")
ax.set_xlabel("cap_aged_est_Ah [Ah]")
ax.set_ylabel("soh_cap [%]")
ax.set_title("24 celdas, filas CU: una sola recta")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
## 3. SoH final y degradación

¿Cuánto bajó cada celda? ¿Cuántas cruzaron los umbrales del diseño
(80 % y 50 % nominales)?
"""))
    cells.append(code(r"""
fin = por_celda["soh_fin"]
print("SoH nominal final: media %.1f %%, mediana %.1f %%, min %.1f %%, max %.1f %%"
      % (fin.mean(), fin.median(), fin.min(), fin.max()))
print("celdas bajo 80%% nominal al final:", (fin < 80).sum(), "de", len(fin))
print("celdas bajo 50%% nominal al final:", (fin < 50).sum(), "de", len(fin))
print("celdas que nunca bajan de 80%%:", (fin >= 80).sum())
por_celda["caida_por_cu"] = (por_celda["soh_ini"] - por_celda["soh_fin"]) / por_celda["n_cu"]
print()
print("caida de SoH nominal por CU (puntos/CU):")
print(por_celda["caida_por_cu"].describe().round(3).to_string())
"""))
    cells.append(code(r"""
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(fin, bins=20, edgecolor="white")
axes[0].axvline(80, color="r", ls="--", label="80 %")
axes[0].axvline(50, color="r", ls=":", label="50 %")
axes[0].set_xlabel("SoH nominal final [%]")
axes[0].set_ylabel("Celdas")
axes[0].set_title("SoH final por celda")
axes[0].legend(); axes[0].grid(True, alpha=0.3)
axes[1].hist(por_celda["caida_por_cu"], bins=20, edgecolor="white")
axes[1].set_xlabel("Caida de SoH por CU [puntos/CU]")
axes[1].set_ylabel("Celdas")
axes[1].set_title("Velocidad de degradacion")
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
"""))
    cells.append(md(r"""
## 4. Degradación por condición

Tipo de envejecimiento (1 = calendario, 2 = cíclico, 3 = perfil de
conducción) y temperatura (0/10/25/40 °C). ¿Dónde se degrada más rápido?
"""))
    cells.append(code(r"""
g = por_celda.groupby("tipo").agg(celdas=("soh_fin", "size"),
                                  soh_fin_media=("soh_fin", "mean"),
                                  cu_media=("n_cu", "mean"),
                                  caida_media=("caida_por_cu", "mean"))
print("por tipo de envejecimiento:")
print(g.round(2).to_string())
print()
g2 = por_celda.groupby("temp").agg(celdas=("soh_fin", "size"),
                                   soh_fin_media=("soh_fin", "mean"),
                                   cu_media=("n_cu", "mean"),
                                   caida_media=("caida_por_cu", "mean"))
print("por temperatura:")
print(g2.round(2).to_string())
"""))
    cells.append(code(r"""
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
por_celda.boxplot(column="soh_fin", by="tipo", ax=axes[0])
axes[0].set_xlabel("Tipo (1=calendario, 2=ciclico, 3=perfil)")
axes[0].set_ylabel("SoH nominal final [%]")
axes[0].set_title("SoH final por tipo")
por_celda.boxplot(column="soh_fin", by="temp", ax=axes[1])
axes[1].set_xlabel("Temperatura [°C]")
axes[1].set_ylabel("SoH nominal final [%]")
axes[1].set_title("SoH final por temperatura")
plt.suptitle("")
plt.tight_layout()
plt.show()
"""))
    cells.append(code(r"""
cond_info = cons.groupby("condicion").first().reset_index()[
    ["condicion", "age_type", "age_temp", "age_soc",
     "age_chg_rate", "age_dischg_rate"]]
tabla = (por_celda.groupby("cond")
         .agg(celdas=("soh_fin", "size"),
              cu_media=("n_cu", "mean"),
              soh_fin_media=("soh_fin", "mean"))
         .reset_index().merge(cond_info, left_on="cond", right_on="condicion"))
print("76 condiciones (primeras 12):")
print(tabla.head(12).round(2).to_string(index=False))
print("...")
print("peor condicion (menor SoH final medio):")
print(tabla.nsmallest(3, "soh_fin_media").round(2).to_string(index=False))
print("mejor condicion (mayor SoH final medio):")
print(tabla.nlargest(3, "soh_fin_media").round(2).to_string(index=False))
"""))
    cells.append(md(r"""
## 5. Réplicas: ¿cuánto varía una celda de su gemela?

Cada condición tiene 3 réplicas (misma receta, celdas distintas). La
dispersión entre réplicas mide la variabilidad celda a celda que ningún
modelo basado solo en la condición puede explicar.
"""))
    cells.append(code(r"""
rep = por_celda.groupby("cond")["soh_fin"].agg(["mean", "std", "count"])
rep = rep.rename(columns={"mean": "soh_fin_media", "std": "soh_fin_std"})
print("desviacion tipica del SoH final dentro de la condicion (3 replicas):")
print(rep["soh_fin_std"].describe().round(2).to_string())
print()
print("condicion con mas dispersion entre replicas:")
print(rep.nlargest(3, "soh_fin_std").round(2).to_string())
print("condicion con menos dispersion:")
print(rep.nsmallest(3, "soh_fin_std").round(2).to_string())
"""))
    cells.append(code(r"""
cond_max = rep["soh_fin_std"].idxmax()
cond_min = rep["soh_fin_std"].idxmin()
fig, ax = plt.subplots(figsize=(8, 4))
for cond, ls in [(cond_max, "-"), (cond_min, "--")]:
    for cid, g in cons[cons["condicion"] == cond].groupby("cell_id"):
        ax.plot(g["cu"], g["soh_nominal"], ls, lw=1.5,
                label=f"{cid} (cond {cond})")
ax.set_xlabel("Check-up (CU)")
ax.set_ylabel("SoH nominal [%]")
ax.set_title("Trayectorias de las 3 replicas: mayor vs menor dispersion")
ax.legend(); ax.grid(True, alpha=0.3)
plt.show()
"""))
    cells.append(md(r"""
## 6. Cobertura de EIS y PLS

Los archivos de impedancia y pulso existen para las 228 celdas. La EIS de
esta version (v2) ya trae todas las condiciones (P001–P076); no hace falta
el archivo corregido del addendum.
"""))
    cells.append(code(r"""
import glob
eis_files = sorted(glob.glob(str(REPO / "dataset" / "extraido" / "cell_eisv2" / "*.csv")))
pls_files = sorted(glob.glob(str(REPO / "dataset" / "extraido" / "cell_plsv2" / "*.csv")))
print("archivos EIS:", len(eis_files), "| archivos PLS:", len(pls_files))
for f in [eis_files[1], eis_files[100], eis_files[200]]:
    d = pd.read_csv(f, sep=";")
    print(Path(f).name, "->", d.shape)
for f in [pls_files[1], pls_files[100], pls_files[200]]:
    d = pd.read_csv(f, sep=";")
    print(Path(f).name, "->", d.shape)
"""))
    cells.append(md(r"""
## 7. Implicaciones para el diseño experimental

El diseño (`diseno-experimental-proyecto2-bateria-litio.tex`) fija: unidad =
celda, partición por celda (GroupKFold) + por condición (Leave-Conditions-Out)
+ corte temporal, historia mínima de 6 CU y corte C1 en 8 CU. ¿Cuántas celdas
llegan? ¿En cuántas se observa el RUL?
"""))
    cells.append(code(r"""
print("celdas con >= 6 CU (historia minima):", (por_celda["n_cu"] >= 6).sum(), "de 228")
print("celdas con >= 8 CU (llegan al corte C1):", (por_celda["n_cu"] >= 8).sum(), "de 228")
cruza80 = cons[cons["soh_nominal"] < 80].groupby("cell_id")["cu"].min()
cruza50 = cons[cons["soh_nominal"] < 50].groupby("cell_id")["cu"].min()
print("celdas que cruzan 80%% nominal (RUL a 80%% observable):", len(cruza80))
print("celdas que cruzan 50%% nominal (RUL a 50%% observable):", len(cruza50))
print("CU mediano del cruce 80%%:", cruza80.median(), "| del cruce 50%%:", cruza50.median())
print()
print("celdas que NO cruzan 80%%: su RUL a 80%% es censurado (no observado):",
      228 - len(cruza80))
"""))
    cells.append(md(r"""
**Conclusiones del AED 02**
1. Cobertura completa: 228 celdas, 76 condiciones × 3 réplicas, 4006 filas CU.
2. La fuga se confirma a escala (24 celdas, correlación 1,0): `cap_aged_est_Ah`
   queda fuera de las variables en todo el proyecto.
3. El SoH final varía mucho: media 70,9 % nominal; 163 celdas bajo 80 % y 15
   bajo 50 % al final. La degradación depende de la condición (tipo y temperatura).
4. La dispersión entre réplicas de la misma condición es la variabilidad que
   ningún modelo basado solo en la condición puede explicar: es el piso de error.
5. No todas las celdas llegan al corte (8 CU) ni cruzan los umbrales: el RUL
   es parcialmente censurado y hay que reportar cobertura, como fija el diseño.
6. EIS y PLS cubren las 228 celdas: son la primera mejora del modelo.
"""))
    nb["cells"] = cells
    return nb


def main():
    AED.mkdir(parents=True, exist_ok=True)
    nb1 = build_nb1()
    p1 = AED / "01_baterias_individuales.ipynb"
    nbf.write(nb1, p1)
    print("escrito", p1)
    nb2 = build_nb2()
    p2 = AED / "02_conjunto_baterias.ipynb"
    nbf.write(nb2, p2)
    print("escrito", p2)
    for p in (p1, p2):
        r = subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
             "--execute", "--inplace", "--allow-errors",
             "--ExecutePreprocessor.kernel_name=baterias",
             "--ExecutePreprocessor.timeout=600", str(p)],
            cwd=AED, capture_output=True, text=True)
        print("ejecutado", p.name, "-> rc", r.returncode)
        if r.returncode != 0:
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
    for p in (p1, p2):
        print(p.name, f"{p.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
