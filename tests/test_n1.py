"""Casos sintéticos de N1: tres sitios comparten horas, sin datos del kit."""

import pandas as pd
import pytest

from src.evaluacion.episodios import episodios_desde_etiquetas, evaluar_episodios
from src.evaluacion.reglas import reglas_fijas
from src.metricas.impacto import exceso_no_ti, pue_wue_por_sitio
from src.sinteticos import generar


def test_pue_y_wue_son_cocientes_de_sumas_por_sitio():
    ts = pd.Timestamp("2026-10-01T00:00:00Z")
    df = pd.DataFrame({
        "site_id": ["A", "A", "B"], "timestamp": [ts, ts + pd.Timedelta(hours=1), ts],
        "kw_ti": [100, 200, 100], "kw_total": [150, 220, 120],
        "agua_reposicion_l": [10, 40, 0],
        "etiqueta_particion": ["evaluacion"] * 3,
    })
    resultado = pue_wue_por_sitio(df, particion="evaluacion",
                                  unidad_energia="kwh_intervalo",
                                  horas_por_intervalo=1).set_index("site_id")
    assert resultado.loc["A", "pue"] == pytest.approx(370 / 300)
    assert resultado.loc["A", "wue_in_situ_l_kwh"] == pytest.approx(50 / 300)
    assert resultado.loc["B", "pue"] == pytest.approx(1.2)
    assert resultado.loc["B", "wue_in_situ_l_kwh"] == 0
    assert resultado.loc["A", "n_intervalos"] == 2
    assert resultado.loc["A", "periodo_inicio"] == ts
    assert resultado.loc["A", "periodo_fin"] == ts + pd.Timedelta(hours=1)


def test_sinteticos_de_cinco_minutos_convierten_kw_a_kwh():
    df = generar(dias=1, minutos=5).assign(etiqueta_particion="evaluacion")
    resultado = pue_wue_por_sitio(df, particion="evaluacion",
                                  unidad_energia="kw_promedio",
                                  horas_por_intervalo=5 / 60).iloc[0]
    assert resultado["energia_it_kwh"] == pytest.approx(df["kw_ti"].sum() / 12)
    assert resultado["wue_in_situ_l_kwh"] == pytest.approx(
        df["agua_reposicion_l"].sum() / (df["kw_ti"].sum() / 12),
    )


def test_exceso_estimado_une_por_sitio_y_hora_y_conserva_sin_alerta():
    hora = pd.Timestamp("2026-10-01T00:00:00Z")
    df = pd.DataFrame({"site_id": ["A", "B"], "timestamp": [hora, hora],
                       "kw_ti": [100, 100], "kw_total": [150, 120],
                       "etiqueta_particion": ["evaluacion"] * 2})
    alertas = pd.DataFrame({"site_id": ["B", "A"], "timestamp": [hora, hora],
                            "anomalia": [False, True],
                            "esperado_no_ti": [10, 30]})
    resultado = exceso_no_ti(df, alertas, columna_esperado="esperado_no_ti",
                             unidad_energia="kwh_intervalo",
                             horas_por_intervalo=1).set_index("site_id")
    assert resultado.loc["A", "exceso_no_ti_estimado_kwh"] == 20
    assert resultado.loc["A", "exceso_no_ti_con_alerta_kwh"] == 20
    assert resultado.loc["B", "exceso_no_ti_estimado_kwh"] == 10
    assert resultado.loc["B", "exceso_no_ti_sin_alerta_kwh"] == 10
    with pytest.raises(ValueError, match="site_id"):
        exceso_no_ti(df, alertas.drop(columns="site_id"),
                     columna_esperado="esperado_no_ti",
                     unidad_energia="kwh_intervalo", horas_por_intervalo=1)


