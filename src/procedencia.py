"""Procedencia verificable de la medición G3 (contrato 3 v2).

Este módulo NO lee filas del kit: solo calcula hashes de archivos y metadatos
del equipo y del código. Sirve para que `consumo_modelo.json` diga de forma
auditable qué kit, qué commit y qué equipo produjeron la medición.

Uso:
    python -m src.procedencia --kit "$KIT_CSV" --entrada data/procesado/telemetria.csv
    python -m src.procedencia --entrada data/procesado/telemetria.csv --salida resultados/g3_procedencia.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Los mismos archivos que congela N2, más la medición y este módulo. Si cambia
# uno, cambia la medición y el hash deja de coincidir.
ARCHIVOS_CODIGO = [
    "src/modelo/detector.py",
    "src/modelo/medicion.py",
    "src/ot/clases.py",
    "src/datos/cargar.py",
    "src/contrato.py",
    "src/procedencia.py",
    "src/metricas/balance_neto.py",
    "src/pipeline.py",
    "config/columnas.json",
]

# Supuesto conservador si CodeCarbon no puede resolver la energía (macOS/TDP).
TDP_W = 30.0

# Frecuencia de anualización. Son supuestos del diseño (D15), no mediciones:
# inferencia cada hora y un reentrenamiento por temporada (4 al año).
FRECUENCIA_POR_DEFECTO = {
    "horas_anio": 8760,
    "lotes_inferencia_por_hora": 1,
    "reentrenamientos_anio": 4,
}


def sha256_archivo(ruta: Path) -> str:
    """SHA256 de un archivo, leído por bloques (no interpreta su contenido)."""
    digest = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def sha256_tabla(tabla) -> str:
    """SHA256 de la tabla exacta que se midió, en CSV canónico.

    Se usa cuando la medición recibe un DataFrame en memoria (por ejemplo, la
    telemetría ya procesada) y no un archivo.
    """
    return hashlib.sha256(tabla.to_csv(index=False).encode("utf-8")).hexdigest()


def huella_kit(ruta_csv: Path) -> dict:
    """Identifica el kit por el hash del CSV y de su MANIFEST, sin abrir filas.

    El manifiesto puede estar en la misma carpeta que el CSV o un nivel arriba
    (el kit lo publica en la raíz de «Código y recursos»).
    """
    ruta_csv = Path(ruta_csv)
    manifest = next(
        (candidato for candidato in (
            ruta_csv.parent / "MANIFEST.json",
            ruta_csv.parent.parent / "MANIFEST.json",
        ) if candidato.is_file()),
        None,
    )
    return {
        "csv_sha256": sha256_archivo(ruta_csv),
        "csv_bytes": ruta_csv.stat().st_size,
        "manifest_sha256": sha256_archivo(manifest) if manifest else None,
    }


def _git(raiz: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=raiz, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def huella_codigo(raiz: Path = RAIZ) -> dict:
    """Commit y hashes de los archivos que producen la medición."""
    commit = _git(raiz, "rev-parse", "HEAD")
    corto = _git(raiz, "rev-parse", "--short", "HEAD")
    sucio = bool(_git(raiz, "status", "--porcelain", "--", *ARCHIVOS_CODIGO))
    archivos = {
        ruta: sha256_archivo(raiz / ruta)
        for ruta in ARCHIVOS_CODIGO
        if (raiz / ruta).is_file()
    }
    return {
        "commit": commit,
        "commit_corto": corto,
        "sucio": sucio,
        "sha256_archivos": archivos,
    }


def _sysctl(nombre: str) -> str | None:
    try:
        return subprocess.run(
            ["sysctl", "-n", nombre], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def equipo() -> dict:
    """Equipo donde se midió. Sin nombre de usuario, hostname ni rutas locales."""
    memoria = _sysctl("hw.memsize")
    return {
        "modelo": _sysctl("hw.model") or platform.machine() or "desconocido",
        "chip": _sysctl("machdep.cpu.brand_string") or platform.processor() or "desconocido",
        "ram_gb": round(int(memoria) / 1_000_000_000, 1) if memoria and memoria.isdigit() else None,
        "so": f"{platform.system()} {platform.mac_ver()[0] or platform.release()}".strip(),
        "python": platform.python_version(),
        "cpu_logicos": os.cpu_count(),
    }


def metodo(sensor_hardware: bool = False) -> dict:
    """Cómo se obtuvo la energía: sensor de hardware o estimación por TDP."""
    try:
        import codecarbon

        version = getattr(codecarbon, "__version__", None)
    except Exception:  # CodeCarbon puede no estar instalado
        version = None
    return {
        "herramienta": "codecarbon",
        "version": version,
        "tracker": "OfflineEmissionsTracker",
        "pais": "MEX",
        "fuente_energia": "sensor_hardware" if sensor_hardware else "tdp_estimado",
        "tipo": "medido" if sensor_hardware else "estimado",
        "descripcion": (
            "Lectura de un sensor de potencia del equipo."
            if sensor_hardware
            else "CodeCarbon offline estima con el TDP del CPU; no hay sensor de pared."
        ),
        "tdp_w": None if sensor_hardware else TDP_W,
    }


def construir(
    *,
    kit: Path | None = None,
    telemetria: Path | None = None,
    tabla=None,
    raiz: Path = RAIZ,
    sensor_hardware: bool = False,
) -> dict:
    """Bloque `_meta` de la medición: kit, código, equipo, método y tabla medida."""
    datos = {
        "kit": huella_kit(kit) if kit else None,
        "codigo": huella_codigo(raiz),
        "equipo": equipo(),
        "metodo": metodo(sensor_hardware),
        "generado_el": date.today().isoformat(),
        "aviso": "Solo hashes y metadatos; no contiene filas del kit.",
    }
    # Dos huellas distintas y explícitas: el archivo de telemetría (bytes) y la
    # tabla exacta que se midió (CSV canónico en memoria). No se mezclan.
    if telemetria is not None:
        datos["telemetria_archivo_sha256"] = sha256_archivo(telemetria)
    if tabla is not None:
        datos["tabla_medida_sha256"] = sha256_tabla(tabla)
    return datos


def validar_consumo(consumo: dict) -> list[str]:
    """Contrato 3 v2: la medición debe poder auditarse sin abrir el kit.

    Un archivo del formato 1 (``kwh_inferencia_anual``) se acepta por
    compatibilidad y se tratará como cota superior en el balance.
    """
    if not isinstance(consumo, dict):
        return ["consumo_modelo.json no es un objeto JSON"]
    if consumo.get("formato") != 2:
        if "kwh_inferencia_anual" not in consumo:
            return ["consumo v1 sin 'kwh_inferencia_anual'"]
        return []

    problemas: list[str] = []
    meta = consumo.get("_meta")
    if not isinstance(meta, dict):
        return ["consumo v2 sin '_meta' de procedencia"]

    obligatorios = {
        "kit": ("csv_sha256", "manifest_sha256"),
        "codigo": ("commit", "sha256_archivos"),
        "equipo": ("modelo", "so", "python"),
        "metodo": ("herramienta", "tracker", "pais", "fuente_energia", "tipo"),
    }
    for seccion, campos in obligatorios.items():
        bloque = meta.get(seccion)
        if not isinstance(bloque, dict):
            problemas.append(f"_meta.{seccion} ausente")
            continue
        for campo in campos:
            if bloque.get(campo) in (None, "", {}):
                problemas.append(f"_meta.{seccion}.{campo} ausente")
    if not meta.get("tabla_medida_sha256"):
        problemas.append("_meta.tabla_medida_sha256 ausente")

    metodo = meta.get("metodo") if isinstance(meta.get("metodo"), dict) else {}
    if metodo.get("tipo") not in {"medido", "estimado"}:
        problemas.append("_meta.metodo.tipo debe ser 'medido' o 'estimado'")

    repeticiones = consumo.get("repeticiones")
    if isinstance(repeticiones, bool) or not isinstance(repeticiones, int) or repeticiones <= 0:
        problemas.append("'repeticiones' debe ser un entero positivo")
        return problemas

    for fase in ("entrenamiento", "inferencia", "corrida_completa"):
        datos = consumo.get(fase)
        if not isinstance(datos, dict):
            problemas.append(f"falta la fase '{fase}'")
            continue
        valores = datos.get("kwh_por_repeticion")
        if not isinstance(valores, list) or len(valores) != repeticiones:
            problemas.append(f"{fase}: se esperaban {repeticiones} valores de kWh")
            continue
        if any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
            for v in valores
        ):
            problemas.append(f"{fase}: hay kWh por repetición inválidos")
        elif datos.get("kwh_mediana") is None:
            problemas.append(f"{fase}: falta kwh_mediana")
        elif abs(statistics.median(valores) - float(datos["kwh_mediana"])) > 1e-15:
            problemas.append(f"{fase}: kwh_mediana no coincide con las repeticiones")
        tiempos = datos.get("ms_por_repeticion")
        if not isinstance(tiempos, list) or len(tiempos) != repeticiones:
            problemas.append(f"{fase}: se esperaban {repeticiones} tiempos en ms")
        if not isinstance(datos.get("fuente_energia"), str) or not datos["fuente_energia"]:
            problemas.append(f"{fase}: falta fuente_energia")

    if metodo.get("tipo") == "medido":
        if metodo.get("fuente_energia") != "sensor_hardware":
            problemas.append("metodo 'medido' exige fuente_energia 'sensor_hardware'")
        for fase in ("entrenamiento", "inferencia", "corrida_completa"):
            datos = consumo.get(fase)
            if isinstance(datos, dict) and datos.get("baja_resolucion"):
                problemas.append(f"{fase}: 'medido' con energía bajo la resolución")

    frecuencia = consumo.get("frecuencia")
    if not isinstance(frecuencia, dict):
        problemas.append("falta 'frecuencia' de anualización")
    else:
        for clave in ("horas_anio", "lotes_inferencia_por_hora", "reentrenamientos_anio"):
            valor = frecuencia.get(clave)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor < 0:
                problemas.append(f"frecuencia.{clave} inválida")

    lote = consumo.get("lote")
    horas_lote = lote.get("horas") if isinstance(lote, dict) else None
    if isinstance(horas_lote, bool) or not isinstance(horas_lote, (int, float)) or horas_lote <= 0:
        problemas.append("falta 'lote.horas' (> 0) para anualizar la inferencia por hora")

    return problemas


def validar_balance_oficial(numeros: dict) -> list[str]:
    """Reglas de procedencia y validación conjunta del bloque balance_neto."""
    problemas: list[str] = []
    balance = numeros.get("balance_neto", {})
    costo = balance.get("costo_detector_kwh_anual", {})
    if costo.get("valor") is not None and costo.get("tipo") == "medido":
        procedencia = numeros.get("_meta", {}).get("procedencia_g3")
        if not isinstance(procedencia, dict):
            problemas.append("costo 'medido' sin _meta.procedencia_g3")
        else:
            for seccion in ("kit", "codigo", "equipo", "metodo"):
                if not isinstance(procedencia.get(seccion), dict) or not procedencia[seccion]:
                    problemas.append(f"_meta.procedencia_g3.{seccion} ausente")
    validado = balance.get("validado_por")
    if validado is not None and sorted(validado) != ["Misa", "Nico"]:
        problemas.append("balance_neto.validado_por debe incluir a Misa y Nico")
    if costo.get("valor") is not None and validado is None and not balance.get("nota_validacion"):
        problemas.append("costo disponible sin validación conjunta ni nota de pendiente")
    return problemas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera el bloque de procedencia de la medición G3 (sin leer filas del kit)."
    )
    parser.add_argument("--kit", type=Path, help="CSV crudo del kit (solo se calcula su hash)")
    parser.add_argument("--entrada", type=Path, help="telemetría usada en la medición")
    parser.add_argument("--salida", type=Path, help="archivo JSON de salida (si se omite, solo imprime)")
    parser.add_argument("--sensor-hardware", action="store_true",
                        help="la energía viene de un sensor de potencia, no del TDP")
    parser.add_argument("--validar", type=Path, help="valida un consumo_modelo.json (contrato 3 v2)")
    parser.add_argument("--validar-oficial", type=Path,
                        help="valida procedencia y validación conjunta de numeros_oficiales.json")
    args = parser.parse_args()

    if args.validar:
        consumo = json.loads(args.validar.read_text(encoding="utf-8"))
        problemas = validar_consumo(consumo)
        if problemas:
            print("NO cumple el contrato 3 v2:")
            for problema in problemas:
                print(f"  - {problema}")
            raise SystemExit(1)
        if consumo.get("formato") != 2:
            print(f"ADVERTENCIA: {args.validar} es formato 1 (cota superior), no v2.")
        else:
            print(f"OK: {args.validar} cumple el contrato 3 v2")
        return
    if args.validar_oficial:
        numeros = json.loads(args.validar_oficial.read_text(encoding="utf-8"))
        problemas = validar_balance_oficial(numeros)
        if problemas:
            print("El balance NO cumple las reglas de procedencia:")
            for problema in problemas:
                print(f"  - {problema}")
            raise SystemExit(1)
        print(f"OK: {args.validar_oficial} cumple las reglas de procedencia y validación")
        return

    datos = construir(kit=args.kit, telemetria=args.entrada, sensor_hardware=args.sensor_hardware)
    texto = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto, encoding="utf-8")
    print(texto, end="")


if __name__ == "__main__":
    main()
