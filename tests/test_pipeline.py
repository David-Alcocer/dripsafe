"""Flujo completo (src/pipeline.py, #4) y balance neto (src/metricas/balance_neto.py, #14).

Se usa app.kit.ejemplo(): datos INVENTADOS con el formato del kit. El kit real
nunca entra a las pruebas ni al repositorio.
"""

import json
import subprocess
from pathlib import Path

import pytest

from app import kit
from src import contrato, pipeline
from src.datos.cargar import cargar
from src.metricas import balance_neto
from src.metricas.pue import pue_inicial

RAIZ = Path(__file__).resolve().parents[1]


# ---------- balance neto ----------

def test_costo_anual_usa_la_inferencia_anual_medida():
    consumo = {"kwh_entrenamiento": 0.001, "kwh_inferencia_anual": 2.5}
    assert balance_neto.costo_anual_kwh(consumo) == pytest.approx(2.5)


def test_costo_anual_rechaza_consumo_sin_inferencia():
    with pytest.raises(ValueError):
        balance_neto.costo_anual_kwh({"kwh_entrenamiento": 0.001})


def test_horas_para_equilibrio_divide_costo_entre_exceso_tipico():
    # Exceso típico (mediana) por hora alertada = 4 kWh; costo 2 kWh/año → media hora.
    resultado = balance_neto.horas_para_equilibrio(2.0, [0.0, 3.0, 4.0, 5.0])
    assert resultado["exceso_tipico_kwh_por_hora"] == pytest.approx(4.0)
    assert resultado["horas_necesarias_al_año"] == pytest.approx(0.5)


def test_horas_para_equilibrio_sin_exceso_queda_indefinido():
    resultado = balance_neto.horas_para_equilibrio(2.0, [0.0, 0.0])
    assert resultado["exceso_tipico_kwh_por_hora"] is None
    assert resultado["horas_necesarias_al_año"] is None


# ---------- PUE inicial (src/metricas/pue.py) ----------

@pytest.fixture(scope="module")
def crudo():
    return kit.ejemplo()


@pytest.fixture(scope="module")
def telemetria(crudo, tmp_path_factory):
    ruta = tmp_path_factory.mktemp("kit") / "ejemplo.csv"
    crudo.to_csv(ruta, index=False)
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    return cargar(ruta, mapeo)


def test_pue_inicial_es_cociente_de_sumas_de_la_particion(crudo, telemetria):
    esperado = crudo[crudo["split"] == "evaluacion"]
    cifras = pue_inicial(telemetria, "evaluacion")
    assert cifras["pue"] == pytest.approx(esperado["energy_total_kwh"].sum() / esperado["energy_it_kwh"].sum())
    assert cifras["wue"] == pytest.approx(esperado["water_l"].sum() / esperado["energy_it_kwh"].sum())
    assert cifras["energia_no_ti_kwh"] == pytest.approx(
        cifras["energia_total_kwh"] - cifras["energia_it_kwh"])


def test_pue_inicial_cuenta_filas_y_horas_de_reloj(telemetria):
    ref, eva = pue_inicial(telemetria, "entrenamiento"), pue_inicial(telemetria, "evaluacion")
    assert (ref["horas_reloj"], ref["sitios"], ref["filas"]) == (72, 3, 216)
    assert (eva["horas_reloj"], eva["sitios"], eva["filas"]) == (96, 3, 288)


# ---------- marca de commit ----------

def _git_falso(salida_status: str):
    def correr(comando, **_):
        salida = "abc1234\n" if "rev-parse" in comando else salida_status
        return subprocess.CompletedProcess(comando, 0, stdout=salida, stderr="")
    return correr


def test_commit_con_archivo_sin_seguimiento_es_sucio(monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, "run", _git_falso("?? src/nuevo.py\n"))
    assert pipeline._commit() == "abc1234-sucio"


def test_commit_limpio_no_lleva_marca(monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, "run", _git_falso(""))
    assert pipeline._commit() == "abc1234"


# ---------- pipeline de punta a punta (contrato 4 de Nico) ----------

