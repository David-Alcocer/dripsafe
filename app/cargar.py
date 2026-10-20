"""Junta todo lo que muestra el dashboard: telemetría del kit, detector y cifras.

Fuentes, de la más oficial a la de respaldo:
- Telemetría: el CSV del kit CIFOX, leído FUERA del repo (app/kit.py). Si no está en la
  laptop (por ejemplo en el CI), se usan datos de ejemplo inventados con el mismo formato.
- Detector: data/resultados/alertas.csv (Gadiel construye, Guille clasifica), con las columnas
  de app/linea_base.COLUMNAS. Mientras no exista, la vista previa de app/linea_base.py.
- Cifras: resultados/numeros_oficiales.json (contrato 4, Nico). Mientras no exista,
  app/ejemplos/numeros_ejemplo.json, con valores FICTICIOS que la app marca como ejemplo.

El dashboard no inventa cifras oficiales: solo las muestra y dice de dónde salió cada una.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app import calculos, kit, linea_base

RAIZ = Path(__file__).resolve().parent.parent
RUTAS = {
    "alertas": RAIZ / "data/resultados/alertas.csv",
    "consumo": RAIZ / "data/resultados/consumo_modelo.json",
    "numeros": RAIZ / "resultados/numeros_oficiales.json",
    "ejemplo": Path(__file__).resolve().parent / "ejemplos/numeros_ejemplo.json",
}


@dataclass
class Datos:
    tabla: pd.DataFrame      # una fila por sitio y hora: telemetría + reglas del kit + detector
    eventos: pd.DataFrame    # alertas de DripSafe agrupadas en eventos por sitio
    evaluacion: dict         # {"dripsafe": (por escenario, resumen), "reglas": (…)}
    numeros: dict            # contrato 4 (oficial) o el ejemplo ficticio
    benchmarks: dict         # corridas de ejemplo del kit: reglas e Isolation Forest
    fuentes: dict = field(default_factory=dict)
    consumo: dict = field(default_factory=dict)   # contrato 3: consumo_modelo.json (CodeCarbon), si existe
    avisos: list = field(default_factory=list)    # problemas de formato que el dashboard debe mostrar

    @property
    def cifras_de_ejemplo(self) -> bool:
        return self.fuentes.get("numeros") != "oficial"


def _detector_oficial(avisos: list) -> pd.DataFrame | None:
    """La salida del detector del equipo, si ya existe y trae las columnas que la app necesita.

    Si el archivo existe pero tiene otro formato (por ejemplo, el contrato 3 anterior, sin
    site_id ni esperado), la app NO lo ignora en silencio: agrega un aviso visible y usa la vista previa.
    """
    if not RUTAS["alertas"].exists():
        return None
    al = pd.read_csv(RUTAS["alertas"])
    faltan = sorted(set(linea_base.COLUMNAS) - {"motivo"} - set(al.columns))
    if faltan:
        avisos.append(f"data/resultados/alertas.csv existe pero no trae las columnas que la app necesita "
                      f"({', '.join(faltan)}). Se usa la vista previa hasta acordar el contrato 3 (ver app/ejemplos/README.md).")
        return None
    al["timestamp"] = pd.to_datetime(al["timestamp"], utc=True)
    if "motivo" not in al.columns:
        al["motivo"] = ""
    al["motivo"] = al["motivo"].fillna("")
    return al[linea_base.COLUMNAS]


def unir(datos: pd.DataFrame, detector: pd.DataFrame) -> pd.DataFrame:
    """Telemetría + reglas del kit (para comparar) + salida del detector, con el exceso de cada hora."""
    t = kit.reglas(datos).rename(columns={"alerta": "alerta_reglas", "motivo": "motivo_reglas"})
    t = t.drop(columns="tipo_sugerido").merge(detector, on=["timestamp", "site_id"], how="left")
    t["clase"] = t["clase"].fillna("normal")
    t["motivo"] = t["motivo"].fillna("")
    t["alerta"] = t["clase"] != "normal"
    t["energia_no_ti_kwh"] = t["energy_total_kwh"] - t["energy_it_kwh"]
    fisica = t["alerta_umbral"].fillna(False).astype(bool) | t["alerta_media_4h"].fillna(False).astype(bool)
    t["exceso_kwh"] = (t["energia_no_ti_kwh"] - t["esperado_energia_no_ti_kwh"]).clip(lower=0).where(fisica, 0.0)
    t["exceso_l"] = (t["water_l"] - t["esperado_agua_l"]).clip(lower=0).where(fisica, 0.0)
    t["clima_no_visto"] = t["clima_no_visto"].fillna(False).astype(bool)
    return t


def cargar() -> Datos:
    fuentes = {}
    if kit.disponible():
        datos, fuentes["telemetria"] = kit.leer(), "kit"
    else:
        datos, fuentes["telemetria"] = kit.ejemplo(), "ejemplo"

    avisos = []
    detector = _detector_oficial(avisos)
    if detector is not None:
        fuentes["detector"] = "modelo"
    else:
        detector, fuentes["detector"] = linea_base.detectar(datos), "vista_previa"
    tabla = unir(datos, detector)

    if RUTAS["numeros"].exists():
        numeros, fuentes["numeros"] = json.loads(RUTAS["numeros"].read_text(encoding="utf-8")), "oficial"
    else:
        numeros, fuentes["numeros"] = json.loads(RUTAS["ejemplo"].read_text(encoding="utf-8")), "ejemplo"

    evaluacion = {"dripsafe": calculos.evaluacion(tabla, "alerta"),
                  "reglas": calculos.evaluacion(tabla, "alerta_reglas")}
    consumo = {}
    if RUTAS["consumo"].exists():
        consumo = json.loads(RUTAS["consumo"].read_text(encoding="utf-8"))
    return Datos(tabla, calculos.eventos(tabla), evaluacion, numeros, kit.benchmarks(), fuentes, consumo, avisos)


def cifra(numeros: dict, clave: str, defecto=None):
    """Valor de una cifra del contrato 4, o `defecto` si todavía no existe."""
    dato = numeros.get(clave)
    return dato["valor"] if isinstance(dato, dict) and "valor" in dato else defecto


# De la cifra más firme a la más débil. Una cifra calculada con otras hereda la más débil.
FIRMEZA = ["observado", "medido", "estimado", "proyectado", "vista_previa", "ejemplo"]


def mas_debil(*tipos: str) -> str:
    """La etiqueta más débil: algo calculado con una cifra de ejemplo también es de ejemplo."""
    return max(tipos, key=FIRMEZA.index)


def tipo_cifra(numeros: dict, clave: str, ejemplo: bool) -> str:
    """Qué tan firme es una cifra: el «tipo» del JSON, o «ejemplo» si el archivo es el de ejemplo."""
    if ejemplo:
        return "ejemplo"
    dato = numeros.get(clave)
    return dato.get("tipo", "estimado") if isinstance(dato, dict) else "vista_previa"
