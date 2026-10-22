"""Preparación y firma del balance: selección del agregado y rechazos auditables.

Solo datos inventados; ninguna fila del kit.
"""

from copy import deepcopy

import pandas as pd
import pytest

from src import pipeline, procedencia
from src.metricas.generar_numeros import _agregado_equilibrio


def test_agregado_solo_incluye_exceso_positivo_con_alerta_fisica():
    residuos = pd.DataFrame({
        "site_id": ["A"] * 6,
        "coincide_alerta": [True, True, True, True, False, False],
        "exceso_no_ti_estimado_kwh": [0.0, 2.0, 4.0, 6.0, 100.0, 200.0],
    })
    agregado = _agregado_equilibrio(residuos)
    assert agregado["exceso_tipico_kwh_por_hora"] == 4.0
    assert agregado["horas_sitio_con_alerta_fisica"] == 4
    assert agregado["horas_sitio_con_exceso_positivo"] == 3


@pytest.mark.parametrize("alerta", [False, True])
def test_agregado_sin_muestra_positiva_no_inventa_un_denominador(alerta):
    agregado = _agregado_equilibrio(pd.DataFrame({
        "site_id": ["A"], "coincide_alerta": [alerta], "exceso_no_ti_estimado_kwh": [0.0],
    }))
    assert agregado["exceso_tipico_kwh_por_hora"] is None
    assert agregado["horas_sitio_con_exceso_positivo"] == 0


@pytest.fixture
def preparado():
    # Mediana de 4 kWh/h y costo 2 kWh/año: el umbral debe ser 0.5 h/año.
    base = {"balance_neto": {
        "validado_por": ["Misa", "Nico"], "fecha_validacion": "2026-01-01",
        "nota_validacion": "Pendiente de validación conjunta de Misa y Nico.",
        "ahorro_proyectado_kwh_anual": {"valor": 10.0},
        "umbral_equilibrio": {"supuestos": _agregado_equilibrio(pd.DataFrame({
            "site_id": ["A", "B"], "coincide_alerta": [True, True],
            "exceso_no_ti_estimado_kwh": [3.0, 5.0],
        }))},
    }}
    consumo = {"kwh_inferencia_anual": 2.0, "repeticiones": 10}
    args = pipeline._argumentos(["--sin-medir"])
    return base, consumo, args


def test_regenerar_sin_firma_borra_los_nombres_y_fecha_anteriores(preparado):
    base, consumo, args = preparado
    balance = pipeline._balance(base, consumo, args)
    assert balance["validado_por"] is None
    assert "fecha_validacion" not in balance
    assert balance["balance_energia_kwh_anual"]["valor"] == 8.0
    assert balance["umbral_equilibrio"]["valor"] == 0.5
    assert procedencia.validar_balance_oficial({"balance_neto": balance}) == []


def test_firma_reemplaza_nota_pendiente_sin_firmar_el_objeto_de_entrada(preparado):
    base, consumo, args = preparado
    args.validacion_conjunta = True
    anterior = deepcopy(base)
    balance = pipeline._balance(base, consumo, args)
    assert base == anterior
    assert balance["validado_por"] == ["Misa", "Nico"]
    assert "pendiente" not in balance["nota_validacion"].lower()
    assert procedencia.validar_balance_oficial({"balance_neto": balance}, exigir_firma=True) == []


def test_no_se_puede_firmar_sin_consumo(preparado):
    base, _, args = preparado
    args.validacion_conjunta = True
    with pytest.raises(ValueError, match="sin consumo"):
        pipeline._balance(base, None, args)


def test_umbral_sin_mediana_queda_pendiente_y_con_motivo(preparado):
    base, consumo, args = preparado
    base["balance_neto"]["umbral_equilibrio"]["supuestos"] = {}
    balance = pipeline._balance(base, consumo, args)
    assert balance["umbral_equilibrio"]["valor"] is None
    assert balance["umbral_equilibrio"]["motivo_pendiente"]
    assert balance["balance_energia_kwh_anual"]["valor"] == 8.0


@pytest.mark.parametrize(("campo", "valor", "mensaje"), [
    ("balance_energia_kwh_anual", 9.0, "saldo energético"),
    ("razon_ahorro_costo", 6.0, "razón ahorro/costo"),
    ("umbral_equilibrio", 0.6, "umbral no coincide"),
])
def test_validador_rechaza_aritmetica_alterada(preparado, campo, valor, mensaje):
    base, consumo, args = preparado
    balance = pipeline._balance(base, consumo, args)
    balance[campo]["valor"] = valor
    assert any(mensaje in error for error in procedencia.validar_balance_oficial({"balance_neto": balance}))


def test_validador_rechaza_umbral_sin_agregado(preparado):
    base, consumo, args = preparado
    balance = pipeline._balance(base, consumo, args)
    del balance["umbral_equilibrio"]["supuestos"]
    assert any("sin mediana" in error for error in procedencia.validar_balance_oficial({"balance_neto": balance}))


def test_validador_rechaza_doble_conteo_en_costo(preparado):
    base, consumo, args = preparado
    balance = pipeline._balance(base, consumo, args)
    balance["frecuencia_anualizacion"]["modo"] = "fases_separadas"
    balance["costo_entrenamiento_kwh_anual"]["valor"] = 1.0
    balance["costo_inferencia_kwh_anual"]["valor"] = 1.5
    assert any("entrenamiento + inferencia" in error for error in
               procedencia.validar_balance_oficial({"balance_neto": balance}))


def test_tdp_no_puede_publicarse_como_medido(preparado):
    base, consumo, args = preparado
    balance = pipeline._balance(base, consumo, args)
    balance["costo_detector_kwh_anual"]["tipo"] = "medido"
    numeros = {"balance_neto": balance, "_meta": {"procedencia_g3": {
        "metodo": {"fuente_energia": "tdp_estimado"},
    }}}
    assert any("TDP" in error for error in procedencia.validar_balance_oficial(numeros))


@pytest.mark.parametrize("fecha", [None, "2026-02-30", "20261022", 2026])
def test_firma_requiere_fecha_valida(preparado, fecha):
    base, consumo, args = preparado
    args.validacion_conjunta = True
    balance = pipeline._balance(base, consumo, args)
    balance["fecha_validacion"] = fecha
    assert any("fecha_validacion" in error for error in procedencia.validar_balance_oficial({"balance_neto": balance}))
