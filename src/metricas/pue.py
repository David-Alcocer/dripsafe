"""PUE inicial de DripSafe (#2 · Misa).

Módulo delgado sobre `src/metricas/impacto.py`: suma la energía y el agua de
TODOS los sitios de una partición y luego divide (cociente de sumas, nunca
promedio de PUE horarios ni por sitio).

- particion="entrenamiento" → referencia: la línea base normal del kit.
- particion="evaluacion"   → el "antes" real, con las anomalías tal como vienen.
  Es el mismo periodo sobre el que se calcula el exceso y el PUE proyectado.
"""

import numpy as np
import pandas as pd

from src import contrato
from src.metricas.impacto import pue_wue_por_sitio


def unidad_y_horas(telemetria: pd.DataFrame) -> tuple[str, float]:
    """Unidad de energía y horas por intervalo (el kit es horario: kWh por intervalo)."""
    primer_sitio = telemetria[telemetria["site_id"] == telemetria["site_id"].iloc[0]]
    horas = contrato.intervalo_horas(primer_sitio)
    return ("kwh_intervalo" if np.isclose(horas, 1.0) else "kw_promedio"), horas


def pue_inicial(telemetria: pd.DataFrame, particion: str) -> dict:
    """PUE, WUE y energías totales de una partición, con sus filas y horas de reloj."""
    unidad, horas = unidad_y_horas(telemetria)
    por_sitio = pue_wue_por_sitio(telemetria, particion=particion,
                                  unidad_energia=unidad, horas_por_intervalo=horas)
    it = float(por_sitio["energia_it_kwh"].sum())
    total = float(por_sitio["energia_total_kwh"].sum())
    agua = float(por_sitio["agua_in_situ_l"].sum())
    filas = telemetria["etiqueta_particion"] == particion
    return {
        "particion": particion,
        "pue": total / it,
        "wue": agua / it,
        "energia_it_kwh": it,
        "energia_total_kwh": total,
        "energia_no_ti_kwh": total - it,
        "agua_l": agua,
        "filas": int(filas.sum()),
        "horas_reloj": int(telemetria.loc[filas, "timestamp"].nunique()),
        "sitios": int(por_sitio["site_id"].nunique()),
    }
