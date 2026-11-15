# Predicción de la vida útil de las baterías de litio

Predicción del estado de salud (SoH) y de la vida útil restante (RUL) de
baterías de litio LG INR18650HG2 (NMC/C-SiO, 3000 mAh nominales), a partir
del dataset de envejecimiento de Luh & Blank (2024).

**Dataset:** *Comprehensive battery aging dataset: capacity and impedance fade
measurements of a lithium-ion NMC/C-SiO cell* [dataset – version 2: result
data], RADAR4KIT, DOI [10.35097/1969](https://doi.org/10.35097/1969).
228 celdas, 76 condiciones (16 de calendario, 48 cíclicas, 12 perfiles de
conducción), ~600 días. Licencia CC BY 4.0. Artículo:
[Luh & Blank, *Sci Data* 11, 1004 (2024)](https://doi.org/10.1038/s41597-024-03831-x).

**Baseline del proyecto:** doble exponencial $Q(k) = a e^{bk} + c e^{dk}$
(He *et al.*, 2011), ajustada por celda. El diseño experimental completo
(pregunta, partición por celda y por condición, corte temporal, métricas)
está en `diseno-experimental-proyecto2-bateria-litio.tex` (fuera de este repo).

## Estructura

```
.
├── README.md
├── descarga_dataset.py      # descarga los 10 archivos de RADAR4KIT y los descomprime
├── build_datos.py           # construye datos/consolidado_capacidad.csv
├── dataset/                 # datos crudos (NO versionados: ~141 MB zip, ~872 MB descomprimido)
│   ├── cell_eocv2.zip       # capacidad por check-up (93 MB)
│   ├── cell_eisv2.zip       # impedancia EIS (20 MB)
│   ├── cell_plsv2.zip       # resistencia de pulso (23 MB)
│   ├── cfg.zip              # condiciones por celda
│   └── ...                  # readme, estructura, plausibility check, WLTP
├── datos/
│   ├── consolidado_capacidad.csv   # 4006 filas: 1 por celda y check-up
│   └── README_datos.md
└── aed/
    ├── 01_baterias_individuales.ipynb   # AED por celda (ejecutado)
    ├── 02_conjunto_baterias.ipynb       # AED de las 228 celdas (ejecutado)
    └── 03_consolidado_nulos_y_variables.ipynb  # AED del consolidado (ejecutado)
```

## Cómo reproducirlo

```bash
python descarga_dataset.py   # descarga y descomprime en dataset/
python build_datos.py        # construye datos/consolidado_capacidad.csv
```

Requisitos: Python 3.10+, `pandas`, `numpy`, `matplotlib`, `jupyter`
(`pip install pandas numpy matplotlib jupyter`).

## Hallazgos del AED (ver `aed/`)

1. **Fuga de información (confirmada):** `soh_cap` es función exacta de
   `cap_aged_est_Ah` (correlación 1,0). En filas de check-up,
   `soh_cap = (cap − 1,5) / 1,5 × 100`. **Se elimina la capacidad en Ah
   de las variables**; el objetivo es el SoH.
2. **Dos escalas de SoH:** `soh_cap` es un SoH reescalado con piso en el
   50 % de la nominal (0 % ↔ 1,5 Ah). El SoH del diseño es
   `SoH_nominal = Q / 3,0 × 100`; conversión: `SoH_nominal = 50 + soh_cap / 2`
   (80 % nominal ↔ `soh_cap` 60; 50 % nominal ↔ `soh_cap` 0).
3. **Dos pisos:** 50 % en check-ups, 40 % en filas de ciclado. El modelo
   usa solo check-ups (`cyc_condition = 2`), medidas comparables.
4. **Dos medidas por CU** (carga y descarga, diferencia ~0,6 %): un valor
   por CU = media de ambas. 8 de 4006 CU tienen una sola medida.
5. **Cobertura:** 228 celdas; 48 con menos de 6 CU y 64 con menos de 8 CU;
   166 cruzan el 80 % nominal (RUL observable) y 15 el 50 %; 62 nunca
   cruzan el 80 % (RUL censurado).
6. **P000:** 12 archivos vacíos (0 filas), excluidos.
7. **EIS y PLS** cubren las 228 celdas (la EIS v2 aquí ya trae todas las
   condiciones): son la primera mejora del modelo.
8. **Calidad del consolidado (AED 03):** nulos solo en `q_chg_Ah` (1) y
   `q_dischg_Ah` (7), las 8 CU con una sola medida; 0 duplicados; CU
   consecutivos sin huecos; `soh_cap` negativo en 16 filas de 15 celdas
   (Q por debajo de 1,5 Ah, no un error); 64 celdas con pequeños aumentos
   de Q entre CU (mediana 0,017 Ah: ruido, no regeneración); tiempo y
   ciclos de operación monótonos en las 228 celdas.

## Cita del dataset

> Luh, M. & Blank, T. (2024). *Comprehensive battery aging dataset:
> capacity and impedance fade measurements of a lithium-ion NMC/C-SiO cell
> [dataset – version 2: result data]*. RADAR4KIT.
> https://doi.org/10.35097/1969
