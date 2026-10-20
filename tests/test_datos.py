"""Pruebas del cargador del kit (src/datos/cargar.py).

Usa un CSV mínimo embebido (2 horas × 3 sitios) con un escenario de cada tipo
para no depender del kit real (que no está en el repo).
"""
import pandas as pd
import pytest

from src import contrato
from src.datos.cargar import cargar

MAPEO = {
    "timestamp": "timestamp",
    "kw_ti": "energy_it_kwh",
    "kw_total": "energy_total_kwh",
    "t_exterior": "outdoor_temp_c",
    "agua_reposicion_l": "water_l",
    "site_id": "site_id",
    "cooling_type": "cooling_type",
    "load_pct": "load_pct",
    "inlet_temp_c": "inlet_temp_c",
    "ot_event": "ot_event",
}

CSV_MINIMO = """timestamp,site_id,cooling_type,energy_it_kwh,energy_total_kwh,water_l,load_pct,outdoor_temp_c,inlet_temp_c,ot_event,scenario,simulated_anomaly,split,is_simulated
2026-10-12T00:00:00+00:00,SIM-A,aire,139.4,189.9,4.2,40.7,16.7,22.7,normal,base,0,referencia,True
2026-10-12T00:00:00+00:00,SIM-B,evaporativa,126.5,155.6,101.2,33.9,16.1,22.6,normal,base,0,referencia,True
2026-10-12T00:00:00+00:00,SIM-C,liquida,128.3,152.9,25.7,34.5,17.4,22.8,normal,base,0,referencia,True
2026-10-12T01:00:00+00:00,SIM-A,aire,123.9,166.3,3.7,33.2,15.9,22.5,normal,ineficiencia,1,evaluacion,True
2026-10-12T01:00:00+00:00,SIM-B,evaporativa,137.8,169.8,110.2,40.0,15.7,23.4,login_fallido,evento_ot,1,evaluacion,True
2026-10-12T01:00:00+00:00,SIM-C,liquida,137.2,162.2,27.4,40.8,16.1,22.9,normal,fuga_agua,1,evaluacion,True
"""


@pytest.fixture
def df(tmp_path):
    ruta = tmp_path / "kit.csv"
    ruta.write_text(CSV_MINIMO, encoding="utf-8")
    return cargar(ruta, MAPEO)


def test_renombra_columnas_al_contrato(df):
    esperadas = {"timestamp", "kw_ti", "kw_total", "agua_reposicion_l", "t_exterior", "site_id"}
    assert esperadas <= set(df.columns)
    assert "energy_it_kwh" not in df.columns
    assert "water_l" not in df.columns


def test_descarta_columnas_prohibidas(df):
    assert "simulated_anomaly" not in df.columns
    assert "is_simulated" not in df.columns


def test_deriva_etiqueta_tipo_desde_scenario(df):
    assert set(df["etiqueta_tipo"].unique()) == {"normal", "falla", "evento_ot"}
    # Dos escenarios distintos ('ineficiencia' y 'fuga_agua') caen en 'falla'.
    assert (df["etiqueta_tipo"] == "falla").sum() == 2


def test_deriva_etiqueta_particion_desde_split(df):
    assert set(df["etiqueta_particion"].unique()) == {"entrenamiento", "evaluacion"}


def test_etiqueta_escenario_vacia_cuando_scenario_es_base(df):
    normales = df[df["etiqueta_tipo"] == "normal"]
    assert (normales["etiqueta_escenario"] == "").all()


def test_etiqueta_escenario_preserva_otros_valores(df):
    no_normales = df[df["etiqueta_tipo"] != "normal"]
    assert set(no_normales["etiqueta_escenario"].unique()) == {
        "ineficiencia", "fuga_agua", "evento_ot",
    }


def test_ordenado_por_site_id_y_timestamp(df):
    for site, grupo in df.groupby("site_id"):
        ts = pd.to_datetime(grupo["timestamp"])
        assert ts.is_monotonic_increasing, f"timestamp no ordenado para {site}"


def test_cumple_contrato_validar(df):
    problemas = contrato.validar(df)
    assert problemas == [], f"problemas encontrados: {problemas}"


def test_validar_detecta_timestamp_duplicado_por_sitio(df):
    # Después del sort por (site_id, timestamp), idx 2 es SIM-B/00:00; si lo
    # cambio a SIM-A, SIM-A queda con dos filas a las 00:00 → duplicado.
    duplicado = df.copy()
    duplicado.loc[2, "site_id"] = "SIM-A"
    problemas = contrato.validar(duplicado)
    assert any("SIM-A" in p and "duplicado" in p for p in problemas), problemas


def test_etiquetas_del_kit_no_entran_al_modelo(df):
    # M1 (plan-ejecucion): tras cargar el kit, ninguna columna 'etiqueta_*' ni
    # las columnas crudas del kit (scenario/split/simulated_anomaly) deben
    # entrar como variable del modelo.
    columnas = contrato.columnas_del_modelo(df)
    assert not any(c.startswith("etiqueta_") for c in columnas), (
        f"Fuga de etiquetas: {[c for c in columnas if c.startswith('etiqueta_')]}"
    )
    for prohibida in ("scenario", "split", "simulated_anomaly", "is_simulated"):
        assert prohibida not in columnas, f"'{prohibida}' llegó al modelo"
