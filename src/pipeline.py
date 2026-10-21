"""Un solo comando que corre todo el flujo de DripSafe (#4 · Misa).

    kit → contrato v2 → detector → rejilla de inyecciones → contrato 4
        → resultados/numeros_oficiales.json y vista plana de Leo

Uso:
    python -m src.pipeline --kit RUTA/operaciones_simuladas.csv --sin-medir
    python -m src.pipeline --sin-medir          # usa data/procesado/telemetria.csv
    python -m src.pipeline --ejemplo --sin-medir --semillas-ruido ""   # sin el kit

Las tablas por hora se quedan en data/resultados/ (fuera de Git). El contrato 4
solo incluye agregados y preserva como pendientes las mediciones de Gadiel y
los insumos faltantes de Misa y Guille. Con --ejemplo los datos son INVENTADOS
y nunca se escriben en el JSON oficial.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import contrato
from src.ataques import correr_rejilla
from src.datos.cargar import cargar
from src.metricas import balance_neto
from src.metricas.impacto import exceso_no_ti
from src.metricas.pue import pue_inicial, unidad_y_horas
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[1]
OFICIAL = RAIZ / "resultados" / "numeros_oficiales.json"
REPETICIONES_CODECARBON = 10


def _leer(args) -> tuple[pd.DataFrame, str]:
    """Telemetría del contrato v2 y una descripción de su fuente."""
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    if args.ejemplo:
        from app import kit

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ejemplo.csv"
            kit.ejemplo().to_csv(ruta, index=False)
            return cargar(ruta, mapeo), "app.kit.ejemplo (datos INVENTADOS)"
    if args.kit:
        return cargar(args.kit, mapeo), f"{args.kit.name} (kit CIFOX, no se sube)"
    return contrato.leer(args.entrada), f"{args.entrada.name} (kit procesado, no se sube)"


def _commit() -> str:
    """Commit corto; con '-sucio' si hay cambios sin commit (la cifra no es reproducible).

    Cuenta también archivos nuevos sin seguimiento (un .py sin commit cambia el
    resultado). Lo que está en .gitignore, como data/ con el kit, no cuenta.
    """
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, cwd=RAIZ, check=True).stdout.strip()
        cambios = subprocess.run(["git", "status", "--porcelain"],
                                 capture_output=True, text=True, cwd=RAIZ, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconocido"
    return f"{commit}-sucio" if cambios else commit


def _consumo(args, telemetria: pd.DataFrame) -> dict | None:
    """Mide con CodeCarbon, o reutiliza una medición previa; None si no hay ninguna."""
    if not args.sin_medir:
        return detector._medir_consumo(telemetria, REPETICIONES_CODECARBON, args.consumo)
    if args.consumo.is_file():
        return json.loads(args.consumo.read_text(encoding="utf-8"))
    return None


def _combinar(base: dict, nuevo: dict) -> dict:
    """Copia de `base` con las claves de `nuevo` encima, recursivamente."""
    salida = copy.deepcopy(base)
    for clave, valor in nuevo.items():
        if isinstance(valor, dict) and isinstance(salida.get(clave), dict):
            salida[clave] = _combinar(salida[clave], valor)
        else:
            salida[clave] = valor
    return salida


def _r(x: float | None, decimales: int = 4) -> float | None:
    return None if x is None else round(float(x), decimales)


def _filas_texto(cifras: dict) -> str:
    """Ej.: '96 h × 3 sitios = 288 filas'."""
    return f"{cifras['horas_reloj']} h × {cifras['sitios']} sitios = {cifras['filas']} filas"


def _energias(cifras: dict, particion: str, origen: str) -> dict:
    """Energías y agua de una partición, cada una con su partición y filas."""
    nota = f"Partición {particion}: {_filas_texto(cifras)}."
    return {
        "it_kwh": {"valor": _r(cifras["energia_it_kwh"], 3), "origen": origen,
                   "particion": particion, "nota": nota},
        "total_kwh": {"valor": _r(cifras["energia_total_kwh"], 4), "origen": origen,
                      "particion": particion, "nota": nota},
        "no_ti_kwh": {"valor": _r(cifras["energia_no_ti_kwh"], 4), "particion": particion},
        "agua_l": {"valor": _r(cifras["agua_l"], 4), "origen": origen, "particion": particion},
    }


def _bloque_impacto(telemetria: pd.DataFrame, alertas: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """PUE/WUE de referencia y de evaluación + exceso estimado en evaluación.

    `pue.antes` y el exceso salen de las MISMAS filas (evaluación): así el PUE
    proyectado de Nico resta el exceso sin mezclar periodos. La referencia se
    reporta aparte, solo como línea base normal.
    """
    unidad, horas = unidad_y_horas(telemetria)
    ref = pue_inicial(telemetria, "entrenamiento")
    eva = pue_inicial(telemetria, "evaluacion")
    con_bandera = alertas.assign(anomalia=alertas["clase"] != "normal")
    exceso = exceso_no_ti(telemetria, con_bandera, columna_esperado="esperado_energia_no_ti_kwh",
                          columna_esperado_agua="esperado_agua_l", unidad_energia=unidad,
                          horas_por_intervalo=horas)
    origen_pue = "src/metricas/pue.py · pue_inicial"
    origen_exceso = "src/pipeline.py → src/metricas/impacto.py · exceso_no_ti"
    filas_eva = _filas_texto(eva)
    bloque = {
        "pue": {
            "referencia": {"valor": _r(ref["pue"]), "unidad": "", "tipo": "medido",
                           "origen": f"{origen_pue} (referencia)", "responsable": "Misa (#2)",
                           "particion": "referencia",
                           "nota": f"Línea base normal, {_filas_texto(ref)}. Cociente de sumas. "
                                   "No se compara directo con el PUE proyectado."},
            "antes": {"valor": _r(eva["pue"]), "tipo": "medido",
                      "origen": f"{origen_pue} (evaluación)", "responsable": "Misa (#2)",
                      "particion": "evaluacion",
                      "nota": f"Evaluación tal como viene (con anomalías), {filas_eva}. "
                              "Cociente de sumas; mismas filas que el exceso estimado."},
            "despues_proyectado": {
                "nota": "Pendiente (Nico, #3). Se calcula sobre EVALUACIÓN: (energía total de "
                        "evaluación − exceso estimado) / la misma energía de TI que pue.antes. "
                        "NO es un ahorro observado."},
        },
        "wue": {
            "referencia": {"valor": _r(ref["wue"]), "unidad": "L/kWh", "tipo": "medido",
                           "origen": f"{origen_pue} (referencia)", "responsable": "Misa",
                           "particion": "referencia",
                           "nota": "Captación in situ / energía de TI, línea base normal."},
            "antes": {"valor": _r(eva["wue"]), "tipo": "medido",
                      "origen": f"{origen_pue} (evaluación)", "particion": "evaluacion",
                      "nota": f"Captación in situ / energía de TI, {filas_eva}. "
                              "NO es huella hídrica total."},
        },
        "energia": {
            **_energias(ref, "referencia", origen_pue),
            "evaluacion": _energias(eva, "evaluacion", origen_pue),
        },
        "exceso_estimado": {
            "kwh_sobre_evaluacion": {
                "valor": _r(exceso["exceso_no_ti_estimado_kwh"].sum(), 3),
                "origen": origen_exceso, "particion": "evaluacion", "filas": eva["filas"],
                "nota": f"Suma de residuos positivos en evaluación ({filas_eva}). "
                        f"Coincidente con alerta: {exceso['exceso_no_ti_con_alerta_kwh'].sum():.3f} kWh. "
                        "Es estimado, no ahorro observado.",
            },
            "litros_sobre_evaluacion": {
                "valor": _r(exceso["exceso_agua_in_situ_estimado_l"].sum(), 3),
                "origen": origen_exceso, "particion": "evaluacion", "filas": eva["filas"],
                "nota": f"Captación in situ, {filas_eva}. "
                        f"Coincidente con alerta: {exceso['exceso_agua_con_alerta_l'].sum():.3f} L.",
            },
        },
    }
    return bloque, exceso


def _bloque_balance(consumo: dict | None, exceso: pd.DataFrame) -> dict:
    """Costo del detector y umbral de equilibrio; el ahorro proyectado queda para Misa + Nico."""
    if consumo is None:
        return {}
    costo = balance_neto.costo_anual_kwh(consumo)
    alertadas = exceso.loc[exceso["coincide_alerta"], "exceso_no_ti_estimado_kwh"]
    equilibrio = balance_neto.horas_para_equilibrio(costo, alertadas)
    return {"balance_neto": {
        "costo_detector_kwh_anual": {
            "valor": _r(costo, 6),
            "origen": f"consumo_modelo.json ({consumo.get('repeticiones')} repeticiones, "
                      f"{consumo.get('fecha')}) → src/metricas/balance_neto.py",
            "nota": consumo.get("nota", ""),
        },
        "umbral_equilibrio": {
            "horas_ineficiencia_para_equilibrio_al_año": _r(equilibrio["horas_necesarias_al_año"], 6),
            "exceso_tipico_kwh_por_hora": _r(equilibrio["exceso_tipico_kwh_por_hora"], 4),
            "unidad": "horas de ineficiencia típica al año",
            "origen": "src/metricas/balance_neto.py · horas_para_equilibrio",
        },
    }}


def _bloque_rejilla(args, telemetria: pd.DataFrame, fuente: str) -> dict:
    """Corre la rejilla (U2), guarda sus tablas y regresa el bloque `deteccion`."""
    semillas = tuple(int(s) for s in args.semillas_ruido.split(",") if s.strip())
    por_inyeccion, limpia, coincidencias, manifiesto = correr_rejilla.correr(telemetria, semillas)
    manifiesto["fuente"] = fuente
    (args.resultados / "rejilla.manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    por_inyeccion.to_csv(args.resultados / "rejilla_por_inyeccion.csv", index=False)
    correr_rejilla.resumir(por_inyeccion).to_csv(args.resultados / "rejilla_resumen.csv", index=False)
    limpia.to_csv(args.resultados / "rejilla_base_limpia.csv", index=False)
    coincidencias.to_csv(args.resultados / "coincidencias_al_azar.csv", index=False)
    bloque = correr_rejilla.bloque_deteccion(por_inyeccion, limpia, coincidencias, fuente)
    return {"deteccion": bloque["deteccion"]}


def _plantilla_ejemplo() -> dict:
    """Esqueleto aislado: la prueba ficticia no hereda cifras del JSON oficial."""
    return {
        "pue": {"despues_proyectado": {
            "valor": None,
            "nota": "Pendiente de proyectar sobre EVALUACIÓN; no es ahorro observado.",
        }},
        "balance_neto": {
            "costo_detector_kwh_anual": {"valor": None},
            "ahorro_proyectado_kwh_anual": {"valor": None},
            "umbral_equilibrio": {"valor": None},
        },
    }


def _meta(args, telemetria: pd.DataFrame, fuente: str) -> dict:
    aviso = ("DATOS INVENTADOS (app.kit.ejemplo) · solo prueban el flujo, NO van al pitch"
             if args.ejemplo else "DATOS SIMULADOS · generado por src.pipeline")
    ts = pd.to_datetime(telemetria["timestamp"], utc=True)
    _, horas = unidad_y_horas(telemetria)
    return {"_meta": {
        "aviso": aviso,
        "generado_con_commit": _commit(),
        "generado_el": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "periodo": {"inicio": ts.min().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fin": ts.max().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sitios": sorted(telemetria["site_id"].unique().tolist()),
                    "filas": len(telemetria), "horas_reloj": int(ts.nunique()),
                    "nota": "filas = horas-sitio (horas de reloj × sitios).",
                    "intervalo": f"{horas:g}h"},
        "fuente_datos": fuente,
    }}


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Corre todo el flujo de DripSafe y escribe las cifras oficiales.")
    fuente = p.add_mutually_exclusive_group()
    fuente.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"),
                        help="telemetría del contrato v2 (salida de src.datos.cargar)")
    fuente.add_argument("--kit", type=Path, help="CSV crudo del kit (se carga con src.datos.cargar)")
    fuente.add_argument("--ejemplo", action="store_true", help="datos INVENTADOS con el formato del kit")
    p.add_argument("--resultados", type=Path, default=Path("data/resultados"),
                   help="carpeta de tablas intermedias (fuera de Git)")
    p.add_argument("--salida", type=Path, help="JSON de salida (por defecto el oficial; con --ejemplo, "
                                               "numeros_ejemplo.json dentro de --resultados)")
    p.add_argument("--plantilla", type=Path, default=OFICIAL,
                   help="conservado por compatibilidad; el contrato 4 se genera desde los datos")
    p.add_argument("--consumo", type=Path, help="consumo_modelo.json (por defecto dentro de --resultados)")
    p.add_argument("--sin-medir", action="store_true", help="no correr CodeCarbon; reutiliza --consumo si existe")
    p.add_argument("--sin-rejilla", action="store_true", help="omitir la rejilla de inyecciones")
    p.add_argument("--semillas-ruido", default="1,2,3,4,5", help="semillas de la prueba de ruido (vacío = sin ruido)")
    args = p.parse_args(argv)

    args.consumo = args.consumo or args.resultados / "consumo_modelo.json"
    if args.salida is None:
        args.salida = args.resultados / "numeros_ejemplo.json" if args.ejemplo else OFICIAL
    if args.ejemplo and args.salida.resolve() == OFICIAL.resolve():
        p.error("--ejemplo usa datos inventados: no puede escribir resultados/numeros_oficiales.json")
    return args


def main(argv: list[str] | None = None) -> None:
    args = _argumentos(argv)
    telemetria, fuente = _leer(args)
    problemas = contrato.validar(telemetria)
    if problemas:
        print("La telemetría NO cumple el contrato:")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)
    args.resultados.mkdir(parents=True, exist_ok=True)

    print(f"1/5 Datos: {len(telemetria)} filas · {fuente}")
    alertas = detector.detectar(telemetria)
    alertas.to_csv(args.resultados / "alertas.csv", index=False)
    print(f"2/5 Detector: {int((alertas['clase'] != 'normal').sum())} horas con clase distinta de normal")

    # La medición local se conserva bajo data/ y jamás se atribuye a Gadiel en
    # las cifras oficiales. El modo ficticio mantiene el diagnóstico de #4.
    consumo = _consumo(args, telemetria) if args.ejemplo or not args.sin_medir else None
    print("3/5 Consumo local: " + ("sin medición" if consumo is None
                                   else f"{consumo['kwh_inferencia_anual']:.6f} kWh/año"))

    if args.ejemplo:
        impacto, exceso = _bloque_impacto(telemetria, alertas)
        print(f"4/5 Impacto: PUE referencia {impacto['pue']['referencia']['valor']} · "
              f"PUE antes (evaluación) {impacto['pue']['antes']['valor']}")
    else:
        print("4/5 Impacto: se calcula en el generador del contrato 4")

    rejilla = {} if args.sin_rejilla else _bloque_rejilla(args, telemetria, fuente)
    print("5/5 Rejilla: " + ("omitida" if args.sin_rejilla else f"tablas en {args.resultados}"))

    if args.ejemplo:
        numeros = _plantilla_ejemplo()
        for bloque in (_meta(args, telemetria, fuente), impacto, _bloque_balance(consumo, exceso), rejilla):
            numeros = _combinar(numeros, bloque)
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(json.dumps(numeros, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nCifras de prueba → {args.salida}  (commit {numeros['_meta']['generado_con_commit']})")
        print("DATOS INVENTADOS: sirven para probar el flujo, no son cifras del pitch.")
        return

    if not rejilla:
        raise ValueError("El contrato 4 requiere la rejilla; quite --sin-rejilla para generar cifras oficiales")
    from src.metricas.generar_numeros import construir, escribir

    (args.resultados / "deteccion_para_numeros_oficiales.json").write_text(
        json.dumps(rejilla, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    clima = RAIZ / "data/clima/merida_era5_2025.json"
    numeros = construir(telemetria, alertas, rejilla, clima)
    if args.salida.resolve() == OFICIAL.resolve():
        escribir(numeros)
        print(f"\nContrato 4 → {OFICIAL}\nVista de Leo → {RAIZ / 'app/ejemplos/numeros_ejemplo.json'}")
    else:
        problemas = contrato.validar_numeros_oficiales(numeros)
        if problemas:
            raise ValueError(f"Contrato 4 inválido: {problemas}")
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(json.dumps(numeros, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(f"\nContrato 4 → {args.salida}")


if __name__ == "__main__":
    main()
