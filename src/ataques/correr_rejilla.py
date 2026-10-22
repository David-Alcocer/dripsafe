"""Corre la rejilla de inyecciones contra el detector congelado y las reglas del kit (U2 · #32).

Para cada copia de `src/ataques/rejilla.py` responde, con DripSafe y con las reglas
fijas del kit en la misma tabla:
- ¿Se detectó el episodio y en cuántas horas? (evaluación por episodio de Nico, D17)
- ¿En cuántas horas se vio el EFECTO físico? Un evento OT lo ven las dos; el
  exceso de energía o agua es otra cosa.
- ¿Cuántos kWh o litros inyectados pasaron antes de verlo? Es el exceso exacto
  que metimos, no una estimación.
- ¿La clase OT fue la correcta? (solo DripSafe; las reglas no clasifican)
- ¿El tipo sugerido (ineficiencia o posible ataque, src/modelo/explicar.py) fue el
  correcto? (`clasificacion_correcta_pct`, el mismo criterio de src/ataques/evaluar.py)

También mide, sobre la evaluación sin inyecciones, las falsas alarmas por día y
las coincidencias al azar de la ventana de 24 h (docs/06 §4b).

Uso:
    python -m src.ataques.correr_rejilla --entrada data/procesado/telemetria.csv
    python -m src.ataques.correr_rejilla --kit RUTA/operaciones_simuladas.csv
    python -m src.ataques.correr_rejilla --ejemplo        # sin el kit (datos inventados)

Salidas en data/ (fuera de Git): manifiesto, tabla por inyección, resumen por
magnitud y coincidencias al azar. Solo los agregados pueden ir al JSON oficial.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src import contrato
from src.ataques import rejilla
from src.ataques.evaluar import TIPO_ESPERADO
from src.evaluacion.episodios import episodios_desde_etiquetas, evaluar_episodios
from src.evaluacion.reglas import reglas_fijas
from src.modelo import detector, explicar
from src.ot import clases

METODOS = ("dripsafe", "reglas_kit")
RAIZ = Path(__file__).resolve().parents[2]


def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True)


def _con_clave(tabla: pd.DataFrame) -> pd.DataFrame:
    t = tabla.copy()
    t["timestamp"] = _utc(t["timestamp"])
    return t.set_index(["site_id", "timestamp"]).sort_index()


def _mismos_parametros(a: dict, b: dict) -> bool:
    """¿El detector aprendió exactamente lo mismo? (detector congelado)"""
    if a.keys() != b.keys():
        return False
    for sitio in a:
        for clave, valor in a[sitio].items():
            otro = b[sitio][clave]
            if isinstance(valor, dict):
                if valor.keys() != otro.keys() or any(not np.isclose(valor[k], otro[k], rtol=0, atol=1e-12)
                                                      for k in valor):
                    return False
            elif not np.allclose(valor, otro, rtol=0, atol=1e-12):
                return False
    return True


def _banderas(telemetria: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Para cada método: `anomalia` (cualquier alerta) y `fisica` (exceso de energía o agua)."""
    horas = contrato.intervalo_horas(telemetria[telemetria["site_id"] == telemetria["site_id"].iloc[0]])
    unidad = "kwh_intervalo" if np.isclose(horas, 1.0) else "kw_promedio"
    salida = explicar.explicar(detector.detectar(telemetria))
    d = _con_clave(salida)
    dripsafe = pd.DataFrame({
        "anomalia": d["clase"] != "normal",
        "fisica": d["alerta_umbral"] | d["alerta_media_4h"],
        "clase": d["clase"],
        "tipo_sugerido": d["tipo_sugerido"],
        "alerta_umbral": d["alerta_umbral"],
        "alerta_media_4h": d["alerta_media_4h"],
    })
    con_ot = _con_clave(reglas_fijas(telemetria, horas_por_intervalo=horas, unidad_energia=unidad))
    sin_ot = _con_clave(reglas_fijas(telemetria, horas_por_intervalo=horas, unidad_energia=unidad,
                                     incluir_ot=False))
    reglas = pd.DataFrame({"anomalia": con_ot["anomalia"], "fisica": sin_ot["anomalia"]})
    return {"dripsafe": dripsafe, "reglas_kit": reglas}


