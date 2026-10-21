"""Fijación de N2 con telemetría inventada; el CSV de CIFOX nunca entra a tests."""

import hashlib
import json
import subprocess

import pytest

from src.evaluacion import congelar_n2
from src.sinteticos import generar


def _telemetria_sintetica():
    datos = generar(dias=7, minutos=60)
    datos["site_id"] = "SIM-PRUEBA"
    datos["inlet_temp_c"] = 23 + datos["t_exterior"] * 0.05
    datos["ot_event"] = "normal"
    datos["etiqueta_particion"] = ["entrenamiento"] * 72 + ["evaluacion"] * 96
    datos["etiqueta_tipo"] = "normal"
    datos["etiqueta_escenario"] = ""
    return datos


def _revision():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=congelar_n2.RAIZ,
                          capture_output=True, text=True, check=True).stdout.strip()


def test_fija_ventanas_parametros_y_exclusion_de_etiquetas():
    datos = _telemetria_sintetica()
    identidad = {"nombre": "sintetico.csv", "csv_sha256": "solo-prueba"}
    primero = congelar_n2.construir(datos, identidad, _revision())
    segundo = congelar_n2.construir(datos.assign(etiqueta_tipo="falla",
                                                 etiqueta_escenario="inventado"), identidad, _revision())
    sitio = primero["sitios"]["SIM-PRUEBA"]
    assert [sitio[p]["horas"] for p in ("ajuste", "calibracion", "evaluacion")] == [48, 24, 96]
    assert sitio["ajuste"]["fin_utc_inclusivo"] < sitio["calibracion"]["inicio_utc"]
    assert sitio["calibracion"]["fin_utc_inclusivo"] < sitio["evaluacion"]["inicio_utc"]
    assert sitio["parametros"] == segundo["sitios"]["SIM-PRUEBA"]["parametros"]
    assert len(sitio["parametros"]["coef_energia"]) == 3
    assert primero["protocolo"]["etiquetas_no_alteran_predicciones"] is True
    assert primero["protocolo"]["evaluacion_no_altera_parametros"] is True
    assert primero["codigo"]["commit_corte"] == _revision()
    assert "/home/" not in json.dumps(primero)


def test_rechaza_kit_que_no_coincide_con_su_inventario(tmp_path):
    carpeta = tmp_path / "kit"
    (carpeta / "data").mkdir(parents=True)
    csv = carpeta / "data/operaciones_simuladas.csv"
    csv.write_text("datos sintéticos de prueba\n", encoding="utf-8")
    entrada = {"path": "data/operaciones_simuladas.csv", "bytes": csv.stat().st_size,
               "sha256": hashlib.sha256(csv.read_bytes()).hexdigest()}
    inventario = carpeta / "MANIFEST.json"
    inventario.write_text(json.dumps({"files": [entrada]}), encoding="utf-8")
    assert congelar_n2._identidad_kit(csv)["csv_sha256"] == entrada["sha256"]
    csv.write_text("datos cambiados\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no coincide"):
        congelar_n2._identidad_kit(csv)


def test_rechaza_particion_incompleta():
    datos = _telemetria_sintetica()
    datos.loc[0, "etiqueta_particion"] = "evaluacion"
    with pytest.raises(ValueError, match="72 h de referencia"):
        congelar_n2.construir(datos, {"nombre": "sintetico.csv"}, _revision())
