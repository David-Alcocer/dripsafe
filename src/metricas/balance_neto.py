"""Balance neto de DripSafe (#14 · Misa + Nico).

Calcula el costo anual del detector a partir de G3, el umbral de equilibrio
según el exceso no TI y el saldo entre ahorro proyectado y costo anual.
La proyección del ahorro se calcula por separado con los supuestos de Nico.

Regla contra el doble conteo
----------------------------
``detectar()`` ajusta la línea base en cada llamada. Por eso su energía
(``corrida_completa``) NO se puede anualizar como inferencia y además sumarle
reentrenamientos. El formato 2 del contrato separa:

    E_año = E_inferencia_pura × horas_año × lotes_por_hora
          + E_entrenamiento × reentrenamientos_año

El formato 1 (``kwh_inferencia_anual``) ya incluía el ajuste en cada corrida:
se trata como cota superior y se ignoran los reentrenamientos.
"""

import math
import statistics
from collections.abc import Iterable

from src.procedencia import FRECUENCIA_POR_DEFECTO

# Factores externos usados en #14. El factor de emisión es oficial; la
# intensidad hídrica es una estimación trazable, no un factor oficial de México.
FACTOR_EMISION_SEN_KG_KWH = 0.444
URL_FESEN_2024 = "https://www.gob.mx/cms/uploads/attachment/file/981194/aviso_fesen_2024.pdf"
URL_AVISO_COA_2026 = (
    "https://www.gob.mx/cms/uploads/attachment/file/1081506/"
    "aviso_factor_de_emision_electrico_coa_2026.pdf"
)
INTENSIDAD_HIDRICA_SEN_L_KWH = 2.0632
URL_MEZCLA_CNE_2024 = (
    "https://www.cne.gob.mx/Electricidad%20CNE/Codigo%20de%20red/"
    "Anexo%20Acuerdo%20RCSEN2024%20R00.pdf"
)
URL_NREL_2012 = "https://openei.org/datasets/files/969/pub/1748-9326_7_4_045802.pdf"


def _kwh_no_negativo(valor: float, nombre: str) -> float:
    """Convierte a float y rechaza negativos, booleanos, NaN e infinitos."""
    if isinstance(valor, bool):
        raise ValueError(f"{nombre} debe ser un número finito no negativo")
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{nombre} debe ser un número finito no negativo") from exc
    if not math.isfinite(numero) or numero < 0:
        raise ValueError(f"{nombre} debe ser un número finito no negativo")
    return numero


def _frecuencia(frecuencia: dict | None) -> dict:
    """Completa y valida la frecuencia de anualización (supuestos explícitos)."""
    f = {**FRECUENCIA_POR_DEFECTO, **(frecuencia or {})}
    for clave in ("horas_anio", "lotes_inferencia_por_hora", "reentrenamientos_anio"):
        valor = f[clave]
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
            raise ValueError(f"frecuencia.{clave} debe ser un número no negativo")
        f[clave] = float(valor)
    return f


def _kwh_fase(consumo: dict, nombre: str) -> float | None:
    fase = consumo.get(nombre)
    if isinstance(fase, dict) and fase.get("kwh_mediana") is not None:
        return float(fase["kwh_mediana"])
    return None


