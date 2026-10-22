"""Explicación de cada alerta (src/modelo/explicar.py, issue #8).

Todo con datos SINTÉTICOS: filas hechas a mano, src/sinteticos.py o app.kit.ejemplo()
(datos inventados con el formato del kit). El kit real nunca entra a las pruebas.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from app import kit
from src.ataques import correr_rejilla, rejilla
from src.ataques.evaluar import evaluar
from src.ataques.inyectar import inyectar
from src.datos.cargar import cargar
from src.modelo import detector, explicar
from src.sinteticos import generar

RAIZ = Path(__file__).resolve().parents[1]
MAPEO = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))


def _fila(clase="normal", energia=0.0, agua=0.0, entrada=0.0, excesos=()):
    """Una hora de salida del detector con solo lo que explicar() necesita."""
    return {
        "clase": clase,
        "residuo_energia_pct": energia,
        "residuo_agua_pct": agua,
        "residuo_entrada_c": entrada,
        "exceso_energia": "energia" in excesos,
        "exceso_agua": "agua" in excesos,
        "exceso_entrada": "entrada" in excesos,
    }


def _una(**kw) -> pd.Series:
    return explicar.explicar(pd.DataFrame([_fila(**kw)])).iloc[0]


# ------------------------------------------------------------ variable_principal

def test_solo_energia():
    r = _una(clase="escalon_sin_registro", energia=31.0, excesos=("energia",))
    assert r["variable_principal"] == "energia"
    assert r["tipo_sugerido"] == "ineficiencia"


def test_solo_agua():
    r = _una(clase="escalon_sin_registro", agua=40.0, excesos=("agua",))
    assert r["variable_principal"] == "agua"
    assert r["tipo_sugerido"] == "ineficiencia"


def test_solo_entrada():
    r = _una(clase="escalon_sin_registro", entrada=1.2, excesos=("entrada",))
    assert r["variable_principal"] == "entrada"
    assert r["tipo_sugerido"] == "ineficiencia"


def test_gana_el_mayor_residuo_relativo():
    assert _una(clase="escalon_sin_registro", energia=10.0, agua=40.0,
                excesos=("energia", "agua"))["variable_principal"] == "agua"
    # 3 °C de entrada equivalen a 18 % (0.5 °C ↔ 3 %): pesa más que +10 % de energía.
    assert _una(clase="escalon_sin_registro", energia=10.0, entrada=3.0,
                excesos=("energia", "entrada"))["variable_principal"] == "entrada"
    # 1 °C equivale a 6 %: pesa menos que +10 % de energía.
    assert _una(clase="escalon_sin_registro", energia=10.0, entrada=1.0,
                excesos=("energia", "entrada"))["variable_principal"] == "energia"


def test_solo_cuentan_las_variables_con_exceso():
    # El agua tiene un residuo más grande, pero el detector no la marcó.
    r = _una(clase="escalon_sin_registro", energia=8.0, agua=50.0, excesos=("energia",))
    assert r["variable_principal"] == "energia"


def test_empate_sigue_el_orden_energia_agua_entrada():
    assert _una(clase="escalon_sin_registro", energia=20.0, agua=20.0,
                excesos=("energia", "agua"))["variable_principal"] == "energia"
    # 6 % de energía y 1 °C de entrada pesan lo mismo (2 veces el mínimo del detector).
    assert _una(clase="escalon_sin_registro", energia=6.0, entrada=1.0,
                excesos=("energia", "entrada"))["variable_principal"] == "energia"
    assert _una(clase="escalon_sin_registro", agua=6.0, entrada=1.0,
                excesos=("agua", "entrada"))["variable_principal"] == "agua"


def test_residuo_vacio_no_le_gana_a_uno_con_valor():
    r = _una(clase="escalon_sin_registro", energia=float("nan"), agua=5.0, excesos=("energia", "agua"))
    assert r["variable_principal"] == "agua"


# ------------------------------------------------------------ tipo_sugerido

def test_clase_ot_sin_exceso_fisico():
    r = _una(clase="cambio_no_autorizado")
    assert r["variable_principal"] == ""
    assert r["tipo_sugerido"] == "posible_ataque"


def test_exceso_con_clase_ot():
    r = _una(clase="incidente_ot", energia=20.0, excesos=("energia",))
    assert r["variable_principal"] == "energia"
    assert r["tipo_sugerido"] == "posible_ataque"
    # La hora del cambio que coincide con un exceso que ya venía de antes.
    r = _una(clase="cambio_no_autorizado", agua=12.0, excesos=("agua",))
    assert (r["variable_principal"], r["tipo_sugerido"]) == ("agua", "posible_ataque")


def test_intento_de_acceso():
    # Un login fallido no prueba una intrusión, pero es un evento de seguridad: «posible».
    r = _una(clase="intento_acceso")
    assert r["variable_principal"] == ""
    assert r["tipo_sugerido"] == "posible_ataque"


def test_sin_alerta():
    r = _una(clase="normal", energia=-2.0, agua=1.0, entrada=0.1)
    assert r["variable_principal"] == ""
    assert r["tipo_sugerido"] == "normal"


def test_cada_clase_tiene_tipo():
    from src.ot import clases

    assert set(explicar.TIPO_POR_CLASE) == set(clases.CLASES) | {"normal"}
    assert set(explicar.TIPO_POR_CLASE.values()) == {"normal", "ineficiencia", "posible_ataque"}


# ------------------------------------------------------------ forma de la salida

def test_no_recalcula_ni_modifica_la_entrada():
    entrada = pd.DataFrame([_fila(clase="escalon_sin_registro", energia=31.0, excesos=("energia",)),
                            _fila()])
    copia = entrada.copy()
    salida = explicar.explicar(entrada)
    pd.testing.assert_frame_equal(entrada, copia)
    assert list(salida.columns) == list(entrada.columns) + ["variable_principal", "tipo_sugerido"]
    pd.testing.assert_frame_equal(salida[entrada.columns], entrada)


def test_es_idempotente():
    una = explicar.explicar(pd.DataFrame([_fila(clase="intento_acceso")]))
    dos = explicar.explicar(una)
    pd.testing.assert_frame_equal(una, dos)


def test_faltan_columnas_o_clase_desconocida():
    with pytest.raises(ValueError, match="exceso_agua"):
        explicar.explicar(pd.DataFrame([_fila()]).drop(columns="exceso_agua"))
    with pytest.raises(ValueError, match="ataque_raro"):
        explicar.explicar(pd.DataFrame([_fila(clase="ataque_raro")]))


# ------------------------------------------------------------ con el detector real

@pytest.fixture(scope="module")
def telemetria(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("kit") / "ejemplo.csv"
    kit.ejemplo().to_csv(ruta, index=False)
    return cargar(ruta, MAPEO)


@pytest.fixture(scope="module")
def alertas(telemetria):
    return explicar.explicar(detector.detectar(telemetria))


def test_sobre_el_detector_variable_solo_con_alerta_fisica(alertas):
    fisica = alertas["alerta_umbral"] | alertas["alerta_media_4h"]
    assert fisica.any()
    assert (alertas.loc[fisica, "variable_principal"] != "").all()
    assert (alertas.loc[~fisica, "variable_principal"] == "").all()
    # La variable elegida siempre es una que el detector marcó.
    for variable in explicar.VARIABLES:
        elegida = alertas["variable_principal"] == variable
        assert alertas.loc[elegida, f"exceso_{variable}"].all()


def test_sobre_el_detector_tipo_coherente_con_la_clase(alertas):
    assert set(alertas["tipo_sugerido"]) <= {"normal", "ineficiencia", "posible_ataque"}
    assert ((alertas["tipo_sugerido"] == "normal") == (alertas["clase"] == "normal")).all()
    assert ((alertas["tipo_sugerido"] == "ineficiencia")
            == (alertas["clase"] == "escalon_sin_registro")).all()


def test_cli_enriquece_un_csv(alertas, tmp_path, monkeypatch, capsys):
    entrada, salida = tmp_path / "alertas.csv", tmp_path / "explicadas.csv"
    sin_explicar = alertas.drop(columns=["variable_principal", "tipo_sugerido"])
    sin_explicar.to_csv(entrada, index=False)
    monkeypatch.setattr(sys, "argv", ["explicar", "--alertas", str(entrada), "--salida", str(salida)])
    explicar.main()
    leidas = pd.read_csv(salida)
    assert list(leidas.columns) == list(detector.COLUMNAS_SALIDA) + ["variable_principal", "tipo_sugerido"]
    assert leidas["variable_principal"].fillna("").tolist() == alertas["variable_principal"].tolist()
    assert leidas["tipo_sugerido"].tolist() == alertas["tipo_sugerido"].tolist()
    assert "tipo_sugerido" in capsys.readouterr().out


def test_la_app_ignora_las_columnas_nuevas(alertas):
    from app import cargar as app_cargar
    from app import linea_base

    unida = app_cargar.unir(kit.ejemplo(), alertas[linea_base.COLUMNAS + ["accion"]])
    assert len(unida) == len(kit.ejemplo())


# ------------------------------------------------------------ evaluador (#10)

@pytest.fixture(scope="module")
def escenarios():
    out, _ = inyectar(generar(dias=14))
    return out


def _alertas_de(escenarios, clase_ataque):
    """Salida tipo detector: marca las horas de cada escenario y les pone una clase."""
    tipo = escenarios["etiqueta_tipo"]
    clase = tipo.map({"ataque": clase_ataque, "falla": "escalon_sin_registro"}).fillna("normal")
    filas = pd.DataFrame([_fila(clase=c, energia=25.0, excesos=("energia",)) if c != "normal" else _fila()
                          for c in clase])
    filas.insert(0, "timestamp", escenarios["timestamp"].to_numpy())
    enriquecidas = explicar.explicar(filas)
    # Como el resto de evaluadores (src/evaluacion): anomalía = cualquier clase distinta de normal.
    return enriquecidas.assign(anomalia=enriquecidas["clase"] != "normal")


def test_evaluar_reporta_clasificacion_con_alertas_enriquecidas(escenarios):
    tabla, _ = evaluar(escenarios, _alertas_de(escenarios, "incidente_ot"))
    assert "clasificacion_correcta_pct" in tabla.columns
    assert tabla["detectado"].all()
    assert (tabla["clasificacion_correcta_pct"] == 100).all()


def test_evaluar_un_ataque_sin_registro_ot_sale_como_ineficiencia(escenarios):
    # Límite declarado (docs/06 §7.5): un exceso sin evento OT no distingue falla de ataque.
    tabla, _ = evaluar(escenarios, _alertas_de(escenarios, "escalon_sin_registro"))
    assert (tabla.loc[tabla["tipo"] == "ataque", "clasificacion_correcta_pct"] == 0).all()
    assert (tabla.loc[tabla["tipo"] == "falla", "clasificacion_correcta_pct"] == 100).all()


# ------------------------------------------------------------ rejilla (U2)

@pytest.fixture(scope="module")
def corrida(telemetria):
    seleccion = [rejilla.POR_NOMBRE[n] for n in ("energia_+80", "cambio_sin_registro", "cambio_con_efecto")]
    return correr_rejilla.correr(rejilla._preparar(telemetria), semillas_ruido=(), rejilla_=seleccion,
                                 inicios_h=(6,))


def test_rejilla_mide_la_clasificacion_por_tipo(corrida):
    t = corrida[0]
    ds = t[t["metodo"] == "dripsafe"].set_index(["site_id", "nombre"])
    assert {"tipo_esperado", "tipo_obtenido", "clasificacion_correcta_pct"} <= set(t.columns)
    assert t.loc[t["metodo"] == "reglas_kit", "clasificacion_correcta_pct"].isna().all()
    vistas = ds[ds["efecto_visto"]]
    assert len(vistas)
    por_nombre = vistas.groupby(level="nombre")["clasificacion_correcta_pct"].mean()
    assert por_nombre["energia_+80"] == 100.0
    assert por_nombre["cambio_con_efecto"] == 100.0
    # Ataque sin registro OT: sale como ineficiencia (límite declarado, docs/06 §7.5).
    assert por_nombre["cambio_sin_registro"] == 0.0
    resumen = correr_rejilla.resumir(t)
    assert "clasificacion_correcta_pct" in resumen.columns


def test_rejilla_no_cambia_el_bloque_para_numeros_oficiales(corrida):
    por_inyeccion, limpia, coincidencias, _ = corrida
    bloque = correr_rejilla.bloque_deteccion(por_inyeccion, limpia, coincidencias, "ejemplo")
    curva = bloque["deteccion"]["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"]
    assert curva and all("clasificacion_correcta_pct" not in f for f in curva)
    assert "clasificacion_correcta_pct" not in json.dumps(bloque)
