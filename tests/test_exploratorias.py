"""Pruebas exploratorias (src/ataques/exploratorias.py): piso, rampa lenta y ataque con calor.

Se usa app.kit.ejemplo(): datos INVENTADOS con el formato del kit. El kit real
nunca entra a las pruebas ni al repositorio.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from app import kit
from src.ataques import exploratorias, rejilla
from src.datos.cargar import cargar
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[1]
MAPEO = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("kit") / "ejemplo.csv"
    kit.ejemplo().to_csv(ruta, index=False)
    return rejilla._preparar(cargar(ruta, MAPEO))


@pytest.fixture(scope="module")
def params(base):
    return detector.entrenar(base)


def test_piso_lee_los_umbrales_del_detector_congelado(params):
    piso = exploratorias.piso(params)
    assert len(piso) == 3 * len(params)
    for f in piso.itertuples():
        assert f.umbral_hora == round(params[f.site_id]["limites"][f.variable], 2)
        assert 0 < f.umbral_media_4h <= f.umbral_hora  # la media de 4 h ve excesos más chicos


def test_una_rampa_empinada_se_ve_y_queda_como_escalon(base, params):
    r = exploratorias.rampas(base, params, pendientes=(2.0,), inicios_h=(6,), largo_h=12)
    hechas = r[~r["omitida"]]
    assert len(hechas) == base["site_id"].nunique()
    assert hechas["vista"].all()
    assert (hechas["clase_al_ver"] == "escalon_sin_registro").all()
    assert (hechas["pct_al_ver"] <= 24).all() and (hechas["kwh_antes_de_ver"] >= 0).all()


def test_si_una_prueba_toca_el_entrenamiento_se_detiene(base, params):
    copia = base.copy()
    entrenamiento = copia.index[copia["etiqueta_particion"] != "evaluacion"]
    copia.loc[entrenamiento[:3], "kw_total"] *= 1.5
    with pytest.raises(AssertionError, match="ajuste o calibración"):
        exploratorias._detectar_igual(params, copia)


def test_el_calor_solo_no_genera_alertas_y_si_sale_del_clima_aprendido(base, params):
    c = exploratorias.calor(base, params, ataques_pct=(0,))
    assert len(c) > 0
    assert not c["vista"].any()                                     # el calor explicado no alerta
    assert (c["horas_fuera_de_clima"] == len(exploratorias.HORAS_TARDE)).all()  # umbral ×2 en todas


def test_un_ataque_grande_con_calor_se_sigue_viendo(base, params):
    c = exploratorias.calor(base, params, ataques_pct=(80,))
    assert c["vista"].all()


def test_el_resumen_solo_trae_agregados(base, params):
    r = exploratorias.resumen(params, exploratorias.rampas(base, params, pendientes=(1.0,)),
                              exploratorias.calor(base, params, ataques_pct=(0, 30)))
    texto = json.dumps(r, ensure_ascii=False)
    assert "fuera de la rejilla fijada" in r["_meta"]["aviso"]
    assert "timestamp" not in texto and "20" + "26-" not in texto   # sin fechas ni filas
    assert {f["ataque_pct"] for f in r["calor"]} == {0, 30}
    assert all(np.isfinite(f["rampas"]) for f in r["rampas"])
