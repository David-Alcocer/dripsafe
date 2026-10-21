"""Cierra N2 desde la rejilla U2 auditada y el kit fijado, sin medir CodeCarbon.

Las tablas por posición y semilla se guardan en data/ (ignorado por Git). El
resumen contiene solo agregados y se incorpora al Contrato 4 de Leo.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ataques import rejilla
from src.datos.cargar import cargar
from src.evaluacion import auditar_rejilla
from src.evaluacion.__main__ import _ruta_kit
from src.evaluacion.comparar_originales import _validar_fijacion, comparar
from src.evaluacion.reglas import reglas_fijas
from src.modelo.detector import detectar

RAIZ = Path(__file__).resolve().parents[2]
METODOS = ("dripsafe", "reglas_kit")
SEMILLAS = (1, 2, 3, 4, 5)


def _registros(tabla: pd.DataFrame) -> list[dict]:
    """Serializa solo agregados; pandas transforma NaN en null."""
    return json.loads(tabla.to_json(orient="records", double_precision=10))


def _seleccion(tabla: pd.DataFrame, condicion: str, semilla: int | None) -> pd.DataFrame:
    return tabla[(tabla["condicion"] == condicion) &
                 (tabla["semilla"].isna() if semilla is None else tabla["semilla"] == semilla)]


def _alertas(datos: pd.DataFrame) -> dict[str, pd.DataFrame]:
    predicciones = detectar(datos)
    return {"dripsafe": predicciones[["site_id", "timestamp", "clase"]].assign(
                anomalia=predicciones["clase"].ne("normal")),
            "reglas_kit": reglas_fijas(datos, horas_por_intervalo=1,
                                       unidad_energia="kwh_intervalo")}


def _validar_rejilla(manifiesto: dict, tabla: pd.DataFrame) -> None:
    if manifiesto["rejilla"] != [rejilla.ficha_publica(i.__dict__) for i in rejilla.REJILLA] or \
            manifiesto["inicios_h"] != list(rejilla.INICIOS_H) or \
            manifiesto["margen_h"] != rejilla.MARGEN_H or \
            manifiesto["sin_ot_previo_h"] != rejilla.SIN_OT_PREVIO_H or \
            manifiesto["ruido"] != {"energia_pct_ti": rejilla.RUIDO_ENERGIA_PCT_TI,
                                     "agua_pct": rejilla.RUIDO_AGUA_PCT}:
        raise ValueError("El manifiesto no coincide con la rejilla y el ruido fijados")
    for col in ("detectado", "efecto_visto"):
        if not pd.api.types.is_bool_dtype(tabla[col]) or tabla[col].isna().any():
            raise ValueError(f"{col} debe ser booleano y completo")
    fichas = {f["nombre"]: f for f in manifiesto["rejilla"]}
    for fila in tabla.itertuples(index=False):
        ficha = fichas[fila.nombre]
        if (fila.grupo != ficha["grupo"] or fila.variable != ficha["variable"] or
                float(fila.magnitud_pct) != ficha["magnitud_pct"] or
                fila.clase_esperada != ficha["clase_esperada"]):
            raise ValueError(f"La fila de {fila.nombre} cambió los atributos fijados")
        for bandera, latencia, maximo in ((fila.detectado, fila.horas_hasta_detectar,
                                           ficha["horas"] + ficha["retraso_h"] - 1),
                                          (fila.efecto_visto, fila.horas_hasta_ver_efecto,
                                           ficha["horas"] - 1)):
            if bool(bandera) != bool(pd.notna(latencia)) or \
                    (pd.notna(latencia) and not 0 <= float(latencia) <= maximo):
                raise ValueError(f"Bandera y latencia incoherentes en {fila.nombre}")
        unidad = "kwh" if fila.variable == "energia" else "l"
        inyectado = getattr(fila, f"inyectado_{unidad}")
        no_visto = getattr(fila, f"no_visto_{unidad}")
        if not np.isfinite(inyectado) or not np.isfinite(no_visto) or \
                inyectado <= 0 or not -1e-8 <= no_visto <= inyectado + 1e-8:
            raise ValueError(f"Exceso inyectado/no visto inválido en {fila.nombre}")
        if fila.metodo == "dripsafe":
            correcta = fila.clase_correcta_pct
            if bool(fila.efecto_visto) != bool(pd.notna(correcta)) or \
                    (pd.notna(correcta) and not 0 <= float(correcta) <= 100):
                raise ValueError(f"Clase condicional inválida en {fila.nombre}")
            if (fila.efecto_visto and float(correcta) == 100 and
                    fila.clase_obtenida != fila.clase_esperada) or \
                    (not fila.efecto_visto and fila.clase_obtenida != "sin_efecto_visto"):
                raise ValueError(f"Clase obtenida incoherente en {fila.nombre}")


def _comparar_bases(datos: pd.DataFrame, manifiesto: dict, limpia: pd.DataFrame
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(limpia) != 2 * len(manifiesto["corridas"]) or \
            limpia.duplicated(["condicion", "semilla", "metodo"]).any():
        raise ValueError("Faltan condiciones o métodos en la base limpia")
    resultados, detalles_base = [], None
    for corrida in manifiesto["corridas"]:
        condicion, semilla = corrida["condicion"], corrida["semilla"]
        copia = rejilla._preparar(datos) if semilla is None else rejilla.con_ruido(datos, int(semilla))
        alertas = _alertas(copia)
        resumen, detalle = comparar(copia, alertas)
        if condicion == "base":
            detalles_base = detalle
        for metodo in METODOS:
            r = resumen[(resumen["metodo"] == metodo) & (resumen["site_id"] == "TOTAL")].iloc[0]
            esperado = _seleccion(limpia, condicion, semilla)
            esperado = esperado[esperado["metodo"] == metodo]
            if len(esperado) != 1:
                raise ValueError(f"Falta base limpia de {condicion}/{semilla}/{metodo}")
            e = esperado.iloc[0]
            for campo, valor in (("episodios_kit", r["episodios_verdaderos"]),
                                 ("detectados_kit", r["tp_episodios"]),
                                 ("falsas_alarmas", r["fp_episodios"]),
                                 ("horas_limpias_sitio", r["horas_limpias_sitio"]),
                                 ("falsas_alarmas_por_dia_sitio", r["falsas_alarmas_por_dia_sitio"])):
                if not np.isclose(float(e[campo]), float(valor), rtol=0, atol=1e-6):
                    raise ValueError(f"Base limpia discordante: {condicion}/{semilla}/{metodo}/{campo}")
            latencias = detalle[detalle["metodo"] == metodo]["horas_hasta_detectar"].tolist()
            guardadas = ast.literal_eval(e["latencias_h"]) if isinstance(e["latencias_h"], str) else e["latencias_h"]
            if latencias != guardadas:
                raise ValueError(f"Latencias originales discordantes: {condicion}/{semilla}/{metodo}")
            if metodo == "dripsafe":
                guardadas = (ast.literal_eval(e["horas_por_clase"])
                             if isinstance(e["horas_por_clase"], str) else e["horas_por_clase"])
                pred = alertas[metodo]
                ev = copia.loc[copia["etiqueta_particion"] == "evaluacion", ["site_id", "timestamp"]]
                clases = ev.merge(pred[["site_id", "timestamp", "clase"]],
                                  on=["site_id", "timestamp"], validate="one_to_one")["clase"].value_counts()
                if {k: int(clases.get(k, 0)) for k in guardadas} != guardadas:
                    raise ValueError(f"Clases originales discordantes: {condicion}/{semilla}")
        resumen.insert(0, "semilla", semilla)
        resumen.insert(0, "condicion", condicion)
        resultados.append(resumen)
    return pd.concat(resultados, ignore_index=True), detalles_base


def _tabla_inyecciones(tabla: pd.DataFrame, denominadores: pd.DataFrame) -> pd.DataFrame:
    t = tabla.copy()
    t["semilla"] = pd.to_numeric(t["semilla"]).astype(float)
    denominadores = denominadores.copy()
    denominadores["semilla"] = pd.to_numeric(denominadores["semilla"]).astype(float)
    t["inyectado"] = t["inyectado_kwh"].fillna(0) + t["inyectado_l"].fillna(0)
    t["no_visto"] = t["no_visto_kwh"].fillna(0) + t["no_visto_l"].fillna(0)
    claves = ["condicion", "semilla", "site_id", "nombre", "grupo", "variable",
              "magnitud_pct", "metodo"]
    g = t.groupby(claves, dropna=False, sort=False)
    salida = g.agg(ejecutadas=("detectado", "size"), tp_episodios=("detectado", "sum"),
                   efectos_vistos=("efecto_visto", "sum"),
                   latencia_episodio_mediana_h=("horas_hasta_detectar", "median"),
                   latencia_efecto_mediana_h=("horas_hasta_ver_efecto", "median"),
                   inyectado=("inyectado", "sum"), no_visto=("no_visto", "sum"),
                   clase_correcta_pct_condicional=("clase_correcta_pct", "mean"),
                   clases_evaluadas=("clase_correcta_pct", "count")).reset_index()
    salida = salida.merge(denominadores, on=["condicion", "semilla", "site_id", "nombre"],
                          how="left", validate="many_to_one")
    if salida["planeadas"].isna().any() or not (salida["ejecutadas_x"] == salida["ejecutadas_y"]).all():
        raise ValueError("Los denominadores no coinciden con las inyecciones medidas")
    salida = salida.rename(columns={"ejecutadas_x": "ejecutadas"}).drop(columns="ejecutadas_y")
    salida["fn_episodios"] = salida["ejecutadas"] - salida["tp_episodios"]
    salida["recall_episodios_pct"] = 100 * salida["tp_episodios"] / salida["ejecutadas"]
    salida["pct_efectos_vistos"] = 100 * salida["efectos_vistos"] / salida["ejecutadas"]
    salida["pct_no_visto"] = 100 * salida["no_visto"] / salida["inyectado"]
    salida["unidad"] = np.where(salida["variable"] == "energia", "kWh", "L")
    return salida.sort_values(["condicion", "semilla", "site_id", "nombre", "metodo"],
                              na_position="first").reset_index(drop=True)


def _curva(tabla: pd.DataFrame) -> pd.DataFrame:
    t = tabla[tabla["condicion"] == "base"]
    claves = ["nombre", "grupo", "variable", "magnitud_pct", "metodo"]
    r = t.groupby(claves, sort=False).agg(
        inyecciones=("detectado", "size"), tp_episodios=("detectado", "sum"),
        efectos_vistos=("efecto_visto", "sum"),
        latencia_episodio_mediana_h=("horas_hasta_detectar", "median"),
        latencia_efecto_mediana_h=("horas_hasta_ver_efecto", "median"),
        inyectado=("inyectado", "sum"), no_visto=("no_visto", "sum"),
        clase_correcta_pct_condicional=("clase_correcta_pct", "mean"),
        clases_evaluadas=("clase_correcta_pct", "count")).reset_index()
    r["fn_episodios"] = r["inyecciones"] - r["tp_episodios"]
    r["recall_episodios_pct"] = 100 * r["tp_episodios"] / r["inyecciones"]
    r["pct_efectos_vistos"] = 100 * r["efectos_vistos"] / r["inyecciones"]
    r["pct_no_visto"] = 100 * r["no_visto"] / r["inyectado"]
    r["unidad"] = np.where(r["variable"] == "energia", "kWh", "L")
    return r


def _ruido(tabla: pd.DataFrame) -> pd.DataFrame:
    t = tabla[tabla["condicion"] == "ruido"]
    claves = ["nombre", "grupo", "variable", "magnitud_pct", "metodo"]
    r = t.groupby(claves, sort=False).agg(
        semillas=("semilla", "nunique"), inyecciones=("detectado", "size"),
        tp_episodios=("detectado", "sum"), efectos_vistos=("efecto_visto", "sum"),
        inyectado=("inyectado", "sum"), no_visto=("no_visto", "sum"),
        clase_correcta_pct_condicional=("clase_correcta_pct", "mean"),
        clases_evaluadas=("clase_correcta_pct", "count")).reset_index()
    por_semilla = t.groupby([*claves, "semilla"], sort=False).agg(
        n=("detectado", "size"), tp=("detectado", "sum"), vistos=("efecto_visto", "sum")).reset_index()
    por_semilla["recall"] = 100 * por_semilla["tp"] / por_semilla["n"]
    por_semilla["efecto"] = 100 * por_semilla["vistos"] / por_semilla["n"]
    rango = por_semilla.groupby(claves, sort=False).agg(
        recall_episodios_min_pct=("recall", "min"),
        recall_episodios_max_pct=("recall", "max"),
        pct_efectos_vistos_min=("efecto", "min"),
        pct_efectos_vistos_max=("efecto", "max")).reset_index()
    r = r.merge(rango, on=claves, validate="one_to_one")
    r["fn_episodios"] = r["inyecciones"] - r["tp_episodios"]
    r["recall_episodios_pct"] = 100 * r["tp_episodios"] / r["inyecciones"]
    r["pct_efectos_vistos"] = 100 * r["efectos_vistos"] / r["inyecciones"]
    r["pct_no_visto"] = 100 * r["no_visto"] / r["inyectado"]
    r["unidad"] = np.where(r["variable"] == "energia", "kWh", "L")
    return r


def construir(datos: pd.DataFrame, manifiesto: dict, por_inyeccion: pd.DataFrame,
             limpia: pd.DataFrame, denominadores: pd.DataFrame, fijacion: dict
             ) -> tuple[dict, pd.DataFrame]:
    """Consolida cifras de N2 después de verificar las salidas de U2."""
    _validar_rejilla(manifiesto, por_inyeccion)
    evaluaciones, _ = _comparar_bases(datos, manifiesto, limpia)
    tabla = _tabla_inyecciones(por_inyeccion, denominadores)
    curva, ruido = _curva(por_inyeccion.assign(
        inyectado=por_inyeccion["inyectado_kwh"].fillna(0) + por_inyeccion["inyectado_l"].fillna(0),
        no_visto=por_inyeccion["no_visto_kwh"].fillna(0) + por_inyeccion["no_visto_l"].fillna(0))), \
        _ruido(por_inyeccion.assign(
            inyectado=por_inyeccion["inyectado_kwh"].fillna(0) + por_inyeccion["inyectado_l"].fillna(0),
            no_visto=por_inyeccion["no_visto_kwh"].fillna(0) + por_inyeccion["no_visto_l"].fillna(0)))
    base = evaluaciones[evaluaciones["condicion"] == "base"]
    originales = base[["metodo", "site_id", "episodios_verdaderos", "tp_episodios", "fp_episodios",
                      "fn_episodios", "precision_episodios", "recall_episodios", "latencia_media_h",
                      "latencia_max_h", "horas_evaluacion_sitio", "horas_anomalas", "horas_limpias_sitio",
                      "tp_horas", "fp_horas", "fn_horas", "precision_horas", "recall_horas",
                      "falsas_alarmas_por_dia_sitio"]]
    falsas = evaluaciones[["condicion", "semilla", "metodo", "site_id", "episodios_verdaderos",
                          "tp_episodios", "fp_episodios", "fn_episodios", "precision_episodios",
                          "recall_episodios", "horas_limpias_sitio", "falsas_alarmas_por_dia_sitio",
                          "tp_horas", "fp_horas", "fn_horas"]]
    total = tabla[(tabla["condicion"] == "base")].groupby("metodo").agg(
        inyecciones=("ejecutadas", "sum"), tp_episodios=("tp_episodios", "sum"),
        efectos_vistos=("efectos_vistos", "sum")).reset_index()
    ruido_total = tabla[tabla["condicion"] == "ruido"].groupby("metodo").agg(
        inyecciones=("ejecutadas", "sum"), tp_episodios=("tp_episodios", "sum"),
        efectos_vistos=("efectos_vistos", "sum")).reset_index()
    for t in (total, ruido_total):
        t["fn_episodios"] = t["inyecciones"] - t["tp_episodios"]
        t["recall_episodios_pct"] = 100 * t["tp_episodios"] / t["inyecciones"]
        t["pct_efectos_vistos"] = 100 * t["efectos_vistos"] / t["inyecciones"]
    return {"_meta": {"aviso": "DATOS SIMULADOS · cierre N2",
                      "kit_csv_sha256": fijacion["kit"]["csv_sha256"],
                      "codigo_commit_corte": fijacion["codigo"]["commit_corte"],
                      "semillas_ruido": list(SEMILLAS), "periodo": "evaluacion",
                      "estado": "completo en calidad; costo del detector pendiente de Gadiel"},
            "definiciones": {"tp_fp_fn_originales": "episodios; FP = tramo alertado en horas limpias",
                             "tp_fp_fn_horas": "horas-sitio de evaluación",
                             "rejilla": "una inyección por copia; recall por episodio y efecto físico visto se separan",
                             "fp_rejilla": "no atribuible a una copia; se informa en la base sin inyecciones",
                             "clase_correcta_pct_condicional": "solo sobre inyecciones con efecto físico visto"},
            "originales_por_metodo_sitio": _registros(originales),
            "rejilla_base_por_sitio_escenario": _registros(tabla[tabla["condicion"] == "base"].drop(columns=["condicion", "semilla"])),
            "curva_base": _registros(curva),
            "rejilla_base_total": _registros(total),
            "ruido_por_escenario": _registros(ruido),
            "ruido_total": _registros(ruido_total),
            "falsas_alarmas_base_y_ruido": _registros(falsas)}, tabla


def integrar(bloque: dict, cierre: dict, episodios: int, horas_anomalas: int) -> dict:
    """Adjunta los agregados auditados a U2 y exige que ambos insumos coincidan."""
    if "DATOS SIMULADOS" not in cierre.get("_meta", {}).get("aviso", ""):
        raise ValueError("El cierre N2 no identifica el kit simulado")
    salida = copy.deepcopy(bloque)
    comparacion = salida["comparacion_contra_reglas_kit"]
    original = comparacion["episodios_originales_kit"]
    filas = cierre["originales_por_metodo_sitio"]
    if len(filas) != 8 or len({(f["metodo"], f["site_id"]) for f in filas}) != 8:
        raise ValueError("Falta la comparación original por método y sitio")
    for metodo, prefijo in (("dripsafe", "dripsafe"), ("reglas_kit", "reglas")):
        total = next(f for f in filas if f["metodo"] == metodo and f["site_id"] == "TOTAL")
        if total["episodios_verdaderos"] != episodios or total["horas_anomalas"] != horas_anomalas:
            raise ValueError("El cierre N2 no corresponde a las etiquetas del kit")
        for clave, columna in (("tp", "tp_episodios"), ("fp", "fp_episodios"), ("fn", "fn_episodios")):
            if original[f"{prefijo}_{clave}"] != total[columna]:
                raise ValueError(f"U2 y N2 difieren en {metodo}/{clave}")
    curva_u2 = {(f["nombre"], f["metodo"]): f for f in comparacion["rejilla_inyecciones"]["datos_curva"]}
    curva_n2 = {(f["nombre"], f["metodo"]): f for f in cierre["curva_base"]}
    if len(curva_u2) != 16 or curva_u2.keys() != curva_n2.keys():
        raise ValueError("Faltan escenarios o métodos en la curva base")
    for clave, nueva in curva_n2.items():
        vieja = curva_u2[clave]
        if vieja["inyecciones"] != nueva["inyecciones"] or \
                not np.isclose(vieja["pct_efectos_vistos"], round(nueva["pct_efectos_vistos"], 1)) or \
                not np.isclose(vieja["no_visto"], nueva["no_visto"], atol=1e-4):
            raise ValueError(f"U2 y N2 difieren en la curva {clave}")
        vieja.update(tp_episodios=nueva["tp_episodios"], fn_episodios=nueva["fn_episodios"],
                     recall_episodios_pct=round(nueva["recall_episodios_pct"], 4),
                     efectos_vistos=nueva["efectos_vistos"],
                     latencia_episodio_mediana_h=nueva["latencia_episodio_mediana_h"])
    ruido_u2 = {(f["nombre"], f["metodo"]): f for f in comparacion["robustez_ruido"]["resultado"]}
    ruido_n2 = {(f["nombre"], f["metodo"]): f for f in cierre["ruido_por_escenario"]}
    if len(ruido_u2) != 16 or ruido_u2.keys() != ruido_n2.keys():
        raise ValueError("Faltan escenarios o métodos en el ruido")
    for clave, nueva in ruido_n2.items():
        vieja = ruido_u2[clave]
        if vieja["semillas"] != nueva["semillas"] or \
                not np.isclose(vieja["pct_efectos_vistos_media"], round(nueva["pct_efectos_vistos"], 1)) or \
                not np.isclose(vieja["pct_efectos_vistos_min"], round(nueva["pct_efectos_vistos_min"], 1)) or \
                not np.isclose(vieja["pct_efectos_vistos_max"], round(nueva["pct_efectos_vistos_max"], 1)):
            raise ValueError(f"U2 y N2 difieren en el ruido {clave}")
        vieja.update(inyecciones=nueva["inyecciones"], tp_episodios=nueva["tp_episodios"],
                     fn_episodios=nueva["fn_episodios"],
                     recall_episodios_pct=round(nueva["recall_episodios_pct"], 4),
                     recall_episodios_min_pct=round(nueva["recall_episodios_min_pct"], 4),
                     recall_episodios_max_pct=round(nueva["recall_episodios_max_pct"], 4),
                     efectos_vistos=nueva["efectos_vistos"])
    falsas = pd.DataFrame(cierre["falsas_alarmas_base_y_ruido"])
    por_metodo = (falsas[(falsas["condicion"] == "ruido") & (falsas["site_id"] == "TOTAL")]
                  .groupby("metodo")["falsas_alarmas_por_dia_sitio"].mean().to_dict())
    for metodo in METODOS:
        if metodo not in por_metodo:
            raise ValueError(f"Falta la tasa de falsas alarmas con ruido de {metodo}")
    comparacion["robustez_ruido"]["falsas_alarmas_por_dia_sitio_media_por_metodo"] = {
        k: round(float(v), 4) for k, v in por_metodo.items()}
    original.update(episodios=episodios, horas_anomalas=horas_anomalas,
                    unidad_conteo="episodios", por_metodo_sitio=filas)
    comparacion["cierre_n2"] = cierre
    comparacion["origen"] = "src/evaluacion/cerrar_n2.py; rejilla U2 auditada"
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description="Audita y consolida N2 desde los datos simulados fijados")
    p.add_argument("--kit", type=Path, help="CSV local del kit; se busca si se omite")
    p.add_argument("--congelamiento", type=Path, default=RAIZ / "resultados/n2_congelamiento.json")
    p.add_argument("--manifiesto", type=Path, default=RAIZ / "data/escenarios/rejilla.manifiesto.json")
    p.add_argument("--inyecciones", type=Path, default=RAIZ / "data/resultados/rejilla_por_inyeccion.csv")
    p.add_argument("--base-limpia", type=Path, default=RAIZ / "data/resultados/rejilla_base_limpia.csv")
    p.add_argument("--originales", type=Path, default=RAIZ / "data/resultados/n2_originales_comparacion.csv")
    p.add_argument("--salida", type=Path, default=RAIZ / "data/resultados")
    a = p.parse_args()
    ruta = _ruta_kit(a.kit)
    fijacion = json.loads(a.congelamiento.read_text(encoding="utf-8"))
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    datos = cargar(ruta, mapeo)
    _validar_fijacion(ruta, datos, fijacion)
    manifiesto = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    tabla = pd.read_csv(a.inyecciones)
    limpia = pd.read_csv(a.base_limpia)
    _, denominadores = auditar_rejilla.auditar(manifiesto, tabla, fijacion)
    cierre, por_sitio = construir(datos, manifiesto, tabla, limpia, denominadores, fijacion)
    if a.originales.is_file():
        guardado = pd.read_csv(a.originales)
        actual = pd.DataFrame(cierre["originales_por_metodo_sitio"])
        campos = ["metodo", "site_id", "episodios_verdaderos", "tp_episodios", "fp_episodios",
                  "fn_episodios", "tp_horas", "fp_horas", "fn_horas", "latencia_media_h"]
        try:
            pd.testing.assert_frame_equal(actual[campos], guardado[campos], check_dtype=False)
        except AssertionError as error:
            raise ValueError("El paso 3 difiere de la base N2 recalculada") from error
    a.salida.mkdir(parents=True, exist_ok=True)
    por_sitio.to_csv(a.salida / "n2_tabla_final.csv", index=False)
    (a.salida / "n2_cierre.json").write_text(
        json.dumps(cierre, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("DATOS SIMULADOS · N2 auditado: base, cinco semillas, originales, denominadores y efectos")
    print(pd.DataFrame(cierre["rejilla_base_total"]).to_string(index=False))
    print(pd.DataFrame(cierre["ruido_total"]).to_string(index=False))
    print(f"Agregados y tabla local → {a.salida}/n2_cierre.json · n2_tabla_final.csv")


if __name__ == "__main__":
    main()
