"""Casos sintéticos para el cierre N2; ninguna fila del kit entra a Git."""

import copy

import pandas as pd
import pytest

from src.ataques import rejilla
from src.evaluacion import cerrar_n2


def _manifiesto():
    return {"rejilla": [rejilla.ficha_publica(i.__dict__) for i in rejilla.REJILLA],
            "inicios_h": list(rejilla.INICIOS_H), "margen_h": rejilla.MARGEN_H,
            "sin_ot_previo_h": rejilla.SIN_OT_PREVIO_H,
            "ruido": {"energia_pct_ti": rejilla.RUIDO_ENERGIA_PCT_TI,
                      "agua_pct": rejilla.RUIDO_AGUA_PCT}}


def _inyecciones():
    return pd.DataFrame([
        {"condicion": "base", "semilla": None, "site_id": "A", "nombre": "cambio_con_efecto",
         "grupo": "cambio_con_efecto", "variable": "energia", "magnitud_pct": 20,
         "metodo": "dripsafe", "clase_esperada": "incidente_ot", "detectado": True,
         "horas_hasta_detectar": 0, "efecto_visto": True, "horas_hasta_ver_efecto": 0,
         "inyectado_kwh": 10.0, "no_visto_kwh": 0.0, "inyectado_l": None,
         "no_visto_l": None, "clase_correcta_pct": 100.0,
         "clase_obtenida": "incidente_ot"},
        {"condicion": "base", "semilla": None, "site_id": "A", "nombre": "cambio_con_efecto",
         "grupo": "cambio_con_efecto", "variable": "energia", "magnitud_pct": 20,
         "metodo": "reglas_kit", "clase_esperada": "incidente_ot", "detectado": True,
         "horas_hasta_detectar": 0, "efecto_visto": False, "horas_hasta_ver_efecto": None,
         "inyectado_kwh": 10.0, "no_visto_kwh": 10.0, "inyectado_l": None,
         "no_visto_l": None, "clase_correcta_pct": None,
         "clase_obtenida": None},
    ])


def test_episodio_ot_detectado_no_implica_efecto_fisico_visto():
    datos = _inyecciones()
    cerrar_n2._validar_rejilla(_manifiesto(), datos)
    denominadores = pd.DataFrame({"condicion": ["base"], "semilla": [None],
                                  "site_id": ["A"], "nombre": ["cambio_con_efecto"],
                                  "planeadas": [2], "ejecutadas": [1], "omitidas": [1]})
    tabla = cerrar_n2._tabla_inyecciones(datos, denominadores).set_index("metodo")
    assert tabla.loc["reglas_kit", "tp_episodios"] == 1
    assert tabla.loc["reglas_kit", "efectos_vistos"] == 0
    assert tabla.loc["reglas_kit", "pct_no_visto"] == 100
    assert tabla.loc["reglas_kit", "clases_evaluadas"] == 0
    assert tabla.loc["dripsafe", "clases_evaluadas"] == 1
    assert tabla.loc["dripsafe", "omitidas"] == 1


@pytest.mark.parametrize(("cambio", "error"), [
    ({"horas_hasta_detectar": None}, "latencia"),
    ({"no_visto_kwh": 11.0}, "inyectado/no visto"),
    ({"clase_correcta_pct": None}, "Clase condicional"),
])
def test_rechaza_resultados_incoherentes(cambio, error):
    tabla = _inyecciones()
    for clave, valor in cambio.items():
        tabla.loc[0, clave] = valor
    with pytest.raises(ValueError, match=error):
        cerrar_n2._validar_rejilla(_manifiesto(), tabla)


def _bloques():
    filas = []
    for metodo in cerrar_n2.METODOS:
        for sitio in ("SIM-A", "SIM-B", "SIM-C", "TOTAL"):
            n = 3 if sitio == "TOTAL" else 1
            filas.append({"metodo": metodo, "site_id": sitio, "episodios_verdaderos": n,
                          "horas_anomalas": 21 if sitio == "TOTAL" else 7,
                          "tp_episodios": n, "fp_episodios": 0, "fn_episodios": 0})
    curva, ruido = [], []
    for ficha in rejilla.REJILLA:
        for metodo in cerrar_n2.METODOS:
            base = {"nombre": ficha.nombre, "metodo": metodo}
            curva.append({**base, "inyecciones": 2, "pct_efectos_vistos": 50.0,
                          "no_visto": 5.0})
            ruido.append({**base, "semillas": 5, "pct_efectos_vistos_media": 50.0,
                          "pct_efectos_vistos_min": 0.0, "pct_efectos_vistos_max": 100.0})
    cierre = {"_meta": {"aviso": "DATOS SIMULADOS"}, "originales_por_metodo_sitio": filas,
              "curva_base": [{"nombre": f["nombre"], "metodo": f["metodo"],
                              "inyecciones": 2, "pct_efectos_vistos": 50.0, "no_visto": 5.0,
                              "tp_episodios": 2, "fn_episodios": 0, "recall_episodios_pct": 100.0,
                              "efectos_vistos": 1, "latencia_episodio_mediana_h": 0.0}
                             for f in curva],
              "ruido_por_escenario": [{"nombre": f["nombre"], "metodo": f["metodo"],
                                         "semillas": 5, "inyecciones": 10, "tp_episodios": 8,
                                         "fn_episodios": 2, "recall_episodios_pct": 80.0,
                                         "recall_episodios_min_pct": 60.0,
                                         "recall_episodios_max_pct": 100.0,
                                         "efectos_vistos": 5, "pct_efectos_vistos": 50.0,
                                         "pct_efectos_vistos_min": 0.0,
                                         "pct_efectos_vistos_max": 100.0}
                                        for f in ruido],
              "falsas_alarmas_base_y_ruido": [
                  {"condicion": "ruido", "semilla": s, "site_id": "TOTAL", "metodo": metodo,
                   "falsas_alarmas_por_dia_sitio": 0.2 if metodo == "dripsafe" else 0.0}
                  for s in range(1, 6) for metodo in cerrar_n2.METODOS]}
    bloque = {"comparacion_contra_reglas_kit": {
        "episodios_originales_kit": {f"{pref}_{k}": 3 if k == "tp" else 0
                                     for pref in ("dripsafe", "reglas") for k in ("tp", "fp", "fn")},
        "rejilla_inyecciones": {"datos_curva": curva},
        "robustez_ruido": {"resultado": ruido}}}
    return bloque, cierre


def test_integra_recall_y_efecto_y_no_modifica_el_insumo_u2():
    bloque, cierre = _bloques()
    anterior = copy.deepcopy(bloque)
    salida = cerrar_n2.integrar(bloque, cierre, 3, 21)
    assert bloque == anterior
    curva = salida["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"][0]
    assert curva["tp_episodios"] == 2 and curva["efectos_vistos"] == 1
    ruido = salida["comparacion_contra_reglas_kit"]["robustez_ruido"]
    assert ruido["resultado"][0]["recall_episodios_pct"] == 80
    assert ruido["falsas_alarmas_por_dia_sitio_media_por_metodo"] == {
        "dripsafe": 0.2, "reglas_kit": 0.0}


def test_integra_rechaza_discrepancias_de_u2():
    bloque, cierre = _bloques()
    bloque["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"][0]["no_visto"] = 6.0
    with pytest.raises(ValueError, match="difieren en la curva"):
        cerrar_n2.integrar(bloque, cierre, 3, 21)
