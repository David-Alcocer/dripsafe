"""Tabla de decisión de las 4 clases OT (src/ot/clases.py · D16 · U1 · #30).

Cada prueba es una fila de la tabla de docs/06-ciberseguridad-ot.md §4: entra una
historia por hora (excesos y registro OT) y sale la clase que debe tener. No usan
el kit ni el detector: las banderas de exceso se escriben a mano.
"""

import pandas as pd
import pytest

from src.ot import clases

INICIO = pd.Timestamp("2026-10-15 00:00", tz="UTC")


def _historia(horas=48, umbral=(), media=(), agua=(), ot=None, sitio="SIM-C"):
    """Una fila por hora. `umbral`, `media` y `agua` son las horas con esa bandera."""
    t = pd.date_range(INICIO, periods=horas, freq="h")
    df = pd.DataFrame({
        "timestamp": t,
        "site_id": sitio,
        "alerta_umbral": [h in set(umbral) for h in range(horas)],
        "alerta_media_4h": [h in set(media) for h in range(horas)],
        "exceso_agua": [h in set(agua) for h in range(horas)],
        "ot_event": "normal",
    })
    for h, evento in (ot or {}).items():
        df.loc[h, "ot_event"] = evento
    return df


def _clases(df, **kw):
    return clases.clasificar(df, **kw)


def _set(salida, horas):
    return set(salida.loc[list(horas), "clase"])


# ------------------------------------------------------------ casos básicos


def test_sin_eventos_ni_excesos_todo_es_normal():
    salida = _clases(_historia())
    assert (salida["clase"] == "normal").all()
    assert (salida["prioridad"] == "").all()
    assert (salida["accion"] == "").all()


def test_exceso_sin_evento_es_escalon_y_manda_a_revisar_configuracion():
    salida = _clases(_historia(umbral=range(10, 14)))
    assert _set(salida, range(10, 14)) == {"escalon_sin_registro"}
    assert set(salida.loc[10:13, "prioridad"]) == {"alta"}
    assert set(salida.loc[10:13, "forma"]) == {"escalon"}
    # Regla de oro 1: primero la configuración, nunca mantenimiento directo.
    accion = salida.loc[10, "accion"]
    assert accion.index("setpoints") < accion.index("mantenimiento")


def test_exceso_de_agua_sin_evento_pide_inspeccion_fisica():
    salida = _clases(_historia(umbral=range(10, 14), agua=range(10, 14)))
    assert _set(salida, range(10, 14)) == {"escalon_sin_registro"}
    assert "inspección física" in salida.loc[10, "accion"]
    # Si el exceso no es de agua, no se manda a nadie a buscar una fuga.
    sin_agua = _clases(_historia(umbral=range(10, 14)))
    assert "inspección física" not in sin_agua.loc[10, "accion"]


def test_exceso_gradual_solo_por_media_movil_es_escalon_con_forma_gradual():
    salida = _clases(_historia(media=range(10, 16)))
    assert _set(salida, range(10, 16)) == {"escalon_sin_registro"}
    assert set(salida.loc[10:15, "forma"]) == {"gradual"}


def test_login_fallido_sin_exceso_es_intento_de_acceso():
    salida = _clases(_historia(ot={5: "login_fallido", 6: "login_fallido"}))
    assert _set(salida, [5, 6]) == {"intento_acceso"}
    assert set(salida.loc[[5, 6], "prioridad"]) == {"media"}
    assert "no prueba una intrusión" in salida.loc[5, "accion"]


def test_cambio_sin_efecto_es_cambio_no_autorizado_con_prioridad_alta():
    # Regla de oro 2: un cambio no autorizado nunca es «sin urgencia».
    salida = _clases(_historia(ot={4: "cambio_config_no_autorizado"}))
    assert salida.loc[4, "clase"] == "cambio_no_autorizado"
    assert salida.loc[4, "prioridad"] == "alta"
    assert (salida.drop(index=4)["clase"] == "normal").all()


# ------------------------------------------------------ evento con efecto


