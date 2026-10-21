"""Comparación por tipo de enfriamiento y WUE del híbrido del bono (#15 · Misa).

1. `comparar_por_enfriamiento`: por sitio y partición, energía de TI y total,
   agua, PUE y L/kWh de TI. Siempre cocientes de SUMAS (nunca promedios de
   cocientes horarios). Reutiliza `impacto.pue_wue_por_sitio`.
2. `estimar_hibrido`: WUE total, WUE de agua potable y PUE de la propuesta
   híbrida (circuito cerrado + respaldo con agua tratada) a partir de
   SUPUESTOS explícitos. Es una proyección, no algo observado.

Los sitios del kit son escenarios SIMULADOS: no son un experimento controlado
ni una clasificación de tecnologías reales. El agua del kit es captación in
situ: no es consumo neto, ni agua de la generación eléctrica, ni potabilidad.

Uso:
    python -m src.metricas.refrigeracion                      # data/procesado/telemetria.csv
    python -m src.metricas.refrigeracion --kit RUTA/operaciones_simuladas.csv
    python -m src.metricas.refrigeracion --ejemplo            # datos INVENTADOS
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src import contrato
from src.datos.cargar import cargar
from src.metricas.impacto import pue_wue_por_sitio
from src.metricas.pue import unidad_y_horas

RAIZ = Path(__file__).resolve().parents[2]

# Partición del contrato → nombre del kit que se muestra en los docs.
PARTICIONES = {"entrenamiento": "referencia", "evaluacion": "evaluacion"}


def _tipo_por_sitio(telemetria: pd.DataFrame) -> dict[str, str]:
    """Tipo de enfriamiento de cada sitio; falla si un sitio tiene más de uno."""
    if "cooling_type" not in telemetria:
        raise ValueError("falta la columna cooling_type")
    tipos = telemetria.groupby("site_id")["cooling_type"].unique()
    mezclados = [sitio for sitio, valores in tipos.items() if len(valores) != 1]
    if mezclados:
        raise ValueError(f"sitios con más de un tipo de enfriamiento: {mezclados}")
    return {sitio: valores[0] for sitio, valores in tipos.items()}


def comparar_por_enfriamiento(telemetria: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sitio y partición con energías, agua, PUE y L/kWh de TI."""
    tipos = _tipo_por_sitio(telemetria)
    unidad, horas = unidad_y_horas(telemetria)
    partes = []
    for particion, nombre in PARTICIONES.items():
        por_sitio = pue_wue_por_sitio(telemetria, particion=particion,
                                      unidad_energia=unidad, horas_por_intervalo=horas)
        partes.append(pd.DataFrame({
            "site_id": por_sitio["site_id"],
            "cooling_type": por_sitio["site_id"].map(tipos),
            "particion": nombre,
            "filas": por_sitio["n_intervalos"],
            "energia_it_kwh": por_sitio["energia_it_kwh"],
            "energia_total_kwh": por_sitio["energia_total_kwh"],
            "agua_l": por_sitio["agua_in_situ_l"],
            "pue": por_sitio["pue"],
            "l_por_kwh_ti": por_sitio["wue_in_situ_l_kwh"],
        }))
    return pd.concat(partes, ignore_index=True)


@dataclass(frozen=True)
class SupuestosHibrido:
    """Supuestos editables del híbrido. Todo es SUPUESTO, no medición.

    `fraccion_respaldo` es la fracción de la energía de TI servida en modo
    respaldo (picos de calor); el resto va con el circuito cerrado (base).
    `no_potable_*` es la fracción del agua de cada modo que es agua tratada.
    """

    fraccion_respaldo: float
    wue_base: float          # L/kWh de TI del circuito cerrado (reposición)
    wue_respaldo: float      # L/kWh de TI del respaldo evaporativo
    pue_base: float
    pue_respaldo: float
    no_potable_base: float
    no_potable_respaldo: float


def _validar(s: SupuestosHibrido) -> None:
    for nombre in ("fraccion_respaldo", "no_potable_base", "no_potable_respaldo"):
        valor = getattr(s, nombre)
        if not 0.0 <= valor <= 1.0:
            raise ValueError(f"{nombre} debe estar entre 0 y 1 (vale {valor})")
    if s.wue_base < 0 or s.wue_respaldo < 0:
        raise ValueError("los WUE no pueden ser negativos")
    if s.pue_base < 1 or s.pue_respaldo < 1:
        raise ValueError("un PUE no puede ser menor que 1")