def desglose_costo_anual(consumo: dict, frecuencia: dict | None = None) -> dict:
    """kWh/año del detector con el desglose que justifica cada sumando.

    Devuelve ``modo``, los dos sumandos, el total y la frecuencia aplicada.
    Si el archivo es del formato 1, ``reentrenamientos_aplicados`` es 0: su
    ``kwh_inferencia_anual`` ya incluye el ajuste en cada corrida.
    """
    # La frecuencia del archivo manda; un valor explícito la puede sobrescribir.
    del_archivo = consumo.get("frecuencia")
    base = del_archivo if isinstance(del_archivo, dict) else {}
    f = _frecuencia({**base, **(frecuencia or {})})

    if consumo.get("formato") == 2 or (
        isinstance(consumo.get("inferencia"), dict)
        and isinstance(consumo.get("entrenamiento"), dict)
    ):
        inferencia = _kwh_fase(consumo, "inferencia")
        entrenamiento = _kwh_fase(consumo, "entrenamiento")
        if inferencia is None:
            raise ValueError("consumo_modelo.json no trae la mediana de inferencia")
        entrenamiento = entrenamiento or 0.0
        lote = consumo.get("lote")
        horas_lote = lote.get("horas") if isinstance(lote, dict) else None
        if isinstance(horas_lote, bool) or not isinstance(horas_lote, (int, float)) or horas_lote <= 0:
            raise ValueError("consumo_modelo.json v2 no trae 'lote.horas' (> 0)")
        inf_por_hora = inferencia / float(horas_lote)
        inf_anual = inf_por_hora * f["horas_anio"] * f["lotes_inferencia_por_hora"]
        ent_anual = entrenamiento * f["reentrenamientos_anio"]
        return {
            "modo": "fases_separadas",
            "inferencia_kwh_por_hora": inf_por_hora,
            "inferencia_kwh_anual": inf_anual,
            "entrenamiento_kwh_anual": ent_anual,
            "total_kwh_anual": inf_anual + ent_anual,
            "horas_lote": float(horas_lote),
            "reentrenamientos_aplicados": f["reentrenamientos_anio"],
            "supuestos": f,
            "nota": (
                f"Inferencia por hora (lote medido de {float(horas_lote):g} h) × "
                "horas × lotes + entrenamiento × reentrenamientos. La corrida "
                "completa no se suma."
            ),
        }

    if "kwh_inferencia_anual" in consumo:
        total = float(consumo["kwh_inferencia_anual"])
        if total < 0:
            raise ValueError("el costo del detector no puede ser negativo")
        return {
            "modo": "legacy_corrida_completa",
            "inferencia_kwh_anual": total,
            "entrenamiento_kwh_anual": 0.0,
            "total_kwh_anual": total,
            "reentrenamientos_aplicados": 0.0,
            "supuestos": f,
            "nota": (
                "Formato 1: kwh_inferencia_anual ya incluye el ajuste en cada "
                "corrida; no se suma reentrenamiento (cota superior)."
            ),
        }

    if "kwh_corrida_completa" in consumo:
        total = float(consumo["kwh_corrida_completa"]) * f["horas_anio"] * f["lotes_inferencia_por_hora"]
        if total < 0:
            raise ValueError("el costo del detector no puede ser negativo")
        return {
            "modo": "cota_superior_corrida_completa",
            "inferencia_kwh_anual": total,
            "entrenamiento_kwh_anual": 0.0,
            "total_kwh_anual": total,
            "reentrenamientos_aplicados": 0.0,
            "supuestos": f,
            "nota": (
                "Solo hay corrida completa y ya incluye ajuste: se anualiza "
                "como cota superior y no se suma reentrenamiento."
            ),
        }

    raise ValueError(
        "consumo_modelo.json no trae 'inferencia'/'entrenamiento' ni "
        "'kwh_inferencia_anual' ni 'kwh_corrida_completa'"
    )


def costo_anual_kwh(consumo: dict, frecuencia: dict | None = None) -> float:
    """kWh al año que cuesta el detector, ya sin doble conteo del ajuste."""
    return float(desglose_costo_anual(consumo, frecuencia)["total_kwh_anual"])


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


def balance_energia_anual(ahorro_proyectado_kwh_anual: float, costo_detector_kwh_anual: float) -> float:
    """Ahorro proyectado menos costo del detector, en kWh por año."""
    ahorro = _kwh_no_negativo(ahorro_proyectado_kwh_anual, "el ahorro proyectado")
    costo = _kwh_no_negativo(costo_detector_kwh_anual, "el costo del detector")
    return ahorro - costo


def emisiones_detector_gco2e_anual(costo_detector_kwh_anual: float) -> float:
    """Emisiones estimadas del detector: kWh/año × 0.444 kgCO₂e/kWh × 1000."""
    costo = _kwh_no_negativo(costo_detector_kwh_anual, "el costo del detector")
    return costo * FACTOR_EMISION_SEN_KG_KWH * 1000


def co2_evitado_kg_anual(ahorro_proyectado_kwh_anual: float) -> float:
    """CO₂e evitado proyectado con el FESEN oficial aplicable a 2026."""
    ahorro = _kwh_no_negativo(ahorro_proyectado_kwh_anual, "el ahorro proyectado")
    return ahorro * FACTOR_EMISION_SEN_KG_KWH


def agua_indirecta_evitada_l_anual(ahorro_proyectado_kwh_anual: float) -> float:
    """Agua de generación evitada, con la intensidad hídrica estimada para el SEN."""
    ahorro = _kwh_no_negativo(ahorro_proyectado_kwh_anual, "el ahorro proyectado")
    return ahorro * INTENSIDAD_HIDRICA_SEN_L_KWH
