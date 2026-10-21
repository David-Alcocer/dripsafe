"""Contrato de datos de DripSafe.

Define los nombres de columna que TODAS las piezas del proyecto usan para
hablarse entre sí (ver docs/11-trabajo-en-paralelo.md). Si cambias algo aquí,
cambias el contrato: necesitas el visto bueno de todo el equipo.

Reglas:
- Potencias en kW (promedio del intervalo), temperaturas en °C,
  caudal en m3/h y agua en litros por intervalo.
- El intervalo entre filas es fijo (por ejemplo, 5 o 15 minutos).
- Las columnas que empiezan con "etiqueta_" son la respuesta correcta de los
  escenarios simulados: el modelo NUNCA las usa para entrenar ni para predecir.
"""

import pandas as pd
import math
import re

# Sin estas columnas no se puede calcular el PUE.
OBLIGATORIAS = ["timestamp", "kw_ti", "kw_total"]

# Si el kit las trae, se usan. Si no, las piezas que las necesitan se saltan.
OPCIONALES = {
    "kw_chiller": "Potencia del chiller (enfriador de agua) en kW",
    "kw_bombas": "Potencia de las bombas de agua helada en kW",
    "kw_torre": "Potencia de los ventiladores de la torre de enfriamiento en kW",
    "t_exterior": "Temperatura exterior en °C",
    "t_suministro": "Temperatura del agua helada que sale hacia los servidores en °C",
    "t_retorno": "Temperatura del agua que regresa de los servidores en °C",
    "setpoint_suministro": "Temperatura objetivo del agua helada en °C",
    "flujo_m3h": "Caudal de agua helada en m3/h",
    "agua_reposicion_l": "Agua que se repone en la torre durante el intervalo, en litros",
    "bomba_encendida": "1 si la bomba está encendida, 0 si está apagada",
    # Columnas v2 (kit real: varios sitios con tecnologías distintas).
    "site_id": "Identificador del sitio (ej. SIM-A, SIM-B, SIM-C en el kit)",
    "cooling_type": "Tecnología de enfriamiento del sitio (aire, evaporativa, liquida)",
    "load_pct": "Carga de IT en porcentaje",
    "inlet_temp_c": "Temperatura del aire a la entrada del rack en °C",
    "ot_event": "Evento OT resumido (normal, login_fallido, cambio_config_no_autorizado)",
}

# Valores válidos para etiqueta_tipo. 'evento_ot' es nuevo en v2: el kit lo distingue
# de 'ataque' porque un login fallido no prueba una intrusión (ver docs/02 D14).
TIPOS_VALIDOS = {"normal", "falla", "ataque", "evento_ot"}

PREFIJO_ETIQUETA = "etiqueta_"
ETIQUETAS = ["etiqueta_escenario", "etiqueta_tipo", "etiqueta_tecnica", "etiqueta_particion"]


def validar(df: pd.DataFrame) -> list[str]:
    """Regresa una lista de problemas. Lista vacía = el DataFrame cumple el contrato."""
    problemas = []
    for col in OBLIGATORIAS:
        if col not in df.columns:
            problemas.append(f"falta la columna obligatoria '{col}'")
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        if ts.isna().any():
            problemas.append("hay valores de 'timestamp' que no son fechas")
        elif "site_id" in df.columns:
            # v2: el timestamp se repite por sitio; validar orden y unicidad POR sitio.
            df_ts = df.assign(_ts=ts)
            for site, grupo in df_ts.groupby("site_id", sort=False):
                if not grupo["_ts"].is_monotonic_increasing:
                    problemas.append(f"'timestamp' no está ordenado para site_id='{site}'")
                if grupo["_ts"].duplicated().any():
                    problemas.append(f"'timestamp' tiene duplicados para site_id='{site}'")
        elif not ts.is_monotonic_increasing:
            problemas.append("'timestamp' no está ordenado de menor a mayor")
    desconocidas = [
        c for c in df.columns
        if c not in OBLIGATORIAS and c not in OPCIONALES and not c.startswith(PREFIJO_ETIQUETA)
    ]
    if desconocidas:
        problemas.append(f"columnas fuera del contrato: {desconocidas}")
    return problemas


def columnas_del_modelo(df: pd.DataFrame) -> list[str]:
    """Columnas que el modelo SÍ puede usar: todo menos timestamp y etiquetas."""
    return [c for c in df.columns if c != "timestamp" and not c.startswith(PREFIJO_ETIQUETA)]


def intervalo_horas(df: pd.DataFrame) -> float:
    """Duración de un intervalo en horas (por ejemplo, 5 minutos = 0.0833)."""
    ts = pd.to_datetime(df["timestamp"])
    return ts.diff().median().total_seconds() / 3600


def leer(ruta) -> pd.DataFrame:
    """Lee un CSV del contrato con 'timestamp' como fecha."""
    return pd.read_csv(ruta, parse_dates=["timestamp"])


TIPOS_CIFRA = {"observado", "medido", "estimado", "proyectado"}


def validar_numeros_oficiales(numeros: dict) -> list[str]:
    """Contrato 4: periodos comparables, procedencia y pendientes explícitos.

    Solo se versionan agregados. La vista plana de Leo se deriva de este objeto.
    """
    problemas = []
    meta = numeros.get("_meta", {})
    if "DATOS SIMULADOS" not in meta.get("aviso", ""):
        problemas.append("_meta.aviso debe identificar DATOS SIMULADOS")
    if meta.get("estado") != "parcial":
        problemas.append("_meta.estado debe declarar parcial mientras haya pendientes")
    periodos = meta.get("periodos", {})
    for clave in ("referencia", "evaluacion"):
        p = periodos.get(clave, {})
        if not all(p.get(c) for c in ("inicio", "fin", "horas_sitio", "sitios", "intervalo_h")):
            problemas.append(f"periodo {clave} incompleto")
    if numeros.get("pue", {}).get("antes", {}).get("periodo") != "evaluacion" or \
            numeros.get("pue", {}).get("despues_proyectado", {}).get("periodo") != "evaluacion":
        problemas.append("PUE antes/después debe usar la misma evaluación")
    if numeros.get("pue", {}).get("referencia", {}).get("periodo") != "referencia":
        problemas.append("PUE de referencia debe identificarse por separado")

    def recorrer(obj, ruta=""):
        if isinstance(obj, dict):
            if "valor" in obj:
                for campo in ("unidad", "tipo", "origen", "responsable", "estado"):
                    if campo not in obj or not isinstance(obj[campo], str) or not obj[campo]:
                        problemas.append(f"{ruta}: falta {campo}")
                if obj.get("tipo") not in TIPOS_CIFRA:
                    problemas.append(f"{ruta}: tipo inválido")
                valor = obj["valor"]
                if valor is None:
                    if obj.get("estado") != "pendiente" or not obj.get("motivo_pendiente"):
                        problemas.append(f"{ruta}: null sin pendiente y motivo")
                elif isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                    problemas.append(f"{ruta}: valor no numérico o no finito")
                elif obj.get("estado") != "disponible":
                    problemas.append(f"{ruta}: cifra disponible sin estado")
            for k, v in obj.items():
                recorrer(v, f"{ruta}.{k}" if ruta else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                recorrer(v, f"{ruta}[{i}]")

    recorrer(numeros)
    bruto = str(numeros)
    if re.search(r"['\"]/(?:home|Users|tmp)/", bruto):
        problemas.append("El JSON contiene una ruta absoluta local")
    return problemas
