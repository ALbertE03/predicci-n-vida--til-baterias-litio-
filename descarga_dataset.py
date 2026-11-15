"""Descarga el dataset RADAR4KIT v2 (result data, DOI 10.35097/1969).

Descarga los 10 archivos utiles (141 MB en total) y descomprime los zips
en dataset/extraido/. No descarga result_plot_examples.7z (192 MB de
ejemplos de graficos, no hace falta para el analisis).

El servidor limita la velocidad (HTTP 429) si se descarga muy rapido:
entre archivos espera 20 s, y ante un 429 espera 120 s y reintenta
(hasta 3 veces por archivo).

Uso:  python descarga_dataset.py
"""
import time
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "dataset"
OUT.mkdir(exist_ok=True)

# (nombre local, URL directa de RADAR4KIT)
ARCHIVOS = [
    ("plausibility-check-v05.3.xlsx",
     "https://radar.kit.edu/radar/en/file/37nz6hpz9qqrv901.Battery%2BAging%2BData%2BPlausibility%2BCheck%2Bv05.3%2B%2528colored%2529.xlsx"),
    ("cell_eisv2.zip",
     "https://radar.kit.edu/radar/en/file/tz7dk0ag5pcdgm45.cell_eisv2.zip"),
    ("cell_eocv2.zip",
     "https://radar.kit.edu/radar/en/file/15a3gtgdzdeffbr8.cell_eocv2.zip"),
    ("cell_plsv2.zip",
     "https://radar.kit.edu/radar/en/file/juxdw51w2ec8gedg.cell_plsv2.zip"),
    ("cfg.zip",
     "https://radar.kit.edu/radar/en/file/w049egbgr21pfcm2.cfg.zip"),
    ("cell-overview.pdf",
     "https://radar.kit.edu/radar/en/file/9n4j4q7grn6c0xqe.Cycling%2BExperiment%2BCell%2BOverview%2B%25282024-09-26%2B15-31%2529.pdf"),
    ("cell-overview.xlsx",
     "https://radar.kit.edu/radar/en/file/vq05j4x6e9g9bznf.Cycling%2BExperiment%2BCell%2BOverview%2B%25282024-09-26%2B15-31%2529.xlsx"),
    ("data-structure-v05.3.xlsx",
     "https://radar.kit.edu/radar/en/file/8m5bgr4w4mzz8q0z.Data%2BStructure%2Bv05.3.xlsx"),
    ("readme-v2.pdf",
     "https://radar.kit.edu/radar/en/file/5t6d2ewd5gx4r0qk.Readme%2Bv2.pdf"),
    ("wltp-class-3b.xlsx",
     "https://radar.kit.edu/radar/en/file/8w6a0g6v1q0a1nmk.WLTP_Class_3b_cycle_power_profile.xlsx"),
]

# Tamanos esperados (bytes) segun la pagina de RADAR4KIT.
ESPERADO = {
    "plausibility-check-v05.3.xlsx": 2361523,
    "cell_eisv2.zip": 19894633,
    "cell_eocv2.zip": 93167507,
    "cell_plsv2.zip": 22972041,
    "cfg.zip": 97252,
    "cell-overview.pdf": 401249,
    "cell-overview.xlsx": 74470,
    "data-structure-v05.3.xlsx": 186499,
    "readme-v2.pdf": 1226669,
    "wltp-class-3b.xlsx": 492237,
}


def descargar(nombre, url):
    dest = OUT / nombre
    if dest.exists() and dest.stat().st_size == ESPERADO[nombre]:
        print(f"{nombre}: ya descargado ({dest.stat().st_size} bytes), se salta")
        return dest
    for intento in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while True:
                    bloque = r.read(1 << 20)
                    if not bloque:
                        break
                    f.write(bloque)
            print(f"{nombre}: {dest.stat().st_size} bytes "
                  f"(esperado {ESPERADO[nombre]})")
            return dest
        except urllib.error.HTTPError as e:
            print(f"{nombre}: intento {intento} -> HTTP {e.code}, esperando 120 s...")
            time.sleep(120)
    raise RuntimeError(f"no se pudo descargar {nombre}")


def main():
    for i, (nombre, url) in enumerate(ARCHIVOS):
        descargar(nombre, url)
        if i < len(ARCHIVOS) - 1:
            time.sleep(20)  # no saturar el servidor
    extraido = OUT / "extraido"
    for nombre, _ in ARCHIVOS:
        if nombre.endswith(".zip"):
            with zipfile.ZipFile(OUT / nombre) as z:
                z.extractall(extraido / nombre[:-4])
            print(f"{nombre}: descomprimido en extraido/{nombre[:-4]}")
    print("listo.")


if __name__ == "__main__":
    main()
