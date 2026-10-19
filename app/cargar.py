"""Lee los contratos que necesita el dashboard. Si todavía no existen, usa los simulados.

El dashboard solo conoce estos archivos (ver docs/11-trabajo-en-paralelo.md):
- Contrato 2: data/escenarios/telemetria_escenarios.csv (+ .manifiesto.json)
- Contrato 3: data/resultados/alertas.csv
- Contrato 4: resultados/numeros_oficiales.json

Cuando Misa, Guille y Gadiel entreguen sus archivos, no hay que tocar código:
basta con que estén en estas rutas.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app import calculos, simulado
from src import contrato
from src.ataques.evaluar import evaluar

RAIZ = Path(__file__).resolve().parent.parent
RUTAS = {
    "escenarios": RAIZ / "data/escenarios/telemetria_escenarios.csv",
    "alertas": RAIZ / "data/resultados/alertas.csv",
    "numeros": RAIZ / "resultados/numeros_oficiales.json",
}


@dataclass
class Datos:
    tabla: pd.DataFrame          # telemetría + alertas + columnas derivadas, una fila por intervalo
    manifiesto: dict             # ventanas de cada escenario
    numeros: dict                # contrato 4
    deteccion: pd.DataFrame      # una fila por escenario
    resumen_deteccion: dict
    eventos: pd.DataFrame        # alertas agrupadas en tramos
    fuentes: dict = field(default_factory=dict)  # "real" o "simulado" por cada contrato


def cargar() -> Datos:
    fuentes = {}
    if RUTAS["escenarios"].exists() and RUTAS["alertas"].exists():
        escenarios = contrato.leer(RUTAS["escenarios"])
        manifiesto = json.loads(RUTAS["escenarios"].with_suffix(".manifiesto.json").read_text(encoding="utf-8"))
        alertas = contrato.leer(RUTAS["alertas"])
        limpia = None
        fuentes["escenarios"] = fuentes["alertas"] = "real"
    else:
        # Los dos van juntos: las alertas simuladas necesitan la telemetría limpia de la que salieron.
        limpia, escenarios, manifiesto = simulado.telemetria()
        alertas = simulado.alertas(limpia, escenarios)
        fuentes["escenarios"] = fuentes["alertas"] = "simulado"

    for col in ["etiqueta_escenario", "etiqueta_tecnica"]:
        escenarios[col] = escenarios[col].fillna("")
    deteccion, resumen = evaluar(escenarios, alertas)

    if RUTAS["numeros"].exists():
        numeros = json.loads(RUTAS["numeros"].read_text(encoding="utf-8"))
        fuentes["numeros"] = "real"
    else:
        if limpia is None:
            limpia, _, _ = simulado.telemetria()
        numeros = simulado.numeros_oficiales(escenarios, alertas, limpia, resumen)
        fuentes["numeros"] = "simulado"

    tabla = escenarios.merge(alertas, on="timestamp", how="left", validate="one_to_one")
    tabla["anomalia"] = tabla["anomalia"].fillna(False).astype(bool)
    tabla["variable_principal"] = tabla["variable_principal"].fillna("")
    tabla = calculos.agregar_derivadas(tabla)

    return Datos(tabla, manifiesto, numeros, deteccion, resumen, calculos.eventos(tabla), fuentes)


def cifra(numeros: dict, clave: str, defecto=None):
    """Valor de una cifra del contrato 4, o `defecto` si todavía no existe."""
    dato = numeros.get(clave)
    return dato["valor"] if isinstance(dato, dict) else defecto
