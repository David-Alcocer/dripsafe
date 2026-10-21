"""La vista previa del dashboard (app/linea_base.py) clasifica igual que src/ot/clases.py.

Si la demo cae en la vista previa (falta alertas.csv), las clases no pueden cambiar.
Casos de docs/06 §4 que la copia anterior resolvía distinto. Datos INVENTADOS.
"""

import numpy as np
import pandas as pd
import pytest

from app import linea_base
from src.ot import clases


def _sitio(n=60):
    horas = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"timestamp": horas, "alerta_umbral": np.zeros(n, bool),
                         "alerta_media_4h": np.zeros(n, bool), "_ot": ["normal"] * n})


def _igual_que_oficial(o):
    vista = linea_base._clasificar(o)
    oficial = clases.clasificar(o.rename(columns={"_ot": "ot_event"}))["clase"]
    pd.testing.assert_series_equal(vista, oficial, check_names=False)
    return vista


def test_login_en_una_hora_con_exceso_es_escalon():
    """Caso 9: el exceso es más grave que el intento."""
    o = _sitio()
    o.loc[10, "_ot"] = "login_fallido"
    o.loc[8:12, "alerta_umbral"] = True
    assert _igual_que_oficial(o).loc[10] == "escalon_sin_registro"


def test_exceso_que_empieza_25_h_despues_no_se_atribuye():
    """Caso 2: la ventana es de 24 h después de la última hora del evento, no de 25."""
    o = _sitio()
    o.loc[10, "_ot"] = "cambio_config_no_autorizado"
    o.loc[35:38, "alerta_umbral"] = True       # empieza 25 h después
    vista = _igual_que_oficial(o)
    assert (vista.loc[35:38] == "escalon_sin_registro").all()
    assert vista.loc[10] == "cambio_no_autorizado"


def test_un_segundo_cambio_no_baja_un_incidente():
    """Caso 5: precedencia; ninguna regla baja la clase que ya tiene una hora."""
    o = _sitio()
    o.loc[10, "_ot"] = "cambio_config_no_autorizado"
    o.loc[14:20, "alerta_umbral"] = True
    o.loc[16, "_ot"] = "cambio_config_no_autorizado"
    assert (_igual_que_oficial(o).loc[14:20] == "incidente_ot").all()


@pytest.mark.parametrize("semilla", range(5))
def test_casos_al_azar_coinciden(semilla):
    rng = np.random.default_rng(semilla)
    o = _sitio(120)
    o["alerta_umbral"] = rng.random(120) < 0.08
    o["alerta_media_4h"] = rng.random(120) < 0.05
    o["_ot"] = rng.choice(["normal", "login_fallido", "cambio_config_no_autorizado"], 120, p=[0.9, 0.05, 0.05])
    _igual_que_oficial(o)
