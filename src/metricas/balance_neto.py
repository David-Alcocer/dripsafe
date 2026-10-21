"""Balance neto de DripSafe (#14 · Misa + Nico).

Compara lo que cuesta correr el detector un año (medido con CodeCarbon por
Gadiel, G3) contra el exceso de energía no TI que el detector señala.

Aquí NO se calcula un ahorro proyectado: eso necesita supuestos que Nico fija
(horas de ineficiencia al año, tiempo hasta corregir). Solo se calcula el
umbral de equilibrio: cuántas horas de ineficiencia típica al año pagan el
costo del detector. Si basta con muy pocas, el balance es positivo aunque la
proyección no sea exacta.
"""

import statistics
from collections.abc import Iterable


def costo_anual_kwh(consumo: dict) -> float:
    """kWh al año que cuesta el detector, desde consumo_modelo.json.

    Se usa `kwh_inferencia_anual` (8 760 corridas completas). Cada corrida ya
    incluye el ajuste de la línea base, así que es una cota alta del costo.
    """
    if "kwh_inferencia_anual" not in consumo:
        raise ValueError("consumo_modelo.json no trae 'kwh_inferencia_anual'")
    costo = float(consumo["kwh_inferencia_anual"])
    if costo < 0:
        raise ValueError("el costo del detector no puede ser negativo")
    return costo


def horas_para_equilibrio(costo_kwh_anual: float, exceso_por_hora_alertada: Iterable[float]) -> dict:
    """Horas de ineficiencia típica al año que igualan el costo del detector.

    `exceso_por_hora_alertada` son los kWh de exceso no TI de cada hora con
    alerta. Se usa la mediana de las horas con exceso positivo como "típica".
    """
    positivos = [float(x) for x in exceso_por_hora_alertada if x > 0]
    if not positivos:
        return {"exceso_tipico_kwh_por_hora": None, "horas_necesarias_al_año": None}
    tipico = statistics.median(positivos)
    return {"exceso_tipico_kwh_por_hora": tipico, "horas_necesarias_al_año": costo_kwh_anual / tipico}