def _primera(mascara: pd.Series) -> pd.Timestamp | None:
    horas = mascara[mascara].index.get_level_values("timestamp")
    return horas.min() if len(horas) else None


def medir(ficha: dict, telemetria: pd.DataFrame, banderas: dict, episodios_kit: pd.DataFrame) -> list[dict]:
    """Una fila por método para una inyección."""
    sitio = ficha["site_id"]
    inicio, fin = _utc(pd.Series([ficha["inicio"], ficha["fin"]]))
    inicio_efecto = _utc(pd.Series([ficha["inicio_efecto"]]))[0]
    delta = ficha["_delta_por_hora"].copy()
    delta.index = _utc(pd.Series(delta.index))
    horas_intervalo = ficha["_paso"] / pd.Timedelta(hours=1)
    episodio = pd.DataFrame({"site_id": [sitio], "inicio": [inicio], "fin": [fin], "origen": ["inyeccion"]})
    episodios = pd.concat([episodios_kit[["site_id", "inicio", "fin", "origen"]], episodio], ignore_index=True)

    filas = []
    for metodo in METODOS:
        b = banderas[metodo]
        alertas = b["anomalia"].rename("anomalia").reset_index()
        detalle, _ = evaluar_episodios(telemetria, alertas, episodios, horas_por_intervalo=horas_intervalo)
        propio = detalle[(detalle["origen"] == "inyeccion") & (detalle["site_id"] == sitio)
                         & (_utc(detalle["inicio"]) <= inicio) & (_utc(detalle["fin"]) >= fin)].iloc[0]

        del_sitio = b.xs(sitio, level="site_id")
        efecto = del_sitio.index.isin(delta.index)
        fisica_efecto = del_sitio["fisica"][efecto]
        visto = fisica_efecto[fisica_efecto]
        primera = visto.index.min() if len(visto) else None
        no_visto = float(delta[delta.index < primera].sum()) if primera is not None else float(delta.sum())
        unidad = "kwh" if ficha["variable"] == "energia" else "l"

        fila = {
            "condicion": ficha.get("condicion", "base"),
            "semilla": ficha.get("semilla"),
            "site_id": sitio,
            "nombre": ficha["nombre"],
            "grupo": ficha["grupo"],
            "variable": ficha["variable"],
            "magnitud_pct": ficha["magnitud_pct"],
            "inicio": inicio,
            "desfase_h": ficha["desfase_h"],
            "recorrido_h": ficha["recorrido_h"],
            "metodo": metodo,
            "detectado": bool(propio["detectado"]),
            "horas_hasta_detectar": propio["horas_hasta_detectar"],
            "efecto_visto": primera is not None,
            "horas_hasta_ver_efecto": ((primera - inicio_efecto) / pd.Timedelta(hours=1)
                                       if primera is not None else None),
            f"inyectado_{unidad}": float(delta.sum()),
            f"no_visto_{unidad}": no_visto,
            "clase_esperada": ficha["clase_esperada"],
        }
        if metodo == "dripsafe":
            clases_vistas = del_sitio["clase"][efecto][fisica_efecto.to_numpy()]
            if len(clases_vistas):
                fila["clase_obtenida"] = clases_vistas.value_counts().idxmax()
                fila["clase_correcta_pct"] = round(100 * float((clases_vistas == ficha["clase_esperada"]).mean()), 1)
            else:
                fila["clase_obtenida"] = "sin_efecto_visto"
                fila["clase_correcta_pct"] = None
            tipos_vistos = del_sitio["tipo_sugerido"][efecto][fisica_efecto.to_numpy()]
            fila["tipo_esperado"] = TIPO_ESPERADO[ficha["tipo"]]
            if len(tipos_vistos):
                fila["tipo_obtenido"] = tipos_vistos.value_counts().idxmax()
                fila["clasificacion_correcta_pct"] = round(
                    100 * float((tipos_vistos == fila["tipo_esperado"]).mean()), 1)
            else:
                fila["tipo_obtenido"] = "sin_efecto_visto"
                fila["clasificacion_correcta_pct"] = None
        filas.append(fila)
    return filas


