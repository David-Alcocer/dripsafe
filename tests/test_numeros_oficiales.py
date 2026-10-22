"""Invariantes del Contrato 4 versionado; sin abrir ni copiar filas del kit."""

import json
from pathlib import Path

import pytest

from src import contrato, procedencia
from src.metricas.generar_numeros import plano

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cifras():
    canonico = json.loads((RAIZ / "resultados/numeros_oficiales.json").read_text(encoding="utf-8"))
    return canonico, plano(canonico)


def test_contrato_y_vista_en_memoria_son_consistentes(cifras):
    canonico, leo = cifras
    assert contrato.validar_numeros_oficiales(canonico) == []
    assert leo == plano(canonico)  # proyección determinista
    assert leo["_ejemplo"] is False
    assert "DATOS SIMULADOS" in leo["_meta"]["aviso"]
    assert not (RAIZ / "app/ejemplos/numeros_demo.json").exists()
    assert not (RAIZ / "app/ejemplos/numeros_ejemplo.json").exists()


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


def test_n2_cerrado_con_denominadores_y_unidades_separadas(cifras):
    c, leo = cifras
    n2 = c["deteccion"]["comparacion_contra_reglas_kit"]["cierre_n2"]
    assert n2["_meta"]["kit_csv_sha256"] == json.loads(
        (RAIZ / "resultados/n2_congelamiento.json").read_text(encoding="utf-8"))["kit"]["csv_sha256"]
    assert len(n2["originales_por_metodo_sitio"]) == 8
    assert len(n2["rejilla_base_por_sitio_escenario"]) == 48
    assert len(n2["curva_base"]) == len(n2["ruido_por_escenario"]) == 16
    assert len(n2["falsas_alarmas_base_y_ruido"]) == 48
    assert leo["comparacion_por_sitio"]["filas"] == n2["originales_por_metodo_sitio"]
    assert leo["rejilla_por_sitio"]["filas"] == n2["rejilla_base_por_sitio_escenario"]
    for fila in n2["rejilla_base_por_sitio_escenario"]:
        assert fila["planeadas"] == fila["ejecutadas"] + fila["omitidas"]
        assert fila["ejecutadas"] == fila["tp_episodios"] + fila["fn_episodios"]
        assert fila["clases_evaluadas"] <= fila["efectos_vistos"]
    totales = {f["metodo"]: f for f in n2["rejilla_base_total"]}
    assert totales["dripsafe"]["tp_episodios"] == totales["dripsafe"]["inyecciones"] == 141
    assert totales["reglas_kit"]["tp_episodios"] == 22
    assert totales["reglas_kit"]["efectos_vistos"] == 6
    ruidosos = {f["metodo"]: f for f in n2["ruido_total"]}
    assert ruidosos["dripsafe"]["inyecciones"] == 705
    assert ruidosos["dripsafe"]["tp_episodios"] == 625
    assert ruidosos["dripsafe"]["efectos_vistos"] == 623
    cambio = next(f for f in n2["curva_base"] if f["nombre"] == "cambio_con_efecto"
                  and f["metodo"] == "reglas_kit")
    assert cambio["tp_episodios"] == 16 and cambio["efectos_vistos"] == 0


def test_curva_y_falsas_alarmas_de_leo_usen_los_agregados_n2(cifras):
    c, leo = cifras
    curva = c["deteccion"]["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"]
    for f in leo["curva_sensibilidad"]["filas"]:
        origen = next(x for x in curva if x["magnitud_pct"] == f["magnitud_pct"]
                      and x["metodo"] == ("dripsafe" if f["metodo"] == "DripSafe" else "reglas_kit"))
        assert f["detectados"] == origen["tp_episodios"]
        assert f["horas_hasta_detectar"] == origen["latencia_episodio_mediana_h"]
    falsas = c["deteccion"]["comparacion_contra_reglas_kit"]["robustez_ruido"][
        "falsas_alarmas_por_dia_sitio_media_por_metodo"]
    assert falsas["dripsafe"] > 0 and falsas["reglas_kit"] == 0
    assert leo["falsas_alarmas_ruido"]["unidad_conteo"] == "alarmas/día/sitio"


