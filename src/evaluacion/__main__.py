"""Ejecuta N1 con el kit local sin copiar datos al repositorio."""

import argparse
import json
import os
from pathlib import Path

from app import kit
from src.datos.cargar import cargar
from src.evaluacion.episodios import episodios_desde_etiquetas, evaluar_episodios
from src.evaluacion.reglas import reglas_fijas
from src.metricas.impacto import exceso_no_ti, pue_wue_por_sitio

RAIZ_REPO = Path(__file__).resolve().parents[2]


def _ruta_kit(explicita: Path | None) -> Path:
    if explicita is not None:
        ruta = explicita.expanduser()
        if not ruta.is_file():
            raise ValueError(f"No existe el CSV indicado: {ruta}")
        return ruta

    carpeta_env = os.environ.get("DRIPSAFE_KIT")
    if carpeta_env:
        ruta = Path(carpeta_env).expanduser() / "data" / "operaciones_simuladas.csv"
        if not ruta.is_file():
            raise ValueError(f"DRIPSAFE_KIT no contiene el CSV esperado: {ruta}")
        return ruta

    if kit.ruta_csv().is_file():
        return kit.ruta_csv()

    carpeta_datos = Path.home() / "dataset"
    coincidencias = sorted(carpeta_datos.rglob("operaciones_simuladas.csv")) if carpeta_datos.is_dir() else []
    if len(coincidencias) != 1:
        raise ValueError(
            f"Se encontraron {len(coincidencias)} kits en {carpeta_datos}. "
            "Indica el CSV con --kit o define DRIPSAFE_KIT."
        )
    return coincidencias[0]


def _mostrar_ratios(datos, particion: str) -> None:
    tabla = pue_wue_por_sitio(
        datos, particion=particion, unidad_energia="kwh_intervalo", horas_por_intervalo=1,
    )
    print(f"\nPUE y WUE in situ · {particion}")
    print("Sitio   Horas-sitio    PUE    WUE (L/kWh TI)")
    for fila in tabla.itertuples(index=False):
        print(f"{fila.site_id:<7} {fila.n_intervalos:>11}  {fila.pue:>7.4f}  {fila.wue_in_situ_l_kwh:>14.4f}")
    energia_it = tabla["energia_it_kwh"].sum()
    print(
        f"TOTAL   {int(tabla['n_intervalos'].sum()):>11}  "
        f"{tabla['energia_total_kwh'].sum() / energia_it:>7.4f}  "
        f"{tabla['agua_in_situ_l'].sum() / energia_it:>14.4f}"
    )


def _mostrar_episodios(nombre: str, datos, alertas, episodios) -> None:
    detalle, resumen = evaluar_episodios(datos, alertas, episodios, horas_por_intervalo=1)
    print(f"\nEvaluación por episodio · {nombre}")
    print(f"TP={resumen['tp']}  FP={resumen['fp']}  FN={resumen['fn']}")
    precision = "sin definir" if resumen["precision"] is None else f"{resumen['precision']:.4f}"
    recall = "sin definir" if resumen["recall"] is None else f"{resumen['recall']:.4f}"
    print(f"Precisión={precision}  Recall={recall}")
    print(
        f"Falsas alarmas/día-sitio={resumen['falsas_alarmas_por_dia_sitio']:.4f} "
        f"(IC 95 %: {resumen['ic_falsas_alarmas_por_dia_sitio'][0]:.4f}–"
        f"{resumen['ic_falsas_alarmas_por_dia_sitio'][1]:.4f}; "
        f"{resumen['horas_limpias_sitio']} horas limpias de sitio)"
    )
    for ep in detalle.itertuples(index=False):
        latencia = f"{ep.horas_hasta_detectar:g} h" if ep.detectado else "sin detectar"
        print(f"  {ep.site_id}: {ep.inicio} → {ep.fin} · {latencia}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Corre las métricas N1 con el kit local simulado.")
    parser.add_argument("--kit", type=Path, help="Ruta al CSV del kit; por defecto se busca localmente")
    parser.add_argument(
        "--vista-previa", action="store_true",
        help="Incluye residuos estimados con el detector provisional del dashboard",
    )
    args = parser.parse_args()
    try:
        ruta = _ruta_kit(args.kit)
    except ValueError as error:
        parser.error(str(error))

    mapeo = json.loads((RAIZ_REPO / "config/columnas.json").read_text(encoding="utf-8"))
    datos = cargar(ruta, mapeo)
    print(f"Kit local SIMULADO: {ruta} ({len(datos)} filas)")
    print("Unidad: kWh por intervalo de 1 hora; agua: litros captados in situ.")
    for particion in ("entrenamiento", "evaluacion"):
        _mostrar_ratios(datos, particion)

    episodios = episodios_desde_etiquetas(datos, horas_por_intervalo=1)
    reglas = reglas_fijas(datos, unidad_energia="kwh_intervalo", horas_por_intervalo=1)
    _mostrar_episodios("reglas didácticas con OT", datos, reglas, episodios)

    if args.vista_previa:
        from app.linea_base import detectar

        preview = detectar(kit.leer(ruta))
        preview["anomalia"] = preview["clase"].ne("normal")
        _mostrar_episodios("detector de VISTA PREVIA", datos, preview, episodios)
        exceso = exceso_no_ti(
            datos, preview, columna_esperado="esperado_energia_no_ti_kwh",
            columna_esperado_agua="esperado_agua_l", unidad_energia="kwh_intervalo",
            horas_por_intervalo=1,
        )
        print("\nExceso positivo ESTIMADO con vista previa (no es ahorro observado)")
        for columna, unidad in (
            ("exceso_no_ti_estimado_kwh", "kWh no TI"),
            ("exceso_no_ti_con_alerta_kwh", "kWh no TI coincidentes con alerta"),
            ("exceso_agua_in_situ_estimado_l", "L de agua in situ"),
            ("exceso_agua_con_alerta_l", "L de agua coincidentes con alerta"),
        ):
            print(f"  {unidad}: {exceso[columna].sum():.2f}")
    else:
        print("\nPredicciones oficiales pendientes; usa --vista-previa para una estimación provisional.")


if __name__ == "__main__":
    main()
