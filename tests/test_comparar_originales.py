"""Comparación sintética: las unidades de hora y episodio no se mezclan."""

import pandas as pd
import pytest

from src.evaluacion.comparar_originales import comparar


def test_comparacion_originales_separa_episodios_horas_y_latencia():
    horas = pd.date_range("2026-10-01", periods=9, freq="h", tz="UTC")
    datos = pd.DataFrame({
        "site_id": ["A"] * 9,
        "timestamp": horas,
        "etiqueta_particion": ["entrenamiento"] + ["evaluacion"] * 8,
        "etiqueta_escenario": ["", "", "ineficiencia", "ineficiencia"] + [""] * 5,
    })
    dripsafe = datos[["site_id", "timestamp"]].copy()
    dripsafe["anomalia"] = [True, False, False, True, False, False, True, True, False]
    reglas = datos[["site_id", "timestamp"]].copy()
    reglas["anomalia"] = [False, False, True, True, False, False, False, False, False]

    tabla, detalle = comparar(datos, {"dripsafe": dripsafe, "reglas_kit": reglas})
    assert len(tabla) == 4  # dos métodos × (sitio y total)
    dr = tabla.set_index(["metodo", "site_id"]).loc[("dripsafe", "A")]
    assert (dr["episodios_verdaderos"], dr["tp_episodios"], dr["fp_episodios"],
            dr["fn_episodios"]) == (1, 1, 1, 0)
    assert (dr["horas_evaluacion_sitio"], dr["horas_anomalas"],
            dr["horas_limpias_sitio"]) == (8, 2, 6)
    assert (dr["tp_horas"], dr["fp_horas"], dr["fn_horas"]) == (1, 2, 1)
    assert dr["precision_episodios"] == pytest.approx(1 / 2)
    assert dr["recall_episodios"] == 1
    assert dr["precision_horas"] == pytest.approx(1 / 3)
    assert dr["recall_horas"] == pytest.approx(1 / 2)
    assert dr["latencia_media_h"] == 1
    assert dr["falsas_alarmas_por_dia_sitio"] == pytest.approx(4)
    assert tabla.set_index(["metodo", "site_id"]).loc[("reglas_kit", "A"), "tp_horas"] == 2
    assert detalle.set_index("metodo").loc["dripsafe", "duracion_h"] == 2
    assert detalle.set_index("metodo").loc["dripsafe", "horas_hasta_detectar"] == 1


def test_comparacion_originales_rechaza_horas_sin_alerta():
    horas = pd.date_range("2026-10-01", periods=2, freq="h", tz="UTC")
    datos = pd.DataFrame({"site_id": ["A", "A"], "timestamp": horas,
                          "etiqueta_particion": ["evaluacion"] * 2,
                          "etiqueta_escenario": ["", "ineficiencia"]})
    incompletas = pd.DataFrame({"site_id": ["A"], "timestamp": [horas[0]],
                                 "anomalia": [False]})
    with pytest.raises(ValueError, match="faltan alertas"):
        comparar(datos, {"dripsafe": incompletas, "reglas_kit": incompletas})


def test_comparacion_originales_no_mezcla_sitios_con_horas_iguales():
    horas = pd.date_range("2026-10-01", periods=3, freq="h", tz="UTC")
    datos = pd.DataFrame({"site_id": ["A"] * 3 + ["B"] * 3,
                          "timestamp": list(horas) * 2,
                          "etiqueta_particion": ["evaluacion"] * 6,
                          "etiqueta_escenario": ["", "fuga_agua", ""] + [""] * 3})
    alertas = datos[["site_id", "timestamp"]].copy()
    alertas["anomalia"] = [False, True, False, False, False, True]
    tabla, _ = comparar(datos, {"dripsafe": alertas, "reglas_kit": alertas})
    dr = tabla[tabla["metodo"] == "dripsafe"].set_index("site_id")
    assert dr.loc["A", ["tp_episodios", "fp_episodios", "fn_episodios"]].tolist() == [1, 0, 0]
    assert dr.loc["B", ["tp_episodios", "fp_episodios", "fn_episodios"]].tolist() == [0, 1, 0]
    assert pd.isna(dr.loc["B", "recall_episodios"])
    assert dr.loc["TOTAL", ["horas_evaluacion_sitio", "horas_limpias_sitio",
                            "tp_episodios", "fp_episodios"]].tolist() == [6, 5, 1, 1]