def test_reglas_fijas_usan_umbrales_estrictos_y_misma_hora_en_dos_sitios():
    hora = pd.Timestamp("2026-10-01T00:00:00Z")
    df = pd.DataFrame({
        "site_id": ["A", "B"], "timestamp": [hora, hora],
        "kw_ti": [100, 100], "kw_total": [160, 161],
        "agua_reposicion_l": [150, 151], "inlet_temp_c": [29, 29.1],
        "ot_event": ["login_fallido", "normal"],
    })
    resultado = reglas_fijas(df, horas_por_intervalo=1,
                             unidad_energia="kwh_intervalo").set_index("site_id")
    assert resultado.loc["A", "anomalia"]
    assert resultado.loc["A", "motivo_regla"] == "ot"
    assert resultado.loc["B", "anomalia"]
    assert resultado.loc["B", "motivo_regla"] == "pue, agua, entrada"
    sin_ot = reglas_fijas(df, horas_por_intervalo=1,
                          unidad_energia="kwh_intervalo", incluir_ot=False).set_index("site_id")
    assert not sin_ot.loc["A", "anomalia"]


def test_episodios_separan_sitio_y_tramos_contiguos():
    horas = pd.date_range("2026-10-01", periods=5, freq="h", tz="UTC")
    df = pd.DataFrame({
        "site_id": ["A"] * 5 + ["B"] * 5,
        "timestamp": list(horas) * 2,
        "etiqueta_particion": ["evaluacion"] * 10,
        "etiqueta_escenario": ["", "ineficiencia", "ineficiencia", "", "ineficiencia"]
                              + ["", "", "fuga_agua", "fuga_agua", ""],
    })
    episodios = episodios_desde_etiquetas(df, horas_por_intervalo=1)
    assert len(episodios) == 3
    assert list(episodios["site_id"]) == ["A", "A", "B"]
    assert episodios.iloc[0]["fin"] == horas[2]
    assert episodios.iloc[1]["inicio"] == horas[4]


def test_evaluacion_cuenta_episodios_y_fp_por_tramo_limpio():
    horas = pd.date_range("2026-10-01", periods=8, freq="h", tz="UTC")
    df = pd.DataFrame({"site_id": ["A"] * 8 + ["B"] * 8,
                       "timestamp": list(horas) * 2,
                       "etiqueta_particion": ["evaluacion"] * 16})
    avisos = df[["site_id", "timestamp"]].copy()
    avisos["anomalia"] = ([False, False, True, False, False, True, True, False]
                          + [True, False, False, False, False, False, False, False])
    ventanas = pd.DataFrame({
        "site_id": ["A", "A", "B"],
        "inicio": [horas[1], horas[2], horas[4]],
        "fin": [horas[2], horas[3], horas[5]],
        "origen": ["kit", "inyeccion", "kit"],
    })
    episodios, resumen = evaluar_episodios(df, avisos, ventanas, horas_por_intervalo=1)
    assert len(episodios) == 2  # las dos ventanas solapadas de A se fusionan
    assert episodios.iloc[0]["origen"] == "inyeccion"
    assert episodios.iloc[0]["horas_hasta_detectar"] == 1
    assert resumen["tp"] == 1 and resumen["fn"] == 1 and resumen["fp"] == 2
    assert resumen["precision"] == pytest.approx(1 / 3)
    assert resumen["recall"] == pytest.approx(1 / 2)
    assert resumen["dias_limpios_sitio"] == pytest.approx(11 / 24)
    assert resumen["falsas_alarmas_por_dia_sitio"] == pytest.approx(2 * 24 / 11)
    inferior, superior = resumen["ic_falsas_alarmas_por_dia_sitio"]
    assert inferior < resumen["falsas_alarmas_por_dia_sitio"] < superior


def test_evaluacion_rechaza_episodio_con_horas_faltantes():
    horas = pd.date_range("2026-10-01", periods=3, freq="h", tz="UTC")
    telemetria = pd.DataFrame({"timestamp": [horas[0], horas[2]],
                              "etiqueta_particion": ["evaluacion"] * 2})
    avisos = telemetria.assign(anomalia=False)
    ventanas = pd.DataFrame({"inicio": [horas[0]], "fin": [horas[2]]})
    with pytest.raises(ValueError, match="horas incompletas"):
        evaluar_episodios(telemetria, avisos, ventanas, horas_por_intervalo=1)


