"""Invariantes del Contrato 4 versionado; sin abrir ni copiar filas del kit."""

import json
from pathlib import Path

import pytest

from src import contrato
from src.metricas.generar_numeros import plano

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cifras():
    canonico = json.loads((RAIZ / "resultados/numeros_oficiales.json").read_text(encoding="utf-8"))
    leo = json.loads((RAIZ / "app/ejemplos/numeros_ejemplo.json").read_text(encoding="utf-8"))
    return canonico, leo


def test_contrato_y_vista_de_leo_son_identicos(cifras):
    canonico, leo = cifras
    assert contrato.validar_numeros_oficiales(canonico) == []
    assert leo == plano(canonico)
    assert leo == plano(canonico)  # proyección determinista
    assert leo["_ejemplo"] is False
    assert "DATOS SIMULADOS" in leo["_meta"]["aviso"]


def test_periodos_y_unidades_no_se_mezclan(cifras):
    c, leo = cifras
    assert c["_meta"]["periodos"]["referencia"]["horas_sitio"] == 216
    assert c["_meta"]["periodos"]["evaluacion"]["horas_sitio"] == 288
    assert c["pue"]["referencia"]["periodo"] == "referencia"
    assert c["pue"]["antes"]["periodo"] == c["pue"]["despues_proyectado"]["periodo"] == "evaluacion"
    assert c["pue"]["antes"]["valor"] > c["pue"]["despues_proyectado"]["valor"]
    assert c["wue"]["antes"]["periodo"] == c["wue"]["despues_proyectado"]["periodo"] == "evaluacion"
    assert c["exceso_estimado"]["kwh_sobre_evaluacion"]["unidad"] == "kWh"
    assert c["exceso_estimado"]["litros_sobre_evaluacion"]["unidad"] == "L"
    assert leo["punto_ciego_pct"]["nota"].find("no TI") >= 0


def test_episodios_separados_de_horas_y_clases(cifras):
    c, leo = cifras
    original = c["deteccion"]["comparacion_contra_reglas_kit"]["episodios_originales_kit"]
    assert original["episodios"] == 3 and original["horas_anomalas"] == 21
    assert [(f["tp"], f["fp"], f["fn"]) for f in leo["comparacion"]["filas"]] == [(3, 0, 0), (3, 0, 0)]
    assert leo["comparacion"]["unidad_conteo"] == "episodios"
    assert c["deteccion"]["clases_ot_conteo"]["unidad"] == "horas"
    assert set(c["deteccion"]["clases_ot_conteo"]) >= {
        "incidente_ot", "cambio_no_autorizado", "escalon_sin_registro", "intento_acceso"}


def test_pendientes_no_se_convierten_en_balance(cifras):
    c, leo = cifras
    for clave, responsable in (("detector_cpu_ms", "Gadiel"), ("detector_kwh_anual", "Gadiel"),
                               ("equilibrio_horas", "Gadiel"), ("pue_con_bono", "Misa"),
                               ("acuifero_3105", "Guille")):
        x = leo[clave]
        assert x["valor"] is None and x["estado"] == "pendiente"
        assert responsable in x.get("motivo_pendiente", "")
    assert c["balance_neto"]["razon_ahorro_costo"]["valor"] is None
    assert c["balance_neto"]["ahorro_proyectado_kwh_anual"]["tipo"] == "proyectado"
    assert "ahorro observado" in c["balance_neto"]["ahorro_proyectado_kwh_anual"]["nota"]


def test_json_versionado_solo_contiene_agregados(cifras):
    c, leo = cifras
    for j in (c, leo):
        texto = json.dumps(j, ensure_ascii=False)
        assert "/home/nicolas/" not in texto
        assert '"simulated_anomaly"' not in texto
        assert '"timestamp"' not in texto  # ninguna fila por hora