def test_g3_y_balance_preparados_para_firma(cifras):
    c, leo = cifras
    bono = c["bono_zero_freshwater"]["pue_con_bono"]
    assert bono == leo["pue_con_bono"]
    assert bono["tipo"] == "proyectado" and bono["responsable"] == "Misa"
    assert bono["valor"] == 1.2842
    assert bono["supuestos"]["pue_base"] == 1.198
    assert bono["supuestos"]["horas_respaldo_proxy"] == c["bono_zero_freshwater"][
        "horas_respaldo_mérida_al_año"]["umbral_30c"]
    assert bono["supuestos"]["cop"] == 2.96
    x = leo["acuifero_3105"]
    assert x["valor"] is None and x["estado"] == "pendiente"
    assert "Nico" in x.get("motivo_pendiente", "")
    balance = c["balance_neto"]
    costo = balance["costo_detector_kwh_anual"]["valor"]
    ahorro = balance["ahorro_proyectado_kwh_anual"]["valor"]
    fuentes = c["fuentes_externas"]
    assert fuentes["factor_emision_sen"]["valor"] == 0.444
    assert fuentes["factor_emision_sen"]["estado"] == "disponible"
    assert fuentes["intensidad_hidrica_sen"]["valor"] == 2.0632
    assert fuentes["intensidad_hidrica_sen"]["estado"] == "disponible"
    assert "estimación" in fuentes["intensidad_hidrica_sen"]["nota"].lower()
    assert balance["emisiones_detector_gco2e_anual"]["valor"] == round(costo * 0.444 * 1000, 8)
    assert balance["co2_evitado_kg_anual"]["valor"] == round(ahorro * 0.444, 4)
    assert balance["agua_indirecta_evitada_l_anual"]["valor"] == round(ahorro * 2.0632, 4)
    assert balance["co2_evitado_kg_anual"]["tipo"] == "proyectado"
    assert balance["agua_indirecta_evitada_l_anual"]["tipo"] == "proyectado"
    assert costo == pytest.approx(1.2916184e-05)
    assert costo == pytest.approx(balance["costo_entrenamiento_kwh_anual"]["valor"]
                                 + balance["costo_inferencia_kwh_anual"]["valor"])
    assert balance["costo_detector_kwh_anual"]["tipo"] == "estimado"
    assert balance["tiempo_detector_ms"]["tipo"] == "medido"
    assert leo["detector_kwh_anual"] == balance["costo_detector_kwh_anual"]
    assert leo["detector_cpu_ms"] == balance["tiempo_detector_ms"]
    assert balance["frecuencia_anualizacion"]["modo"] == "fases_separadas"
    assert procedencia.validar_balance_oficial(c) == []
    if balance["validado_por"] is None:
        assert balance["nota_validacion"] and "fecha_validacion" not in balance
    else:
        assert procedencia.validar_balance_oficial(c, exigir_firma=True) == []
    assert c["_meta"]["procedencia_g3"]["metodo"]["fuente_energia"] == "tdp_estimado"
    assert balance["razon_ahorro_costo"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] / costo, 1)
    assert "costo publicado" in balance["razon_ahorro_costo"]["nota"]
    assert balance["razon_ahorro_costo"]["tipo"] == "proyectado"
    umbral = balance["umbral_equilibrio"]
    assert umbral["valor"] == round(costo / umbral["supuestos"]["exceso_tipico_kwh_por_hora"], 12)
    assert umbral["supuestos"]["horas_sitio_con_alerta_fisica"] >= umbral["supuestos"]["horas_sitio_con_exceso_positivo"] > 0
    assert leo["equilibrio_horas"] == umbral
    assert balance["balance_energia_kwh_anual"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] - costo, 12)
    assert balance["balance_energia_kwh_anual"]["tipo"] == "proyectado"
    assert leo["balance_energia_kwh_anual"] == balance["balance_energia_kwh_anual"]
    assert "Nico" in leo["acuifero_3105"]["motivo_pendiente"]
    assert c["_meta"]["generado_con_commit"] and "sucio" not in c["_meta"]["generado_con_commit"]
    assert balance["ahorro_proyectado_kwh_anual"]["tipo"] == "proyectado"
    assert "ahorro observado" in balance["ahorro_proyectado_kwh_anual"]["nota"]


def test_json_versionado_solo_contiene_agregados(cifras):
    c, leo = cifras
    for j in (c, leo):
        texto = json.dumps(j, ensure_ascii=False)
        assert "/home/nicolas/" not in texto
        assert '"simulated_anomaly"' not in texto
        assert '"timestamp"' not in texto  # ninguna fila por hora
