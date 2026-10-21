"""Fija la entrada y el detector usados por N2, sin versionar filas del kit.

Uso: python -m src.evaluacion.congelar_n2 --kit RUTA/operaciones_simuladas.csv

El JSON contiene hashes, ventanas y parámetros por sitio. No mide consumo ni
modifica el detector, las alertas o los números oficiales de Leo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src import contrato
from src.datos.cargar import cargar
from src.modelo import detector

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVOS_CODIGO = (
    "src/modelo/detector.py",
    "src/ot/clases.py",
    "src/datos/cargar.py",
    "src/contrato.py",
    "config/columnas.json",
)


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _identidad_kit(csv: Path) -> dict:
    """Contrasta el CSV con el inventario que entrega CIFOX en el kit."""
    inventario = csv.parent.parent / "MANIFEST.json"
    if not inventario.is_file():
        raise ValueError("Falta MANIFEST.json junto al kit: no se puede fijar su versión")
    contenido = json.loads(inventario.read_text(encoding="utf-8"))
    entradas = [f for f in contenido.get("files", [])
                if f.get("path") == "data/operaciones_simuladas.csv"]
    if len(entradas) != 1:
        raise ValueError("MANIFEST.json no identifica un único CSV oficial")
    declarada = entradas[0]
    real = _sha256(csv)
    if csv.name != "operaciones_simuladas.csv" or real != declarada.get("sha256") or \
            csv.stat().st_size != declarada.get("bytes"):
        raise ValueError("El CSV no coincide con el MANIFEST.json del kit")
    diccionario = csv.parent.parent / "docs/DATA_DICTIONARY.md"
    texto_diccionario = diccionario.read_text(encoding="utf-8") if diccionario.is_file() else ""
    semilla = re.search(r"semilla\s+`?(\d+)", texto_diccionario, flags=re.IGNORECASE)
    return {
        "nombre": csv.name,
        "tipo": "DATOS SIMULADOS · kit CIFOX",
        "identificador": "sha256 del MANIFEST.json; el kit no declara número de versión",
        "manifest_sha256": _sha256(inventario),
        "csv_sha256": real,
        "csv_bytes": csv.stat().st_size,
        "semilla_documentada": int(semilla.group(1)) if semilla else None,
    }


def _revision_codigo(revision: str) -> dict:
    """Exige que el código ejecutado coincida con el commit fijado por N2."""
    commit = subprocess.run(["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], cwd=RAIZ,
                            capture_output=True, text=True, check=True).stdout.strip()
    hashes = {}
    for nombre in ARCHIVOS_CODIGO:
        actual = _sha256(RAIZ / nombre)
        guardado = subprocess.run(["git", "show", f"{commit}:{nombre}"], cwd=RAIZ,
                                 capture_output=True, check=True).stdout
        if actual != hashlib.sha256(guardado).hexdigest():
            raise ValueError(f"{nombre} no coincide con la revisión fijada {commit[:7]}")
        hashes[nombre] = actual
    return {"commit_corte": commit, "sha256_archivos": hashes,
            "generador_sha256": _sha256(RAIZ / "src/evaluacion/congelar_n2.py"),
            "entorno": {"python": sys.version.split()[0], "numpy": np.__version__,
                       "pandas": pd.__version__}}


def _parametros_json(parametros: dict) -> dict:
    return {
        "coef_energia": [float(x) for x in parametros["coef_energia"]],
        "coef_agua": [float(x) for x in parametros["coef_agua"]],
        "coef_entrada": [float(x) for x in parametros["coef_entrada"]],
        "limites": {k: float(v) for k, v in parametros["limites"].items()},
        "limites_media": {k: float(v) for k, v in parametros["limites_media"].items()},
        "t_min_c": float(parametros["t_min"]),
        "t_max_c": float(parametros["t_max"]),
    }


def _hash_objeto(objeto: dict) -> str:
    contenido = json.dumps(objeto, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(contenido).hexdigest()


def _ventana(filas: pd.DataFrame) -> dict:
    return {"inicio_utc": pd.to_datetime(filas["timestamp"].iloc[0], utc=True).isoformat(),
            "fin_utc_inclusivo": pd.to_datetime(filas["timestamp"].iloc[-1], utc=True).isoformat(),
            "horas": len(filas)}


def construir(telemetria: pd.DataFrame, identidad_kit: dict, revision: str) -> dict:
    """Produce un manifiesto estable desde datos del contrato v2 y un kit identificado."""
    problemas = contrato.validar(telemetria)
    if problemas:
        raise ValueError(f"Telemetría inválida: {problemas}")
    prohibidas = {"etiqueta_escenario", "etiqueta_tipo", "simulated_anomaly", "is_simulated"}
    if prohibidas & set(detector.COLUMNAS_ENTRADA):
        raise ValueError("El detector acepta una etiqueta de resultado como entrada")
    if "etiqueta_particion" not in detector.COLUMNAS_ENTRADA:
        raise ValueError("El detector no declara cómo separa ajuste y evaluación")

    ordenada = detector._preparar(telemetria)
    parametros = detector.entrenar(telemetria)
    # Las etiquetas de resultado nunca alteran predicciones; la partición sí
    # se conserva porque selecciona ajuste y calibración, pero no es predictor.
    sin_resultados = telemetria.drop(columns=list(prohibidas & set(telemetria.columns)))
    if not detector.detectar(telemetria).equals(detector.detectar(sin_resultados)):
        raise ValueError("Una etiqueta de resultado alteró la salida del detector")
    # El modelo no puede aprender de las 96 horas de evaluación.
    evaluacion_alterada = telemetria.copy()
    es_evaluacion = evaluacion_alterada["etiqueta_particion"] == "evaluacion"
    for columna in ("kw_total", "agua_reposicion_l", "inlet_temp_c", "t_exterior"):
        evaluacion_alterada.loc[es_evaluacion, columna] += 1.0
    if _hash_objeto({s: _parametros_json(p) for s, p in parametros.items()}) != \
            _hash_objeto({s: _parametros_json(p) for s, p in detector.entrenar(evaluacion_alterada).items()}):
        raise ValueError("Los parámetros cambiaron al alterar la evaluación")

    sitios = {}
    for sitio, grupo in ordenada.groupby("site_id", sort=True):
        grupo = grupo.reset_index(drop=True)
        referencia = grupo[grupo["etiqueta_particion"] == "entrenamiento"]
        evaluacion = grupo[grupo["etiqueta_particion"] == "evaluacion"]
        if len(referencia) != detector.HORAS_AJUSTE + detector.HORAS_CALIBRACION or \
                len(evaluacion) != 96 or len(grupo) != 168 or \
                not grupo["timestamp"].diff().iloc[1:].eq(pd.Timedelta(hours=1)).all() or \
                not grupo["etiqueta_particion"].iloc[:len(referencia)].eq("entrenamiento").all():
            raise ValueError(f"El sitio {sitio} no tiene 72 h de referencia y 96 h de evaluación contiguas")
        p = _parametros_json(parametros[sitio])
        sitios[sitio] = {
            "ajuste": _ventana(referencia.iloc[:detector.HORAS_AJUSTE]),
            "calibracion": _ventana(referencia.iloc[detector.HORAS_AJUSTE:]),
            "evaluacion": _ventana(evaluacion),
            "parametros": p,
            "parametros_sha256": _hash_objeto(p),
        }
    return {
        "_meta": {"aviso": "DATOS SIMULADOS · fijación técnica de N2",
                  "estado": "fijado localmente; pendiente de confirmación de Gadiel",
                  "sin_medicion_codecarbon": True},
        "kit": identidad_kit,
        "codigo": _revision_codigo(revision),
        "protocolo": {
            "detector_actual": "mínimos cuadrados por sitio + umbrales de residuo + EWMA + clasificación OT",
            "incluye_isolation_forest": False,
            "intervalo_h": 1,
            "horas_ajuste_por_sitio": detector.HORAS_AJUSTE,
            "horas_calibracion_por_sitio": detector.HORAS_CALIBRACION,
            "horas_evaluacion_por_sitio": 96,
            "margen_umbral": detector.MARGEN,
            "minimos": detector.MINIMOS,
            "span_ewma": detector.SPAN_EWMA,
            "columnas_entrada_detector": detector.COLUMNAS_ENTRADA,
            "columnas_resultado_excluidas": sorted(prohibidas),
            "etiqueta_particion": "solo selecciona las ventanas; no es predictor numérico",
            "ot_event": "entrada legítima para clasificación OT; no interviene en el ajuste numérico",
            "coeficientes_energia_y_agua": ["1", "energia_it_kwh", "energia_it_kwh × max(t_exterior_c - 20, 0)"],
            "coeficientes_entrada": ["1", "max(t_exterior_c - 20, 0)"],
            "unidades_limites": {"energia": "% residuo no TI", "agua": "% residuo agua", "entrada": "°C residuo entrada"},
            "etiquetas_no_alteran_predicciones": True,
            "evaluacion_no_altera_parametros": True,
        },
        "sitios": sitios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True,
                        help="CSV original dentro del kit CIFOX, fuera del repositorio")
    parser.add_argument("--revision", required=True,
                        help="commit de corte de N2; el código ejecutado debe coincidir con él")
    parser.add_argument("--salida", type=Path, default=Path("resultados/n2_congelamiento.json"))
    args = parser.parse_args()
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    identidad = _identidad_kit(args.kit)
    resultado = construir(cargar(args.kit, mapeo), identidad, args.revision)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(f"Fijación N2: {len(resultado['sitios'])} sitios; kit y parámetros identificados → {args.salida}")


if __name__ == "__main__":
    main()