def test_cambio_con_exceso_8_h_despues_es_incidente_en_ambos():
    salida = _clases(_historia(umbral=range(12, 16), ot={4: "cambio_config_no_autorizado"}))
    assert _set(salida, range(12, 16)) == {"incidente_ot"}
    assert salida.loc[4, "clase"] == "incidente_ot"
    assert set(salida.loc[12:15, "causalidad"]) == {"causal"}
    assert (salida.loc[12:15, "evento_ot_inicio"] == INICIO + pd.Timedelta(hours=4)).all()
    assert "8 h después" in salida.loc[12, "nota_ot"]
    assert set(salida.loc[[4, 12], "prioridad"]) == {"maxima"}


def test_la_ventana_es_de_24_h_despues_de_la_ultima_hora_del_evento():
    # Evento a las 04:00: cuenta un exceso que empieza a las 04:00 del día siguiente…
    dentro = _clases(_historia(umbral=[28, 29], ot={4: "cambio_config_no_autorizado"}))
    assert _set(dentro, [28, 29]) == {"incidente_ot"}
    # …pero no uno que empieza una hora más tarde.
    fuera = _clases(_historia(umbral=[29, 30], ot={4: "cambio_config_no_autorizado"}))
    assert _set(fuera, [29, 30]) == {"escalon_sin_registro"}
    assert fuera.loc[4, "clase"] == "cambio_no_autorizado"


def test_ventana_configurable_para_el_analisis_de_sensibilidad():
    salida = _clases(_historia(umbral=[12], ot={4: "cambio_config_no_autorizado"}), ventana_h=4)
    assert salida.loc[12, "clase"] == "escalon_sin_registro"


def test_exceso_que_empieza_en_la_hora_del_evento_es_incidente():
    salida = _clases(_historia(umbral=[4, 5, 6], ot={4: "cambio_config_no_autorizado"}))
    assert _set(salida, [4, 5, 6]) == {"incidente_ot"}


def test_login_fallido_seguido_de_exceso_es_incidente():
    # El login pudo ser el paso previo de un acceso que sí funcionó y no dejó evento.
    salida = _clases(_historia(umbral=range(11, 14), ot={5: "login_fallido"}))
    assert _set(salida, range(11, 14)) == {"incidente_ot"}
    assert "login fallido" in salida.loc[11, "nota_ot"]
    # El login en sí sigue siendo un intento: no hubo exceso en esa hora.
    assert salida.loc[5, "clase"] == "intento_acceso"


def test_logins_y_cambio_seguidos_sin_efecto_como_en_sim_c():
    ot = {20: "login_fallido", 21: "login_fallido", 22: "login_fallido",
          23: "cambio_config_no_autorizado", 24: "cambio_config_no_autorizado"}
    salida = _clases(_historia(ot=ot))
    assert _set(salida, [20, 21, 22]) == {"intento_acceso"}
    assert _set(salida, [23, 24]) == {"cambio_no_autorizado"}


def test_con_login_y_cambio_previos_el_efecto_se_atribuye_al_cambio():
    ot = {2: "login_fallido", 8: "cambio_config_no_autorizado"}
    salida = _clases(_historia(umbral=[14, 15], ot=ot))
    assert salida.loc[14, "evento_ot_inicio"] == INICIO + pd.Timedelta(hours=8)
    assert "cambio de configuración" in salida.loc[14, "nota_ot"]


# --------------------------------------------------- coincidencias y orden


def test_exceso_que_ya_venia_de_antes_es_coincidente_no_causal():
    salida = _clases(_historia(umbral=range(10, 20), ot={14: "cambio_config_no_autorizado"}))
    # El exceso empezó 4 h antes del cambio: no lo causó.
    assert _set(salida, [10, 11, 12, 13, 15, 16]) == {"escalon_sin_registro"}
    assert set(salida.loc[10:19, "causalidad"]) == {"coincidente_no_causal"}
    assert "no causal" in salida.loc[10, "nota_ot"]
    # Y el cambio no baja de prioridad por caer dentro de un exceso.
    assert salida.loc[14, "clase"] == "cambio_no_autorizado"


