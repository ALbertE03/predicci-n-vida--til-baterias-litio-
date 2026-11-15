import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent
EOC_DIR = REPO / "dataset" / "extraido" / "cell_eocv2"
CFG_DIR = REPO / "dataset" / "extraido" / "cfg"
OUT = REPO / "datos" / "consolidado_capacidad.csv"

CELL_RE = re.compile(r"cell_eocv2_P(\d+)_(\d+)_S(\d+)_C(\d+)\.csv")
CFG_RE = re.compile(r"cell_cfg_P(\d+)_(\d+)_S(\d+)_C(\d+)\.csv")

COND_COLS = ["age_type", "age_temp", "age_soc", "age_chg_rate",
             "age_dischg_rate", "age_profile"]


def leer_cfg():
    """Condicion de envejecimiento por celda, desde los cfg."""
    rows = []
    for f in sorted(CFG_DIR.glob("cell_cfg_P*.csv")):
        m = CFG_RE.match(f.name)
        if not m:
            continue
        p, rep, slave, slot = (int(x) for x in m.groups())
        df = pd.read_csv(f, sep=";")
        if len(df) == 0:
            continue
        r = df.iloc[0]
        rows.append({
            "condicion": p, "replica": rep, "slave": slave, "slot": slot,
            "cell_id": f"P{p:03d}_{rep}",
            **{c: r[c] for c in COND_COLS},
        })
    return pd.DataFrame(rows)


def consolidar():
    cfg = leer_cfg()
    print(f"cfg: {len(cfg)} celdas con condicion")
    out_rows, vacias, sin_cu = [], [], []
    n_una_fila = [0]
    for f in sorted(EOC_DIR.glob("cell_eocv2_P*.csv")):
        m = CELL_RE.match(f.name)
        if not m:
            continue
        p, rep, slave, slot = (int(x) for x in m.groups())
        df = pd.read_csv(f, sep=";")
        if len(df) == 0:
            vacias.append(f"P{p:03d}_{rep}")
            continue
        cu = df[(df["cyc_condition"] == 2) & df["soh_cap"].notna()].copy()
        if len(cu) == 0:
            sin_cu.append(f"P{p:03d}_{rep}")
            continue
        # Dos filas por CU: carga (cyc_charged=1) y descarga (=0).
        # Excepcion rara (8 de 4006 CU): falta una de las dos medidas.
        for j, g in cu.groupby("num_cycles_checkup"):
            chg = g[g["cyc_charged"] == 1]
            dis = g[g["cyc_charged"] == 0]
            q_chg = float(chg["cap_aged_est_Ah"].iloc[0]) if len(chg) else np.nan
            q_dis = float(dis["cap_aged_est_Ah"].iloc[0]) if len(dis) else np.nan
            s_chg = float(chg["soh_cap"].iloc[0]) if len(chg) else np.nan
            s_dis = float(dis["soh_cap"].iloc[0]) if len(dis) else np.nan
            q = float(np.nanmean([q_chg, q_dis]))
            soh = float(np.nanmean([s_chg, s_dis]))
            ref = dis.iloc[0] if len(dis) else chg.iloc[0]
            if len(g) == 1:
                n_una_fila[0] += 1
            out_rows.append({
                "cell_id": f"P{p:03d}_{rep}", "condicion": p, "replica": rep,
                "slave": slave, "slot": slot, "cu": int(j),
                "timestamp_s": float(ref["timestamp_s"]),
                "num_cycles_op": int(ref["num_cycles_op"]),
                "q_chg_Ah": q_chg,
                "q_dischg_Ah": q_dis,
                "q_Ah": q, "soh_cap": soh,
                "soh_nominal": q / 3.0 * 100.0,
            })
    cons = pd.DataFrame(out_rows)
    cons = cons.merge(cfg, on=["cell_id", "condicion", "replica", "slave", "slot"],
                      how="left", validate="many_to_one")
    cons = cons.sort_values(["condicion", "replica", "cu"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cons.to_csv(OUT, index=False)
    print(f"celdas vacias (P000, 0 filas): {len(vacias)} -> {vacias}")
    print(f"celdas sin filas CU: {sin_cu}")
    print(f"CU con una sola medida (carga o descarga): {n_una_fila[0]} de {len(cons)}")
    print(f"consolidado: {len(cons)} filas, {cons['cell_id'].nunique()} celdas, "
          f"{cons['condicion'].nunique()} condiciones")
    print(f"CU por celda: min {cons.groupby('cell_id')['cu'].max().min()}, "
          f"mediana {cons.groupby('cell_id')['cu'].max().median()}, "
          f"max {cons.groupby('cell_id')['cu'].max().max()}")
    print(f"guardado en {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
    return cons


if __name__ == "__main__":
    consolidar()
