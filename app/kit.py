"""Lectura del kit oficial de CIFOX (operaciones_simuladas.csv) desde FUERA del repo.

El kit es confidencial: nunca se copia a esta carpeta ni se sube a GitHub. El dashboard lo
lee de su ubicación en la laptop. Por defecto busca en:

    ~/hackathon/Kit Stack Tecnológico/Para participantes/Código y recursos/

Para otra ubicación, definir la variable de entorno DRIPSAFE_KIT con la carpeta del kit
(la que contiene data/ y docs/). Si no se encuentra, se usa `ejemplo()`: datos inventados
con el mismo formato, para las pruebas y el CI.

Las reglas de `reglas()` son las mismas reglas didácticas de common/cifox.py del kit
(licencia MIT): PUE > 1.6, agua > 1.5 L/kWh IT, entrada > 29 °C o evento OT.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

CARPETA_POR_DEFECTO = Path.home() / "hackathon" / "Kit Stack Tecnológico" / "Para participantes" / "Código y recursos"
SITIOS = {"SIM-A": "aire", "SIM-B": "evaporativa", "SIM-C": "liquida"}
NUMERICAS = ["energy_it_kwh", "energy_total_kwh", "water_l", "load_pct", "outdoor_temp_c", "inlet_temp_c"]
COLUMNAS = ["timestamp", "site_id", "cooling_type", *NUMERICAS, "ot_event", "scenario", "simulated_anomaly", "split"]

# Umbrales de las reglas del kit (didácticos, no operativos).
UMBRAL_PUE = 1.6
UMBRAL_WUE = 1.5
UMBRAL_ENTRADA = 29.0


def carpeta() -> Path:
    return Path(os.environ.get("DRIPSAFE_KIT", CARPETA_POR_DEFECTO)).expanduser()


def ruta_csv() -> Path:
    return carpeta() / "data" / "operaciones_simuladas.csv"


def disponible() -> bool:
    return ruta_csv().exists()


def leer(ruta: Path | None = None) -> pd.DataFrame:
    """Lee el CSV del kit y revisa lo básico (columnas, energía positiva, sin duplicados)."""
    df = pd.read_csv(ruta or ruta_csv())
    faltan = set(COLUMNAS) - set(df.columns)
    if faltan:
        raise ValueError(f"Al CSV del kit le faltan columnas: {sorted(faltan)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if (df["energy_it_kwh"] <= 0).any() or (df["energy_total_kwh"] < df["energy_it_kwh"]).any():
        raise ValueError("Energía IT debe ser positiva y la total mayor o igual que la IT")
    if df.duplicated(["timestamp", "site_id"]).any():
        raise ValueError("Hay un sitio con dos filas en la misma hora")
    return df[COLUMNAS].sort_values(["site_id", "timestamp"]).reset_index(drop=True)


def benchmarks() -> dict:
    """Corridas de ejemplo del kit (reglas e Isolation Forest): tiempo, memoria y aciertos."""
    salida = {}
    for metodo, archivo in [("reglas", "benchmark_rules_example.json"), ("isolation_forest", "benchmark_if_example.json")]:
        ruta = carpeta() / "docs" / archivo
        if ruta.exists():
            salida[metodo] = json.loads(ruta.read_text(encoding="utf-8"))
    return salida


def reglas(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega pue, wue, alerta, motivo y tipo_sugerido a cada fila (reglas del kit)."""
    out = df.copy()
    out["pue"] = out["energy_total_kwh"] / out["energy_it_kwh"]
    out["wue"] = out["water_l"] / out["energy_it_kwh"]
    condiciones = [
        (out["pue"] > UMBRAL_PUE, f"PUE > {UMBRAL_PUE}"),
        (out["wue"] > UMBRAL_WUE, f"agua > {UMBRAL_WUE} L/kWh IT"),
        (out["inlet_temp_c"] > UMBRAL_ENTRADA, f"entrada > {UMBRAL_ENTRADA:.0f} °C"),
        (out["ot_event"] != "normal", "evento OT"),
    ]
    # Para cada fila, junta los textos de las reglas que se cumplen: «PUE > 1.6; entrada > 29 °C».
    out["motivo"] = ["; ".join(texto for mascara, texto in condiciones if mascara.iloc[i]) for i in range(len(out))]
    out["alerta"] = out["motivo"] != ""
    # Un evento OT se trata como posible ataque; lo demás, como ineficiencia.
    out["tipo_sugerido"] = np.where(out["ot_event"] != "normal", "posible_ataque",
                                    np.where(out["alerta"], "ineficiencia", "normal"))
    return out


def ejemplo(semilla: int = 7) -> pd.DataFrame:
    """Datos INVENTADOS con el formato del kit (3 sitios × 168 h), para pruebas y CI.

    No son los datos del kit: solo imitan sus columnas y sus tres tipos de anomalía.
    """
    rng = np.random.default_rng(semilla)
    horas = pd.date_range("2026-10-12", periods=168, freq="h", tz="UTC")
    filas = []
    for i, (sitio, enfriamiento) in enumerate(SITIOS.items()):
        hora = horas.hour.to_numpy()
        carga = 55 + 15 * np.sin(2 * np.pi * (hora - 9) / 24) + rng.normal(0, 2, len(horas))
        it = 2.9 * carga + rng.normal(0, 3, len(horas))
        pue = [1.38, 1.24, 1.20][i] + rng.normal(0, 0.02, len(horas))
        wue = [0.03, 0.90, 0.21][i] * (1 + rng.normal(0, 0.03, len(horas)))
        df = pd.DataFrame({
            "timestamp": horas, "site_id": sitio, "cooling_type": enfriamiento,
            "energy_it_kwh": it, "energy_total_kwh": it * pue, "water_l": np.clip(it * wue, 0, None),
            "load_pct": carga, "outdoor_temp_c": 23 + 5 * np.sin(2 * np.pi * (hora - 9) / 24),
            "inlet_temp_c": 23.5 + rng.normal(0, 0.3, len(horas)), "ot_event": "normal",
            "scenario": "base", "simulated_anomaly": 0,
            "split": np.where(np.arange(len(horas)) < 72, "referencia", "evaluacion"),
        })
        ventana = slice(90 + 20 * i, 98 + 20 * i)
        idx = df.index[ventana]
        if sitio == "SIM-A":
            df.loc[idx, "energy_total_kwh"] = df.loc[idx, "energy_it_kwh"] * 1.7
            df.loc[idx, "inlet_temp_c"] = 29.5
            df.loc[idx, "scenario"] = "ineficiencia"
        elif sitio == "SIM-B":
            df.loc[idx, "water_l"] = df.loc[idx, "energy_it_kwh"] * 1.8
            df.loc[idx, "scenario"] = "fuga_agua"
        else:
            idx = idx[:5]
            df.loc[idx, "ot_event"] = ["login_fallido"] * 3 + ["cambio_config_no_autorizado"] * 2
            df.loc[idx, "scenario"] = "evento_ot"
        df.loc[idx, "simulated_anomaly"] = 1
        filas.append(df)
    return pd.concat(filas, ignore_index=True)[COLUMNAS]
