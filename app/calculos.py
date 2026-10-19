"""Cálculos que el dashboard hace sobre los contratos. Sin Streamlit, para poder probarlos."""

import numpy as np
import pandas as pd

from src.sinteticos import CP_AGUA

COLUMNAS_ENFRIAMIENTO = ["kw_chiller", "kw_bombas", "kw_torre"]


def agregar_derivadas(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas que ayudan a explicar las alertas (no cambian los contratos)."""
    df = df.copy()
    presentes = [c for c in COLUMNAS_ENFRIAMIENTO if c in df.columns]
    if presentes:
        df["kw_enfriamiento"] = df[presentes].sum(axis=1)
    if {"flujo_m3h", "t_retorno", "t_suministro"} <= set(df.columns):
        # Calor que se lleva el agua: caudal (kg/s) × calor específico × ΔT.
        df["calor_agua_kw"] = df["flujo_m3h"] * 1000 / 3600 * CP_AGUA * (df["t_retorno"] - df["t_suministro"])
    return df


def pue_por_hora(df: pd.DataFrame) -> pd.Series:
    """PUE de cada hora: energía total entre energía de TI."""
    g = df.set_index("timestamp")[["kw_total", "kw_ti"]].resample("1h").sum()
    return (g["kw_total"] / g["kw_ti"]).rename("pue")


def por_hora(df: pd.DataFrame, columna: str, como: str = "mean") -> pd.Series:
    """Una columna agregada por hora: 'mean' para potencias y temperaturas, 'sum' para litros."""
    return df.set_index("timestamp")[columna].resample("1h").agg(como)


def periodo(df: pd.DataFrame, solo_evaluacion: bool) -> pd.DataFrame:
    """Filas de la semana de evaluación (donde están los escenarios) o todas."""
    if solo_evaluacion and "etiqueta_particion" in df.columns:
        return df[df["etiqueta_particion"] == "evaluacion"]
    return df


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha(ts, con_hora: bool = True) -> str:
    """Timestamp → '14 oct 23:55' (o '14 oct' sin hora)."""
    ts = pd.Timestamp(ts)
    texto = f"{ts.day:02d} {MESES[ts.month - 1]}"
    return f"{texto} {ts:%H:%M}" if con_hora else texto


def duracion(horas: float) -> str:
    return f"{horas * 60:.0f} min" if horas < 1 else f"{horas:.1f} h"


def eventos(df: pd.DataFrame, hueco_max: int = 3) -> pd.DataFrame:
    """Junta las filas con anomalía en eventos (tramos seguidos).

    Dos tramos separados por `hueco_max` filas normales o menos cuentan como el mismo evento.
    """
    columnas = ["inicio", "fin", "horas", "tipo_sugerido", "variable_principal", "escenario", "score_min"]
    pos = np.flatnonzero(df["anomalia"].to_numpy())
    if len(pos) == 0:
        return pd.DataFrame(columns=columnas)

    cortes = np.flatnonzero(np.diff(pos) > hueco_max + 1) + 1
    filas = []
    for grupo in np.split(pos, cortes):
        v = df.iloc[grupo]
        inicio, fin = v["timestamp"].iloc[0], v["timestamp"].iloc[-1]
        filas.append({
            "inicio": inicio,
            "fin": fin,
            "horas": round((fin - inicio).total_seconds() / 3600, 2),
            "tipo_sugerido": v["tipo_sugerido"].mode().iloc[0],
            "variable_principal": _moda(v, "variable_principal"),
            "escenario": _moda(v, "etiqueta_escenario"),
            "score_min": v["score"].min(),
        })
    return pd.DataFrame(filas, columns=columnas)


def _moda(v: pd.DataFrame, columna: str) -> str:
    if columna not in v.columns:
        return ""
    valores = v[columna].fillna("").astype(str)
    valores = valores[valores != ""]
    return valores.mode().iloc[0] if len(valores) else ""


def ventana(df: pd.DataFrame, inicio, fin, margen_horas: float = 6) -> pd.DataFrame:
    """Filas entre `inicio` y `fin`, con un margen antes y después para ver el contraste."""
    margen = pd.Timedelta(hours=margen_horas)
    t = df["timestamp"]
    return df[(t >= pd.Timestamp(inicio) - margen) & (t <= pd.Timestamp(fin) + margen)]
