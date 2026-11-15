# Datos consolidados

## `consolidado_capacidad.csv` (4006 filas, 468 KB)

Una fila por celda y check-up (CU), construida con `../build_datos.py`
desde las filas de check-up (`cyc_condition = 2`) de los archivos EOC v2.
228 celdas (P001_1–P076_3), 76 condiciones × 3 réplicas.

| Columna | Descripción |
|---|---|
| `cell_id` | Celda, p. ej. `P001_1` (condición 001, réplica 1) |
| `condicion`, `replica`, `slave`, `slot` | Identificación de la celda |
| `cu` | Índice de check-up (0 = primero) |
| `timestamp_s` | Tiempo Unix de la medida (fila de descarga) |
| `num_cycles_op` | Ciclos de operación acumulados hasta ese CU |
| `q_chg_Ah` | Capacidad estimada en la carga del CU (NaN si falta) |
| `q_dischg_Ah` | Capacidad estimada en la descarga del CU (NaN si falta) |
| `q_Ah` | Capacidad por CU = media de carga y descarga |
| `soh_cap` | SoH del dataset, en % (media de ambas medidas) |
| `soh_nominal` | SoH del diseño = `q_Ah / 3,0 × 100` |
| `age_type` | 1 = calendario, 2 = cíclico, 3 = perfil de conducción |
| `age_temp` | Temperatura de envejecimiento [°C] (0/10/25/40) |
| `age_soc` | SoC de envejecimiento [%] |
| `age_chg_rate`, `age_dischg_rate` | Tasas de carga/descarga [C] |
| `age_profile` | Perfil de conducción (0 si no aplica) |

## Decisiones (ver `aed/`)

- **Solo filas de check-up.** Las celdas cíclicas también traen estimaciones
  de capacidad en cada ciclo de operación, pero ahí el SoH usa otro piso
  (40 % en vez de 50 %); no son comparables con las medidas de CU.
- **`cap_aged_est_Ah` no está en este archivo: es fuga.** `soh_cap` es
  función exacta de la capacidad en Ah (correlación 1,0), así que incluirla
  como variable sería darle el objetivo al modelo. Ver AED 01 y 02.
- **Dos escalas de SoH.** `soh_cap` es un SoH reescalado con piso en el
  50 % de la nominal (`soh_cap = 0` ↔ Q = 1,5 Ah). El diseño usa
  `soh_nominal = Q / 3,0 × 100`; conversión: `soh_nominal = 50 + soh_cap / 2`.
- **8 de 4006 CU** tienen una sola medida (falta la carga o la descarga);
  ahí `q_Ah` es el valor disponible y el otro lado queda en NaN.
- **Las 12 celdas P000** traen archivos vacíos (0 filas) y no aparecen aquí.

## Fuente

Luh & Blank (2024), RADAR4KIT v2, *result data*,
DOI [10.35097/1969](https://doi.org/10.35097/1969), licencia CC BY 4.0.
Los archivos crudos se descargan con `../descarga_dataset.py` y **no** se
versionan (141 MB comprimidos, 872 MB descomprimidos).
