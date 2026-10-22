"""Flujo completo (src/pipeline.py, #4) y balance neto (src/metricas/balance_neto.py, #14).

Se usa app.kit.ejemplo(): datos INVENTADOS con el formato del kit. El kit real
nunca entra a las pruebas ni al repositorio.
"""

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from app import kit
from src import contrato, pipeline, procedencia
from src.datos.cargar import cargar
from src.metricas import balance_neto
from src.metricas.pue import pue_inicial
from src.modelo import detector, medicion

RAIZ = Path(__file__).resolve().parents[1]


# ---------- balance neto ----------

@pytest.mark.parametrize(("ahorro", "costo", "saldo"), [
    (10.0, 2.0, 8.0),
    (2.0, 2.0, 0.0),
    (2.0, 10.0, -8.0),
    (10.0, 0.0, 10.0),
])
def test_balance_energia_anual_resta_ahorro_y_costo(ahorro, costo, saldo):
    assert balance_neto.balance_energia_anual(ahorro, costo) == pytest.approx(saldo)


@pytest.mark.parametrize("valor_invalido", [
    pytest.param(-1.0, id="negativo"),
    pytest.param(float("inf"), id="infinito"),
    pytest.param(float("-inf"), id="infinito-negativo"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(True, id="booleano-verdadero"),
    pytest.param(False, id="booleano-falso"),
])
@pytest.mark.parametrize(("posicion", "nombre"), [
    (0, "ahorro proyectado"),
    (1, "costo del detector"),
])
def test_balance_energia_anual_rechaza_entradas_invalidas(
    valor_invalido, posicion, nombre,
):
    argumentos = [10.0, 2.0]
    argumentos[posicion] = valor_invalido
    with pytest.raises(ValueError, match=nombre):
        balance_neto.balance_energia_anual(*argumentos)


def test_factores_externos_se_aplican_sin_inventar_unidades():
    assert balance_neto.emisiones_detector_gco2e_anual(0.001) == pytest.approx(0.444)
    assert balance_neto.co2_evitado_kg_anual(1000) == pytest.approx(444)
    assert balance_neto.agua_indirecta_evitada_l_anual(1000) == pytest.approx(2063.2)


@pytest.mark.parametrize("funcion", [
    balance_neto.emisiones_detector_gco2e_anual,
    balance_neto.co2_evitado_kg_anual,
    balance_neto.agua_indirecta_evitada_l_anual,
])
@pytest.mark.parametrize("valor", [-1.0, float("nan"), float("inf"), True])
def test_factores_externos_rechazan_kwh_invalidos(funcion, valor):
    with pytest.raises(ValueError):
        funcion(valor)


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


# ---------- contrato 3 v2: fases separadas y procedencia ----------

def _consumo_v2() -> dict:
    """Consumo v2 mínimo pero completo, para probar el contrato sin el kit."""
    def fase(kwh: float, incluye_ajuste: bool) -> dict:
        return {
            "kwh_por_repeticion": [kwh, kwh],
            "ms_por_repeticion": [10.0, 11.0],
            "kwh_mediana": kwh,
            "kwh_p95": kwh,
            "kwh_desviacion": 0.0,
            "ms_mediana": 10.5,
            "ms_desviacion": 0.5,
            "fuente_energia": "tdp_estimado",
            "baja_resolucion": True,
            "incluye_ajuste": incluye_ajuste,
        }

    return {
        "formato": 2,
        "repeticiones": 2,
        "frecuencia": {"horas_anio": 8760, "lotes_inferencia_por_hora": 1,
                       "reentrenamientos_anio": 4},
        "lote": {"horas": 168, "sitios": 3, "filas": 504},
        "entrenamiento": fase(1e-7, True),
        "inferencia": fase(2e-7, False),
        "corrida_completa": fase(3e-7, True),
        "_meta": {
            "kit": {"csv_sha256": "a" * 64, "manifest_sha256": "b" * 64},
            "codigo": {"commit": "c" * 40, "sha256_archivos": {"x.py": "d" * 64}},
            "equipo": {"modelo": "MacTest", "so": "macOS", "python": "3.12"},
            "metodo": {"herramienta": "codecarbon", "tracker": "OfflineEmissionsTracker",
                       "pais": "MEX", "fuente_energia": "tdp_estimado", "tipo": "estimado"},
            "tabla_medida_sha256": "e" * 64,
        },
    }


def test_costo_v2_suma_inferencia_y_entrenamiento_sin_doble_conteo():
    desglose = balance_neto.desglose_costo_anual(
        _consumo_v2(), {"horas_anio": 8760, "lotes_inferencia_por_hora": 1,
                        "reentrenamientos_anio": 4})
    assert desglose["modo"] == "fases_separadas"
    assert desglose["inferencia_kwh_por_hora"] == pytest.approx(2e-7 / 168)
    assert desglose["inferencia_kwh_anual"] == pytest.approx(2e-7 / 168 * 8760)
    assert desglose["entrenamiento_kwh_anual"] == pytest.approx(1e-7 * 4)
    assert desglose["total_kwh_anual"] == pytest.approx(2e-7 / 168 * 8760 + 1e-7 * 4)
    assert desglose["reentrenamientos_aplicados"] == 4


def test_costo_v1_es_cota_superior_y_no_suma_reentrenamiento():
    desglose = balance_neto.desglose_costo_anual(
        {"kwh_inferencia_anual": 0.02}, {"reentrenamientos_anio": 4})
    assert desglose["modo"] == "legacy_corrida_completa"
    assert desglose["total_kwh_anual"] == pytest.approx(0.02)
    assert desglose["reentrenamientos_aplicados"] == 0
    assert "no se suma" in desglose["nota"]


def test_validar_consumo_v2_exige_kit_y_repeticiones():
    assert procedencia.validar_consumo(_consumo_v2()) == []
    sin_kit = _consumo_v2()
    sin_kit["_meta"]["kit"] = None
    assert any("kit" in problema for problema in procedencia.validar_consumo(sin_kit))
    pocas = _consumo_v2()
    pocas["inferencia"]["kwh_por_repeticion"] = [2e-7]
    assert any("inferencia" in problema for problema in procedencia.validar_consumo(pocas))
    sin_lote = _consumo_v2()
    sin_lote.pop("lote")
    assert any("lote" in problema for problema in procedencia.validar_consumo(sin_lote))


def test_inferencia_pura_coincide_con_detectar_sin_ajustar(telemetria):
    params = detector.entrenar(telemetria)
    pura = medicion.inferir(telemetria, params)
    completa = detector.detectar(telemetria)
    pd.testing.assert_frame_equal(pura, completa)


def test_huella_kit_encuentra_manifest_un_nivel_arriba(tmp_path):
    datos = tmp_path / "data"
    datos.mkdir()
    csv = datos / "operaciones_simuladas.csv"
    csv.write_text("timestamp\n2026-01-01\n", encoding="utf-8")
    (tmp_path / "MANIFEST.json").write_text("{}", encoding="utf-8")
    huella = procedencia.huella_kit(csv)
    assert huella["csv_sha256"] == procedencia.sha256_archivo(csv)
    assert huella["manifest_sha256"] == procedencia.sha256_archivo(tmp_path / "MANIFEST.json")


def test_medicion_v2_guarda_cada_repeticion_y_procedencia(tmp_path, crudo, telemetria):
    kit_csv = tmp_path / "operaciones_simuladas.csv"
    crudo.to_csv(kit_csv, index=False)
    (tmp_path / "MANIFEST.json").write_text("{}", encoding="utf-8")
    consumo = medicion.medir_consumo(
        telemetria, 1, tmp_path / "consumo.json", kit=kit_csv,
        frecuencia={"horas_anio": 8760, "lotes_inferencia_por_hora": 1,
                    "reentrenamientos_anio": 4})
    assert consumo["formato"] == 2
    assert len(consumo["inferencia"]["kwh_por_repeticion"]) == 1
    assert consumo["lote"]["horas"] == 168
    assert consumo["lote"]["horas_entrenamiento"] == 72
    assert consumo["kwh_inferencia_anual"] == pytest.approx(
        consumo["inferencia"]["kwh_mediana"] / 168 * 8760)
    assert consumo["_meta"]["kit"]["csv_sha256"]
    assert consumo["_meta"]["tabla_medida_sha256"]
    assert procedencia.validar_consumo(consumo) == []


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
    acuifero = numeros["fuentes_externas"]["disponibilidad_acuifero_3105"]
    assert acuifero["valor"] == 2059.634923
    assert acuifero["unidad"] == "hm³/año" and acuifero["estado"] == "disponible"
    assert "regional calculada" in acuifero["nota"]


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
    tipico = balance["umbral_equilibrio"]["supuestos"]["exceso_tipico_kwh_por_hora"]
    assert balance["umbral_equilibrio"]["valor"] == round(0.02 / tipico, 12)
    assert balance["balance_energia_kwh_anual"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] - 0.02, 12)
    assert balance["balance_energia_kwh_anual"]["tipo"] == "proyectado"
    ahorro = balance["ahorro_proyectado_kwh_anual"]["valor"]
    assert balance["razon_ahorro_costo"]["valor"] == pytest.approx(ahorro / 0.02, rel=1e-3)


