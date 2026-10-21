"""Genera el contrato 4 canónico y la vista plana de Leo a partir de agregados.

Uso: python -m src.metricas.generar_numeros --entrada data/procesado/telemetria.csv
     --alertas data/resultados/alertas.csv
     --deteccion data/resultados/deteccion_para_numeros_oficiales.json
     --clima data/clima/merida_era5_2025.json
Las entradas por fila permanecen bajo data/ (ignorado por Git).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from app.cargar import adaptar_oficial
from src import contrato
from src.metricas.impacto import exceso_no_ti, pue_wue_por_sitio

RAIZ = Path(__file__).resolve().parents[2]
URL_CLIMA = ("https://archive-api.open-meteo.com/v1/archive?latitude=20.9674&longitude=-89.5926"
             "&start_date=2025-01-01&end_date=2025-12-31&hourly=temperature_2m&models=era5"
             "&timezone=America%2FMexico_City")


def metrica(valor, unidad, tipo, origen, responsable, *, periodo=None, nota=None,
            motivo=None, supuestos=None):
    dato = {"valor": valor, "unidad": unidad, "tipo": tipo, "origen": origen,
            "responsable": responsable, "estado": "pendiente" if valor is None else "disponible"}
    if periodo:
        dato["periodo"] = periodo
    if nota:
        dato["nota"] = nota
    if motivo:
        dato["motivo_pendiente"] = motivo
    if supuestos:
        dato["supuestos"] = supuestos
    return dato


def _r(valor, cifras=4):
    return round(float(valor), cifras)


def _periodo(tabla: pd.DataFrame, particion: str) -> dict:
    t = tabla[tabla["etiqueta_particion"] == particion]
    return {"inicio": pd.Timestamp(t["timestamp"].min()).isoformat(),
            "fin": pd.Timestamp(t["timestamp"].max()).isoformat(),
            "horas_sitio": len(t), "sitios": sorted(t["site_id"].unique().tolist()),
            "intervalo_h": 1, "fin_inclusivo": True}


def _totales(tabla: pd.DataFrame, particion: str) -> dict:
    sitios = pue_wue_por_sitio(tabla, particion=particion, unidad_energia="kwh_intervalo",
                              horas_por_intervalo=1)
    it = float(sitios["energia_it_kwh"].sum())
    total = float(sitios["energia_total_kwh"].sum())
    agua = float(sitios["agua_in_situ_l"].sum())
    return {"energia_it_kwh": _r(it), "energia_total_kwh": _r(total),
            "energia_no_ti_kwh": _r(total - it), "agua_in_situ_l": _r(agua),
            "pue": _r(total / it), "wue_in_situ_l_kwh": _r(agua / it),
            "sitios": [{"site_id": f.site_id, "horas": int(f.n_intervalos),
                        "energia_it_kwh": _r(f.energia_it_kwh),
                        "energia_total_kwh": _r(f.energia_total_kwh),
                        "agua_in_situ_l": _r(f.agua_in_situ_l), "pue": _r(f.pue),
                        "wue_in_situ_l_kwh": _r(f.wue_in_situ_l_kwh)}
                       for f in sitios.itertuples()]}


def _clima(ruta: Path | None) -> dict:
    pendiente = {f"umbral_{u}c": None for u in (27, 30, 33, 35)}
    if ruta is None or not ruta.exists():
        return {**pendiente, "tipo": "estimado", "estado": "pendiente", "responsable": "Nico (N4)",
                "motivo_pendiente": "Falta serie horaria climática verificable de Mérida."}
    j = json.loads(ruta.read_text(encoding="utf-8"))
    serie = j["hourly"]["temperature_2m"]
    fechas = j["hourly"]["time"]
    if len(serie) != 8760 or len(fechas) != 8760 or any(x is None for x in serie):
        raise ValueError("ERA5 debe traer las 8760 temperaturas horarias completas de 2025")
    if fechas[0] != "2025-01-01T00:00" or fechas[-1] != "2025-12-31T23:00":
        raise ValueError("El periodo ERA5 no es el año civil 2025")
    return {**{f"umbral_{u}c": sum(float(x) > u for x in serie) for u in (27, 30, 33, 35)},
            "tipo": "estimado", "estado": "disponible", "responsable": "Nico (N4)",
            "periodo": "2025-01-01/2025-12-31", "unidad": "h/año", "operador": ">",
            "fuente": "Open-Meteo Historical Weather API, ERA5, temperatura_2m, Mérida 20.9674,-89.5926, America/Mexico_City",
            "url": URL_CLIMA,
            "nota": "Temperatura exterior estimada; umbrales ilustrativos, no horas reales de operación del chiller."}


def construir(tabla: pd.DataFrame, alertas: pd.DataFrame, deteccion: dict,
             clima: Path | None = None) -> dict:
    problemas = contrato.validar(tabla)
    if problemas:
        raise ValueError(f"Telemetría inválida: {problemas}")
    tabla = tabla.copy()
    alertas = alertas.copy()
    tabla["timestamp"] = pd.to_datetime(tabla["timestamp"], utc=True)
    alertas["timestamp"] = pd.to_datetime(alertas["timestamp"], utc=True)
    alertas["anomalia"] = (alertas["alerta_umbral"].astype(bool) |
                           alertas["alerta_media_4h"].astype(bool))
    ref, ev = _totales(tabla, "entrenamiento"), _totales(tabla, "evaluacion")
    residuos = exceso_no_ti(tabla, alertas, columna_esperado="esperado_energia_no_ti_kwh",
                            columna_esperado_agua="esperado_agua_l",
                            unidad_energia="kwh_intervalo", horas_por_intervalo=1)
    exceso_kwh = float(residuos["exceso_no_ti_con_alerta_kwh"].sum())
    exceso_l = float(residuos["exceso_agua_con_alerta_l"].sum())
    todos_kwh = float(residuos["exceso_no_ti_estimado_kwh"].sum())
    todos_l = float(residuos["exceso_agua_in_situ_estimado_l"].sum())
    it = ev["energia_it_kwh"]
    pue_proy = (ev["energia_total_kwh"] - exceso_kwh) / it
    wue_proy = (ev["agua_in_situ_l"] - exceso_l) / it
    if pue_proy < 1 or wue_proy < 0:
        raise ValueError("Exceso mayor que el consumo observado")
    por_sitio = []
    for f in ev["sitios"]:
        s = residuos[residuos["site_id"] == f["site_id"]]
        ek = float(s["exceso_no_ti_con_alerta_kwh"].sum())
        el = float(s["exceso_agua_con_alerta_l"].sum())
        por_sitio.append({"site_id": f["site_id"], "horas": f["horas"],
                          "exceso_no_ti_con_alerta_kwh": _r(ek),
                          "exceso_agua_con_alerta_l": _r(el),
                          "pue_observado": f["pue"],
                          "pue_proyectado": _r((f["energia_total_kwh"] - ek) / f["energia_it_kwh"]),
                          "wue_observado_l_kwh": f["wue_in_situ_l_kwh"],
                          "wue_proyectado_l_kwh": _r((f["agua_in_situ_l"] - el) / f["energia_it_kwh"]),
                          "residuo_positivo_total_kwh": _r(s["exceso_no_ti_estimado_kwh"].sum()),
                          "residuo_positivo_total_l": _r(s["exceso_agua_in_situ_estimado_l"].sum())})
    # SIM-C, solo horas limpias de evaluación; margen físico hasta que PUE > 1.6.
    limpia = tabla[(tabla["site_id"] == "SIM-C") & (tabla["etiqueta_particion"] == "evaluacion") &
                   (tabla["etiqueta_tipo"] == "normal") & (tabla["ot_event"] == "normal")]
    no_ti = limpia["kw_total"] - limpia["kw_ti"]
    margen = (1.6 * limpia["kw_ti"] - limpia["kw_total"]) / no_ti * 100
    if limpia.empty or (no_ti <= 0).any() or (margen <= 0).any():
        raise ValueError("SIM-C carece de horas limpias válidas para punto ciego")
    punto = math.floor(float(margen.min()))
    # Comprobación: al subir solo el overhead, WUE, temperatura y OT siguen bajo los otros umbrales.
    if (limpia["agua_reposicion_l"] / limpia["kw_ti"] > 1.5).any() or \
            (limpia["inlet_temp_c"] > 29).any():
        raise ValueError("Otra regla dispara en la muestra limpia de SIM-C")
    horas_ref = tabla.loc[tabla["etiqueta_particion"] == "entrenamiento", "timestamp"].nunique()
    base_h = ref["energia_no_ti_kwh"] / horas_ref  # los tres sitios sumados, por hora común
    agua_evap = next(s for s in ref["sitios"] if s["site_id"] == "SIM-B")["agua_in_situ_l"] / horas_ref
    sup = {"fallas_por_sitio_al_anio": 6, "exceso_pct_no_ti": 20, "horas_sin_alerta": 72,
           "horas_con_alerta_hasta_correccion": 4,
           "energia_no_ti_referencia_kwh_por_hora_tres_sitios": _r(base_h),
           "agua_sim_b_referencia_l_por_hora": _r(agua_evap)}
    horas_ev = sup["fallas_por_sitio_al_anio"] * (sup["horas_sin_alerta"] - sup["horas_con_alerta_hasta_correccion"])
    anual_kwh = horas_ev * sup["exceso_pct_no_ti"] / 100 * base_h
    anual_agua = horas_ev * sup["exceso_pct_no_ti"] / 100 * agua_evap
    bloque = deteccion["deteccion"]
    bloque["comparacion_contra_reglas_kit"]["episodios_originales_kit"]["horas_anomalas"] = 21
    bloque["comparacion_contra_reglas_kit"]["episodios_originales_kit"]["episodios"] = 3
    bloque["comparacion_contra_reglas_kit"]["episodios_originales_kit"]["unidad_conteo"] = "episodios"
    bloque["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["unidad_conteo"] = "inyecciones"
    bloque["falsas_alarmas_por_dia"]["unidad"] = "alarmas/día/sitio"
    bloque["falsas_alarmas_por_dia"]["periodo"] = "evaluacion"
    bloque["falsas_alarmas_por_dia"].update(tipo="observado", origen="src/ataques/correr_rejilla.py",
                                              responsable="Nico", estado="disponible")
    bloque["clases_ot_conteo"]["unidad"] = "horas"
    bloque["clases_ot_conteo"]["periodo"] = "evaluacion"
    bloque["clases_ot_conteo"].update(tipo="observado", origen="src/ataques/correr_rejilla.py",
                                       responsable="Nico")
    bloque["latencia_horas_hasta_detectar_por_episodio_unidad"] = "h"
    bloque["latencia_horas_hasta_detectar_por_episodio_tipo"] = "observado"
    bloque["comparacion_contra_reglas_kit"]["tipo"] = "observado"
    bloque["comparacion_contra_reglas_kit"]["origen"] = "src/ataques/correr_rejilla.py"
    origen = "src/metricas/generar_numeros.py + kit CIFOX (simulado)"
    pend_g = "Pendiente de Gadiel: medición del detector con repeticiones y CodeCarbon."
    pend_m = "Pendiente de Misa: rendimiento y potencia del chiller de respaldo."
    return {
        "_meta": {"aviso": "DATOS SIMULADOS · cifras del kit, no de una instalación real",
                  "estado": "parcial", "fecha_corte_datos": _periodo(tabla, "evaluacion")["fin"],
                  "base_main": "f2e5c4b", "fuente_datos": "kit CIFOX, operaciones_simuladas.csv (fuera de Git)",
                  "periodos": {"referencia": _periodo(tabla, "entrenamiento"),
                               "evaluacion": _periodo(tabla, "evaluacion")},
                  "unidad_energia_entrada": "kWh/intervalo", "responsable": "Nico (N2/N3/N4)"},
        "periodos_y_sitios": {"tipo": "observado", "origen": origen, "responsable": "Nico",
                              "unidad_energia": "kWh", "unidad_agua": "L", "unidad_tiempo": "horas-sitio",
                              "referencia": ref, "evaluacion": ev,
                              "exceso_evaluacion_por_sitio": por_sitio},
        "pue": {"referencia": metrica(ref["pue"], "ratio", "observado", origen, "Misa + Nico", periodo="referencia"),
                "antes": metrica(ev["pue"], "ratio", "observado", origen, "Misa + Nico", periodo="evaluacion",
                                  nota="Cociente de sumas; antes y después usan el mismo periodo."),
                "despues_proyectado": metrica(_r(pue_proy), "ratio", "proyectado", origen, "Nico", periodo="evaluacion",
                                               nota="Contrafactual: restar solo residuo positivo en horas con alerta física. No es ahorro observado.")},
        "wue": {"referencia": metrica(ref["wue_in_situ_l_kwh"], "L/kWh IT", "observado", origen, "Misa + Nico", periodo="referencia"),
                "antes": metrica(ev["wue_in_situ_l_kwh"], "L/kWh IT", "observado", origen, "Misa + Nico", periodo="evaluacion",
                                  nota="Captación in situ, no huella hídrica total."),
                "despues_proyectado": metrica(_r(wue_proy), "L/kWh IT", "proyectado", origen, "Nico", periodo="evaluacion",
                                               nota="Contrafactual de agua en horas con alerta; no ahorro observado.")},
        "energia": {k: metrica(v, "L" if k == "agua_in_situ_l" else "kWh", "observado", origen,
                               "Misa + Nico", periodo="evaluacion") for k, v in ev.items() if k in
                    {"energia_it_kwh", "energia_total_kwh", "energia_no_ti_kwh", "agua_in_situ_l"}},
        "punto_ciego_pct": metrica(punto, "% de energía no TI", "estimado", origen, "Nico", periodo="evaluacion / SIM-C / horas limpias",
                                   nota=f"Piso del mínimo de ((1.6×IT−total)/(total−IT))×100 en {len(limpia)} horas limpias; solo aumenta no TI."),
        "exceso_estimado": {"kwh_sobre_evaluacion": metrica(_r(exceso_kwh), "kWh", "estimado", origen, "Nico", periodo="evaluacion",
                                                            nota="Residuo positivo solo en horas con alerta física; no es ahorro observado."),
                             "litros_sobre_evaluacion": metrica(_r(exceso_l), "L", "estimado", origen, "Nico", periodo="evaluacion",
                                                               nota="Agua in situ; solo horas con alerta física."),
                             "residuo_positivo_todas_horas_kwh": _r(todos_kwh),
                             "residuo_positivo_todas_horas_l": _r(todos_l),
                             "unidad_residuo": {"energia": "kWh", "agua": "L"}},
        "balance_neto": {
            "costo_detector_kwh_anual": metrica(None, "kWh/año", "estimado", "CodeCarbon (10 repeticiones) × frecuencia anual", "Gadiel", motivo=pend_g),
            "tiempo_detector_ms": metrica(None, "ms", "medido", "benchmark del equipo", "Gadiel", motivo=pend_g),
            "emisiones_detector_gco2e_anual": metrica(None, "gCO2e/año", "estimado", "CodeCarbon × factor SEN", "Gadiel + Nico", motivo=pend_g),
            "ahorro_proyectado_kwh_anual": metrica(_r(anual_kwh), "kWh/año", "proyectado", origen, "Nico", supuestos=sup,
                                                    nota="Seis fallas por sitio/año en tres sitios; escenario editable, no ahorro observado."),
            "agua_in_situ_evitada_l_anual": metrica(_r(anual_agua), "L/año", "proyectado", origen, "Nico", supuestos=sup,
                                                     nota="Solo SIM-B evaporativo; escenario editable."),
            "co2_evitado_kg_anual": metrica(None, "kgCO2e/año", "proyectado", "ahorro × factor SEN", "Nico",
                                            motivo="Factor SEN vigente no verificado; no se publica un producto sin fuente."),
            "agua_indirecta_evitada_l_anual": metrica(None, "L/año", "proyectado", "ahorro × intensidad hídrica SEN", "Nico",
                                                       motivo="Falta mezcla SEN verificable para combinar intensidades NREL."),
            "razon_ahorro_costo": metrica(None, "veces", "proyectado", "ahorro/costo detector", "Misa + Nico", motivo=pend_g),
            "umbral_equilibrio": metrica(None, "h/año", "proyectado", "costo detector/exceso típico por hora", "Misa + Nico", motivo=pend_g),
        },
        "deteccion": bloque,
        "bono_zero_freshwater": {"wue_potable_meta": metrica(0, "L/kWh IT", "proyectado", "diseño de bono", "Misa",
                                                             nota="Objetivo de diseño; no observado: el kit no separa potable/no potable."),
                                 "horas_respaldo_mérida_al_año": _clima(clima),
                                 "pue_con_bono": metrica(None, "ratio", "proyectado", "modelo de chiller", "Misa", motivo=pend_m)},
        "fuentes_externas": {
            "factor_emision_sen": metrica(None, "kgCO2e/kWh", "estimado", "SEMARNAT/CNE aviso vigente", "Nico",
                                           motivo="El aviso vigente aún no se ha extraído y comprobado."),
            "intensidad_hidrica_sen": metrica(None, "L/kWh", "estimado", "NREL 2012 × mezcla SEN", "Nico",
                                              motivo="Falta mezcla de generación verificable y ponderación."),
            "disponibilidad_acuifero_3105": metrica(None, "hm³/año", "observado", "DOF/CONAGUA", "Guille",
                                                      motivo="Pendiente de Guille: fuente y año del dato del acuífero."),
        },
        "limites_declarados": ["Kit simulado de 3 sitios y 7 días; no valida eficacia en plantas reales.",
                              "El exceso detectado no es ahorro observado; el después es contrafactual.",
                              "Sin medición de Gadiel no hay balance neto ni umbral de equilibrio.",
                              "El kit no separa usos de agua potable ni rendimiento del chiller."],
    }


def plano(o: dict) -> dict:
    """Proyección determinista de Contrato 4 a las claves existentes de Leo."""
    adaptado = adaptar_oficial(o)
    n = {"_ejemplo": False, "_meta": o["_meta"], "generado": {"fecha_corte_datos": o["_meta"]["fecha_corte_datos"],
                                                                "base_main": o["_meta"]["base_main"]}}
    mapa = {
        "pue_referencia": o["pue"]["referencia"], "pue_antes": o["pue"]["antes"],
        "pue_sin_exceso": o["pue"]["despues_proyectado"],
        "wue_referencia": o["wue"]["referencia"], "wue_antes": o["wue"]["antes"],
        "wue_sin_exceso": o["wue"]["despues_proyectado"],
        "punto_ciego_pct": o["punto_ciego_pct"],
        "exceso_energia_kwh": o["exceso_estimado"]["kwh_sobre_evaluacion"],
        "exceso_agua_l": o["exceso_estimado"]["litros_sobre_evaluacion"],
        "detector_cpu_ms": o["balance_neto"]["tiempo_detector_ms"],
        "detector_kwh_anual": o["balance_neto"]["costo_detector_kwh_anual"],
        "detector_gco2e_anual": o["balance_neto"]["emisiones_detector_gco2e_anual"],
        "equilibrio_horas": o["balance_neto"]["umbral_equilibrio"],
        "ahorro_proyectado_kwh_anual": o["balance_neto"]["ahorro_proyectado_kwh_anual"],
        "agua_proyectada_l_anual": o["balance_neto"]["agua_in_situ_evitada_l_anual"],
        "co2_proyectado_kg_anual": o["balance_neto"]["co2_evitado_kg_anual"],
        "pue_con_bono": o["bono_zero_freshwater"]["pue_con_bono"],
        "acuifero_3105": o["fuentes_externas"]["disponibilidad_acuifero_3105"],
    }
    n.update(mapa)
    epis = o["deteccion"]["comparacion_contra_reglas_kit"]["episodios_originales_kit"]
    n["comparacion"] = {"tipo": "observado", "estado": "disponible", "unidad_conteo": "episodios",
                        "periodo": "evaluacion", "horas_anomalas": epis["horas_anomalas"],
                        "origen": "src/ataques/correr_rejilla.py", "responsable": "Nico",
                        "nota": "Tres episodios originales abarcan 21 horas anómalas; las horas se reportan aparte.",
                        "filas": [{"metodo": nombre, "tp": epis[p + "_tp"], "fp": epis[p + "_fp"],
                                   "fn": epis[p + "_fn"],
                                   "precision": _r(epis[p + "_tp"] / max(1, epis[p + "_tp"] + epis[p + "_fp"])),
                                   "recall": _r(epis[p + "_tp"] / max(1, epis[p + "_tp"] + epis[p + "_fn"]))}
                                  for p, nombre in
                                  (("dripsafe", "DripSafe"), ("reglas", "Reglas del kit"))]}
    n["rejilla_completa"] = {"tipo": "observado", "estado": "disponible", "periodo": "evaluacion",
                             "unidad_conteo": "inyecciones", "origen": "src/ataques/correr_rejilla.py",
                             "responsable": "Nico", "filas": o["deteccion"]["comparacion_contra_reglas_kit"]["rejilla_inyecciones"]["datos_curva"]}
    for clave in ("curva_sensibilidad", "robustez", "bono_horas_respaldo"):
        if clave in adaptado:
            n[clave] = adaptado[clave]
        else:
            n[clave] = {"tipo": "estimado" if clave == "bono_horas_respaldo" else "observado",
                        "estado": "pendiente", "filas": [], "responsable": "Nico",
                        "motivo_pendiente": "Falta fuente verificable."}
    for clave in ("curva_sensibilidad", "robustez"):
        n[clave].update(estado="disponible", origen="src/ataques/correr_rejilla.py",
                        responsable="Nico", periodo="evaluacion", unidad_conteo="inyecciones")
    if n["bono_horas_respaldo"]["filas"]:
        n["bono_horas_respaldo"].update(estado="disponible", origen=o["bono_zero_freshwater"]["horas_respaldo_mérida_al_año"]["url"],
                                        responsable="Nico", periodo="2025")
    sup = o["balance_neto"]["ahorro_proyectado_kwh_anual"]["supuestos"]
    n["escenario_anual"] = {"tipo": "proyectado", "estado": "disponible", "origen": "src/metricas/generar_numeros.py",
                             "responsable": "Nico", "nota": "Supuestos editables, no ahorro observado.",
                             "parametros": {"fallas": sup["fallas_por_sitio_al_anio"], "exceso_pct": sup["exceso_pct_no_ti"],
                                            "horas_sin": sup["horas_sin_alerta"],
                                            "horas_con": sup["horas_con_alerta_hasta_correccion"]}}
    n["periodos_y_sitios"] = o["periodos_y_sitios"]
    n["deteccion_detalle"] = {k: o["deteccion"][k] for k in
                             ("falsas_alarmas_por_dia", "clases_ot_conteo", "latencia_horas_hasta_detectar_por_episodio")}
    return n


def escribir(o: dict) -> None:
    errores = contrato.validar_numeros_oficiales(o)
    if errores:
        raise ValueError(f"Contrato 4 inválido: {errores}")
    p = plano(o)
    for ruta, dato in ((RAIZ / "resultados/numeros_oficiales.json", o),
                       (RAIZ / "app/ejemplos/numeros_ejemplo.json", p)):
        ruta.write_text(json.dumps(dato, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"))
    ap.add_argument("--alertas", type=Path, default=Path("data/resultados/alertas.csv"))
    ap.add_argument("--deteccion", type=Path, default=Path("data/resultados/deteccion_para_numeros_oficiales.json"))
    ap.add_argument("--clima", type=Path, default=Path("data/clima/merida_era5_2025.json"))
    ap.add_argument("--descargar-clima", action="store_true",
                    help="Descarga de Open-Meteo ERA5 el año horario 2025 a data/ antes de generar")
    a = ap.parse_args()
    if a.descargar_clima:
        a.clima.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(URL_CLIMA, timeout=30) as respuesta:
            contenido = json.load(respuesta)
        a.clima.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
    o = construir(pd.read_csv(a.entrada), pd.read_csv(a.alertas),
                  json.loads(a.deteccion.read_text(encoding="utf-8")), a.clima)
    escribir(o)
    print("Contrato 4 y vista de Leo generados desde agregados del kit.")


if __name__ == "__main__":
    main()
