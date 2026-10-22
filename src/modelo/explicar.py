"""Explica cada alerta del detector en dos columnas (issue #8).

Toma la salida de ``src/modelo/detector.py`` (una fila por sitio y hora) y le
agrega, sin volver a detectar nada:

- ``variable_principal``: la variable que explica la alerta física
  (``energia``, ``agua`` o ``entrada``), o vacío si no hay alerta física.
- ``tipo_sugerido``: ``ineficiencia``, ``posible_ataque`` o ``normal``. Es lo
  que mide ``src/ataques/evaluar.py`` como ``clasificacion_correcta_pct``.

Reglas (docs/05, «Cómo se explica cada alerta»):

1. variable_principal: entre las variables con ``exceso_*`` verdadero, la de
   mayor residuo relativo. Energía y agua ya vienen en %; la entrada viene en
   °C, así que cada residuo se divide entre el umbral mínimo del detector
   (``detector.MINIMOS``: 3 %, 3 % y 0.5 °C). Así 1 °C de entrada pesa lo mismo
   que 6 % de energía o de agua. En empate gana el orden energía, agua, entrada.
2. tipo_sugerido sale solo de la clase OT (``src/ot/clases.py``):
   - ``posible_ataque``: hay un evento OT de por medio (incidente OT, cambio no
     autorizado o intento de acceso). «Posible»: un login fallido no prueba una
     intrusión (docs/06 §4 y §7).
   - ``ineficiencia``: exceso físico sin evento OT (escalón sin registro). La
     acción sigue siendo la de clases.py: revisar la configuración ANTES de
     mandar a mantenimiento (regla de oro 1), porque un exceso no distingue
     falla de ataque (docs/06 §7.5).
   - ``normal``: sin clase.

Uso:
    python -m src.modelo.explicar --alertas data/resultados/alertas.csv \\
        --salida data/resultados/alertas.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.modelo.detector import MINIMOS

# El orden también es el desempate.
VARIABLES = ["energia", "agua", "entrada"]
RESIDUOS = {
    "energia": "residuo_energia_pct",
    "agua": "residuo_agua_pct",
    "entrada": "residuo_entrada_c",
}

TIPO_POR_CLASE = {
    "incidente_ot": "posible_ataque",
    "cambio_no_autorizado": "posible_ataque",
    "intento_acceso": "posible_ataque",
    "escalon_sin_registro": "ineficiencia",
    "normal": "normal",
}

COLUMNAS_ENTRADA = ["clase", *(f"exceso_{v}" for v in VARIABLES), *RESIDUOS.values()]
COLUMNAS_NUEVAS = ["variable_principal", "tipo_sugerido"]


def _variable_principal(tabla: pd.DataFrame) -> np.ndarray:
    """La variable con exceso de mayor residuo relativo; "" si no hay exceso."""
    exceso = np.column_stack([
        tabla[f"exceso_{v}"].fillna(False).astype(bool).to_numpy() for v in VARIABLES
    ])
    peso = np.column_stack([
        tabla[RESIDUOS[v]].astype(float).to_numpy() / MINIMOS[v] for v in VARIABLES
    ])
    # Un residuo vacío con exceso queda abajo de cualquier valor; sin exceso no compite.
    peso = np.where(np.isnan(peso), -np.finfo(float).max, peso)
    peso = np.where(exceso, peso, -np.inf)
    # argmax se queda con la primera en empate: energía, agua, entrada.
    elegida = np.array(VARIABLES, dtype=object)[peso.argmax(axis=1)]
    return np.where(exceso.any(axis=1), elegida, "")


def explicar(alertas: pd.DataFrame) -> pd.DataFrame:
    """Copia de ``alertas`` con ``variable_principal`` y ``tipo_sugerido`` al final."""
    faltan = [c for c in COLUMNAS_ENTRADA if c not in alertas.columns]
    if faltan:
        raise ValueError(f"Faltan columnas del detector para explicar: {faltan}")
    clase = alertas["clase"].fillna("normal").astype(str)
    desconocidas = sorted(set(clase) - set(TIPO_POR_CLASE))
    if desconocidas:
        raise ValueError(f"Clases sin tipo sugerido: {desconocidas}")

    out = alertas.drop(columns=[c for c in COLUMNAS_NUEVAS if c in alertas.columns])
    out["variable_principal"] = _variable_principal(alertas)
    out["tipo_sugerido"] = clase.map(TIPO_POR_CLASE).to_numpy()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Agrega variable_principal y tipo_sugerido a alertas.csv.")
    parser.add_argument(
        "--alertas", type=Path, default=Path("data/resultados/alertas.csv"),
        help="salida del detector (src.modelo.detector)",
    )
    parser.add_argument(
        "--salida", type=Path, default=None,
        help="CSV enriquecido (por omisión, el mismo --alertas)",
    )
    args = parser.parse_args()
    salida = args.salida or args.alertas

    alertas = explicar(pd.read_csv(args.alertas))
    salida.parent.mkdir(parents=True, exist_ok=True)
    alertas.to_csv(salida, index=False)

    print(f"{len(alertas)} filas → {salida}")
    print("tipo_sugerido:")
    for tipo, conteo in alertas["tipo_sugerido"].value_counts().sort_index().items():
        print(f"  {tipo}: {int(conteo)}")
    print("variable_principal (horas con alerta física):")
    variables = alertas["variable_principal"][alertas["variable_principal"] != ""]
    for variable, conteo in variables.value_counts().sort_index().items():
        print(f"  {variable}: {int(conteo)}")


if __name__ == "__main__":
    main()
