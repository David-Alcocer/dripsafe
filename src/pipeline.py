"""Un solo comando que corre todo el flujo de DripSafe (#4 · Misa).

    kit → contrato v2 → detector → consumo (CodeCarbon) → rejilla de inyecciones
        → src/metricas/generar_numeros.py (contrato 4 de Nico) → numeros_oficiales.json

Uso:
    python -m src.pipeline --kit RUTA/operaciones_simuladas.csv
    python -m src.pipeline                      # usa data/procesado/telemetria.csv
    python -m src.pipeline --ejemplo --sin-medir --semillas-ruido ""   # sin el kit

El JSON lo arma `generar_numeros.construir()` de Nico: aquí solo se corren las
piezas que necesita y se agrega lo que depende de la medición del detector
(costo, tiempo, saldo y razón ahorro/costo). El umbral usa la mediana y los
conteos agregados que conserva generar_numeros en el propio JSON. Antes de escribir,
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
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from src import contrato, procedencia
from src.ataques import correr_rejilla
from src.evaluacion import auditar_rejilla, cerrar_n2
from src.evaluacion.__main__ import _ruta_kit
from src.evaluacion.comparar_originales import _validar_fijacion
from src.datos.cargar import cargar
from src.metricas import balance_neto, generar_numeros
from src.metricas.generar_numeros import metrica
from src.modelo import detector, medicion

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


def _frecuencia_args(args) -> dict:
    """Supuestos de anualización; solo incluye los que se pasaron explícitamente.

    Si no se pasan, manda la frecuencia sellada en consumo_modelo.json y, en su
    defecto, la de ``procedencia.FRECUENCIA_POR_DEFECTO``.
    """
    valores = {
        "horas_anio": args.horas_anio,
        "lotes_inferencia_por_hora": args.lotes_inferencia_por_hora,
        "reentrenamientos_anio": args.reentrenamientos_anio,
    }
    return {clave: valor for clave, valor in valores.items() if valor is not None}


def _consumo(args, telemetria: pd.DataFrame) -> dict | None:
    """Mide con CodeCarbon, o reutiliza una medición previa; None si no hay ninguna.

    Un archivo v2 (con procedencia y fases separadas) se valida contra el
    contrato 3. Un v1 se acepta como cota superior y se avisa.
    """
    if not args.sin_medir:
        if args.kit is None:
            print("La medición con procedencia verificable necesita --kit RUTA/operaciones_simuladas.csv")
            raise SystemExit(1)
        if procedencia.huella_codigo()["sucio"]:
            print("Hay cambios sin commit en los archivos de medición; commitea primero "
                  "para que _meta.codigo.sha256_archivos sea reproducible.")
            raise SystemExit(1)
        consumo = medicion.medir_consumo(
            telemetria, REPETICIONES_CODECARBON, args.consumo,
            kit=args.kit, frecuencia=_frecuencia_args(args),
            sensor_hardware=args.sensor_hardware,
        )
    elif args.consumo.is_file():
        consumo = json.loads(args.consumo.read_text(encoding="utf-8"))
    else:
        return None

    problemas = procedencia.validar_consumo(consumo)
    if problemas:
        print("consumo_modelo.json NO cumple el contrato 3:")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)
    if consumo.get("formato") != 2:
        print("  aviso: consumo v1 sin procedencia; el balance lo tratará como cota superior.")
    return consumo


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


def _es_medicion_hardware(consumo: dict) -> bool:
    metodo = (consumo.get("_meta") or {}).get("metodo") or {}
    return metodo.get("tipo") == "medido" and metodo.get("fuente_energia") == "sensor_hardware"


def _ms_mediana(consumo: dict) -> float | None:
    fase = consumo.get("corrida_completa")
    if isinstance(fase, dict) and fase.get("ms_mediana") is not None:
        return float(fase["ms_mediana"])
    if consumo.get("ms_mediana") is not None:
        return float(consumo["ms_mediana"])
    return None


def _origen_consumo(consumo: dict, modo: str) -> str:
    meta = consumo.get("_meta") or {}
    kit = meta.get("kit") or {}
    codigo = meta.get("codigo") or {}
    piezas = [f"consumo_modelo.json v{consumo.get('formato', 1)}",
              f"CodeCarbon, {consumo.get('repeticiones')} repeticiones, {consumo.get('fecha')}"]
    if kit.get("csv_sha256"):
        piezas.append(f"kit {str(kit['csv_sha256'])[:12]}")
    if codigo.get("commit_corto"):
        piezas.append(f"commit {codigo['commit_corto']}")
    if meta.get("metodo", {}).get("fuente_energia"):
        piezas.append(f"energía {meta['metodo']['fuente_energia']}")
    return f"{' · '.join(piezas)} → {ORIGEN_BALANCE} · {modo}"


def _balance(numeros: dict, consumo: dict | None, args) -> dict:
    """Copia del bloque balance_neto con lo que depende de la medición del detector."""
    actual = dict(numeros["balance_neto"])
    # Cada regeneración exige una decisión explícita; nunca arrastra una firma.
    actual["validado_por"] = None
    actual.pop("fecha_validacion", None)
    actual["nota_validacion"] = "Cálculos preparados para revisión; pendiente de validación conjunta de Misa y Nico."
    if consumo is None:
        if args.validacion_conjunta:
            raise ValueError("No se puede firmar el balance sin consumo del detector verificable.")
        return actual

    desglose = balance_neto.desglose_costo_anual(consumo, _frecuencia_args(args))
    costo = desglose["total_kwh_anual"]
    costo_publicado = round(costo, 12)
    origen = _origen_consumo(consumo, desglose["modo"])
    frecuencia = desglose["supuestos"]
    nota_costo = (
        f"{desglose['nota']} Frecuencia: {frecuencia['horas_anio']:.0f} h/año × "
        f"{frecuencia['lotes_inferencia_por_hora']:g} lote(s)/h; "
        f"{desglose['reentrenamientos_aplicados']:g} reentrenamiento(s)/año."
    )
    actual["costo_detector_kwh_anual"] = metrica(
        costo_publicado, "kWh/año",
        "medido" if _es_medicion_hardware(consumo) else "estimado",
        origen, "Gadiel", nota=f"{nota_costo} {consumo.get('nota', '')}".strip())
    actual["costo_entrenamiento_kwh_anual"] = metrica(
        round(desglose["entrenamiento_kwh_anual"], 12), "kWh/año", "estimado", origen, "Gadiel",
        nota="Entrenamiento × reentrenamientos; no se suma si la corrida ya incluye el ajuste.")
    actual["costo_inferencia_kwh_anual"] = metrica(
        round(desglose["inferencia_kwh_anual"], 12), "kWh/año", "estimado", origen, "Gadiel",
        nota="Inferencia pura × horas × lotes; no incluye ajuste.")
    actual["frecuencia_anualizacion"] = {
        "modo": desglose["modo"],
        "horas_anio": frecuencia["horas_anio"],
        "lotes_inferencia_por_hora": frecuencia["lotes_inferencia_por_hora"],
        "reentrenamientos_anio": frecuencia["reentrenamientos_anio"],
        "reentrenamientos_aplicados": desglose["reentrenamientos_aplicados"],
        "horas_lote": desglose.get("horas_lote"),
        "nota": desglose["nota"],
    }
    if args.validacion_conjunta:
        actual["validado_por"] = ["Misa", "Nico"]
        actual["fecha_validacion"] = date.today().isoformat()
        actual["nota_validacion"] = (
            "Misa y Nico validaron conjuntamente los cálculos, supuestos y límites del balance "
            "energético. CO₂ y agua indirecta son proyecciones con factores externos; la firma "
            "no las convierte en ahorro observado ni sustituye la revisión de esos factores."
        )

    ms = _ms_mediana(consumo)
    if ms is not None:
        ms_desviacion = (consumo.get("corrida_completa") or {}).get("ms_desviacion")
        nota_ms = f"Mediana de {consumo.get('repeticiones')} corridas completas."
        if ms_desviacion is not None:
            nota_ms += f" Desviación {float(ms_desviacion):.2f} ms."
        actual["tiempo_detector_ms"] = metrica(
            round(ms, 3), "ms", "medido", origen, "Gadiel", nota=nota_ms)

    agregado = actual["umbral_equilibrio"].get("supuestos", {})
    tipico = agregado.get("exceso_tipico_kwh_por_hora")
    umbral = round(costo_publicado / tipico, 12) if tipico is not None and tipico > 0 else None
    actual["umbral_equilibrio"] = metrica(
        umbral, "h/año", "proyectado", "costo detector publicado / mediana publicada en supuestos", "Misa + Nico",
        supuestos=agregado,
        nota=("Horas de exceso típico en un sitio que compensan el costo anual del detector para los tres sitios. "
              "Umbral algebraico con el método energético declarado en costo_detector_kwh_anual; no es tiempo de detección ni de corrección. "
              "La resolución de los datos es de una hora.") if umbral is not None else None,
        motivo="Sin mediana positiva de exceso no TI en horas de evaluación con alerta física." if umbral is None else None)
    actual["emisiones_detector_gco2e_anual"] = metrica(
        round(balance_neto.emisiones_detector_gco2e_anual(costo_publicado), 8),
        "gCO2e/año", "estimado",
        "costo_detector_kwh_anual × FESEN 2024 aplicable a 2026", "Gadiel + Nico",
        nota=("Producto del costo estimado por TDP, no de una medición de pared. "
              "El factor es el 0.444 kgCO₂e/kWh del aviso oficial para la COA 2026."),
        supuestos={"factor_emision_kg_kwh": balance_neto.FACTOR_EMISION_SEN_KG_KWH,
                   "fesen": balance_neto.URL_FESEN_2024,
                   "aviso_coa_2026": balance_neto.URL_AVISO_COA_2026})
    ahorro = numeros["balance_neto"]["ahorro_proyectado_kwh_anual"]["valor"]
    saldo = round(balance_neto.balance_energia_anual(ahorro, costo_publicado), 12) if ahorro is not None else None
    if ahorro is not None:
        actual["co2_evitado_kg_anual"] = metrica(
            round(balance_neto.co2_evitado_kg_anual(ahorro), 4),
            "kgCO2e/año", "proyectado",
            "ahorro_proyectado_kwh_anual × FESEN 2024 aplicable a 2026", "Nico",
            nota=("Producto de una proyección, no de un ahorro observado. "
                  "El factor es el 0.444 kgCO₂e/kWh indicado por SEMARNAT para la COA 2026."),
            supuestos={"factor_emision_kg_kwh": balance_neto.FACTOR_EMISION_SEN_KG_KWH,
                       "fesen": balance_neto.URL_FESEN_2024,
                       "aviso_coa_2026": balance_neto.URL_AVISO_COA_2026})
        actual["agua_indirecta_evitada_l_anual"] = metrica(
            round(balance_neto.agua_indirecta_evitada_l_anual(ahorro), 4),
            "L/año", "proyectado",
            "ahorro_proyectado_kwh_anual × estimación NREL 2012 × mezcla CNE 2024", "Nico",
            nota=("Estimación, no factor oficial mexicano: factores medianos de NREL 2012 "
                  "ponderados por la mezcla neta del SEN 2024. Incluye evaporación "
                  "hidroeléctrica; no es agua potable ni captación in situ."),
            supuestos={"intensidad_l_kwh": balance_neto.INTENSIDAD_HIDRICA_SEN_L_KWH,
                       "mezcla": balance_neto.URL_MEZCLA_CNE_2024,
                       "factores": balance_neto.URL_NREL_2012,
                       "metodo": "suma(participación por tecnología × factor de consumo)"})
    actual["balance_energia_kwh_anual"] = metrica(
        saldo, "kWh/año", "proyectado", "ahorro_proyectado_kwh_anual publicado − costo_detector_kwh_anual publicado", "Misa + Nico",
        nota="Saldo calculado con los valores publicados y los supuestos del ahorro y de frecuencia_anualizacion; no es ahorro observado." if saldo is not None else None,
        motivo="Falta el ahorro proyectado para calcular el saldo energético." if saldo is None else None)
    if ahorro is not None and costo_publicado > 0:
        actual["razon_ahorro_costo"] = metrica(
            round(ahorro / costo_publicado, 1), "veces", "proyectado",
            f"ahorro_proyectado_kwh_anual / costo_detector_kwh_anual publicado · {origen}",
            "Misa + Nico", nota="Se calcula con el costo publicado y el ahorro proyectado; no es ahorro observado.")
    elif ahorro is not None and costo > 0:
        actual["razon_ahorro_costo"] = metrica(
            None, "veces", "proyectado", f"ahorro_proyectado_kwh_anual / costo · {origen}",
            "Misa + Nico", motivo="El costo positivo se redondea a cero con la precisión publicada.")
    return actual


def _meta(numeros: dict, args, fuente: str, consumo: dict | None = None) -> dict:
    commit = _commit()
    meta = {**numeros["_meta"], "base_main": commit, "generado_con_commit": commit,
            "generado_el": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fuente_datos": fuente}
    if consumo and consumo.get("formato") == 2 and consumo.get("_meta"):
        # Solo hashes y metadatos: nunca filas del kit.
        meta["procedencia_g3"] = consumo["_meta"]
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
    p.add_argument("--reentrenamientos-anio", type=float,
                   help="reentrenamientos completos al año (si se omite, usa el del consumo o 4)")
    p.add_argument("--lotes-inferencia-por-hora", type=float,
                   help="lotes de inferencia por hora (si se omite, usa el del consumo o 1)")
    p.add_argument("--horas-anio", type=float,
                   help="horas de operación al año (si se omite, usa el del consumo o 8760)")
    p.add_argument("--sensor-hardware", action="store_true",
                   help="la energía viene de un sensor de potencia, no del TDP")
    p.add_argument("--validacion-conjunta", action="store_true",
                   help="Misa y Nico validaron juntos el balance (firma el JSON)")
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
    errores = contrato.validar_numeros_oficiales(numeros) + procedencia.validar_balance_oficial(numeros)
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
    if consumo is None:
        print("3/5 Consumo: sin medición (costo queda pendiente)")
    else:
        desglose = balance_neto.desglose_costo_anual(consumo, _frecuencia_args(args))
        print(f"3/5 Consumo: {desglose['total_kwh_anual']:.6f} kWh/año "
              f"({desglose['modo']}; {desglose['reentrenamientos_aplicados']:g} reentrenos/año)")

    deteccion = _deteccion(args, telemetria, fuente)
    print("4/5 Rejilla: " + ("reutilizada" if args.sin_rejilla else f"tablas en {args.resultados}"))

    cierre = _cierre_n2(args, telemetria)
    base = generar_numeros.construir(telemetria, alertas, deteccion, args.clima, cierre)
    numeros = {**base, "_meta": _meta(base, args, fuente, consumo),
               "balance_neto": _balance(base, consumo, args)}
    _escribir(numeros, args.salida)
    print(f"5/5 Contrato 4: PUE referencia {numeros['pue']['referencia']['valor']} · "
          f"antes {numeros['pue']['antes']['valor']} · después proyectado "
          f"{numeros['pue']['despues_proyectado']['valor']}")
    print(f"\nCifras → {args.salida}  (commit {numeros['_meta']['generado_con_commit']})")
    if args.ejemplo:
        print("DATOS INVENTADOS: sirven para probar el flujo, no son cifras del pitch.")


if __name__ == "__main__":
    main()