def test_pue_wue_no_mezcla_particiones_y_reporta_cobertura():
    horas = pd.date_range("2026-10-01", periods=2, freq="h", tz="UTC")
    datos = pd.DataFrame({
        "site_id": ["A", "A"], "timestamp": horas,
        "etiqueta_particion": ["entrenamiento", "evaluacion"],
        "kw_ti": [100, 200], "kw_total": [150, 220],
        "agua_reposicion_l": [10, 40],
    })
    base = pue_wue_por_sitio(datos, particion="entrenamiento",
                             unidad_energia="kwh_intervalo", horas_por_intervalo=1).iloc[0]
    evaluacion = pue_wue_por_sitio(datos, particion="evaluacion",
                                   unidad_energia="kwh_intervalo", horas_por_intervalo=1).iloc[0]
    assert base["pue"] == 1.5 and evaluacion["pue"] == 1.1
    assert base["n_intervalos"] == evaluacion["n_intervalos"] == 1
    assert base["periodo_inicio"] == base["periodo_fin"] == horas[0]
    assert evaluacion["periodo_inicio"] == evaluacion["periodo_fin"] == horas[1]
    assert evaluacion["unidad_energia_entrada"] == "kwh_intervalo"


def test_kwh_por_intervalo_no_se_multiplica_por_duracion_y_agua_ausente_es_null():
    datos = pd.DataFrame({
        "timestamp": pd.date_range("2026-10-01", periods=2, freq="5min", tz="UTC"),
        "etiqueta_particion": ["evaluacion"] * 2,
        "kw_ti": [100, 200], "kw_total": [150, 220],
    })
    resultado = pue_wue_por_sitio(datos, particion="evaluacion",
                                  unidad_energia="kwh_intervalo",
                                  horas_por_intervalo=5 / 60).iloc[0]
    assert resultado["energia_it_kwh"] == 300
    assert resultado["pue"] == pytest.approx(370 / 300)
    assert pd.isna(resultado["agua_in_situ_l"])
    assert pd.isna(resultado["wue_in_situ_l_kwh"])


@pytest.mark.parametrize(("cambio", "mensaje"), [
    ({"kw_ti": 0}, "energía de TI nula"),
    ({"kw_total": 9}, "kw_total"),
    ({"agua_reposicion_l": -1}, "no negativas"),
    ({"kw_ti": float("nan")}, "no finitos"),
])
def test_pue_wue_rechaza_mediciones_invalidas(cambio, mensaje):
    datos = pd.DataFrame({
        "timestamp": [pd.Timestamp("2026-10-01T00:00:00Z")],
        "etiqueta_particion": ["evaluacion"],
        "kw_ti": [10], "kw_total": [15], "agua_reposicion_l": [1],
    }).assign(**cambio)
    with pytest.raises(ValueError, match=mensaje):
        pue_wue_por_sitio(datos, particion="evaluacion",
                          unidad_energia="kwh_intervalo", horas_por_intervalo=1)


def test_pue_wue_exige_particion_y_unidad_explicitas():
    datos = pd.DataFrame({"timestamp": [pd.Timestamp("2026-10-01T00:00:00Z")],
                          "kw_ti": [10], "kw_total": [15]})
    with pytest.raises(ValueError, match="etiqueta_particion"):
        pue_wue_por_sitio(datos, particion="evaluacion",
                          unidad_energia="kwh_intervalo", horas_por_intervalo=1)
    datos["etiqueta_particion"] = "evaluacion"
    with pytest.raises(ValueError, match="unidad_energia"):
        pue_wue_por_sitio(datos, particion="evaluacion",
                          unidad_energia="desconocida", horas_por_intervalo=1)
    with pytest.raises(ValueError, match="no hay filas"):
        pue_wue_por_sitio(datos, particion="entrenamiento",
                          unidad_energia="kwh_intervalo", horas_por_intervalo=1)