@pytest.fixture(scope="module")
def salida(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("pipeline")
    destino = carpeta / "numeros.json"
    pipeline.main([
        "--ejemplo", "--sin-medir", "--semillas-ruido", "",
        "--resultados", str(carpeta / "resultados"),
        "--clima", str(carpeta / "sin_clima.json"),
        "--salida", str(destino),
    ])
    return carpeta, json.loads(destino.read_text(encoding="utf-8"))


def test_pipeline_cumple_el_contrato_4(salida):
    _, numeros = salida
    assert contrato.validar_numeros_oficiales(numeros) == []


def test_pipeline_escribe_meta_con_commit_y_aviso_de_ejemplo(salida):
    _, numeros = salida
    meta = numeros["_meta"]
    assert "DATOS SIMULADOS" in meta["aviso"] and "INVENTADOS" in meta["aviso"]
    assert meta["generado_con_commit"] == meta["base_main"]
    assert meta["generado_con_commit"] not in ("", "f2e5c4b")
    assert meta["periodos"]["referencia"]["horas_sitio"] == 216
    assert meta["periodos"]["evaluacion"]["horas_sitio"] == 288


def test_pipeline_separa_pue_de_referencia_y_de_evaluacion(salida, crudo):
    _, numeros = salida
    pue = numeros["pue"]
    assert pue["referencia"]["periodo"] == "referencia"
    assert pue["antes"]["periodo"] == pue["despues_proyectado"]["periodo"] == "evaluacion"
    eva = crudo[crudo["split"] == "evaluacion"]
    assert pue["antes"]["valor"] == pytest.approx(
        eva["energy_total_kwh"].sum() / eva["energy_it_kwh"].sum(), abs=1e-4)


def test_pue_antes_y_exceso_usan_el_mismo_periodo(salida):
    _, numeros = salida
    antes = numeros["pue"]["antes"]
    kwh = numeros["exceso_estimado"]["kwh_sobre_evaluacion"]
    litros = numeros["exceso_estimado"]["litros_sobre_evaluacion"]
    assert antes["periodo"] == kwh["periodo"] == litros["periodo"] == "evaluacion"


def test_pipeline_llena_deteccion_con_la_rejilla(salida):
    _, numeros = salida
    deteccion = numeros["deteccion"]
    assert deteccion["comparacion_contra_reglas_kit"]["episodios_originales_kit"]["dripsafe_tp"] is not None
    assert deteccion["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"]
    assert deteccion["falsas_alarmas_por_dia"]["valor"] is not None


def test_pipeline_sin_medicion_deja_el_costo_pendiente(salida):
    _, numeros = salida
    balance = numeros["balance_neto"]
    for clave in ("costo_detector_kwh_anual", "umbral_equilibrio", "razon_ahorro_costo"):
        assert balance[clave]["valor"] is None
        assert balance[clave]["estado"] == "pendiente" and balance[clave]["motivo_pendiente"]


def test_pipeline_deja_las_tablas_intermedias_fuera_del_json(salida):
    carpeta, _ = salida
    assert (carpeta / "resultados" / "alertas.csv").is_file()
    assert (carpeta / "resultados" / "rejilla_resumen.csv").is_file()
    assert (carpeta / "resultados" / "deteccion_para_numeros_oficiales.json").is_file()


def test_pipeline_usa_consumo_ya_medido(salida, tmp_path):
    carpeta, _ = salida
    consumo = tmp_path / "consumo_modelo.json"
    consumo.write_text(json.dumps({"kwh_entrenamiento": 1e-6, "kwh_inferencia_anual": 0.02,
                                   "ms_mediana": 12.5, "repeticiones": 10,
                                   "fecha": "2026-10-20"}), encoding="utf-8")
    destino = tmp_path / "numeros.json"
    pipeline.main([
        "--ejemplo", "--sin-medir", "--sin-rejilla", "--consumo", str(consumo),
        "--resultados", str(carpeta / "resultados"), "--clima", str(tmp_path / "sin_clima.json"),
        "--salida", str(destino),
    ])
    numeros = json.loads(destino.read_text(encoding="utf-8"))
    assert contrato.validar_numeros_oficiales(numeros) == []
    balance = numeros["balance_neto"]
    assert balance["costo_detector_kwh_anual"]["valor"] == pytest.approx(0.02)
    assert balance["tiempo_detector_ms"]["valor"] == pytest.approx(12.5)
    assert balance["umbral_equilibrio"]["unidad"] == "h/año"
    assert balance["umbral_equilibrio"]["valor"] > 0
    ahorro = balance["ahorro_proyectado_kwh_anual"]["valor"]
    assert balance["razon_ahorro_costo"]["valor"] == pytest.approx(ahorro / 0.02, rel=1e-3)


def test_sin_rejilla_exige_una_corrida_previa(tmp_path):
    with pytest.raises(SystemExit):
        pipeline.main(["--ejemplo", "--sin-medir", "--sin-rejilla",
                       "--resultados", str(tmp_path / "vacia"), "--salida", str(tmp_path / "n.json")])


def test_ejemplo_no_sobrescribe_el_json_oficial():
    with pytest.raises(SystemExit):
        pipeline.main(["--ejemplo", "--sin-medir", "--sin-rejilla",
                       "--salida", str(RAIZ / "resultados/numeros_oficiales.json")])
