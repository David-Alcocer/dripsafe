"""Un solo comando que corre todo el flujo de DripSafe (#4 · Misa).

    kit → contrato v2 → detector → consumo (CodeCarbon) → rejilla de inyecciones
        → src/metricas/generar_numeros.py (contrato 4 de Nico) → numeros_oficiales.json

Uso:
    python -m src.pipeline --kit RUTA/operaciones_simuladas.csv
    python -m src.pipeline                      # usa data/procesado/telemetria.csv
    python -m src.pipeline --ejemplo --sin-medir --semillas-ruido ""   # sin el kit

El JSON lo arma `generar_numeros.construir()` de Nico: aquí solo se corren las
piezas que necesita y se agrega lo que depende de la medición del detector
(costo, tiempo, umbral de equilibrio y razón ahorro/costo). Antes de escribir,
el JSON pasa `contrato.validar_numeros_oficiales()`.

Las tablas por hora se quedan en data/resultados/ (fuera de Git). Al JSON
oficial solo van agregados. Con --ejemplo los datos son INVENTADOS y nunca se
escriben en el JSON oficial.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import contrato
from src.ataques import correr_rejilla
from src.evaluacion import auditar_rejilla, cerrar_n2
from src.evaluacion.__main__ import _ruta_kit
from src.evaluacion.comparar_originales import _validar_fijacion
from src.datos.cargar import cargar
from src.metricas import balance_neto, generar_numeros
from src.metricas.generar_numeros import metrica
from src.metricas.impacto import exceso_no_ti
from src.metricas.pue import unidad_y_horas
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[1]
OFICIAL = RAIZ / "resultados" / "numeros_oficiales.json"
REPETICIONES_CODECARBON = 10
ORIGEN_BALANCE = "src/pipeline.py → src/metricas/balance_neto.py"


def _leer(args) -> tuple[pd.DataFrame, str]:
    """Telemetría del contrato v2 y una descripción de su fuente (sin rutas absolutas)."""
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    if args.ejemplo:
        from app import kit

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ejemplo.csv"
            kit.ejemplo().to_csv(ruta, index=False)
            return cargar(ruta, mapeo), "app.kit.ejemplo (datos INVENTADOS)"
    if args.kit:
        return cargar(args.kit, mapeo), f"kit CIFOX, {args.kit.name} (fuera de Git)"
    return contrato.leer(args.entrada), f"kit CIFOX procesado, {args.entrada.name} (fuera de Git)"


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


def _deteccion(args, telemetria: pd.DataFrame, fuente: str) -> dict:
    """Corre la rejilla (U2) y guarda sus tablas; con --sin-rejilla reutiliza la corrida previa."""
    previa = args.resultados / "deteccion_para_numeros_oficiales.json"
    if args.sin_rejilla:
        if not previa.is_file():
            raise SystemExit(f"--sin-rejilla necesita una corrida previa en {previa}")
        return json.loads(previa.read_text(encoding="utf-8"))
    semillas = tuple(int(s) for s in args.semillas_ruido.split(",") if s.strip())
    por_inyeccion, limpia, coincidencias, manifiesto = correr_rejilla.correr(telemetria, semillas)
    manifiesto["fuente"] = fuente if args.ejemplo else str(_ruta_kit(args.kit))
    (args.resultados / "rejilla.manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    por_inyeccion.to_csv(args.resultados / "rejilla_por_inyeccion.csv", index=False)
    correr_rejilla.resumir(por_inyeccion).to_csv(args.resultados / "rejilla_resumen.csv", index=False)
    limpia.to_csv(args.resultados / "rejilla_base_limpia.csv", index=False)
    coincidencias.to_csv(args.resultados / "coincidencias_al_azar.csv", index=False)
    bloque = correr_rejilla.bloque_deteccion(por_inyeccion, limpia, coincidencias, fuente)
    previa.write_text(json.dumps(bloque, ensure_ascii=False, indent=2), encoding="utf-8")
    return bloque


def _cierre_n2(args, telemetria: pd.DataFrame) -> dict | None:
    """Audita U2 y agrega N2 en la ruta oficial; el ejemplo sigue siendo ficticio."""
    if args.ejemplo:
        return None
    ruta = _ruta_kit(args.kit)
    fijacion = json.loads((RAIZ / "resultados/n2_congelamiento.json").read_text(encoding="utf-8"))
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    crudo = cargar(ruta, mapeo)
    _validar_fijacion(ruta, crudo, fijacion)
    procesada = telemetria.copy()
    for columna in ("etiqueta_escenario", "etiqueta_tecnica"):
        if columna in procesada and columna in crudo:
            procesada[columna] = procesada[columna].fillna("")
    try:
        pd.testing.assert_frame_equal(procesada.reset_index(drop=True), crudo.reset_index(drop=True),
                                      check_dtype=False, rtol=1e-12)
    except AssertionError as error:
        raise ValueError("La telemetría procesada difiere del kit fijado en N2") from error
    manifest_local = args.resultados / "rejilla.manifiesto.json"
    manifest_u2 = RAIZ / "data/escenarios/rejilla.manifiesto.json"
    manifiesto = json.loads((manifest_local if manifest_local.is_file() else manifest_u2).read_text(encoding="utf-8"))
    inyecciones = pd.read_csv(args.resultados / "rejilla_por_inyeccion.csv")
    limpia = pd.read_csv(args.resultados / "rejilla_base_limpia.csv")
    _, denominadores = auditar_rejilla.auditar(manifiesto, inyecciones, fijacion)
    cierre, tabla = cerrar_n2.construir(crudo, manifiesto, inyecciones, limpia, denominadores, fijacion)
    tabla.to_csv(args.resultados / "n2_tabla_final.csv", index=False)
    (args.resultados / "n2_cierre.json").write_text(
        json.dumps(cierre, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return cierre


def _exceso_por_hora_alertada(telemetria: pd.DataFrame, alertas: pd.DataFrame) -> pd.Series:
    """kWh de exceso no TI de cada hora con alerta FÍSICA (misma definición que generar_numeros)."""
    unidad, horas = unidad_y_horas(telemetria)
    fisicas = alertas.assign(anomalia=alertas["alerta_umbral"].astype(bool)
                             | alertas["alerta_media_4h"].astype(bool))
    exceso = exceso_no_ti(telemetria, fisicas, columna_esperado="esperado_energia_no_ti_kwh",
                          columna_esperado_agua="esperado_agua_l", unidad_energia=unidad,
                          horas_por_intervalo=horas)
    return exceso.loc[exceso["coincide_alerta"], "exceso_no_ti_estimado_kwh"]


def _balance(numeros: dict, consumo: dict | None, exceso_alertado: pd.Series) -> dict:
    """Copia del bloque balance_neto con lo que depende de la medición del detector."""
    actual = dict(numeros["balance_neto"])
    if consumo is None:
        return actual
    costo = balance_neto.costo_anual_kwh(consumo)
    origen = (f"consumo_modelo.json (CodeCarbon, {consumo.get('repeticiones')} repeticiones, "
              f"{consumo.get('fecha')}) → {ORIGEN_BALANCE}")
    actual["costo_detector_kwh_anual"] = metrica(
        round(costo, 6), "kWh/año", "estimado", origen, "Gadiel", nota=consumo.get("nota"))
    if consumo.get("ms_mediana") is not None:
        actual["tiempo_detector_ms"] = metrica(
            round(float(consumo["ms_mediana"]), 3), "ms", "medido", origen, "Gadiel",
            nota=f"Mediana de {consumo.get('repeticiones')} corridas completas.")
    equilibrio = balance_neto.horas_para_equilibrio(costo, exceso_alertado)
    if equilibrio["horas_necesarias_al_año"] is not None:
        actual["umbral_equilibrio"] = metrica(
            round(equilibrio["horas_necesarias_al_año"], 6), "h/año", "proyectado",
            f"{ORIGEN_BALANCE} · horas_para_equilibrio", "Misa + Nico",
            nota=(f"Horas de ineficiencia típica al año que pagan el costo del detector; "
                  f"exceso típico {equilibrio['exceso_tipico_kwh_por_hora']:.4f} kWh/h "
                  "(mediana en horas con alerta física)."))
    ahorro = numeros["balance_neto"]["ahorro_proyectado_kwh_anual"]["valor"]
    if ahorro is not None and costo > 0:
        actual["razon_ahorro_costo"] = metrica(
            round(ahorro / costo, 1), "veces", "proyectado", f"ahorro_proyectado_kwh_anual / costo · {ORIGEN_BALANCE}",
            "Misa + Nico", nota="Usa los supuestos editables de ahorro_proyectado_kwh_anual; no es ahorro observado.")
    return actual


def _meta(numeros: dict, args, fuente: str) -> dict:
    commit = _commit()
    meta = {**numeros["_meta"], "base_main": commit, "generado_con_commit": commit,
            "generado_el": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fuente_datos": fuente}
    if args.ejemplo:
        meta["aviso"] = ("DATOS SIMULADOS · DATOS INVENTADOS (app.kit.ejemplo): "
                         "solo prueban el flujo, NO van al pitch")
    return meta


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
    p.add_argument("--clima", type=Path, default=Path("data/clima/merida_era5_2025.json"),
                   help="serie ERA5 de Mérida para las horas de respaldo (si no existe, queda pendiente)")
    p.add_argument("--consumo", type=Path, help="consumo_modelo.json (por defecto dentro de --resultados)")
    p.add_argument("--sin-medir", action="store_true", help="no correr CodeCarbon; reutiliza --consumo si existe")
    p.add_argument("--sin-rejilla", action="store_true",
                   help="no correr la rejilla; reutiliza deteccion_para_numeros_oficiales.json de --resultados")
    p.add_argument("--semillas-ruido", default="1,2,3,4,5", help="semillas de la prueba de ruido (vacío = sin ruido)")
    args = p.parse_args(argv)

    args.consumo = args.consumo or args.resultados / "consumo_modelo.json"
    if args.salida is None:
        args.salida = args.resultados / "numeros_ejemplo.json" if args.ejemplo else OFICIAL
    if args.ejemplo and args.salida.resolve() == OFICIAL.resolve():
        p.error("--ejemplo usa datos inventados: no puede escribir resultados/numeros_oficiales.json")
    return args


def _escribir(numeros: dict, salida: Path) -> None:
    """Valida el contrato 4; el oficial se escribe con la vista plana de Leo (generar_numeros.escribir)."""
    errores = contrato.validar_numeros_oficiales(numeros)
    if errores:
        print("El JSON NO cumple el contrato 4:")
        for error in errores:
            print(f"  - {error}")
        raise SystemExit(1)
    if salida.resolve() == OFICIAL.resolve():
        generar_numeros.escribir(numeros)
        return
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(numeros, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                      encoding="utf-8")


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
    print(f"2/5 Detector: {int((alertas['alerta_umbral'] | alertas['alerta_media_4h']).sum())} horas con alerta física")

    consumo = _consumo(args, telemetria)
    print("3/5 Consumo: " + ("sin medición (costo queda pendiente)" if consumo is None
                             else f"{consumo['kwh_inferencia_anual']:.6f} kWh/año"))

    deteccion = _deteccion(args, telemetria, fuente)
    print("4/5 Rejilla: " + ("reutilizada" if args.sin_rejilla else f"tablas en {args.resultados}"))

    cierre = _cierre_n2(args, telemetria)
    base = generar_numeros.construir(telemetria, alertas, deteccion, args.clima, cierre)
    numeros = {**base, "_meta": _meta(base, args, fuente),
               "balance_neto": _balance(base, consumo, _exceso_por_hora_alertada(telemetria, alertas))}
    _escribir(numeros, args.salida)
    print(f"5/5 Contrato 4: PUE referencia {numeros['pue']['referencia']['valor']} · "
          f"antes {numeros['pue']['antes']['valor']} · después proyectado "
          f"{numeros['pue']['despues_proyectado']['valor']}")
    print(f"\nCifras → {args.salida}  (commit {numeros['_meta']['generado_con_commit']})")
    if args.ejemplo:
        print("DATOS INVENTADOS: sirven para probar el flujo, no son cifras del pitch.")


if __name__ == "__main__":
    main()