def _base_limpia(telemetria: pd.DataFrame, banderas: dict, episodios_kit: pd.DataFrame,
                 condicion: str, semilla) -> tuple[list[dict], pd.DataFrame]:
    """Falsas alarmas y coincidencias al azar sobre la evaluación sin inyecciones."""
    horas_intervalo = contrato.intervalo_horas(telemetria[telemetria["site_id"] == telemetria["site_id"].iloc[0]])
    filas = []
    for metodo in METODOS:
        alertas = banderas[metodo]["anomalia"].rename("anomalia").reset_index()
        detalle, resumen = evaluar_episodios(telemetria, alertas, episodios_kit, horas_por_intervalo=horas_intervalo)
        filas.append({"condicion": condicion, "semilla": semilla, "metodo": metodo,
                      "horas_limpias_sitio": resumen["horas_limpias_sitio"],
                      "latencias_h": [None if pd.isna(x) else float(x) for x in detalle["horas_hasta_detectar"]],
                      "episodios_kit": resumen["tp"] + resumen["fn"], "detectados_kit": resumen["tp"],
                      "falsas_alarmas": resumen["fp"],
                      "falsas_alarmas_por_dia_sitio": resumen["falsas_alarmas_por_dia_sitio"],
                      "ic95_inferior": resumen["ic_falsas_alarmas_por_dia_sitio"][0],
                      "ic95_superior": resumen["ic_falsas_alarmas_por_dia_sitio"][1]})
    evaluacion = _con_clave(telemetria)["etiqueta_particion"] == "evaluacion"
    d = banderas["dripsafe"][evaluacion.reindex(banderas["dripsafe"].index).fillna(False).to_numpy()]
    conteo = d["clase"].value_counts()
    for fila in filas:
        if fila["metodo"] == "dripsafe":
            fila["horas_por_clase"] = {c: int(conteo.get(c, 0)) for c in clases.CLASES}
    coincidencias = clases.coincidencias_al_azar(d.reset_index())
    coincidencias.insert(0, "semilla", semilla)
    coincidencias.insert(0, "condicion", condicion)
    return filas, coincidencias


def correr(telemetria: pd.DataFrame, semillas_ruido=(1, 2, 3, 4, 5), rejilla_=None,
           inicios_h=rejilla.INICIOS_H, progreso: Callable[[str], None] | None = None):
    """Corre la rejilla en la condición base y con ruido extra (una vez por semilla).

    Regresa (por_inyeccion, base_limpia, coincidencias, manifiesto).
    """
    condiciones = [("base", None)] + [("ruido", s) for s in semillas_ruido]
    por_inyeccion, limpia, coincidencias = [], [], []
    manifiesto = {"rejilla": [rejilla.ficha_publica(i.__dict__) for i in (rejilla_ or rejilla.REJILLA)],
                  "inicios_h": list(inicios_h), "margen_h": rejilla.MARGEN_H,
                  "sin_ot_previo_h": rejilla.SIN_OT_PREVIO_H,
                  "ruido": {"energia_pct_ti": rejilla.RUIDO_ENERGIA_PCT_TI, "agua_pct": rejilla.RUIDO_AGUA_PCT},
                  "corridas": []}
    for numero_corrida, (condicion, semilla) in enumerate(condiciones, start=1):
        if progreso:
            progreso(f"Corrida {numero_corrida}/{len(condiciones)}: {condicion}"
                     + (f", semilla {semilla}" if semilla is not None else ""))
        base = rejilla._preparar(telemetria) if semilla is None else rejilla.con_ruido(telemetria, semilla)
        parametros = detector.entrenar(base)
        banderas_base = _banderas(base)
        episodios_kit = episodios_desde_etiquetas(base, horas_por_intervalo=contrato.intervalo_horas(
            base[base["site_id"] == base["site_id"].iloc[0]]))
        filas_limpia, coinc = _base_limpia(base, banderas_base, episodios_kit, condicion, semilla)
        limpia += filas_limpia
        coincidencias.append(coinc)
        corrida = {"condicion": condicion, "semilla": semilla, "inyecciones": [], "omitidas": []}
        planeadas = base["site_id"].nunique() * len(rejilla_ or rejilla.REJILLA) * len(inicios_h)
        procesadas = 0
        for copia, ficha in rejilla.generar(base, rejilla_ or rejilla.REJILLA, inicios_h):
            procesadas += 1
            if copia is None:
                corrida["omitidas"].append(rejilla.ficha_publica(ficha))
            else:
                if not _mismos_parametros(parametros, detector.entrenar(copia)):
                    raise AssertionError("La inyección cambió lo que aprende el detector: tocó ajuste o calibración")
                ficha = {**ficha, "condicion": condicion, "semilla": semilla}
                por_inyeccion += medir(ficha, copia, _banderas(copia), episodios_kit)
                corrida["inyecciones"].append(rejilla.ficha_publica(ficha))
            if progreso and (procesadas % 24 == 0 or procesadas == planeadas):
                progreso(f"  {procesadas}/{planeadas} posiciones revisadas; "
                         f"{len(corrida['inyecciones'])} ejecutadas, {len(corrida['omitidas'])} omitidas")
        manifiesto["corridas"].append(corrida)
    return (pd.DataFrame(por_inyeccion), pd.DataFrame(limpia),
            pd.concat(coincidencias, ignore_index=True), manifiesto)


