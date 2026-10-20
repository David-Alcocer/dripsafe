"""Las cuatro reglas didácticas del kit, sobre la telemetría del contrato.

La referencia del kit está fuera de Git en ``common/cifox.py``. Una
comparación posterior entre métodos debe darles el mismo acceso al registro OT.
"""

import math

import pandas as pd

from src.metricas.impacto import UnidadEnergia, _claves, _factor_energia, _numeros


def reglas_fijas(telemetria: pd.DataFrame, *, horas_por_intervalo: float,
                 unidad_energia: UnidadEnergia,
                 pue_max: float = 1.6, wue_max: float = 1.5,
                 entrada_max_c: float = 29.0,
                 incluir_ot: bool = True) -> pd.DataFrame:
    """Devuelve una bandera y motivos por fila, con umbrales estrictos (``>``).

    La energía puede ser kWh/intervalo o kW promedio. El agua es litros por
    intervalo. ``incluir_ot=False`` es una ablación, no la regla del kit.
    """
    factor = _factor_energia(unidad_energia, horas_por_intervalo)
    if not all(math.isfinite(limite) for limite in (pue_max, wue_max, entrada_max_c)):
        raise ValueError("los umbrales deben ser finitos")
    tiene_sitio = "site_id" in telemetria
    tabla = _claves(telemetria)
    claves = ["site_id", "timestamp"] if tiene_sitio else ["timestamp"]
    valores = _numeros(tabla, ["kw_ti", "kw_total", "agua_reposicion_l", "inlet_temp_c"])
    if (valores["kw_ti"] <= 0).any() or (valores[["kw_total", "agua_reposicion_l"]] < 0).any().any():
        raise ValueError("energía TI debe ser positiva y energía/agua no negativas")
    if (valores["kw_total"] < valores["kw_ti"]).any():
        raise ValueError("kw_total no puede ser menor que kw_ti")

    pue = valores["kw_total"] / valores["kw_ti"]
    wue = valores["agua_reposicion_l"] / (valores["kw_ti"] * factor)
    marcas = pd.DataFrame({
        "pue": pue > pue_max,
        "agua": wue > wue_max,
        "entrada": valores["inlet_temp_c"] > entrada_max_c,
    }, index=tabla.index)
    if incluir_ot:
        if "ot_event" not in tabla or tabla["ot_event"].isna().any():
            raise ValueError("se requiere ot_event para la comparación con OT")
        marcas["ot"] = tabla["ot_event"] != "normal"
    salida = tabla[claves].copy()
    salida["anomalia"] = marcas.any(axis=1).to_numpy()
    salida["motivo_regla"] = marcas.apply(
        lambda fila: ", ".join(nombre for nombre, activo in fila.items() if activo), axis=1,
    ).to_numpy()
    return salida
