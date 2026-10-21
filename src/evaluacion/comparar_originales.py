"""Compara DripSafe y las reglas del kit en los episodios originales de N2.

Las salidas por sitio y episodio se guardan solo bajo data/, fuera de Git.
No mide consumo del detector ni atribuye estos resultados a datos reales.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.datos.cargar import cargar
from src.evaluacion import congelar_n2
from src.evaluacion.__main__ import _ruta_kit
from src.evaluacion.episodios import episodios_desde_etiquetas, evaluar_episodios
from src.evaluacion.reglas import reglas_fijas
from src.modelo.detector import detectar

RAIZ = Path(__file__).resolve().parents[2]
METODOS = ("dripsafe", "reglas_kit")


def _division(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def _horas(datos: pd.DataFrame, alertas: pd.DataFrame, episodios: pd.DataFrame) -> dict:
    """Cuenta horas-sitio en evaluación; la verdad sale solo de los episodios."""
    evaluacion = datos.loc[datos["etiqueta_particion"] == "evaluacion",
                           ["site_id", "timestamp", "etiqueta_escenario"]].copy()
    evaluacion["timestamp"] = pd.to_datetime(evaluacion["timestamp"], utc=True)
    banderas = alertas[["site_id", "timestamp", "anomalia"]].copy()
    banderas["timestamp"] = pd.to_datetime(banderas["timestamp"], utc=True)
    evaluacion = evaluacion.merge(banderas, on=["site_id", "timestamp"],
                                  how="left", validate="one_to_one")
    if evaluacion["anomalia"].isna().any():
        raise ValueError("faltan alertas en horas de evaluación")
    verdad = pd.Series(False, index=evaluacion.index)
    for ep in episodios.itertuples(index=False):
        verdad |= ((evaluacion["site_id"] == ep.site_id) &
                    evaluacion["timestamp"].between(ep.inicio, ep.fin))
    escenario = evaluacion["etiqueta_escenario"].fillna("")
    if not verdad.equals((escenario.ne("")) & (escenario.ne("base"))):
        raise ValueError("las ventanas de episodio no cubren las horas etiquetadas")
    alerta = evaluacion["anomalia"].astype(bool)
    tp = int((verdad & alerta).sum())
    fp = int((~verdad & alerta).sum())
    fn = int((verdad & ~alerta).sum())
    return {"horas_evaluacion_sitio": len(evaluacion),
            "horas_anomalas": int(verdad.sum()),
            "horas_limpias_sitio": int((~verdad).sum()),
            "tp_horas": tp, "fp_horas": fp, "fn_horas": fn,
            "precision_horas": _division(tp, tp + fp),
            "recall_horas": _division(tp, tp + fn)}


def comparar(datos: pd.DataFrame, alertas_por_metodo: dict[str, pd.DataFrame]
            ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve resumen método × sitio y detalle de episodio, sin reentrenar."""
    if set(alertas_por_metodo) != set(METODOS):
        raise ValueError(f"se requieren los métodos {METODOS}")
    episodios = episodios_desde_etiquetas(datos, horas_por_intervalo=1)
    episodios["inicio"] = pd.to_datetime(episodios["inicio"], utc=True)
    episodios["fin"] = pd.to_datetime(episodios["fin"], utc=True)
    sitios = sorted(datos["site_id"].unique())
    filas, detalles = [], []
    for metodo in METODOS:
        alertas = alertas_por_metodo[metodo]
        for sitio in [*sitios, "TOTAL"]:
            d = datos if sitio == "TOTAL" else datos[datos["site_id"] == sitio]
            a = alertas if sitio == "TOTAL" else alertas[alertas["site_id"] == sitio]
            e = episodios if sitio == "TOTAL" else episodios[episodios["site_id"] == sitio]
            detalle, resumen = evaluar_episodios(d, a, e, horas_por_intervalo=1)
            horas = _horas(d, a, e)
            if len(e) != resumen["tp"] + resumen["fn"]:
                raise ValueError("el conteo de episodios no coincide con las ventanas")
            latencias = detalle["horas_hasta_detectar"].dropna()
            ev = d[d["etiqueta_particion"] == "evaluacion"]
            fila = {"metodo": metodo, "site_id": sitio, "particion": "evaluacion",
                    "inicio_utc": pd.to_datetime(ev["timestamp"], utc=True).min(),
                    "fin_utc_inclusivo": pd.to_datetime(ev["timestamp"], utc=True).max(),
                    "episodios_verdaderos": len(e),
                    "tp_episodios": resumen["tp"], "fp_episodios": resumen["fp"],
                    "fn_episodios": resumen["fn"],
                    "precision_episodios": resumen["precision"],
                    "recall_episodios": resumen["recall"],
                    "latencia_media_h": float(latencias.mean()) if len(latencias) else None,
                    "latencia_max_h": float(latencias.max()) if len(latencias) else None,
                    "falsas_alarmas_por_dia_sitio": resumen["falsas_alarmas_por_dia_sitio"],
                    "ic95_falsas_inferior": resumen["ic_falsas_alarmas_por_dia_sitio"][0],
                    "ic95_falsas_superior": resumen["ic_falsas_alarmas_por_dia_sitio"][1],
                    **horas}
            filas.append(fila)
            if sitio == "TOTAL":
                # El total puntúa todos los sitios juntos, pero conserva una
                # única fila por episodio verdadero en el detalle.
                detalle = detalle.merge(episodios[["site_id", "inicio", "fin", "nombre"]],
                                        on=["site_id", "inicio", "fin"], validate="one_to_one")
                detalle.insert(0, "metodo", metodo)
                detalle["duracion_h"] = ((detalle["fin"] - detalle["inicio"])
                                         .dt.total_seconds() / 3600 + 1).astype(int)
                detalles.append(detalle)
    return pd.DataFrame(filas), pd.concat(detalles, ignore_index=True)


