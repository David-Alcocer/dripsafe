"""Comparación por tipo de enfriamiento y WUE del híbrido (src/metricas/refrigeracion.py, #15).

Se usa app.kit.ejemplo(): datos INVENTADOS con el formato del kit. El kit real
nunca entra a las pruebas ni al repositorio.
"""

import json
from pathlib import Path

import pytest

from app import kit
from src.datos.cargar import cargar
from src.metricas import refrigeracion
from src.metricas.refrigeracion import SupuestosHibrido

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def crudo():
    return kit.ejemplo()


@pytest.fixture(scope="module")
def telemetria(crudo, tmp_path_factory):
    ruta = tmp_path_factory.mktemp("kit") / "ejemplo.csv"
    crudo.to_csv(ruta, index=False)
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    return cargar(ruta, mapeo)


# ---------- comparación por enfriamiento ----------

def test_una_fila_por_sitio_y_particion(telemetria):
    tabla = refrigeracion.comparar_por_enfriamiento(telemetria)
    assert len(tabla) == 6
    assert set(tabla["particion"]) == {"referencia", "evaluacion"}
    assert dict(zip(tabla["site_id"], tabla["cooling_type"])) == kit.SITIOS


def test_cocientes_son_de_sumas_no_promedios(crudo, telemetria):
    tabla = refrigeracion.comparar_por_enfriamiento(telemetria).set_index(["site_id", "particion"])
    crudo_b = crudo[(crudo["site_id"] == "SIM-B") & (crudo["split"] == "evaluacion")]
    fila = tabla.loc[("SIM-B", "evaluacion")]
    it = crudo_b["energy_it_kwh"].sum()
    assert fila["energia_it_kwh"] == pytest.approx(it)
    assert fila["pue"] == pytest.approx(crudo_b["energy_total_kwh"].sum() / it)
    assert fila["l_por_kwh_ti"] == pytest.approx(crudo_b["water_l"].sum() / it)
    promedio_horario = (crudo_b["water_l"] / crudo_b["energy_it_kwh"]).mean()
    assert fila["l_por_kwh_ti"] != pytest.approx(promedio_horario, rel=1e-9)
    assert fila["filas"] == 96


def test_rechaza_sitio_con_dos_tipos_de_enfriamiento(telemetria):
    mezclado = telemetria.copy()
    mezclado.loc[mezclado.index[0], "cooling_type"] = "liquida"
    with pytest.raises(ValueError, match="SIM-A"):
        refrigeracion.comparar_por_enfriamiento(mezclado)


def test_rechaza_telemetria_sin_tipo_de_enfriamiento(telemetria):
    with pytest.raises(ValueError, match="cooling_type"):
        refrigeracion.comparar_por_enfriamiento(telemetria.drop(columns=["cooling_type"]))


def test_pue_respaldo_aire_suma_energia_sobre_base_sin_contar_horas_dos_veces():
    f = 2235 / 8760
    resultado = refrigeracion.estimar_pue_respaldo_aire(1.198, f, 2.96)
    assert resultado == pytest.approx(1.198 + f / 2.96)
    assert round(resultado, 3) == 1.284
    assert refrigeracion.estimar_pue_respaldo_aire(1.198, 0, 2.96) == 1.198


@pytest.mark.parametrize("pue,f,cop,carga", [(0.99, .25, 2.96, 1), (1.2, 1.1, 2.96, 1),
                                               (1.2, .25, 0, 1), (1.2, .25, 2.96, -1)])
def test_pue_respaldo_aire_rechaza_supuestos_invalidos(pue, f, cop, carga):
    with pytest.raises(ValueError):
        refrigeracion.estimar_pue_respaldo_aire(pue, f, cop, carga)


# ---------- WUE del híbrido ----------

def _supuestos(**cambios):
    base = dict(fraccion_respaldo=0.25, wue_base=0.2, wue_respaldo=1.0, pue_base=1.2,
                pue_respaldo=1.3, no_potable_base=0.0, no_potable_respaldo=1.0)
    return SupuestosHibrido(**{**base, **cambios})


def test_wue_total_y_pue_son_mezcla_por_energia_de_ti():
    r = refrigeracion.estimar_hibrido(_supuestos())
    assert r["wue_total"] == pytest.approx(0.75 * 0.2 + 0.25 * 1.0)
    assert r["pue"] == pytest.approx(0.75 * 1.2 + 0.25 * 1.3)


def test_wue_potable_descuenta_el_agua_tratada():
    # Respaldo 100 % tratada: solo cuenta la reposición potable del circuito cerrado.
    r = refrigeracion.estimar_hibrido(_supuestos())
    assert r["wue_potable"] == pytest.approx(0.75 * 0.2)
    # Todo con agua tratada: el WUE potable llega a cero (lo que premia el bono).
    cero = refrigeracion.estimar_hibrido(_supuestos(no_potable_base=1.0))
    assert cero["wue_potable"] == pytest.approx(0.0)
    assert cero["wue_total"] == pytest.approx(r["wue_total"])


def test_supuestos_fuera_de_rango_se_rechazan():
    with pytest.raises(ValueError):
        refrigeracion.estimar_hibrido(_supuestos(fraccion_respaldo=1.5))
    with pytest.raises(ValueError):
        refrigeracion.estimar_hibrido(_supuestos(no_potable_respaldo=-0.1))
    with pytest.raises(ValueError):
        refrigeracion.estimar_hibrido(_supuestos(pue_base=0.9))


def test_escenarios_toman_base_y_respaldo_de_la_referencia(telemetria):
    tabla = refrigeracion.comparar_por_enfriamiento(telemetria)
    escenarios = refrigeracion.escenarios_de_sensibilidad(tabla)
    assert [e["nombre"] for e in escenarios] == ["optimista", "central", "conservador"]
    ref = tabla[tabla["particion"] == "referencia"].set_index("cooling_type")
    central = next(e for e in escenarios if e["nombre"] == "central")
    assert central["supuestos"]["wue_base"] == pytest.approx(ref.loc["liquida", "l_por_kwh_ti"])
    assert central["supuestos"]["wue_respaldo"] == pytest.approx(ref.loc["evaporativa", "l_por_kwh_ti"])


def test_escenarios_de_diseno_son_100_por_ciento_agua_tratada(telemetria):
    escenarios = refrigeracion.escenarios_de_sensibilidad(refrigeracion.comparar_por_enfriamiento(telemetria))
    assert [e["supuestos"]["fraccion_respaldo"] for e in escenarios] == [0.10, 0.25, 0.50]
    for e in escenarios:
        assert e["supuestos"]["no_potable_base"] == e["supuestos"]["no_potable_respaldo"] == 1.0
        assert e["resultado"]["wue_potable"] == pytest.approx(0.0)
    totales = [e["resultado"]["wue_total"] for e in escenarios]
    assert totales[0] < totales[1] < totales[2]   # más respaldo evaporativo → más agua tratada


def test_riesgo_reposicion_con_red_deja_la_base_como_agua_potable(telemetria):
    tabla = refrigeracion.comparar_por_enfriamiento(telemetria)
    riesgo = refrigeracion.riesgo_reposicion_con_red(tabla)
    s = riesgo["supuestos"]
    assert s["fraccion_respaldo"] == 0.25 and s["no_potable_base"] == 0.0
    assert riesgo["resultado"]["wue_potable"] == pytest.approx(0.75 * s["wue_base"])
