"""Pruebas de la lógica del dashboard (sin Streamlit).

Usan solo `kit.ejemplo()`: datos inventados con el formato del kit. El CSV real del kit
nunca entra a las pruebas ni al repo.
"""

import json

import pandas as pd
import pytest

from app import calculos, cargar, kit, linea_base
from app.textos import CLASES, TIPOS_CIFRA


@pytest.fixture
def datos():
    return kit.ejemplo()


@pytest.fixture
def tabla(datos):
    return cargar.unir(datos, linea_base.detectar(datos))


@pytest.fixture
def sin_kit(monkeypatch, tmp_path):
    """Hace que cargar() no encuentre el kit aunque esté en esta laptop."""
    monkeypatch.setenv("DRIPSAFE_KIT", str(tmp_path))


def test_ejemplo_tiene_formato_del_kit(datos):
    assert list(datos.columns) == kit.COLUMNAS
    assert len(datos) == 3 * 168
    assert set(datos["split"]) == {"referencia", "evaluacion"}
    assert not datos.duplicated(["timestamp", "site_id"]).any()


def test_reglas_del_kit_explican_cada_alerta(datos):
    t = kit.reglas(datos)
    assert (t.loc[t["alerta"], "motivo"] != "").all()
    assert (t.loc[~t["alerta"], "motivo"] == "").all()


def test_pue_con_sumas_no_promedio_de_ratios():
    df = pd.DataFrame({"energy_it_kwh": [100.0, 300.0], "energy_total_kwh": [200.0, 330.0], "water_l": [0.0, 40.0]})
    m = calculos.metricas(df)
    assert m["pue"] == pytest.approx(530 / 400)        # no (2.0 + 1.1) / 2
    assert m["wue"] == pytest.approx(40 / 400)


def test_metricas_sin_filas_no_son_cero():
    vacio = pd.DataFrame({"energy_it_kwh": [], "energy_total_kwh": [], "water_l": []})
    assert calculos.metricas(vacio)["pue"] is None


# ------------------------------------------------------------ vista previa del detector

def test_linea_base_no_usa_etiquetas(datos):
    """Cambiar las etiquetas del kit no cambia nada de lo que detecta."""
    otro = datos.assign(scenario="base", simulated_anomaly=0)
    pd.testing.assert_frame_equal(linea_base.detectar(datos), linea_base.detectar(otro))


def test_linea_base_aprende_lo_normal(tabla):
    ref = tabla[tabla["split"] == "referencia"]
    assert not ref["alerta"].any()  # en las horas con que aprendió, nada es raro
    assert ref["residuo_energia_pct"].abs().median() < 10  # el ejemplo tiene ruido de ~5–10 %


def test_detecta_los_tres_escenarios_con_su_clase(tabla):
    ev = tabla[tabla["split"] == "evaluacion"]
    clase = ev.groupby("scenario")["clase"].agg(lambda c: set(c) - {"normal"})
    assert clase["ineficiencia"] == {"escalon_sin_registro"}
    assert clase["fuga_agua"] == {"escalon_sin_registro"}
    assert clase["evento_ot"] == {"intento_acceso", "cambio_no_autorizado"}  # sin efecto físico


def test_cambio_con_efecto_es_incidente(datos):
    """Si después del cambio de configuración sube la energía, la clase pasa a incidente."""
    d = datos.copy()
    c = d.index[(d["site_id"] == "SIM-C") & (d["ot_event"] == "cambio_config_no_autorizado")]
    despues = d.index[(d["site_id"] == "SIM-C") & (d["timestamp"] > d.loc[c[-1], "timestamp"])][2:6]
    d.loc[despues, "energy_total_kwh"] += (d.loc[despues, "energy_total_kwh"] - d.loc[despues, "energy_it_kwh"]) * 0.6
    det = linea_base.detectar(d)
    assert (det.loc[det["timestamp"].isin(d.loc[despues, "timestamp"]) & (det["site_id"] == "SIM-C"), "clase"]
            == "incidente_ot").all()


def test_exceso_antes_del_evento_no_es_causal(datos):
    """Un exceso que ya venía de antes del evento OT se queda como escalón (coincidente, no causal)."""
    d = datos.copy()
    sim_c = d.index[d["site_id"] == "SIM-C"]
    login = d.index[(d["site_id"] == "SIM-C") & (d["ot_event"] == "login_fallido")][0]
    antes = [i for i in sim_c if 0 < (d.loc[login, "timestamp"] - d.loc[i, "timestamp"]).total_seconds() / 3600 <= 3]
    d.loc[antes, "energy_total_kwh"] += (d.loc[antes, "energy_total_kwh"] - d.loc[antes, "energy_it_kwh"]) * 0.8
    det = linea_base.detectar(d)
    assert (det.loc[det["timestamp"].isin(d.loc[antes, "timestamp"]) & (det["site_id"] == "SIM-C"), "clase"]
            == "escalon_sin_registro").all()


