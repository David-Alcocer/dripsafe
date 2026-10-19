"""Contratos 3 y 4 de mentira, para construir el dashboard sin esperar al modelo.

NO son resultados reales: las alertas se copian de las etiquetas de los escenarios
(la respuesta correcta), así que aquí el «modelo» casi siempre acierta. Sirven
solo para diseñar las pantallas. En cuanto existan los archivos reales
(data/resultados/alertas.csv y resultados/numeros_oficiales.json), el dashboard
los usa en lugar de esto (ver app/cargar.py).
"""

import numpy as np
import pandas as pd

from src import contrato, sinteticos
from src.ataques.escenarios import LITROS_POR_KWH_EXTRA
from src.ataques.inyectar import inyectar

DIAS = 14
SEMILLA = 42

COLUMNAS_ENFRIAMIENTO = ["kw_chiller", "kw_bombas", "kw_torre"]
TIPO_SUGERIDO = {"normal": "normal", "falla": "ineficiencia", "ataque": "posible_ataque"}

# La variable que «más pesó» en cada escenario (en el real lo calcula Gadiel, #8).
VARIABLE_PRINCIPAL = {
    "setpoint_alterado": "setpoint_suministro",
    "sensor_falsificado": "t_retorno",
    "vista_repetida": "kw_bombas",
    "comandos_no_autorizados": "bomba_encendida",
    "ensuciamiento": "kw_chiller",
    "sensor_atorado": "t_retorno",
    "fuga_reposicion": "agua_reposicion_l",
}

# Igual que en docs/06: la denegación de vista se atrapa con una regla, no con el modelo.
NO_DETECTADOS = {"denegacion_de_vista"}

# Consumo del modelo inventado, del orden de lo que mide CodeCarbon para un Isolation Forest.
CONSUMO_MODELO = {"kwh_entrenamiento": 0.004, "kwh_inferencia_anual": 0.35, "kg_co2e_entrenamiento": 0.0018}


def telemetria(dias: int = DIAS, semilla: int = SEMILLA):
    """Regresa (telemetría limpia, telemetría con escenarios = contrato 2, manifiesto)."""
    limpia = sinteticos.generar(dias, semilla=semilla)
    escenarios, manifiesto = inyectar(limpia, semilla=semilla)
    return limpia, escenarios, manifiesto


def alertas(limpia: pd.DataFrame, escenarios: pd.DataFrame, semilla: int = SEMILLA) -> pd.DataFrame:
    """Contrato 3 falso: una fila por cada fila de la telemetría."""
    rng = np.random.default_rng(semilla)
    n = len(escenarios)
    nombre = escenarios["etiqueta_escenario"].fillna("").to_numpy()
    tipo = escenarios["etiqueta_tipo"].to_numpy()

    anomalia = np.zeros(n, dtype=bool)
    variable = np.full(n, "", dtype=object)
    # Un modelo real tarda un poco en reaccionar: marca desde el 15 % de cada ventana.
    for esc in set(nombre) - {""} - NO_DETECTADOS:
        filas = np.flatnonzero(nombre == esc)
        retraso = max(1, int(len(filas) * 0.15))
        anomalia[filas[retraso:]] = True
        variable[filas[retraso:]] = VARIABLE_PRINCIPAL.get(esc, "")

    # Unas cuantas falsas alarmas en horas normales, para que se vean como en la vida real.
    normales = (tipo == "normal") & (escenarios["etiqueta_particion"].to_numpy() == "evaluacion")
    falsas = normales & (rng.random(n) < 0.001)
    anomalia |= falsas
    variable[falsas] = "kw_chiller"

    tipo_sugerido = np.where(anomalia, pd.Series(tipo).map(TIPO_SUGERIDO), "normal")
    tipo_sugerido[falsas] = "ineficiencia"
    score = np.where(anomalia, -rng.uniform(0.01, 0.15, n), rng.normal(0.08, 0.03, n))

    return pd.DataFrame({
        "timestamp": escenarios["timestamp"],
        "score": score.round(4),
        "anomalia": anomalia,
        "tipo_sugerido": tipo_sugerido,
        "variable_principal": variable,
        "kw_esperado_enfriamiento": limpia[COLUMNAS_ENFRIAMIENTO].sum(axis=1).round(2),
    })


def _cifra(valor, unidad, origen="app/simulado.py", responsable="Leo (simulado)"):
    return {"valor": valor, "unidad": unidad, "origen": origen, "responsable": responsable}


def numeros_oficiales(escenarios: pd.DataFrame, alertas_df: pd.DataFrame, limpia: pd.DataFrame,
                      resumen_deteccion: dict) -> dict:
    """Contrato 4 falso, calculado con la misma lógica que se espera del real.

    Ahorro = lo que se gastó de más en enfriamiento (y agua) durante las alertas,
    llevado a un año. Si DripSafe avisa, el operador corrige y eso se evita.
    """
    horas = contrato.intervalo_horas(escenarios)
    ev = (escenarios["etiqueta_particion"] == "evaluacion").to_numpy()
    alerta = alertas_df["anomalia"].to_numpy() & ev

    kwh_ti = (escenarios["kw_ti"] * horas)[ev].sum()
    kwh_total = (escenarios["kw_total"] * horas)[ev].sum()
    enfriamiento = escenarios[COLUMNAS_ENFRIAMIENTO].sum(axis=1)
    exceso_kw = (enfriamiento - alertas_df["kw_esperado_enfriamiento"]).clip(lower=0)
    kwh_evitados = (exceso_kw * horas)[alerta].sum()
    agua_extra = (escenarios["agua_reposicion_l"] - limpia["agua_reposicion_l"]).clip(lower=0)
    litros_evitados = agua_extra[alerta].sum() + kwh_evitados * LITROS_POR_KWH_EXTRA

    dias_evaluacion = ev.sum() * horas / 24
    al_anio = 365 / dias_evaluacion
    kwh_ahorro_anual = kwh_evitados * al_anio
    kwh_modelo_anual = CONSUMO_MODELO["kwh_entrenamiento"] + CONSUMO_MODELO["kwh_inferencia_anual"]

    return {
        "pue_antes": _cifra(round(kwh_total / kwh_ti, 3), ""),
        "pue_despues": _cifra(round((kwh_total - kwh_evitados) / kwh_ti, 3), ""),
        "kwh_ahorrados_anual": _cifra(round(kwh_ahorro_anual), "kWh/año"),
        "litros_ahorrados_anual": _cifra(round(litros_evitados * al_anio), "L/año"),
        "kwh_modelo_anual": _cifra(round(kwh_modelo_anual, 3), "kWh/año"),
        "kg_co2e_modelo": _cifra(CONSUMO_MODELO["kg_co2e_entrenamiento"], "kg CO₂e"),
        "balance_neto_kwh": _cifra(round(kwh_ahorro_anual - kwh_modelo_anual), "kWh/año"),
        "balance_neto_veces": _cifra(round(kwh_ahorro_anual / kwh_modelo_anual), "×"),
        "escenarios_detectados": _cifra(resumen_deteccion["escenarios_detectados"], ""),
        "escenarios_totales": _cifra(resumen_deteccion["escenarios_totales"], ""),
        "falsas_alarmas_por_dia": _cifra(resumen_deteccion["falsas_alarmas_por_dia"], "por día"),
        "generado_con_commit": "simulado",
    }