def estimar_hibrido(s: SupuestosHibrido) -> dict:
    """WUE total, WUE potable y PUE del híbrido, mezclando por energía de TI."""
    _validar(s)
    base, respaldo = 1.0 - s.fraccion_respaldo, s.fraccion_respaldo
    return {
        "wue_total": base * s.wue_base + respaldo * s.wue_respaldo,
        "wue_potable": (base * s.wue_base * (1.0 - s.no_potable_base)
                        + respaldo * s.wue_respaldo * (1.0 - s.no_potable_respaldo)),
        "pue": base * s.pue_base + respaldo * s.pue_respaldo,
    }


# Por diseño la propuesta usa 100 % agua tratada (reposición del circuito
# cerrado y respaldo), así que los escenarios solo varían f. Son SUPUESTOS, no
# datos de Yucatán: las horas reales de respaldo dependen del clima (N4).
TODO_TRATADA = {"no_potable_base": 1.0, "no_potable_respaldo": 1.0}
ESCENARIOS = {
    "optimista": {"fraccion_respaldo": 0.10, **TODO_TRATADA},
    "central": {"fraccion_respaldo": 0.25, **TODO_TRATADA},
    "conservador": {"fraccion_respaldo": 0.50, **TODO_TRATADA},
}

# Riesgo, no escenario de diseño: si la reposición del circuito cerrado se hace
# con agua de la red, el WUE potable deja de ser 0.
RIESGO_REPOSICION_RED = {"fraccion_respaldo": 0.25, "no_potable_base": 0.0, "no_potable_respaldo": 1.0}


def _coeficientes_del_kit(tabla: pd.DataFrame) -> dict:
    """Base = sitio líquido y respaldo = sitio evaporativo, en referencia (coeficientes didácticos)."""
    ref = tabla[tabla["particion"] == "referencia"].set_index("cooling_type")
    return {
        "wue_base": float(ref.loc["liquida", "l_por_kwh_ti"]),
        "wue_respaldo": float(ref.loc["evaporativa", "l_por_kwh_ti"]),
        "pue_base": float(ref.loc["liquida", "pue"]),
        "pue_respaldo": float(ref.loc["evaporativa", "pue"]),
    }


def _escenario(nombre: str, coeficientes: dict, supuestos: dict) -> dict:
    s = SupuestosHibrido(**coeficientes, **supuestos)
    return {"nombre": nombre, "supuestos": asdict(s), "resultado": estimar_hibrido(s)}


def escenarios_de_sensibilidad(tabla: pd.DataFrame) -> list[dict]:
    """Los 3 escenarios de diseño (100 % agua tratada), variando solo f."""
    coeficientes = _coeficientes_del_kit(tabla)
    return [_escenario(nombre, coeficientes, s) for nombre, s in ESCENARIOS.items()]


def riesgo_reposicion_con_red(tabla: pd.DataFrame) -> dict:
    """Límite: f = 25 % pero la reposición del circuito cerrado sale de la red potable."""
    return _escenario("riesgo_reposicion_red", _coeficientes_del_kit(tabla), RIESGO_REPOSICION_RED)


def _leer(args) -> pd.DataFrame:
    if args.ejemplo:
        from app import kit

        mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "ejemplo.csv"
            kit.ejemplo().to_csv(ruta, index=False)
            return cargar(ruta, mapeo)
    if args.kit:
        mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
        return cargar(args.kit, mapeo)
    return contrato.leer(args.entrada)


def main() -> None:
    p = argparse.ArgumentParser(description="Compara los sitios por tipo de enfriamiento (#15).")
    fuente = p.add_mutually_exclusive_group()
    fuente.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"))
    fuente.add_argument("--kit", type=Path, help="CSV crudo del kit")
    fuente.add_argument("--ejemplo", action="store_true", help="datos INVENTADOS con el formato del kit")
    args = p.parse_args()

    tabla = comparar_por_enfriamiento(_leer(args))
    print("DATOS INVENTADOS (app.kit.ejemplo)\n" if args.ejemplo else "DATOS SIMULADOS (kit CIFOX)\n")
    with pd.option_context("display.float_format", "{:.4f}".format, "display.width", 120):
        print(tabla.to_string(index=False))
    print("\nEscenarios del híbrido (SUPUESTOS, 100 % agua tratada; coeficientes didácticos del kit:"
          " base = sitio líquido, respaldo = sitio evaporativo):")
    for e in [*escenarios_de_sensibilidad(tabla), riesgo_reposicion_con_red(tabla)]:
        r, s = e["resultado"], e["supuestos"]
        print(f"  {e['nombre']:<22} respaldo {s['fraccion_respaldo']:.0%} · "
              f"WUE total {r['wue_total']:.3f} · WUE potable {r['wue_potable']:.3f} L/kWh TI · "
              f"PUE {r['pue']:.3f}")


if __name__ == "__main__":
    main()