def test_clima_no_visto_no_apaga_alertas(datos):
    """Fuera del rango de temperatura aprendido, un exceso grande sigue alertando, con «confianza baja»."""
    d = datos.copy()
    i = d.index[(d["site_id"] == "SIM-A") & (d["split"] == "evaluacion")][30]
    d.loc[i, "outdoor_temp_c"] = 45.0
    d.loc[i, "energy_total_kwh"] = d.loc[i, "energy_it_kwh"] * 2.5
    fila = linea_base.detectar(d).set_index(["timestamp", "site_id"]).loc[(d.loc[i, "timestamp"], "SIM-A")]
    assert fila["clima_no_visto"] and fila["clase"] != "normal"
    assert "confianza baja" in fila["motivo"]


# ------------------------------------------------------------ eventos, evaluación y balance

def test_eventos_tienen_clase_y_motivo(tabla):
    ev = calculos.eventos(tabla)
    assert set(ev["clase"]) <= set(CLASES)
    assert (ev["motivo"] != "").all()
    assert ev.loc[ev["sitio"] == "SIM-B", "exceso_l"].max() > 0  # la fuga se mide en litros


def test_evaluacion_solo_en_horas_de_evaluacion(tabla):
    det, resumen = calculos.evaluacion(tabla)
    assert resumen["escenarios_totales"] == 3
    assert resumen["tp"] + resumen["fn"] == int(
        ((tabla["split"] == "evaluacion") & (tabla["simulated_anomaly"] == 1)).sum())


def test_exceso_es_cota_que_no_empeora_el_pue(tabla):
    e = calculos.exceso(tabla[tabla["split"] == "evaluacion"])
    assert e["kwh"] > 0 and e["litros"] > 0
    assert e["pue_sin_exceso"] <= e["pue"]


def test_consumo_y_equilibrio_del_detector():
    c = calculos.consumo_detector(segundos_por_corrida=1.0, watts=36.0, g_co2e_por_kwh=500, corridas_por_anio=1000)
    assert c["kwh_corrida"] == pytest.approx(1e-5)
    assert c["kwh_anio"] == pytest.approx(0.01)
    assert c["kg_co2e_anio"] == pytest.approx(0.005)
    assert calculos.equilibrio(0.01, 20.0) == pytest.approx(0.0005)  # horas
    assert calculos.equilibrio(0.01, None) is None


def test_escenario_anual_es_editable_y_no_negativo():
    e = calculos.escenario_anual(fallas=6, exceso_pct=20, horas_sin=72, horas_con=4, no_ti_kwh_hora=50, agua_l_hora=100)
    assert e["horas_evitadas"] == 6 * 68
    assert e["kwh"] == pytest.approx(6 * 68 * 50 * 0.2)
    assert calculos.escenario_anual(6, 20, 4, 72, 50)["kwh"] == 0  # si DripSafe tardara más, no hay ahorro


# ------------------------------------------------------------ cifras y fuentes

def test_ejemplo_de_numeros_es_ficticio_y_completo():
    n = json.loads(cargar.RUTAS["ejemplo"].read_text(encoding="utf-8"))
    assert n["_ejemplo"] is True
    for clave, dato in n.items():
        if isinstance(dato, dict) and "tipo" in dato:
            assert dato["tipo"] in TIPOS_CIFRA, clave
    assert cargar.tipo_cifra(n, "pue_antes", ejemplo=True) == "ejemplo"
    assert cargar.tipo_cifra(n, "pue_antes", ejemplo=False) == "observado"


def test_cargar_sin_kit_usa_ejemplo_y_vista_previa(sin_kit):
    d = cargar.cargar()
    assert d.fuentes == {"telemetria": "ejemplo", "detector": "vista_previa", "numeros": "ejemplo"} or \
        d.fuentes["numeros"] == "oficial"
    assert d.cifras_de_ejemplo == (d.fuentes["numeros"] != "oficial")
    assert len(d.eventos) >= 3


def test_cifra_derivada_hereda_la_etiqueta_mas_debil():
    assert cargar.mas_debil("estimado", "ejemplo") == "ejemplo"
    assert cargar.mas_debil("medido", "vista_previa") == "vista_previa"
    assert cargar.mas_debil("observado", "estimado") == "estimado"


def test_alertas_con_otro_formato_avisan_y_no_se_ignoran(sin_kit, monkeypatch, tmp_path):
    """Si alertas.csv tiene el contrato 3 anterior, la app avisa en pantalla y usa la vista previa."""
    viejo = tmp_path / "alertas.csv"
    pd.DataFrame({"timestamp": ["2026-10-12T00:00:00Z"], "score": [0.1], "anomalia": [False],
                  "tipo_sugerido": ["normal"], "kw_esperado_enfriamiento": [10.0]}).to_csv(viejo, index=False)
    monkeypatch.setitem(cargar.RUTAS, "alertas", viejo)
    d = cargar.cargar()
    assert d.fuentes["detector"] == "vista_previa"
    assert d.avisos and "site_id" in d.avisos[0]