def resumir(por_inyeccion: pd.DataFrame) -> pd.DataFrame:
    """Curva de sensibilidad: por condición, inyección y método (todos los sitios juntos)."""
    t = por_inyeccion.copy()
    t["inyectado"] = t.get("inyectado_kwh", pd.Series(0.0, index=t.index)).fillna(0) + \
        t.get("inyectado_l", pd.Series(0.0, index=t.index)).fillna(0)
    t["no_visto"] = t.get("no_visto_kwh", pd.Series(0.0, index=t.index)).fillna(0) + \
        t.get("no_visto_l", pd.Series(0.0, index=t.index)).fillna(0)
    claves = ["condicion", "grupo", "nombre", "variable", "magnitud_pct", "metodo"]
    g = t.groupby(claves, sort=False)
    resumen = g.agg(inyecciones=("detectado", "size"),
                    episodios_detectados=("detectado", "sum"),
                    efectos_vistos=("efecto_visto", "sum"),
                    mediana_horas_ver_efecto=("horas_hasta_ver_efecto", "median"),
                    inyectado=("inyectado", "sum"),
                    no_visto=("no_visto", "sum")).reset_index()
    resumen["unidad"] = np.where(resumen["variable"] == "energia", "kWh", "L")
    resumen["pct_efectos_vistos"] = (100 * resumen["efectos_vistos"] / resumen["inyecciones"]).round(1)
    resumen["pct_no_visto"] = (100 * resumen["no_visto"] / resumen["inyectado"]).round(1)
    for columna in ("clase_correcta_pct", "clasificacion_correcta_pct"):
        if columna in t:
            correcta = (t[t["metodo"] == "dripsafe"].groupby(claves, sort=False)[columna]
                        .mean().round(1).rename(columna))
            resumen = resumen.merge(correcta.reset_index(), on=claves, how="left")
    return resumen


def _num(x):
    return None if x is None or pd.isna(x) else (round(float(x), 4) if isinstance(x, float) else x)