def _validar_fijacion(ruta: Path, datos: pd.DataFrame, fijacion: dict) -> None:
    identidad = congelar_n2._identidad_kit(ruta)
    for clave in ("manifest_sha256", "csv_sha256", "csv_bytes"):
        if identidad[clave] != fijacion["kit"][clave]:
            raise ValueError("el kit no coincide con el congelamiento N2")
    codigo = congelar_n2._revision_codigo(fijacion["codigo"]["commit_corte"])
    if codigo["sha256_archivos"] != fijacion["codigo"]["sha256_archivos"]:
        raise ValueError("el código no coincide con el congelamiento N2")
    if set(datos["site_id"]) != set(fijacion["sitios"]):
        raise ValueError("los sitios no coinciden con el congelamiento N2")
    for sitio, ventana in fijacion["sitios"].items():
        ev = datos[(datos["site_id"] == sitio) &
                   (datos["etiqueta_particion"] == "evaluacion")]
        if len(ev) != ventana["evaluacion"]["horas"] or \
                pd.to_datetime(ev["timestamp"], utc=True).min().isoformat() != ventana["evaluacion"]["inicio_utc"] or \
                pd.to_datetime(ev["timestamp"], utc=True).max().isoformat() != ventana["evaluacion"]["fin_utc_inclusivo"]:
            raise ValueError(f"la evaluación de {sitio} no coincide con el congelamiento N2")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara los episodios originales del kit N2")
    parser.add_argument("--kit", type=Path, help="CSV local del kit; se busca si se omite")
    parser.add_argument("--congelamiento", type=Path,
                        default=RAIZ / "resultados/n2_congelamiento.json")
    parser.add_argument("--salida", type=Path, default=RAIZ / "data/resultados")
    args = parser.parse_args()
    ruta = _ruta_kit(args.kit)
    fijacion = json.loads(args.congelamiento.read_text(encoding="utf-8"))
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    datos = cargar(ruta, mapeo)
    _validar_fijacion(ruta, datos, fijacion)
    predicciones = detectar(datos)
    alertas = {
        "dripsafe": predicciones[["site_id", "timestamp"]].assign(
            anomalia=predicciones["clase"].ne("normal")),
        "reglas_kit": reglas_fijas(datos, horas_por_intervalo=1,
                                   unidad_energia="kwh_intervalo"),
    }
    resumen, detalle = comparar(datos, alertas)
    args.salida.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(args.salida / "n2_originales_comparacion.csv", index=False)
    detalle.to_csv(args.salida / "n2_originales_episodios.csv", index=False)
    print("DATOS SIMULADOS · kit original fijado en N2")
    print(resumen[["metodo", "site_id", "episodios_verdaderos", "tp_episodios",
                   "fp_episodios", "fn_episodios", "tp_horas", "fp_horas", "fn_horas",
                   "latencia_media_h"]].to_string(index=False))
    print(f"Tablas locales: {args.salida}/n2_originales_*.csv")


if __name__ == "__main__":
    main()
