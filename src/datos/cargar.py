"""Carga el kit real del hackatón al contrato v2 de DripSafe.

Lee el CSV crudo del kit (3 sitios × 168 h = 504 filas), renombra sus columnas
según config/columnas.json, deriva las etiquetas de evaluación y guarda un
CSV procesado que cumple src/contrato.py.

Uso:
    python -m src.datos.cargar \\
        --kit data/kit/operaciones_simuladas.csv \\
        --salida data/procesado/telemetria.csv
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from src import contrato

# El kit las trae para evaluar y declarar, pero no entran al dataset procesado
# (D14): el modelo nunca ve 'simulated_anomaly' y 'is_simulated' es informativo.
COLUMNAS_IGNORADAS = {"simulated_anomaly", "is_simulated"}

# El kit usa 'scenario' con 4 valores; el contrato distingue tipo y escenario.
# 'evento_ot' se preserva como tipo propio (ver TIPOS_VALIDOS en contrato.py).
MAPEO_TIPO = {
    "base": "normal",
    "ineficiencia": "falla",
    "fuga_agua": "falla",
    "evento_ot": "evento_ot",
}

MAPEO_PARTICION = {
    "referencia": "entrenamiento",
    "evaluacion": "evaluacion",
}


def cargar(ruta_kit: Path, mapeo: dict) -> pd.DataFrame:
    """Lee el kit crudo y lo transforma al contrato v2.

    `mapeo` es el contenido de config/columnas.json: {nombre_contrato: nombre_kit}.
    Regresa un DataFrame listo para `contrato.validar()`.
    """
    df = pd.read_csv(ruta_kit)

    # Invertimos el mapeo (kit → contrato) para rename, saltando metadatos y nulos.
    renombres = {
        kit: ctr
        for ctr, kit in mapeo.items()
        if kit is not None and not ctr.startswith("_")
    }
    df = df.rename(columns=renombres)

    # Derivar etiquetas desde las columnas originales del kit.
    if "scenario" in df.columns:
        df["etiqueta_escenario"] = df["scenario"].where(df["scenario"] != "base", "")
        df["etiqueta_tipo"] = df["scenario"].map(MAPEO_TIPO)
        df = df.drop(columns=["scenario"])

    if "split" in df.columns:
        df["etiqueta_particion"] = df["split"].map(MAPEO_PARTICION)
        df = df.drop(columns=["split"])

    df = df.drop(columns=[c for c in COLUMNAS_IGNORADAS if c in df.columns])

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    orden = ["site_id", "timestamp"] if "site_id" in df.columns else ["timestamp"]
    df = df.sort_values(orden).reset_index(drop=True)

    return df


def main():
    p = argparse.ArgumentParser(description="Carga el kit real al contrato v2.")
    p.add_argument("--kit", type=Path, required=True, help="CSV crudo del kit")
    p.add_argument(
        "--mapeo", type=Path, default=Path("config/columnas.json"),
        help="JSON con el mapeo nombre_contrato → nombre_kit",
    )
    p.add_argument(
        "--salida", type=Path, default=Path("data/procesado/telemetria.csv"),
        help="CSV procesado de salida (cumple src/contrato.py)",
    )
    a = p.parse_args()

    mapeo = json.loads(a.mapeo.read_text(encoding="utf-8"))
    df = cargar(a.kit, mapeo)

    problemas = contrato.validar(df)
    if problemas:
        print("El kit cargado NO cumple el contrato:")
        for p_ in problemas:
            print(f"  - {p_}")
        raise SystemExit(1)

    a.salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.salida, index=False)

    print(f"{len(df)} filas → {a.salida}")
    if "site_id" in df.columns:
        print(f"Sitios: {sorted(df['site_id'].unique())}")
    print(f"Periodo: {df['timestamp'].min()} → {df['timestamp'].max()}")


if __name__ == "__main__":
    main()