def bloque_deteccion(por_inyeccion: pd.DataFrame, limpia: pd.DataFrame, coincidencias: pd.DataFrame,
                     fuente: str) -> dict:
    """Las cifras de la rejilla con la forma de `deteccion` en resultados/numeros_oficiales.json.

    Es un insumo para N2 (Nico): él decide si lo integra tal cual o lo recalcula.
    """
    resumen = resumir(por_inyeccion)
    base = limpia[limpia["condicion"] == "base"].set_index("metodo")
    ds, rg = base.loc["dripsafe"], base.loc["reglas_kit"]
    curva = [{k: _num(v) for k, v in fila.items()} for fila in resumen[resumen["condicion"] == "base"][
        ["nombre", "variable", "magnitud_pct", "metodo", "inyecciones", "pct_efectos_vistos",
         "mediana_horas_ver_efecto", "inyectado", "no_visto", "pct_no_visto", "unidad", "clase_correcta_pct"]
    ].to_dict("records")]
    ruido = por_inyeccion[por_inyeccion["condicion"] == "ruido"]
    robustez = []
    if not ruido.empty:
        por_semilla = (ruido.groupby(["nombre", "metodo", "semilla"])["efecto_visto"].mean() * 100)
        for (nombre, metodo), serie in por_semilla.groupby(level=["nombre", "metodo"], sort=False):
            robustez.append({"nombre": nombre, "metodo": metodo, "semillas": int(serie.size),
                             "pct_efectos_vistos_media": round(float(serie.mean()), 1),
                             "pct_efectos_vistos_min": round(float(serie.min()), 1),
                             "pct_efectos_vistos_max": round(float(serie.max()), 1)})
    fa_ruido = limpia[(limpia["condicion"] == "ruido") & (limpia["metodo"] == "dripsafe")]
    total = coincidencias[(coincidencias["condicion"] == "base") & (coincidencias["site_id"] == "TOTAL")]
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                cwd=RAIZ, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "desconocido"
    return {
        "_meta": {"aviso": "DATOS SIMULADOS · cifras de la rejilla de inyecciones (U2)",
                  "generado_con_commit": commit,
                  "generado_el": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "fuente_datos": fuente, "responsable": "Guille (U2, #32) → insumo de Nico (N2)"},
        "deteccion": {
            "comparacion_contra_reglas_kit": {
                "episodios_originales_kit": {
                    "dripsafe_tp": int(ds["detectados_kit"]), "dripsafe_fp": int(ds["falsas_alarmas"]),
                    "dripsafe_fn": int(ds["episodios_kit"] - ds["detectados_kit"]),
                    "reglas_tp": int(rg["detectados_kit"]), "reglas_fp": int(rg["falsas_alarmas"]),
                    "reglas_fn": int(rg["episodios_kit"] - rg["detectados_kit"]),
                    "nota": "Por episodio (D17): las 21 filas anómalas del kit son 3 episodios.",
                },
                "rejilla_inyecciones": {"datos_curva": curva,
                                        "nota": "Una inyección por copia; ajuste y calibración intactos. "
                                                "Efecto visto = alerta física en las horas del exceso."},
                "robustez_ruido": {"resultado": robustez,
                                   "falsas_alarmas_por_dia_sitio_media": _num(
                                       fa_ruido["falsas_alarmas_por_dia_sitio"].mean()) if len(fa_ruido) else None},
            },
            "falsas_alarmas_por_dia": {"valor": _num(ds["falsas_alarmas_por_dia_sitio"]),
                                       "intervalo_confianza_95": [_num(ds["ic95_inferior"]), _num(ds["ic95_superior"])],
                                       "sobre_horas_limpias": _num(ds["horas_limpias_sitio"]),
                                       "nota": "Por sitio y día, evaluación sin inyecciones."},
            "clases_ot_conteo": {**{c: ds["horas_por_clase"].get(c) for c in clases.CLASES},
                                 "nota": "Horas por clase en la evaluación del kit sin inyecciones."},
            "latencia_horas_hasta_detectar_por_episodio": ds["latencias_h"],
            "coincidencias_al_azar": {"ventanas": [{"ventana_h": int(f.ventana_h), "prob_pct": _num(f.prob_pct),
                                                     "eventos_simulados": int(f.eventos_simulados)}
                                                    for f in total.itertuples()],
                                      "nota": "Probabilidad de atribuir a un evento OT un exceso que no causó."},
        },
    }


def _leer(args) -> pd.DataFrame:
    if args.ejemplo:
        from app import kit
        from src.datos.cargar import cargar
        import tempfile

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ejemplo.csv"
            kit.ejemplo().to_csv(ruta, index=False)
            mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
            return cargar(ruta, mapeo)
    if args.kit:
        from src.datos.cargar import cargar

        mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
        return cargar(args.kit, mapeo)
    return contrato.leer(args.entrada)


