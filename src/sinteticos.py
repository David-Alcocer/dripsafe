"""Datos sintéticos con el formato del contrato (src/contrato.py).

Sirven para que cada quien avance HOY sin esperar a que el kit esté limpio,
y para las pruebas automáticas (el kit nunca entra al repo ni a GitHub).
No son datos reales: los números imitan un centro de datos de ~1 MW en
Mérida con chiller, bombas y torre de enfriamiento.

Uso:
    python -m src.sinteticos --dias 14 --salida data/sinteticos/telemetria.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CP_AGUA = 4.186          # kJ/(kg·°C): calor específico del agua
LITROS_POR_KWH_CALOR = 3600 / 2260   # agua evaporada por kWh de calor (calor latente 2260 kJ/kg)
CICLOS_CONCENTRACION = 4  # la torre purga 1/(ciclos-1) de lo que evapora


def generar(dias: int = 14, minutos: int = 5, semilla: int = 42, kw_ti_base: float = 1000.0) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    n = dias * 24 * 60 // minutos
    ts = pd.date_range("2026-10-01", periods=n, freq=f"{minutos}min")
    hora = ts.hour + ts.minute / 60
    h = minutos / 60

    # Carga de TI: casi plana, con un pico suave por la tarde.
    kw_ti = kw_ti_base * (0.85 + 0.08 * np.sin(2 * np.pi * (hora - 9) / 24)) + rng.normal(0, 8, n)
    # Clima de Mérida en octubre: ~23 °C de madrugada, ~32 °C a las 15 h.
    t_exterior = 27.5 + 4.5 * np.sin(2 * np.pi * (hora - 9) / 24) + rng.normal(0, 0.4, n)

    setpoint = np.full(n, 7.0)
    t_suministro = setpoint + rng.normal(0, 0.08, n)
    flujo_m3h = 160 + rng.normal(0, 1.5, n)
    caudal_kg_s = flujo_m3h * 1000 / 3600
    delta_t = kw_ti / (caudal_kg_s * CP_AGUA)          # todo el calor de TI pasa al agua
    t_retorno = t_suministro + delta_t + rng.normal(0, 0.05, n)

    # El chiller rinde peor con calor exterior y con agua más fría (COP más bajo).
    cop = 6.0 - 0.12 * (t_exterior - 25) + 0.15 * (setpoint - 7)
    kw_chiller = kw_ti / cop + rng.normal(0, 2, n)
    kw_bombas = 35 + rng.normal(0, 0.5, n)
    kw_torre = np.clip(20 + 1.5 * (t_exterior - 25), 8, None) + rng.normal(0, 0.5, n)
    kw_otros = 0.08 * kw_ti                            # iluminación, pérdidas de UPS, etc.
    kw_total = kw_ti + kw_chiller + kw_bombas + kw_torre + kw_otros

    calor_rechazado_kwh = (kw_ti + kw_chiller) * h
    evaporada = calor_rechazado_kwh * LITROS_POR_KWH_CALOR
    agua_reposicion_l = evaporada * CICLOS_CONCENTRACION / (CICLOS_CONCENTRACION - 1)

    return pd.DataFrame({
        "timestamp": ts,
        "kw_ti": kw_ti.round(2),
        "kw_total": kw_total.round(2),
        "kw_chiller": kw_chiller.round(2),
        "kw_bombas": kw_bombas.round(2),
        "kw_torre": kw_torre.round(2),
        "t_exterior": t_exterior.round(2),
        "t_suministro": t_suministro.round(2),
        "t_retorno": t_retorno.round(2),
        "setpoint_suministro": setpoint,
        "flujo_m3h": flujo_m3h.round(2),
        "agua_reposicion_l": agua_reposicion_l.round(1),
        "bomba_encendida": 1,
    })


def main():
    p = argparse.ArgumentParser(description="Genera telemetría sintética con el formato del contrato.")
    p.add_argument("--dias", type=int, default=14)
    p.add_argument("--minutos", type=int, default=5, help="minutos entre filas")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--salida", default="data/sinteticos/telemetria.csv")
    a = p.parse_args()
    df = generar(a.dias, a.minutos, a.semilla)
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.salida, index=False)
    pue = df["kw_total"].sum() / df["kw_ti"].sum()
    print(f"{len(df)} filas → {a.salida} (PUE sintético {pue:.2f})")


if __name__ == "__main__":
    main()