def test_excesos_de_energia_y_agua_separan_residuo_alerta_y_evento_ot():
    horas = pd.date_range("2026-10-01", periods=3, freq="h", tz="UTC")
    datos = pd.DataFrame({
        "site_id": ["A", "A", "B", "A"],
        "timestamp": [horas[0], horas[1], horas[0], horas[2]],
        "etiqueta_particion": ["evaluacion"] * 3 + ["entrenamiento"],
        "kw_ti": [100, 100, 100, 100], "kw_total": [150, 135, 160, 199],
        "agua_reposicion_l": [40, 10, 50, 100],
        "ot_event": ["normal", "login_fallido", "normal", "normal"],
    })
    alertas = pd.DataFrame({
        "site_id": ["B", "A", "A"],
        "timestamp": [horas[0], horas[1], horas[0]],
        "anomalia": [True, True, False],
        "esperado_no_ti": [45, 30, 30], "esperado_agua": [40, 15, 25],
    })
    resultado = exceso_no_ti(
        datos, alertas, columna_esperado="esperado_no_ti",
        columna_esperado_agua="esperado_agua", unidad_energia="kwh_intervalo",
        horas_por_intervalo=1,
    ).set_index(["site_id", "timestamp"])
    a0, a1, b0 = resultado.loc[("A", horas[0])], resultado.loc[("A", horas[1])], resultado.loc[("B", horas[0])]
    assert len(resultado) == 3  # la referencia no se puntúa
    assert a0["residuo_no_ti_kwh"] == 20
    assert a0["exceso_no_ti_sin_alerta_kwh"] == 20
    assert a0["residuo_agua_in_situ_l"] == 15
    assert a0["exceso_agua_sin_alerta_l"] == 15
    assert a1["residuo_no_ti_kwh"] == 5
    assert a1["residuo_agua_in_situ_l"] == -5
    assert a1["exceso_agua_in_situ_estimado_l"] == 0
    assert a1["coincide_evento_ot"]
    assert b0["exceso_no_ti_con_alerta_kwh"] == 15
    assert b0["exceso_agua_con_alerta_l"] == 10
    assert not any("ahorro" in columna for columna in resultado.columns)


def test_exceso_convierte_potencia_promedio_y_recorta_residuo_negativo():
    hora = pd.Timestamp("2026-10-01T00:00:00Z")
    datos = pd.DataFrame({
        "timestamp": [hora, hora + pd.Timedelta(minutes=5)],
        "etiqueta_particion": ["evaluacion"] * 2,
        "kw_ti": [100, 100], "kw_total": [160, 120],
    })
    alertas = pd.DataFrame({
        "timestamp": datos["timestamp"], "anomalia": [False, True],
        "esperado_no_ti": [36, 30],
    })
    resultado = exceso_no_ti(datos, alertas, columna_esperado="esperado_no_ti",
                             unidad_energia="kw_promedio", horas_por_intervalo=5 / 60)
    assert resultado.loc[0, "residuo_no_ti_kwh"] == pytest.approx(2)
    assert resultado.loc[0, "exceso_no_ti_sin_alerta_kwh"] == pytest.approx(2)
    assert resultado.loc[1, "residuo_no_ti_kwh"] == pytest.approx(-10 / 12)
    assert resultado.loc[1, "exceso_no_ti_estimado_kwh"] == 0


@pytest.mark.parametrize(("cambio", "mensaje"), [
    ("duplicado", "duplicadas"),
    ("sin_prediccion", "faltan alertas"),
    ("prediccion_nan", "no finitos"),
    ("bandera_numerica", "booleanos"),
])
def test_exceso_rechaza_uniones_o_predicciones_incompletas(cambio, mensaje):
    hora = pd.Timestamp("2026-10-01T00:00:00Z")
    datos = pd.DataFrame({"site_id": ["A"], "timestamp": [hora],
                          "etiqueta_particion": ["evaluacion"],
                          "kw_ti": [100], "kw_total": [150]})
    alertas = pd.DataFrame({"site_id": ["A"], "timestamp": [hora],
                            "anomalia": [False], "esperado_no_ti": [30]})
    if cambio == "duplicado":
        alertas = pd.concat([alertas, alertas], ignore_index=True)
    elif cambio == "sin_prediccion":
        alertas = alertas.iloc[0:0]
    elif cambio == "prediccion_nan":
        alertas.loc[0, "esperado_no_ti"] = float("nan")
    else:
        alertas["anomalia"] = [1]
    with pytest.raises(ValueError, match=mensaje):
        exceso_no_ti(datos, alertas, columna_esperado="esperado_no_ti",
                     unidad_energia="kwh_intervalo", horas_por_intervalo=1)