def main() -> None:
    p = argparse.ArgumentParser(description="Corre la rejilla de inyecciones (U2).")
    fuente = p.add_mutually_exclusive_group()
    fuente.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"),
                        help="telemetría del contrato v2 (salida de src.datos.cargar)")
    fuente.add_argument("--kit", type=Path, help="CSV crudo del kit (se carga con src.datos.cargar)")
    fuente.add_argument("--ejemplo", action="store_true", help="datos INVENTADOS con el formato del kit")
    p.add_argument("--semillas-ruido", default="1,2,3,4,5", help="semillas de la prueba de ruido (vacío = sin ruido)")
    p.add_argument("--salida", type=Path, default=Path("data/resultados"), help="carpeta de resultados")
    p.add_argument("--manifiesto", type=Path, default=Path("data/escenarios/rejilla.manifiesto.json"))
    a = p.parse_args()

    datos = _leer(a)
    semillas = tuple(int(s) for s in a.semillas_ruido.split(",") if s.strip())
    por_inyeccion, limpia, coincidencias, manifiesto = correr(
        datos, semillas, progreso=lambda mensaje: print(mensaje, flush=True))
    resumen = resumir(por_inyeccion)

    a.salida.mkdir(parents=True, exist_ok=True)
    a.manifiesto.parent.mkdir(parents=True, exist_ok=True)
    manifiesto["fuente"] = "ejemplo (datos inventados)" if a.ejemplo else str(a.kit or a.entrada)
    a.manifiesto.write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    por_inyeccion.to_csv(a.salida / "rejilla_por_inyeccion.csv", index=False)
    resumen.to_csv(a.salida / "rejilla_resumen.csv", index=False)
    limpia.to_csv(a.salida / "rejilla_base_limpia.csv", index=False)
    coincidencias.to_csv(a.salida / "coincidencias_al_azar.csv", index=False)
    bloque = bloque_deteccion(por_inyeccion, limpia, coincidencias, manifiesto["fuente"])
    (a.salida / "deteccion_para_numeros_oficiales.json").write_text(
        json.dumps(bloque, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.ejemplo:
        print("DATOS INVENTADOS (app.kit.ejemplo): sirven para probar el flujo, no son cifras del pitch.\n")
    n = sum(len(c["inyecciones"]) for c in manifiesto["corridas"])
    omitidas = sum(len(c["omitidas"]) for c in manifiesto["corridas"])
    print(f"{n} inyecciones corridas ({omitidas} omitidas por falta de lugar limpio)")
    base = resumen[resumen["condicion"] == "base"]
    vista = base.pivot_table(index=["nombre"], columns="metodo", values="pct_efectos_vistos", sort=False)
    print("\n% de inyecciones cuyo efecto físico se vio (condición base):")
    print(vista.to_string())
    ds = base[base["metodo"] == "dripsafe"].set_index("nombre")
    if "clase_correcta_pct" in ds:
        print("\nClase OT correcta (DripSafe, % de horas con efecto visto):")
        print(ds["clase_correcta_pct"].to_string())
    if "clasificacion_correcta_pct" in ds:
        print("\nTipo sugerido correcto (DripSafe, % de horas con efecto visto):")
        print(ds["clasificacion_correcta_pct"].to_string())
    print("\nEvaluación sin inyecciones:")
    print(limpia[limpia["condicion"] == "base"].drop(columns=["latencias_h", "horas_por_clase"]).to_string(index=False))
    total = coincidencias[(coincidencias["condicion"] == "base") & (coincidencias["site_id"] == "TOTAL")]
    print("\nCoincidencias al azar (DripSafe, todos los sitios):")
    print(total[["ventana_h", "eventos_simulados", "atribuciones_al_azar", "prob_pct"]].to_string(index=False))
    print(f"\nResultados → {a.salida}/rejilla_*.csv · manifiesto → {a.manifiesto}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCorrida cancelada con Ctrl+C.", file=sys.stderr)
        raise SystemExit(130) from None
