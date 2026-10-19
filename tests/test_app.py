"""Pruebas de la lógica del dashboard (sin Streamlit, solo datos sintéticos)."""

import pandas as pd

from app import calculos, simulado
from src.ataques.evaluar import evaluar


def _datos():
    limpia, escenarios, manifiesto = simulado.telemetria(dias=7)
    alertas = simulado.alertas(limpia, escenarios)
    return limpia, escenarios, manifiesto, alertas


def test_alertas_simuladas_cumplen_contrato_3():
    _, escenarios, _, alertas = _datos()
    assert len(alertas) == len(escenarios)
    assert list(alertas.columns) == ["timestamp", "score", "anomalia", "tipo_sugerido",
                                     "variable_principal", "kw_esperado_enfriamiento"]
    assert set(alertas["tipo_sugerido"]) <= {"normal", "ineficiencia", "posible_ataque"}
    # Más bajo = más raro: las anomalías tienen score negativo.
    assert (alertas.loc[alertas["anomalia"], "score"] < 0).all()


def test_numeros_simulados_tienen_formato_del_contrato_4():
    limpia, escenarios, _, alertas = _datos()
    _, resumen = evaluar(escenarios, alertas)
    numeros = simulado.numeros_oficiales(escenarios, alertas, limpia, resumen)
    for clave in ["pue_antes", "pue_despues", "kwh_ahorrados_anual", "balance_neto_veces"]:
        assert {"valor", "unidad", "origen", "responsable"} <= set(numeros[clave])
    assert numeros["pue_despues"]["valor"] <= numeros["pue_antes"]["valor"]
    assert numeros["balance_neto_kwh"]["valor"] > 0


def test_eventos_junta_tramos_seguidos():
    ts = pd.date_range("2026-10-01", periods=10, freq="5min")
    df = pd.DataFrame({
        "timestamp": ts,
        "anomalia": [False, True, True, False, True, False, False, False, False, True],
        "tipo_sugerido": ["normal", "posible_ataque", "posible_ataque", "normal", "posible_ataque",
                          "normal", "normal", "normal", "normal", "ineficiencia"],
        "variable_principal": ["", "kw_bombas", "kw_bombas", "", "kw_bombas", "", "", "", "", "kw_chiller"],
        "score": [0.1, -0.1, -0.2, 0.1, -0.1, 0.1, 0.1, 0.1, 0.1, -0.05],
    })
    ev = calculos.eventos(df, hueco_max=1)
    assert len(ev) == 2
    assert ev.iloc[0]["inicio"] == ts[1] and ev.iloc[0]["fin"] == ts[4]
    assert ev.iloc[0]["tipo_sugerido"] == "posible_ataque"
    assert ev.iloc[1]["variable_principal"] == "kw_chiller"


def test_eventos_sin_anomalias_regresa_tabla_vacia():
    df = pd.DataFrame({"timestamp": pd.date_range("2026-10-01", periods=3, freq="5min"),
                       "anomalia": [False] * 3, "tipo_sugerido": ["normal"] * 3, "score": [0.1] * 3})
    assert calculos.eventos(df).empty


def test_derivadas_y_pue_por_hora():
    limpia, _, _, _ = _datos()
    df = calculos.agregar_derivadas(limpia)
    # En datos limpios, todo el calor de TI pasa al agua (así se generan los sintéticos).
    assert (df["calor_agua_kw"] - df["kw_ti"]).abs().mean() < 30
    pue = calculos.pue_por_hora(df)
    assert pue.between(1.1, 1.6).all()
