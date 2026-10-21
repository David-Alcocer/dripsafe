"""Rejilla de inyecciones (src/ataques/rejilla.py, U1) y su corrida (correr_rejilla.py, U2).

Se usa app.kit.ejemplo(): datos INVENTADOS con el formato del kit. El kit real
nunca entra a las pruebas ni al repositorio.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app import kit
from src import contrato
from src.ataques import correr_rejilla, rejilla
from src.datos.cargar import cargar
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[1]
MAPEO = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
FISICAS = ["kw_ti", "kw_total", "agua_reposicion_l", "t_exterior", "inlet_temp_c", "load_pct"]


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("kit") / "ejemplo.csv"
    kit.ejemplo().to_csv(ruta, index=False)
    return rejilla._preparar(cargar(ruta, MAPEO))


@pytest.fixture(scope="module")
def copias(base):
    return list(rejilla.generar(base))


def _inyectadas(copias):
    return [(c, f) for c, f in copias if c is not None]


# ------------------------------------------------------------------ la rejilla


def test_la_rejilla_es_la_que_fijo_la_propuesta():
    # Propuesta v7 §4. Si alguien la cambia después de ver resultados, esta prueba lo delata.
    resumen = [(i.nombre, i.variable, i.magnitud_pct, i.horas, i.evento_ot, i.retraso_h, i.clase_esperada)
               for i in rejilla.REJILLA]
    assert resumen == [
        ("energia_+10", "energia", 10, 4, "", 0, "escalon_sin_registro"),
        ("energia_+20", "energia", 20, 4, "", 0, "escalon_sin_registro"),
        ("energia_+40", "energia", 40, 4, "", 0, "escalon_sin_registro"),
        ("energia_+80", "energia", 80, 4, "", 0, "escalon_sin_registro"),
        ("agua_+25", "agua", 25, 4, "", 0, "escalon_sin_registro"),
        ("agua_+50", "agua", 50, 4, "", 0, "escalon_sin_registro"),
        ("cambio_sin_registro", "energia", 20, 12, "", 0, "escalon_sin_registro"),
        ("cambio_con_efecto", "energia", 20, 12, "cambio_config_no_autorizado", 8, "incidente_ot"),
    ]
    assert rejilla.INICIOS_H == (6, 18, 30, 42, 54, 66)


def test_cada_copia_cumple_el_contrato_y_no_modifica_la_base(base, copias):
    original = base.copy()
    for copia, _ in _inyectadas(copias)[:10]:
        assert contrato.validar(copia) == []
    pd.testing.assert_frame_equal(base, original)


def test_ajuste_y_calibracion_quedan_intactos(base, copias):
    referencia = base["etiqueta_particion"] != "evaluacion"
    for copia, _ in _inyectadas(copias):
        pd.testing.assert_frame_equal(copia.loc[referencia, FISICAS + ["ot_event"]],
                                      base.loc[referencia, FISICAS + ["ot_event"]])


def test_fuera_del_episodio_nada_cambia(base, copias):
    for copia, f in _inyectadas(copias):
        fuera = ~((copia["site_id"] == f["site_id"]) & copia["timestamp"].between(f["inicio"], f["fin"]))
        pd.testing.assert_frame_equal(copia.loc[fuera, FISICAS + ["ot_event"]],
                                      base.loc[fuera, FISICAS + ["ot_event"]])


def test_la_magnitud_es_exacta_y_solo_en_las_horas_del_efecto(base, copias):
    for copia, f in _inyectadas(copias):
        sitio = copia["site_id"] == f["site_id"]
        efecto = sitio & copia["timestamp"].isin(f["_delta_por_hora"].index)
        assert int(efecto.sum()) == f["horas"]
        assert (copia.loc[efecto, "timestamp"].min() - f["inicio"]) == pd.Timedelta(hours=f["retraso_h"])
        factor = 1 + f["magnitud_pct"] / 100
        if f["variable"] == "energia":
            antes = base.loc[efecto, "kw_total"] - base.loc[efecto, "kw_ti"]
            despues = copia.loc[efecto, "kw_total"] - copia.loc[efecto, "kw_ti"]
            np.testing.assert_allclose(despues, antes * factor)
            np.testing.assert_allclose(copia.loc[efecto, "agua_reposicion_l"], base.loc[efecto, "agua_reposicion_l"])
            assert f["energia_inyectada_kwh"] == pytest.approx(float((despues - antes).sum()))
        else:
            np.testing.assert_allclose(copia.loc[efecto, "agua_reposicion_l"],
                                       base.loc[efecto, "agua_reposicion_l"] * factor)
            np.testing.assert_allclose(copia.loc[efecto, "kw_total"], base.loc[efecto, "kw_total"])
        np.testing.assert_allclose(copia["kw_ti"], base["kw_ti"])


def test_el_cambio_con_efecto_registra_el_evento_y_espera_8_h(base, copias):
    con_efecto = [(c, f) for c, f in _inyectadas(copias) if f["nombre"] == "cambio_con_efecto"]
    assert con_efecto
    for copia, f in con_efecto:
        sitio = copia["site_id"] == f["site_id"]
        evento = copia.loc[sitio & (copia["ot_event"] != base["ot_event"])]
        assert list(evento["timestamp"]) == [f["inicio"]]
        assert set(evento["ot_event"]) == {"cambio_config_no_autorizado"}
        espera = sitio & (copia["timestamp"] >= f["inicio"]) & (copia["timestamp"] < f["inicio_efecto"])
        np.testing.assert_allclose(copia.loc[espera, "kw_total"], base.loc[espera, "kw_total"])


def test_el_episodio_queda_etiquetado(copias):
    for copia, f in _inyectadas(copias):
        ep = (copia["site_id"] == f["site_id"]) & copia["timestamp"].between(f["inicio"], f["fin"])
        assert set(copia.loc[ep, "etiqueta_escenario"]) == {f["nombre"]}
        assert set(copia.loc[ep, "etiqueta_tipo"]) == {f["tipo"]}
        assert set(copia.loc[ep, "etiqueta_particion"]) == {"evaluacion"}


def test_el_detector_no_ve_las_etiquetas_de_la_inyeccion(copias):
    copia, _ = next((c, f) for c, f in _inyectadas(copias) if f["nombre"] == "cambio_con_efecto")
    borrada = copia.assign(etiqueta_escenario="", etiqueta_tipo="normal", etiqueta_tecnica="")
    pd.testing.assert_frame_equal(detector.detectar(copia), detector.detectar(borrada))


def test_el_detector_aprende_lo_mismo_en_todas_las_copias(base, copias):
    parametros = detector.entrenar(base)
    for copia, _ in _inyectadas(copias)[::12]:
        assert correr_rejilla._mismos_parametros(parametros, detector.entrenar(copia))


def test_lugares_limpios_distintos_y_lejos_del_ot_del_kit(base, copias):
    fichas = pd.DataFrame([f for c, f in _inyectadas(copias)])
    assert not fichas.duplicated(["site_id", "nombre", "inicio"]).any()
    for _, f in fichas.iterrows():
        s = base[base["site_id"] == f["site_id"]]
        zona = s["timestamp"].between(f["inicio"] - pd.Timedelta(hours=rejilla.MARGEN_H),
                                      f["fin"] + pd.Timedelta(hours=rejilla.MARGEN_H))
        assert (s.loc[zona, "etiqueta_escenario"] == "").all()
        previas = s["timestamp"].between(f["inicio"] - pd.Timedelta(hours=rejilla.SIN_OT_PREVIO_H), f["fin"])
        assert (s.loc[previas, "ot_event"] == "normal").all()


def test_la_rejilla_es_reproducible(base, copias):
    otra = [f for c, f in rejilla.generar(base) if c is not None]
    assert [(f["site_id"], f["nombre"], f["inicio"]) for f in otra] == \
           [(f["site_id"], f["nombre"], f["inicio"]) for c, f in _inyectadas(copias)]


def test_omitidas_traen_motivo(copias):
    for copia, f in copias:
        if copia is None:
            assert f["omitida"]


# -------------------------------------------------------------------- ruido


def test_el_ruido_es_reproducible_y_respeta_la_fisica(base):
    a, b = rejilla.con_ruido(base, 1), rejilla.con_ruido(base, 1)
    pd.testing.assert_frame_equal(a, b)
    assert (a["kw_total"] >= a["kw_ti"]).all() and (a["agua_reposicion_l"] >= 0).all()
    # Cambia todas las particiones (sensores peores siempre), no solo la evaluación.
    for particion in ("entrenamiento", "evaluacion"):
        m = base["etiqueta_particion"] == particion
        assert not np.allclose(a.loc[m, "kw_total"], base.loc[m, "kw_total"])
    assert not np.allclose(rejilla.con_ruido(base, 2)["kw_total"], a["kw_total"])


# ------------------------------------------------------------- la corrida (U2)


@pytest.fixture(scope="module")
def corrida(base):
    seleccion = [rejilla.POR_NOMBRE["energia_+80"], rejilla.POR_NOMBRE["cambio_con_efecto"],
                 rejilla.POR_NOMBRE["agua_+50"]]
    return correr_rejilla.correr(base, semillas_ruido=(), rejilla_=seleccion, inicios_h=(6, 30))


def test_corrida_una_fila_por_inyeccion_y_metodo(corrida):
    por_inyeccion, limpia, coincidencias, manifiesto = corrida
    n = len(manifiesto["corridas"][0]["inyecciones"])
    assert n > 0 and len(por_inyeccion) == 2 * n
    assert set(por_inyeccion["metodo"]) == {"dripsafe", "reglas_kit"}
    assert set(limpia["metodo"]) == {"dripsafe", "reglas_kit"}
    assert "TOTAL" in set(coincidencias["site_id"])


def test_corrida_dripsafe_ve_el_80_pct_y_clasifica_el_cambio(corrida):
    t = corrida[0]
    ds = t[t["metodo"] == "dripsafe"]
    assert ds.loc[ds["nombre"] == "energia_+80", "efecto_visto"].all()
    con_efecto = ds[ds["nombre"] == "cambio_con_efecto"]
    assert con_efecto["detectado"].all()
    assert set(con_efecto["clase_obtenida"]) == {"incidente_ot"}


def test_corrida_las_reglas_ven_el_evento_pero_no_el_efecto_en_el_sitio_liquido(corrida):
    t = corrida[0]
    reglas = t[(t["metodo"] == "reglas_kit") & (t["nombre"] == "cambio_con_efecto") & (t["site_id"] == "SIM-C")]
    assert len(reglas)
    assert reglas["detectado"].all()          # la regla de OT dispara en la hora del evento
    assert not reglas["efecto_visto"].any()   # pero +20 % no sube el PUE de 1.2 arriba de 1.6
    assert (reglas["no_visto_kwh"] == reglas["inyectado_kwh"]).all()


def test_corrida_lo_no_visto_nunca_supera_lo_inyectado(corrida):
    t = corrida[0]
    for unidad in ("kwh", "l"):
        par = t[[f"inyectado_{unidad}", f"no_visto_{unidad}"]].dropna()
        assert (par[f"no_visto_{unidad}"] <= par[f"inyectado_{unidad}"] + 1e-9).all()


def test_resumen_por_magnitud(corrida):
    resumen = correr_rejilla.resumir(corrida[0])
    assert {"pct_efectos_vistos", "pct_no_visto", "mediana_horas_ver_efecto"} <= set(resumen.columns)
    fila = resumen[(resumen["nombre"] == "energia_+80") & (resumen["metodo"] == "dripsafe")].iloc[0]
    assert fila["pct_efectos_vistos"] == 100.0
    assert fila["unidad"] == "kWh"


def test_bloque_para_numeros_oficiales(corrida):
    por_inyeccion, limpia, coincidencias, _ = corrida
    bloque = correr_rejilla.bloque_deteccion(por_inyeccion, limpia, coincidencias, "ejemplo")
    d = bloque["deteccion"]
    assert bloque["_meta"]["aviso"].startswith("DATOS SIMULADOS")
    assert d["comparacion_contra_reglas_kit"]["episodios_originales_kit"]["dripsafe_tp"] == 3
    assert d["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"]
    assert set(d["clases_ot_conteo"]) >= {"incidente_ot", "cambio_no_autorizado", "escalon_sin_registro", "intento_acceso"}
    assert [v["ventana_h"] for v in d["coincidencias_al_azar"]["ventanas"]] == [1, 4, 8, 12, 24]
    json.dumps(bloque)  # se puede guardar tal cual