def test_un_exceso_nuevo_despues_del_coincidente_si_es_causal():
    ot = {14: "cambio_config_no_autorizado"}
    salida = _clases(_historia(umbral=[*range(10, 16), *range(20, 23)], ot=ot))
    assert salida.loc[12, "causalidad"] == "coincidente_no_causal"
    assert _set(salida, range(20, 23)) == {"incidente_ot"}


def test_un_evento_posterior_no_baja_un_incidente_en_curso():
    # Antes, un segundo cambio a la mitad de un incidente lo bajaba a «cambio no autorizado».
    ot = {2: "cambio_config_no_autorizado", 14: "cambio_config_no_autorizado"}
    salida = _clases(_historia(umbral=range(10, 20), ot=ot))
    assert _set(salida, range(10, 20)) == {"incidente_ot"}


def test_login_en_una_hora_con_exceso_previo_queda_como_escalon_y_se_anota():
    salida = _clases(_historia(umbral=range(10, 14), ot={12: "login_fallido"}))
    assert salida.loc[12, "clase"] == "escalon_sin_registro"
    assert "login fallido" in salida.loc[12, "nota_ot"]


def test_los_sitios_no_se_mezclan():
    otro = _historia(umbral=range(12, 16), sitio="SIM-A")
    con_evento = _historia(ot={4: "cambio_config_no_autorizado"}, sitio="SIM-C")
    salida = _clases(pd.concat([otro, con_evento], ignore_index=True))
    assert set(salida.loc[12:15, "clase"]) == {"escalon_sin_registro"}


def test_un_hueco_en_el_tiempo_corta_el_tramo():
    df = _historia(umbral=[10, 11, 12, 13], ot={11: "cambio_config_no_autorizado"})
    df = df.drop(index=12).reset_index(drop=True)  # falta la hora 12
    salida = _clases(df)
    # La hora 13 (ahora en la fila 12) empieza un tramo nuevo dentro de la ventana.
    assert salida.loc[12, "causalidad"] == "causal"
    assert salida.loc[10, "causalidad"] == "coincidente_no_causal"


def test_el_orden_de_las_filas_no_cambia_el_resultado():
    df = _historia(umbral=range(12, 16), ot={4: "cambio_config_no_autorizado"})
    revuelto = df.sample(frac=1, random_state=3)
    pd.testing.assert_frame_equal(_clases(df), _clases(revuelto).loc[df.index])


def test_faltan_columnas():
    with pytest.raises(ValueError, match="ot_event"):
        clases.clasificar(_historia().drop(columns="ot_event"))


# ----------------------------------------------------- textos y dashboard


def test_toda_clase_tiene_prioridad_y_accion():
    for clase in clases.CLASES:
        assert clases.PRIORIDAD[clase]
        assert clases.ACCION[clase]


def test_el_dashboard_usa_las_mismas_clases_en_el_mismo_orden():
    from app import textos

    assert list(textos.CLASES) == clases.CLASES


# ------------------------------------------------- coincidencias al azar


def test_coincidencias_al_azar_cuenta_los_eventos_que_caerian_en_la_ventana():
    # 48 h con un solo exceso que empieza en la hora 30. Con ventana de 4 h, un evento
    # al azar lo «atrapa» si cae entre las horas 26 y 30: 5 de las 44 horas posibles.
    tabla = clases.coincidencias_al_azar(_historia(umbral=[30, 31]), ventanas_h=(4,))
    fila = tabla[tabla["site_id"] == "SIM-C"].iloc[0]
    assert fila["eventos_simulados"] == 44
    assert fila["atribuciones_al_azar"] == 5
    assert fila["prob_pct"] == pytest.approx(11.4)


def test_coincidencias_al_azar_crece_con_la_ventana_y_trae_total():
    df = pd.concat([_historia(umbral=[30], sitio="SIM-A"), _historia(sitio="SIM-B")],
                   ignore_index=True)
    tabla = clases.coincidencias_al_azar(df, ventanas_h=(1, 24))
    total = tabla[tabla["site_id"] == "TOTAL"].set_index("ventana_h")
    assert total.loc[1, "prob_pct"] < total.loc[24, "prob_pct"]
    sin_excesos = tabla[(tabla["site_id"] == "SIM-B")]
    assert (sin_excesos["atribuciones_al_azar"] == 0).all()
