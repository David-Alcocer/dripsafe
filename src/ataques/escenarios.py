"""Catálogo de ataques y fallas simulados sobre la telemetría.

Cada escenario modifica las filas de UNA ventana de tiempo para dejar la huella
que dejaría el ataque o la falla real. Nada de esto toca sistemas reales: solo
cambia números en un DataFrame (regla 18 de la convocatoria).

Las técnicas vienen de MITRE ATT&CK for ICS: https://attack.mitre.org/matrices/ics/

Para agregar un escenario: escribe una función `_mi_escenario(df, idx, ctx)` y
agrégala a CATALOGO con su ficha. `idx` son las etiquetas de fila de la ventana;
`ctx` trae el generador aleatorio (`ctx.rng`) y la duración del intervalo en
horas (`ctx.horas`).
"""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from src.sinteticos import CICLOS_CONCENTRACION, LITROS_POR_KWH_CALOR

# Un chiller gasta ~3 % más por cada °C que se baja el agua helada.
PENALIZACION_CHILLER_POR_GRADO = 0.03
LITROS_POR_KWH_EXTRA = LITROS_POR_KWH_CALOR * CICLOS_CONCENTRACION / (CICLOS_CONCENTRACION - 1)


@dataclass
class Contexto:
    rng: np.random.Generator
    horas: float               # duración de un intervalo, en horas
    original: pd.DataFrame     # telemetría antes de cualquier escenario


@dataclass
class Escenario:
    nombre: str
    tipo: str                 # "ataque" o "falla"
    tecnica: str              # ID(s) de ATT&CK for ICS separados por ";" o "" si es falla
    nombre_tecnica: str
    descripcion: str          # qué pasa en la planta
    huella: str               # qué debería ver el detector
    requiere: list[str]       # columnas del contrato que necesita
    horas: float              # duración de la ventana
    aplicar: Callable[[pd.DataFrame, pd.Index, Contexto], None]
    hora_inicio: Optional[int] = None  # si el ataque tiene más sentido a cierta hora


# ---------------------------------------------------------------- utilidades

def _rampa(n: int, fraccion_subida: float = 0.2) -> np.ndarray:
    """0 → 1 durante la primera parte de la ventana y luego se queda en 1."""
    subida = max(1, int(n * fraccion_subida))
    return np.minimum(np.arange(1, n + 1) / subida, 1.0)


def _sumar_potencia(df, idx, columna, delta_kw, ctx, agua=True):
    """Suma kW a un equipo y al total; si es calor extra, también sube el agua de la torre."""
    df.loc[idx, columna] += delta_kw
    df.loc[idx, "kw_total"] += delta_kw
    if agua and "agua_reposicion_l" in df.columns:
        df.loc[idx, "agua_reposicion_l"] += delta_kw * ctx.horas * LITROS_POR_KWH_EXTRA


# ------------------------------------------------------------------- ataques

def _setpoint_alterado(df, idx, ctx):
    # El atacante baja la temperatura objetivo 3 °C, poco a poco para no llamar la atención.
    delta = -3.0 * _rampa(len(idx))
    for col in ["setpoint_suministro", "t_suministro", "t_retorno"]:
        if col in df.columns:
            df.loc[idx, col] += delta
    extra = df.loc[idx, "kw_chiller"].to_numpy() * PENALIZACION_CHILLER_POR_GRADO * np.abs(delta)
    _sumar_potencia(df, idx, "kw_chiller", extra, ctx)


def _sensor_falsificado(df, idx, ctx):
    # El sensor de retorno reporta 0.8 °C menos de lo real: valores creíbles uno por uno,
    # pero el calor que «saca» el agua ya no alcanza para el calor de los servidores.
    df.loc[idx, "t_retorno"] -= 0.8 + ctx.rng.normal(0, 0.03, len(idx))


def _vista_repetida(df, idx, ctx):
    # El atacante baja la bomba al 65 % (controla el proceso) y repite en pantalla las
    # lecturas de ayer a la misma hora (el operador ve todo normal). El medidor de
    # energía es otro sistema y sí registra que la bomba gasta mucho menos.
    filas_por_dia = int(round(24 / ctx.horas))
    pos = df.index.get_indexer(idx)
    origen = df.index[np.clip(pos - filas_por_dia, 0, None)]
    for col in ["flujo_m3h", "t_retorno", "t_suministro"]:
        if col in df.columns:
            df.loc[idx, col] = ctx.original.loc[origen, col].to_numpy()
    real = df.loc[idx, "kw_bombas"].to_numpy()
    _sumar_potencia(df, idx, "kw_bombas", real * (0.65 ** 3) - real, ctx, agua=False)