@pytest.mark.parametrize("firmar", [False, True])
def test_pipeline_v2_anualiza_y_solo_firma_si_se_pide(salida, tmp_path, firmar):
    carpeta, _ = salida
    consumo = tmp_path / "consumo_v2.json"
    consumo.write_text(json.dumps(_consumo_v2()), encoding="utf-8")
    destino = tmp_path / "numeros_v2.json"
    pipeline.main([
        "--ejemplo", "--sin-medir", "--sin-rejilla", "--consumo", str(consumo),
        "--resultados", str(carpeta / "resultados"), "--clima", str(tmp_path / "sin_clima.json"),
        "--salida", str(destino),
        *(["--validacion-conjunta"] if firmar else []),
    ])
    numeros = json.loads(destino.read_text(encoding="utf-8"))
    balance = numeros["balance_neto"]
    esperado = 2e-7 / 168 * 8760 + 1e-7 * 4
    assert balance["costo_detector_kwh_anual"]["valor"] == pytest.approx(esperado)
    assert balance["frecuencia_anualizacion"]["modo"] == "fases_separadas"
    assert balance["frecuencia_anualizacion"]["horas_lote"] == 168
    assert balance["frecuencia_anualizacion"]["reentrenamientos_aplicados"] == 4
    if firmar:
        assert balance["validado_por"] == ["Misa", "Nico"]
        assert balance["fecha_validacion"]
        assert "pendiente" not in balance["nota_validacion"].lower()
        assert procedencia.validar_balance_oficial(numeros, exigir_firma=True) == []
    else:
        assert balance["validado_por"] is None and balance["nota_validacion"]
        assert "fecha_validacion" not in balance
        assert procedencia.validar_balance_oficial(numeros, exigir_firma=True)
    assert balance["umbral_equilibrio"]["valor"] == round(
        balance["costo_detector_kwh_anual"]["valor"] /
        balance["umbral_equilibrio"]["supuestos"]["exceso_tipico_kwh_por_hora"], 12)
    assert balance["emisiones_detector_gco2e_anual"]["valor"] == round(
        balance["costo_detector_kwh_anual"]["valor"] * 0.444 * 1000, 8)
    assert balance["co2_evitado_kg_anual"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] * 0.444, 4)
    assert balance["agua_indirecta_evitada_l_anual"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] * 2.0632, 4)
    assert numeros["fuentes_externas"]["factor_emision_sen"]["valor"] == 0.444
    assert numeros["fuentes_externas"]["intensidad_hidrica_sen"]["valor"] == 2.0632
    assert balance["balance_energia_kwh_anual"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] - balance["costo_detector_kwh_anual"]["valor"], 12)
    assert balance["razon_ahorro_costo"]["valor"] == round(
        balance["ahorro_proyectado_kwh_anual"]["valor"] /
        balance["costo_detector_kwh_anual"]["valor"], 1)
    assert numeros["_meta"]["procedencia_g3"]["kit"]["csv_sha256"] == "a" * 64
    assert procedencia.validar_balance_oficial(numeros) == []


def test_sin_rejilla_exige_una_corrida_previa(tmp_path):
    with pytest.raises(SystemExit):
        pipeline.main(["--ejemplo", "--sin-medir", "--sin-rejilla",
                       "--resultados", str(tmp_path / "vacia"), "--salida", str(tmp_path / "n.json")])


def test_ejemplo_no_sobrescribe_el_json_oficial():
    with pytest.raises(SystemExit):
        pipeline.main(["--ejemplo", "--sin-medir", "--sin-rejilla",
                       "--salida", str(RAIZ / "resultados/numeros_oficiales.json")])
