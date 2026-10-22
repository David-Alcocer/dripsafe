"""Balance ilustrativo de una torre evaporativa, independiente del kit.

Supone régimen estacionario, ciclos de concentración constantes y pérdidas
por arrastre, fugas y rebose despreciables. No estima purga de una fuga.
"""

from __future__ import annotations

import math


def balance_torre(evaporacion_l: float, ciclos: float) -> dict[str, float]:
    """Devuelve evaporación, purga y reposición en litros para un periodo común.

    Con M = E + B y ciclos = M / B, B = E / (ciclos - 1).
    Los datos son supuestos del escenario; no proceden de `water_l`.
    """
    for nombre, valor in (("evaporacion_l", evaporacion_l), ("ciclos", ciclos)):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
            raise ValueError(f"{nombre} debe ser un número finito")
    if evaporacion_l < 0:
        raise ValueError("evaporacion_l no puede ser negativa")
    if ciclos <= 1:
        raise ValueError("ciclos debe ser mayor que 1")

    purga = evaporacion_l / (ciclos - 1)
    return {"evaporacion_l": float(evaporacion_l), "purga_l": purga,
            "reposicion_l": evaporacion_l + purga}