def _comandos_no_autorizados(df, idx, ctx):
    # Órdenes de apagar y prender la bomba cada 10 minutos, de madrugada.
    apagada = (np.arange(len(idx)) // 2) % 2 == 0
    filas = idx[apagada]
    real = df.loc[filas, "kw_bombas"].to_numpy()
    _sumar_potencia(df, filas, "kw_bombas", 0.5 - real, ctx, agua=False)
    if "flujo_m3h" in df.columns:
        df.loc[filas, "flujo_m3h"] = ctx.rng.uniform(0, 3, len(filas))
    if "bomba_encendida" in df.columns:
        df.loc[filas, "bomba_encendida"] = 0
    if "t_retorno" in df.columns:
        df.loc[filas, "t_retorno"] += 1.5


def _denegacion_de_vista(df, idx, ctx):
    # La telemetría de la planta deja de llegar; los medidores de energía siguen.
    for col in ["t_suministro", "t_retorno", "setpoint_suministro", "flujo_m3h"]:
        if col in df.columns:
            df.loc[idx, col] = np.nan


# -------------------------------------------------------------------- fallas

def _ensuciamiento(df, idx, ctx):
    # El intercambiador se ensucia: el chiller gasta hasta 12 % más, poco a poco.
    factor = 0.12 * np.linspace(0, 1, len(idx))
    extra = df.loc[idx, "kw_chiller"].to_numpy() * factor
    _sumar_potencia(df, idx, "kw_chiller", extra, ctx)


def _sensor_atorado(df, idx, ctx):
    # El sensor se congela en su último valor: varianza cero, típico de una falla.
    df.loc[idx, "t_retorno"] = df.loc[idx[0], "t_retorno"]


def _fuga_reposicion(df, idx, ctx):
    # Fuga o rebose en la torre: entra 35 % más agua sin que cambie el calor.
    df.loc[idx, "agua_reposicion_l"] *= 1.35


CATALOGO = [
    Escenario(
        "setpoint_alterado", "ataque", "T0836", "Modify Parameter",
        "Alguien baja la temperatura objetivo del agua helada sin una razón operativa.",
        "El setpoint cambia y el chiller gasta más con la misma carga de TI.",
        ["setpoint_suministro", "kw_chiller"], horas=18, aplicar=_setpoint_alterado),
    Escenario(
        "sensor_falsificado", "ataque", "T0856", "Spoof Reporting Message",
        "El sensor de temperatura de retorno reporta valores inventados, pero creíbles.",
        "El balance de calor no cuadra: caudal × ΔT queda por debajo del calor de los servidores.",
        ["t_retorno"], horas=12, aplicar=_sensor_falsificado),
    Escenario(
        "vista_repetida", "ataque", "T0832;T0831", "Manipulation of View + Manipulation of Control",
        "El atacante baja la bomba y repite en pantalla las lecturas de ayer.",
        "La bomba gasta ~70 % menos pero el caudal reportado es normal (ley de afinidad rota).",
        ["flujo_m3h", "kw_bombas"], horas=6, aplicar=_vista_repetida),
    Escenario(
        "comandos_no_autorizados", "ataque", "T0855", "Unauthorized Command Message",
        "Llegan órdenes de apagar y prender la bomba de madrugada.",
        "Arranques y paros que no corresponden con la carga ni el horario.",
        ["kw_bombas"], horas=1, aplicar=_comandos_no_autorizados, hora_inicio=3),
    Escenario(
        "denegacion_de_vista", "ataque", "T0815", "Denial of View",
        "La telemetría de temperatura y caudal deja de llegar al operador.",
        "Huecos (datos faltantes) en sensores mientras los medidores de energía siguen reportando.",
        ["t_retorno"], horas=2, aplicar=_denegacion_de_vista),
    Escenario(
        "ensuciamiento", "falla", "", "",
        "El intercambiador de calor se ensucia con el uso.",
        "El chiller gasta cada vez más con la misma carga; cambio gradual y coherente.",
        ["kw_chiller"], horas=48, aplicar=_ensuciamiento),
    Escenario(
        "sensor_atorado", "falla", "", "",
        "El sensor de retorno se descompone y repite siempre el mismo valor.",
        "Valor constante (varianza cero) mientras todo lo demás varía.",
        ["t_retorno"], horas=12, aplicar=_sensor_atorado),
    Escenario(
        "fuga_reposicion", "falla", "", "",
        "Fuga o rebose en la torre de enfriamiento.",
        "Más agua de reposición sin más calor que disipar (el WUE sube).",
        ["agua_reposicion_l"], horas=24, aplicar=_fuga_reposicion),
]

POR_NOMBRE = {e.nombre: e for e in CATALOGO}
