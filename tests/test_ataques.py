import numpy as np
import pandas as pd
import pytest

from src import contrato
from src.ataques.escenarios import CATALOGO
from src.ataques.evaluar import evaluar
from src.ataques.inyectar import inyectar
from src.sinteticos import generar

ETIQUETAS = contrato.ETIQUETAS


@pytest.fixture(scope="module")
def base():
    return generar(dias=14)


@pytest.fixture(scope="module")
def resultado(base):
    return inyectar(base)


def test_salida_cumple_el_contrato(resultado):
    out, _ = resultado
    assert contrato.validar(out) == []


def test_no_modifica_la_entrada(base):
    copia = base.copy()
    inyectar(base)
    pd.testing.assert_frame_equal(base, copia)


def test_todos_los_escenarios_caben_en_14_dias(resultado):
    _, manifiesto = resultado
    assert manifiesto["omitidos"] == []
    assert len(manifiesto["escenarios"]) == len(CATALOGO)


def test_parte_de_entrenamiento_queda_intacta(base, resultado):
    out, _ = resultado
    ent = out["etiqueta_particion"] == "entrenamiento"
    assert (out.loc[ent, "etiqueta_tipo"] == "normal").all()
    columnas = [c for c in base.columns if c != "timestamp"]
    np.testing.assert_allclose(out.loc[ent, columnas].to_numpy(float), base.loc[ent, columnas].to_numpy(float))


def test_fuera_de_las_ventanas_nada_cambia(base, resultado):
    out, _ = resultado
    normal = (out["etiqueta_tipo"] == "normal").to_numpy()
    columnas = [c for c in base.columns if c != "timestamp"]
    np.testing.assert_allclose(out.loc[normal, columnas].to_numpy(float), base.loc[normal, columnas].to_numpy(float))


def test_cada_ventana_cambia_algo_y_coincide_con_el_manifiesto(base, resultado):
    out, manifiesto = resultado
    columnas = [c for c in base.columns if c != "timestamp"]
    for v in manifiesto["escenarios"]:
        ventana = out["etiqueta_escenario"] == v["nombre"]
        assert ventana.sum() == v["filas"]
        assert str(out.loc[ventana, "timestamp"].iloc[0]) == v["inicio"]
        assert (out.loc[ventana, "etiqueta_particion"] == "evaluacion").all()
        antes = base.loc[ventana, columnas].to_numpy(float)
        despues = out.loc[ventana, columnas].to_numpy(float)
        assert not np.allclose(antes, despues, equal_nan=False), v["nombre"]


def test_las_ventanas_no_se_enciman(resultado):
    _, manifiesto = resultado
    v = manifiesto["escenarios"]
    for a, b in zip(v, v[1:]):
        assert a["fin"] < b["inicio"]


def test_el_total_sube_lo_mismo_que_los_equipos(base, resultado):
    # Física básica: si un equipo gasta más, la instalación completa gasta exactamente eso más.
    out, _ = resultado
    equipos = ["kw_chiller", "kw_bombas", "kw_torre"]
    delta_total = out["kw_total"] - base["kw_total"]
    delta_equipos = (out[equipos] - base[equipos]).sum(axis=1)
    np.testing.assert_allclose(delta_total, delta_equipos, atol=1e-6)


def test_misma_semilla_mismo_resultado(base):
    a, _ = inyectar(base, semilla=3)
    b, _ = inyectar(base, semilla=3)
    pd.testing.assert_frame_equal(a, b)


def test_escenario_sin_sus_columnas_se_omite_sin_romper(base):
    sin_setpoint = base.drop(columns=["setpoint_suministro"])
    out, manifiesto = inyectar(sin_setpoint)
    assert "setpoint_alterado" in [o["nombre"] for o in manifiesto["omitidos"]]
    assert "setpoint_alterado" not in set(out["etiqueta_escenario"])


def test_con_pocos_datos_se_quitan_primero_los_largos(base):
    _, manifiesto = inyectar(generar(dias=4))
    omitidos = [o["nombre"] for o in manifiesto["omitidos"]]
    assert "ensuciamiento" in omitidos
    assert manifiesto["escenarios"], "al menos los escenarios cortos deben caber"


def test_comandos_no_autorizados_empiezan_de_madrugada(resultado):
    out, _ = resultado
    ventana = out[out["etiqueta_escenario"] == "comandos_no_autorizados"]
    assert ventana["timestamp"].iloc[0].hour == 3


def test_entrada_que_no_cumple_el_contrato_se_rechaza(base):
    with pytest.raises(ValueError):
        inyectar(base.drop(columns=["kw_total"]))


# ------------------------------------------------------------------ evaluar

def test_evaluar_detector_perfecto_y_detector_ciego(resultado):
    out, _ = resultado
    perfecto = pd.DataFrame({"timestamp": out["timestamp"], "anomalia": out["etiqueta_tipo"] != "normal"})
    tabla, resumen = evaluar(out, perfecto)
    assert tabla["detectado"].all()
    assert (tabla["minutos_hasta_alerta"] == 0).all()
    assert (tabla["cobertura_pct"] == 100).all()
    assert resumen["falsas_alarmas"] == 0

    ciego = perfecto.assign(anomalia=False)
    tabla, resumen = evaluar(out, ciego)
    assert not tabla["detectado"].any()
    assert resumen["escenarios_detectados"] == 0


def test_evaluar_cuenta_falsas_alarmas_solo_en_horas_normales_de_evaluacion(resultado):
    out, _ = resultado
    alertas = pd.DataFrame({"timestamp": out["timestamp"], "anomalia": True})
    _, resumen = evaluar(out, alertas)
    normales_eval = ((out["etiqueta_tipo"] == "normal") & (out["etiqueta_particion"] == "evaluacion")).sum()
    assert resumen["falsas_alarmas"] == normales_eval
    assert resumen["falsas_alarmas_pct"] == 100


def test_evaluar_mide_clasificacion_falla_contra_ataque(resultado):
    out, _ = resultado
    alertas = pd.DataFrame({
        "timestamp": out["timestamp"],
        "anomalia": out["etiqueta_tipo"] != "normal",
        "tipo_sugerido": out["etiqueta_tipo"].map({"ataque": "posible_ataque", "falla": "ineficiencia"}).fillna("normal"),
    })
    tabla, _ = evaluar(out, alertas)
    assert (tabla["clasificacion_correcta_pct"] == 100).all()


def test_evaluar_funciona_con_csv_leido_de_disco(resultado, tmp_path):
    # Al pasar por CSV, los textos vacíos regresan como NaN.
    out, _ = resultado
    out.to_csv(tmp_path / "e.csv", index=False)
    alertas = pd.DataFrame({"timestamp": out["timestamp"], "anomalia": out["etiqueta_tipo"] == "ataque"})
    alertas.to_csv(tmp_path / "a.csv", index=False)
    tabla, _ = evaluar(contrato.leer(tmp_path / "e.csv"), contrato.leer(tmp_path / "a.csv"))
    assert tabla.loc[tabla["tipo"] == "falla", "tecnica"].eq("").all()
    assert tabla.loc[tabla["tipo"] == "ataque", "detectado"].all()