def test_reglas_en_cinco_minutos_usan_kwh_ti_para_wue():
    datos = pd.DataFrame({
        "timestamp": [pd.Timestamp("2026-10-01T00:00:00Z")],
        "kw_ti": [120], "kw_total": [150],
        "agua_reposicion_l": [12.5], "inlet_temp_c": [29], "ot_event": ["normal"],
    })
    resultado = reglas_fijas(datos, unidad_energia="kw_promedio",
                             horas_por_intervalo=5 / 60)
    assert not resultado.loc[0, "anomalia"]  # 12.5 L / 10 kWh = 1.25
    datos.loc[0, "agua_reposicion_l"] = 15.01
    resultado = reglas_fijas(datos, unidad_energia="kw_promedio",
                             horas_por_intervalo=5 / 60)
    assert resultado.loc[0, "motivo_regla"] == "agua"


def test_etiquetas_contiguas_distintas_son_episodios_distintos():
    horas = pd.date_range("2026-10-01", periods=4, freq="h", tz="UTC")
    datos = pd.DataFrame({
        "timestamp": horas, "etiqueta_particion": ["evaluacion"] * 4,
        "etiqueta_escenario": ["ineficiencia", "ineficiencia", "fuga_agua", "base"],
    })
    episodios = episodios_desde_etiquetas(datos, horas_por_intervalo=1)
    assert list(episodios["nombre"]) == ["ineficiencia", "fuga_agua"]
    assert episodios.loc[0, "fin"] == horas[1]
    assert episodios.loc[1, "inicio"] == horas[2]


def test_varias_alertas_en_episodio_cuentan_un_tp_y_primera_latencia():
    horas = pd.date_range("2026-10-01", periods=4, freq="h", tz="UTC")
    datos = pd.DataFrame({"timestamp": horas, "etiqueta_particion": ["evaluacion"] * 4})
    alertas = datos[["timestamp"]].assign(anomalia=[False, True, True, True])
    ventanas = pd.DataFrame({"inicio": [horas[0]], "fin": [horas[3]]})
    episodios, resumen = evaluar_episodios(datos, alertas, ventanas, horas_por_intervalo=1)
    assert (resumen["tp"], resumen["fp"], resumen["fn"]) == (1, 0, 0)
    assert episodios.loc[0, "horas_hasta_detectar"] == 1
    assert resumen["falsas_alarmas_por_dia_sitio"] is None  # no hay horas limpias
    alertas.loc[0, "anomalia"] = True
    episodios, _ = evaluar_episodios(datos, alertas, ventanas, horas_por_intervalo=1)
    assert episodios.loc[0, "horas_hasta_detectar"] == 0


def test_falsas_alarmas_son_tramos_limpios_por_sitio_y_ignoran_referencia():
    horas = pd.date_range("2026-10-01", periods=5, freq="h", tz="UTC")
    datos = pd.DataFrame({
        "site_id": ["A"] * 5 + ["B"] * 5,
        "timestamp": list(horas) * 2,
        "etiqueta_particion": ["entrenamiento"] + ["evaluacion"] * 4
                              + ["entrenamiento"] + ["evaluacion"] * 4,
    })
    alertas = datos[["site_id", "timestamp"]].copy()
    alertas["anomalia"] = [True, True, True, False, True] + [True, True, False, False, False]
    ventanas = pd.DataFrame(columns=["site_id", "inicio", "fin"])
    _, resumen = evaluar_episodios(datos, alertas, ventanas, horas_por_intervalo=1)
    assert (resumen["tp"], resumen["fp"], resumen["fn"]) == (0, 3, 0)
    assert resumen["horas_evaluacion_sitio"] == 8
    assert resumen["horas_limpias_sitio"] == 8
    assert resumen["precision"] == 0
    assert resumen["recall"] is None
    assert resumen["falsas_alarmas_por_dia_sitio"] == 9


