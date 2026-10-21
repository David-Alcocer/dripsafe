"""Medición G3 del detector: tres fases separadas y procedencia verificable.

Este módulo NO cambia ``detector.py``: N2 congeló ese archivo y su hash forma
parte del cierre. Aquí se reutilizan sus funciones para medir:

1. ``entrenamiento``: ajuste + calibración (lo que se repite por temporada).
2. ``inferencia``: solo ``_aplicar_sitio`` con parámetros congelados (lo que
   corre cada hora en producción).
3. ``corrida_completa``: ``detectar()``, que ajusta e infiere. Se conserva como
   referencia y NO se anualiza junto con el entrenamiento.

Guardar el valor de CADA repetición es lo que permite reportar dispersión de
energía, no solo de tiempo. Si CodeCarbon no resuelve la energía, se usa el TDP
y se marca ``baja_resolucion`` para que no se publique como ``medido``.

Uso:
    python -m src.modelo.medicion --entrada data/procesado/telemetria.csv \
        --kit "$KIT_CSV" --salida data/resultados/consumo_modelo.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import date
from pathlib import Path

import pandas as pd

from src import contrato, procedencia
from src.modelo import detector

# Debajo de 1e-7 kWh (0.36 J) CodeCarbon no distingue señal de ruido.
RESOLUCION_KWH = 1e-7
TDP_W = procedencia.TDP_W


def inferir(tabla: pd.DataFrame, params_por_sitio: dict[str, dict]) -> pd.DataFrame:
    """Inferencia pura con parámetros congelados: no ajusta ni calibra nada."""
    df = detector._preparar(tabla)
    partes = []
    for sitio, grupo in df.groupby("site_id", sort=True):
        if sitio not in params_por_sitio:
            raise ValueError(f"No hay parámetros congelados para el sitio {sitio!r}")
        partes.append(detector._aplicar_sitio(grupo, params_por_sitio[sitio]))
    salida = pd.concat(partes, ignore_index=True)
    return salida[detector.COLUMNAS_SALIDA]


def _resumen(valores: list[float]) -> dict:
    """Mediana, p95 y dispersión de una lista de repeticiones."""
    if not valores:
        return {"mediana": None, "p95": None, "desviacion": None, "min": None, "max": None}
    ordenados = sorted(float(v) for v in valores)
    n = len(ordenados)
    return {
        "mediana": statistics.median(ordenados),
        "p95": ordenados[min(n - 1, math.ceil(0.95 * n) - 1)],
        "desviacion": statistics.pstdev(ordenados) if n > 1 else 0.0,
        "min": ordenados[0],
        "max": ordenados[-1],
    }


def _una_corrida(fn) -> tuple[float, float | None, float]:
    """Corre ``fn`` con un tracker nuevo y regresa (kWh, kgCO2e, ms)."""
    from codecarbon import OfflineEmissionsTracker

    tracker = OfflineEmissionsTracker(
        country_iso_code="MEX",
        save_to_file=False,
        log_level="error",
    )
    tracker.start()
    inicio = time.perf_counter()
    try:
        fn()
    finally:
        ms = (time.perf_counter() - inicio) * 1000.0
        tracker.stop()
    kwh = float(tracker.final_emissions_data.energy_consumed)
    kg = float(tracker.final_emissions_data.emissions)
    return kwh, kg, ms


def _medir_fase(fn, repeticiones: int) -> dict:
    """Mide una fase y conserva el kWh y el tiempo de cada repetición."""
    kwh_cc: list[float] = []
    kg_cc: list[float] = []
    ms: list[float] = []
    try:
        for _ in range(repeticiones):
            kwh, kg, ms_una = _una_corrida(fn)
            kwh_cc.append(kwh)
            kg_cc.append(kg)
            ms.append(ms_una)
        fuente = "codecarbon_offline"
    except Exception:  # CodeCarbon puede no tener permisos o no estar instalado
        kwh_cc, kg_cc, ms = [], [], []
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            fn()
            ms.append((time.perf_counter() - inicio) * 1000.0)
        fuente = "tdp_estimado"

    baja_resolucion = not kwh_cc or statistics.median(kwh_cc) < RESOLUCION_KWH
    if baja_resolucion:
        # ms → h: m / 3_600_000; W × h = Wh; / 1000 = kWh.
        kwh = [TDP_W * (m / 3_600_000.0) / 1000.0 for m in ms]
        if kwh_cc:
            fuente = "tdp_estimado_por_baja_resolucion"
    else:
        kwh = list(kwh_cc)

    salida = {
        "kwh_por_repeticion": kwh,
        "kwh_codecarbon_por_repeticion": kwh_cc or None,
        "kg_co2e_por_repeticion": kg_cc or None,
        "ms_por_repeticion": ms,
        "fuente_energia": fuente,
        "baja_resolucion": baja_resolucion,
        "kg_co2e_mediana": statistics.median(kg_cc) if kg_cc and not baja_resolucion else None,
    }
    for clave, valor in _resumen(kwh).items():
        salida[f"kwh_{clave}"] = valor
    for clave, valor in _resumen(ms).items():
        salida[f"ms_{clave}"] = valor
    return salida


def medir_consumo(
    df: pd.DataFrame,
    repeticiones: int,
    ruta: Path,
    *,
    kit: Path | None = None,
    telemetria: Path | None = None,
    frecuencia: dict | None = None,
    sensor_hardware: bool = False,
) -> dict:
    """Mide las tres fases y escribe el contrato 3 v2 con procedencia.

    ``telemetria`` es el archivo usado; si se pasa, se sella su hash de bytes
    además del hash canónico de la tabla medida.
    """
    repeticiones = max(1, int(repeticiones))
    frecuencia = {**procedencia.FRECUENCIA_POR_DEFECTO, **(frecuencia or {})}

    # El reentrenamiento de producción usa 72 h por sitio (48 de ajuste + 24 de
    # calibración), no las 168 h del archivo. Medir solo esa partición evita
    # atribuir al entrenamiento el costo de procesar la evaluación.
    if "etiqueta_particion" in df.columns:
        particion = df["etiqueta_particion"].astype(str).str.lower()
        entrenamiento_df = df[particion.isin(["entrenamiento", "referencia"])]
    else:
        entrenamiento_df = df
    if entrenamiento_df.empty:
        entrenamiento_df = df
    params = detector.entrenar(entrenamiento_df)

    fases = {
        "entrenamiento": _medir_fase(lambda: detector.entrenar(entrenamiento_df), repeticiones),
        "inferencia": _medir_fase(lambda: inferir(df, params), repeticiones),
        "corrida_completa": _medir_fase(lambda: detector.detectar(df), repeticiones),
    }
    fases["entrenamiento"]["incluye_ajuste"] = True
    fases["inferencia"]["incluye_ajuste"] = False
    fases["corrida_completa"]["incluye_ajuste"] = True

    # La medición de inferencia procesa un lote completo (por ejemplo, 168 h ×
    # 3 sitios). Para anualizar hay que llevarlo a UNA hora de producción; si no,
    # se multiplica un lote de 168 h por 8 760 y se sobreestima 168 veces.
    horas_lote = max(1, int(df["timestamp"].nunique())) if "timestamp" in df.columns else 1
    sitios_lote = max(1, int(df["site_id"].nunique())) if "site_id" in df.columns else 1
    horas_entrenamiento = (
        max(1, int(entrenamiento_df["timestamp"].nunique()))
        if "timestamp" in entrenamiento_df.columns else 1
    )
    lote = {
        "horas": horas_lote,
        "sitios": sitios_lote,
        "filas": len(df),
        "horas_entrenamiento": horas_entrenamiento,
    }
    año = frecuencia["horas_anio"] * frecuencia["lotes_inferencia_por_hora"]
    nota = (
        f"Fases separadas: entrenamiento ({horas_entrenamiento} h por sitio: ajuste + "
        "calibración), inferencia pura (parámetros congelados) y corrida completa "
        "(ajuste + inferencia). La anualización usa (inferencia / horas del lote) × "
        "frecuencia + entrenamiento × reentrenamientos; la corrida completa NO se "
        "suma para evitar doble conteo. CodeCarbon offline estima con el TDP del "
        "CPU: los kWh son estimación, no lectura de un sensor de pared."
    )
    if any(fase["baja_resolucion"] for fase in fases.values()):
        nota += (
            " Alguna fase quedó por debajo de la resolución de CodeCarbon; "
            f"se usó TDP de {TDP_W:.0f} W y se marca baja_resolucion."
        )

    consumo = {
        "formato": 2,
        "_meta": procedencia.construir(
            kit=kit, telemetria=telemetria, tabla=df, sensor_hardware=sensor_hardware
        ),
        "frecuencia": frecuencia,
        "lote": lote,
        "repeticiones": repeticiones,
        "fecha": date.today().isoformat(),
        "entrenamiento": fases["entrenamiento"],
        "inferencia": fases["inferencia"],
        "corrida_completa": fases["corrida_completa"],
        # Compatibilidad con lectores v1. En v2 `kwh_inferencia_anual` es
        # inferencia PURA, sin el ajuste de la línea base.
        "kwh_entrenamiento": fases["entrenamiento"]["kwh_mediana"],
        "kwh_inferencia_anual": (fases["inferencia"]["kwh_mediana"] / horas_lote) * año,
        "kwh_corrida_completa": fases["corrida_completa"]["kwh_mediana"],
        "kg_co2e_entrenamiento": fases["entrenamiento"]["kg_co2e_mediana"],
        "ms_mediana": fases["corrida_completa"]["ms_mediana"],
        "ms_desviacion": fases["corrida_completa"]["ms_desviacion"],
        "nota": nota,
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(consumo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return consumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Medición G3 del detector (contrato 3 v2).")
    parser.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"))
    parser.add_argument("--salida", type=Path, default=Path("data/resultados/consumo_modelo.json"))
    parser.add_argument("--kit", type=Path, help="CSV crudo del kit; solo se usa para sellar su hash")
    parser.add_argument("--repeticiones", type=int, default=10)
    parser.add_argument("--reentrenamientos-anio", type=float, default=4,
                        help="reentrenamientos completos al año (supuesto D15: uno por temporada)")
    parser.add_argument("--lotes-inferencia-por-hora", type=float, default=1,
                        help="lotes de inferencia por hora (1 = todos los sitios de una hora)")
    parser.add_argument("--sensor-hardware", action="store_true",
                        help="la energía viene de un sensor de potencia, no del TDP")
    args = parser.parse_args()
    if args.kit is None:
        parser.error("--kit es obligatorio: sin su hash la medición no es verificable")
    if procedencia.huella_codigo()["sucio"]:
        parser.error(
            "hay cambios sin commit en los archivos de medición; commitea primero "
            "para que _meta.codigo.sha256_archivos sea reproducible"
        )

    df = contrato.leer(args.entrada)
    problemas = contrato.validar(df)
    if problemas:
        print("La telemetría NO cumple el contrato:")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)

    frecuencia = {
        "horas_anio": procedencia.FRECUENCIA_POR_DEFECTO["horas_anio"],
        "lotes_inferencia_por_hora": args.lotes_inferencia_por_hora,
        "reentrenamientos_anio": args.reentrenamientos_anio,
    }
    consumo = medir_consumo(
        df, args.repeticiones, args.salida,
        kit=args.kit, telemetria=args.entrada,
        frecuencia=frecuencia, sensor_hardware=args.sensor_hardware,
    )
    problemas = procedencia.validar_consumo(consumo)
    if problemas:
        print("El consumo NO cumple el contrato 3 v2:")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)
    if consumo["_meta"]["codigo"]["sucio"]:
        print("ADVERTENCIA: hay cambios sin commit; el hash del código no será reproducible.")

    print(f"Consumo → {args.salida}")
    print(f"  entrenamiento: {consumo['entrenamiento']['kwh_mediana']:.3e} kWh/repetición")
    print(f"  inferencia:    {consumo['inferencia']['kwh_mediana']:.3e} kWh/repetición")
    print(f"  corrida completa: {consumo['corrida_completa']['ms_mediana']:.1f} ms "
          f"(± {consumo['corrida_completa']['ms_desviacion']:.1f} ms)")
    print(f"  inferencia anual: {consumo['kwh_inferencia_anual']:.6f} kWh/año")


if __name__ == "__main__":
    main()
