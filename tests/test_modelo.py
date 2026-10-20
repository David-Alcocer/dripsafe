"""Pruebas del detector (src/modelo/detector.py) con datos inventados.

Nunca se usa el kit real: se genera un CSV con el mismo formato (3 sitios ×
168 h), se pasa por ``src.datos.cargar.cargar`` y se prueba el contrato 3 v2.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import contrato
from src.datos.cargar import cargar
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[1]
MAPEO = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))

# (sitio, tecnología, kWh IT base, overhead no TI/IT, agua L/kWh IT)
SITIOS = [
    ("SIM-A", "aire", 250.0, 0.33, 0.03),
    ("SIM-B", "evaporativa", 143.0, 0.21, 1.06),
    ("SIM-C", "liquida", 100.0, 0.17, 0.22),
]


def _kit_sintetico(semilla: int = 7) -> pd.DataFrame:
    """3 sitios × 168 h con el formato crudo del kit (sin datos reales)."""
    rng = np.random.default_rng(semilla)
    horas = pd.date_range("2026-10-12", periods=168, freq="h", tz="UTC")
    hora = horas.hour.to_numpy()
    filas = []

    for sitio, tipo, base, overhead, wue in SITIOS:
        perfil = 1.0 + 0.15 * np.sin(2 * np.pi * (hora - 9) / 24)
        it = base * perfil + rng.normal(0, base * 0.01, len(horas))
        exterior = 23.0 + 5.0 * np.sin(2 * np.pi * (hora - 9) / 24) + rng.normal(0, 0.3, len(horas))
        entrada = 22.5 + 0.10 * np.clip(exterior - 20.0, 0.0, None) + rng.normal(0, 0.15, len(horas))

        # Ruido uniforme de ±1.5 % de la energía IT, como el kit.
        ruido = rng.uniform(-0.015, 0.015, len(horas)) * it
        total = it * (1.0 + overhead) + ruido
        agua = it * wue

        filas.append(pd.DataFrame({
            "timestamp": horas,
            "site_id": sitio,
            "cooling_type": tipo,
            "energy_it_kwh": it,
            "energy_total_kwh": total,
            "water_l": agua,
            "load_pct": it / base * 40.0,
            "outdoor_temp_c": exterior,
            "inlet_temp_c": entrada,
            "ot_event": "normal",
            "scenario": "base",
            "simulated_anomaly": 0,
            "split": np.where(np.arange(len(horas)) < 72, "referencia", "evaluacion"),
            "is_simulated": True,
        }))

    return pd.concat(filas, ignore_index=True)


def _cargar(df: pd.DataFrame, tmp_path: Path) -> pd.DataFrame:
    ruta = tmp_path / f"kit_{len(list(tmp_path.iterdir()))}.csv"
    df.to_csv(ruta, index=False)
    return cargar(ruta, MAPEO)


def _ventana(df: pd.DataFrame, sitio: str, inicio_eval: int, horas: int, columna: str = "timestamp") -> pd.Index:
    """Índices de ``horas`` filas desde ``inicio_eval`` horas después de la evaluación."""
    horas_sitio = df.loc[df["site_id"] == sitio, "timestamp"].sort_values().reset_index(drop=True)
    inicio = horas_sitio.iloc[72 + inicio_eval]
    fin = inicio + pd.Timedelta(hours=horas)
    return df.index[
        (df["site_id"] == sitio) & (df[columna] >= inicio) & (df[columna] < fin)
    ]


def _exceso_energia(df: pd.DataFrame, sitio: str, inicio_eval: int, horas: int, pct: float) -> None:
    """Sube la energía NO TI un ``pct`` % durante ``horas``."""
    idx = _ventana(df, sitio, inicio_eval, horas)
    no_ti = df.loc[idx, "energy_total_kwh"] - df.loc[idx, "energy_it_kwh"]
    df.loc[idx, "energy_total_kwh"] = df.loc[idx, "energy_it_kwh"] + no_ti * (1.0 + pct / 100.0)


def _rampa(df: pd.DataFrame, sitio: str, inicio_eval: int, horas: int, pct_hora: float) -> None:
    """Rampa lineal sobre la energía no TI: +pct_hora % por cada hora."""
    idx = _ventana(df, sitio, inicio_eval, horas).sort_values()
    base = df.loc[idx, "energy_total_kwh"] - df.loc[idx, "energy_it_kwh"]
    for k, i in enumerate(idx):
        df.loc[i, "energy_total_kwh"] = df.loc[i, "energy_it_kwh"] + base.loc[i] * (
            1.0 + pct_hora / 100.0 * (k + 1)
        )


@pytest.fixture
def kit(tmp_path):
    return _cargar(_kit_sintetico(), tmp_path)


def test_salida_tiene_columnas_y_una_fila_por_sitio_y_hora(kit):
    salida = detector.detectar(kit)
    assert list(salida.columns) == detector.COLUMNAS_SALIDA
    assert len(salida) == 3 * 168
    assert not salida.duplicated(["site_id", "timestamp"]).any()
    assert set(salida["site_id"]) == {"SIM-A", "SIM-B", "SIM-C"}
    assert contrato.validar(kit) == []


def test_cambiar_etiquetas_no_cambia_la_salida(tmp_path):
    df = _kit_sintetico()
    _exceso_energia(df, "SIM-A", inicio_eval=30, horas=4, pct=25)
    otro = df.copy()
    otro["scenario"] = "base"
    otro["simulated_anomaly"] = 0
    otro["is_simulated"] = True

    normal = detector.detectar(_cargar(df, tmp_path))
    sin_etiquetas = detector.detectar(_cargar(otro, tmp_path))
    pd.testing.assert_frame_equal(normal, sin_etiquetas)


def test_sin_fallas_casi_no_hay_alertas_fisicas(kit):
    salida = detector.detectar(kit)
    fisicas = salida["alerta_umbral"] | salida["alerta_media_4h"]
    assert int(fisicas.sum()) == 0
    assert (salida["clase"] == "normal").all()


def test_detecta_25_pct_de_energia_en_el_sitio_liquido(tmp_path):
    df = _kit_sintetico()
    _exceso_energia(df, "SIM-C", inicio_eval=30, horas=4, pct=25)
    datos = _cargar(df, tmp_path)

    idx = _ventana(datos, "SIM-C", inicio_eval=30, horas=4)
    # Las reglas del kit no lo verían: el PUE sigue por debajo de 1.6.
    assert (datos.loc[idx, "kw_total"] / datos.loc[idx, "kw_ti"]).max() < 1.6

    salida = detector.detectar(datos)
    ventana = salida.loc[idx]
    fisicas = ventana["alerta_umbral"] | ventana["alerta_media_4h"]
    assert fisicas.any()
    assert set(ventana.loc[fisicas, "clase"]) == {"escalon_sin_registro"}


def test_detecta_una_rampa_de_1_pct_por_hora(tmp_path):
    df = _kit_sintetico()
    _rampa(df, "SIM-A", inicio_eval=30, horas=24, pct_hora=1.0)
    datos = _cargar(df, tmp_path)
    idx = _ventana(datos, "SIM-A", inicio_eval=30, horas=24)

    salida = detector.detectar(datos)
    fisicas = salida.loc[idx, "alerta_umbral"] | salida.loc[idx, "alerta_media_4h"]
    assert fisicas.any()
    assert "escalon_sin_registro" in set(salida.loc[idx, "clase"])


def test_exceso_despues_de_cambio_de_configuracion_es_incidente(tmp_path):
    df = _kit_sintetico()
    evento = _ventana(df, "SIM-C", inicio_eval=10, horas=1)
    df.loc[evento, "ot_event"] = "cambio_config_no_autorizado"
    _exceso_energia(df, "SIM-C", inicio_eval=12, horas=4, pct=40)
    datos = _cargar(df, tmp_path)
    exceso = _ventana(datos, "SIM-C", inicio_eval=12, horas=4)

    salida = detector.detectar(datos)
    assert set(salida.loc[exceso, "clase"]) == {"incidente_ot"}


def test_clima_no_visto_alerta_con_confianza_baja(tmp_path):
    df = _kit_sintetico()
    idx = _ventana(df, "SIM-C", inicio_eval=40, horas=1)
    df.loc[idx, "outdoor_temp_c"] = 45.0
    _exceso_energia(df, "SIM-C", inicio_eval=40, horas=1, pct=100)
    datos = _cargar(df, tmp_path)
    exceso = _ventana(datos, "SIM-C", inicio_eval=40, horas=1)

    salida = detector.detectar(datos)
    fila = salida.loc[exceso].iloc[0]
    assert bool(fila["clima_no_visto"])
    assert fila["clase"] != "normal"
    assert "confianza baja" in fila["motivo"]


def test_clases_de_eventos_ot_sin_efecto(tmp_path):
    df = _kit_sintetico()
    login = _ventana(df, "SIM-C", inicio_eval=20, horas=3)
    cambio = _ventana(df, "SIM-C", inicio_eval=23, horas=2)
    df.loc[login, "ot_event"] = "login_fallido"
    df.loc[cambio, "ot_event"] = "cambio_config_no_autorizado"
    datos = _cargar(df, tmp_path)
    login = _ventana(datos, "SIM-C", inicio_eval=20, horas=3)
    cambio = _ventana(datos, "SIM-C", inicio_eval=23, horas=2)

    salida = detector.detectar(datos)
    assert set(salida.loc[login, "clase"]) == {"intento_acceso"}
    assert set(salida.loc[cambio, "clase"]) == {"cambio_no_autorizado"}
    assert (salida.loc[login.union(cambio), "motivo"] != "").all()