def test_sin_episodios_ni_alertas_define_metricas_sin_denominador():
    horas = pd.date_range("2026-10-01", periods=3, freq="h", tz="UTC")
    datos = pd.DataFrame({"timestamp": horas, "etiqueta_particion": ["evaluacion"] * 3})
    alertas = datos[["timestamp"]].assign(anomalia=False)
    episodios, resumen = evaluar_episodios(datos, alertas, pd.DataFrame(columns=["inicio", "fin"]),
                                           horas_por_intervalo=1)
    assert episodios.empty
    assert (resumen["tp"], resumen["fp"], resumen["fn"]) == (0, 0, 0)
    assert resumen["precision"] is None and resumen["recall"] is None
    assert resumen["falsas_alarmas_por_dia_sitio"] == 0
    inferior, superior = resumen["ic_falsas_alarmas_por_dia_sitio"]
    assert inferior == 0 and superior > 0


def test_evaluacion_rechaza_huecos_limpios_y_alertas_faltantes():
    horas = pd.date_range("2026-10-01", periods=3, freq="h", tz="UTC")
    datos = pd.DataFrame({"timestamp": horas,
                          "etiqueta_particion": ["evaluacion"] * 3})
    alertas = datos[["timestamp"]].assign(anomalia=False)
    sin_ventanas = pd.DataFrame(columns=["inicio", "fin"])
    with pytest.raises(ValueError, match="horas incompletas"):
        evaluar_episodios(datos.drop(index=1), alertas, sin_ventanas, horas_por_intervalo=1)
    with pytest.raises(ValueError, match="faltan alertas"):
        evaluar_episodios(datos, alertas.drop(index=1), sin_ventanas, horas_por_intervalo=1)


def test_ventanas_adyacentes_sin_solapamiento_son_dos_episodios():
    horas = pd.date_range("2026-10-01", periods=4, freq="h", tz="UTC")
    datos = pd.DataFrame({"timestamp": horas, "etiqueta_particion": ["evaluacion"] * 4})
    alertas = datos[["timestamp"]].assign(anomalia=[False, True, True, False])
    ventanas = pd.DataFrame({"inicio": [horas[0], horas[2]],
                             "fin": [horas[1], horas[3]]})
    episodios, resumen = evaluar_episodios(datos, alertas, ventanas, horas_por_intervalo=1)
    assert len(episodios) == 2
    assert resumen["tp"] == 2 and resumen["fp"] == 0
    assert list(episodios["horas_hasta_detectar"]) == [1, 0]


def test_evaluacion_rechaza_sitio_desconocido_duplicados_y_banderas_numericas():
    horas = pd.date_range("2026-10-01", periods=2, freq="h", tz="UTC")
    datos = pd.DataFrame({"site_id": ["A"] * 2, "timestamp": horas,
                          "etiqueta_particion": ["evaluacion"] * 2})
    alertas = datos[["site_id", "timestamp"]].assign(anomalia=False)
    ventanas = pd.DataFrame({"site_id": ["B"],
                             "inicio": [horas[0]], "fin": [horas[1]]})
    with pytest.raises(ValueError, match="sitios ausentes"):
        evaluar_episodios(datos, alertas, ventanas, horas_por_intervalo=1)
    sin_ventanas = ventanas.iloc[0:0]
    with pytest.raises(ValueError, match="duplicadas"):
        evaluar_episodios(datos, pd.concat([alertas, alertas.iloc[[0]]]),
                          sin_ventanas, horas_por_intervalo=1)
    alertas["anomalia"] = [0, 1]
    with pytest.raises(ValueError, match="booleana"):
        evaluar_episodios(datos, alertas, sin_ventanas, horas_por_intervalo=1)


def test_exceso_de_agua_requiere_medidor_y_prediccion():
    hora = pd.Timestamp("2026-10-01T00:00:00Z")
    datos = pd.DataFrame({"timestamp": [hora], "etiqueta_particion": ["evaluacion"],
                          "kw_ti": [100], "kw_total": [150]})
    alertas = pd.DataFrame({"timestamp": [hora], "anomalia": [False],
                            "esperado_no_ti": [30]})
    argumentos = {"columna_esperado": "esperado_no_ti",
                  "columna_esperado_agua": "esperado_agua",
                  "unidad_energia": "kwh_intervalo", "horas_por_intervalo": 1}
    with pytest.raises(ValueError, match="agua_reposicion_l"):
        exceso_no_ti(datos, alertas, **argumentos)
    datos["agua_reposicion_l"] = 20
    with pytest.raises(ValueError, match="esperado_agua"):
        exceso_no_ti(datos, alertas, **argumentos)
