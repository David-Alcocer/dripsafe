"""Detector de anomalías de DripSafe (contrato 3 v2).

Pipeline por sitio, con las filas ordenadas por hora:

1. Línea base con mínimos cuadrados (``numpy.linalg.lstsq``), ajustada con las
   primeras 48 h de ``etiqueta_particion == "entrenamiento"``.
2. Residuos en % (energía no TI y agua) y en °C (temperatura de entrada).
3. Umbral por residuo: máximo absoluto de las 24 h de calibración × 1.5, con
   mínimos de 3 % / 3 % / 0.5 °C. Solo alerta el exceso positivo.
4. EWMA ``span=4`` calculado sin las horas que ya saltaron por umbral. Su
   umbral es el máximo de calibración × 1.5, con un mínimo de 2/3 del umbral
   anterior. Alerta si la EWMA y la hora actual lo superan.
5. Clima no visto: si ``t_exterior`` sale del rango de entrenamiento, los
   umbrales se duplican y la alerta lleva «confianza baja». Nunca se apaga.
6. Clases OT: escalón sin registro, intento de acceso, cambio no autorizado e
   incidente OT con efecto (el exceso debe EMPEZAR dentro del evento o hasta
   24 h después de su fin; uno que ya venía de antes se queda como escalón).

El detector únicamente usa columnas del contrato. En particular, jamás lee
``etiqueta_escenario`` ni ``etiqueta_tipo``: ``etiqueta_particion`` solo separa
las 48 h de ajuste y las 24 h de calibración. El registro ``ot_event`` sí es una
entrada válida del contrato y se usa para clasificar, no para detectar.

Uso:
    python -m src.modelo.detector --entrada data/procesado/telemetria.csv
    python -m src.modelo.detector --entrada ... --sin-medir
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src import contrato

HORAS_AJUSTE = 48
HORAS_CALIBRACION = 24
MARGEN = 1.5
MINIMOS = {"energia": 3.0, "agua": 3.0, "entrada": 0.5}
VENTANA_EFECTO_H = 24
SPAN_EWMA = 4

COLUMNAS_ENTRADA = [
    "timestamp",
    "site_id",
    "kw_ti",
    "kw_total",
    "agua_reposicion_l",
    "t_exterior",
    "inlet_temp_c",
    "ot_event",
    "etiqueta_particion",
]

COLUMNAS_SALIDA = [
    "timestamp",
    "site_id",
    "esperado_energia_no_ti_kwh",
    "esperado_agua_l",
    "esperado_entrada_c",
    "residuo_energia_pct",
    "residuo_agua_pct",
    "residuo_entrada_c",
    "alerta_umbral",
    "alerta_media_4h",
    "clima_no_visto",
    "clase",
    "motivo",
]

_NOMBRES = {"energia": "energía no TI", "agua": "agua", "entrada": "entrada"}
_UNIDADES = {"energia": "%", "agua": "%", "entrada": " °C"}
_RESIDUOS = {
    "energia": "residuo_energia_pct",
    "agua": "residuo_agua_pct",
    "entrada": "residuo_entrada_c",
}


def _bisagra(t: pd.Series) -> pd.Series:
    """Grados por encima de 20 °C: el aire exterior ya no ayuda a enfriar."""
    return (t.astype(float) - 20.0).clip(lower=0.0)


def _matrices(s: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Matrices de diseño de la línea base (energía/agua y entrada)."""
    uno = np.ones(len(s), dtype=float)
    h = _bisagra(s["t_exterior"]).to_numpy(dtype=float)
    it = s["kw_ti"].to_numpy(dtype=float)
    return np.column_stack([uno, it, it * h]), np.column_stack([uno, h])


def _ajustar(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Mínimos cuadrados: coeficientes que mejor explican ``y`` con ``x``."""
    return np.linalg.lstsq(x, y, rcond=None)[0]


def _pct(real: np.ndarray, esperado: np.ndarray) -> np.ndarray:
    """Residuo relativo en %. Si lo esperado es 0, usa ±100 % como tope."""
    real = np.asarray(real, dtype=float)
    esperado = np.asarray(esperado, dtype=float)
    seguro = np.where(esperado > 0.0, esperado, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        residuo = (real - seguro) / seguro * 100.0
    return np.nan_to_num(residuo, nan=0.0, posinf=100.0, neginf=-100.0)


def _paso_horas(horas: pd.Series) -> float:
    """Intervalo mediano entre filas, en horas."""
    diferencias = pd.to_datetime(horas).diff().dropna().dt.total_seconds() / 3600.0
    if diferencias.empty:
        return 1.0
    return float(diferencias.median())


def _tramos(mascara: pd.Series, horas: pd.Series, paso: float) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Horas seguidas donde la máscara es verdadera: [(inicio, fin_exclusivo)]."""
    seleccion = pd.Series(pd.to_datetime(horas))[mascara.to_numpy()].reset_index(drop=True)
    if seleccion.empty:
        return []
    corte = pd.Timedelta(hours=1.5 * max(paso, 1e-9))
    grupo = (seleccion.diff() > corte).cumsum()
    fin = pd.Timedelta(hours=paso)
    return [(g.iloc[0], g.iloc[-1] + fin) for _, g in seleccion.groupby(grupo)]


def _preparar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Valida la entrada y regresa solo las columnas permitidas, ordenadas."""
    faltan = [c for c in COLUMNAS_ENTRADA if c not in tabla.columns]
    if faltan:
        raise ValueError(f"Faltan columnas del contrato para el detector: {faltan}")

    df = tabla[COLUMNAS_ENTRADA].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df["site_id"] = df["site_id"].astype(str)
    df["ot_event"] = df["ot_event"].fillna("normal").astype(str)

    particion = df["etiqueta_particion"].astype(str).str.lower()
    # El contrato usa 'entrenamiento'; se acepta 'referencia' por compatibilidad.
    particion = particion.replace({"referencia": "entrenamiento"})
    df["etiqueta_particion"] = particion

    if not (particion == "entrenamiento").any():
        raise ValueError("No hay filas con etiqueta_particion == 'entrenamiento'")
    if df.duplicated(["site_id", "timestamp"]).any():
        raise ValueError("Hay timestamps duplicados por sitio")
    return df.sort_values(["site_id", "timestamp"], kind="stable").reset_index(drop=True)


def _ajustar_sitio(s: pd.DataFrame) -> dict:
    """Aprende la línea base y calibra los umbrales de un sitio."""
    # ``_preparar`` ya ordenó por (site_id, timestamp); solo alineamos posiciones.
    s = s.reset_index(drop=True)
    referencia = s.index[s["etiqueta_particion"] == "entrenamiento"]
    if len(referencia) <= HORAS_AJUSTE:
        raise ValueError(
            f"El sitio {s['site_id'].iloc[0]!r} necesita más de {HORAS_AJUSTE} h "
            "de entrenamiento (48 h de ajuste + 24 h de calibración)"
        )

    ajuste = referencia[:HORAS_AJUSTE]
    calibracion = referencia[HORAS_AJUSTE:HORAS_AJUSTE + HORAS_CALIBRACION]
    if len(calibracion) == 0:  # datos cortos: se calibra con lo que haya
        calibracion = ajuste

    x_energia, x_clima = _matrices(s)
    no_ti = (s["kw_total"] - s["kw_ti"]).to_numpy(dtype=float)
    agua = s["agua_reposicion_l"].to_numpy(dtype=float)
    entrada = s["inlet_temp_c"].to_numpy(dtype=float)

    coef_energia = _ajustar(x_energia[ajuste], no_ti[ajuste])
    coef_agua = _ajustar(x_energia[ajuste], agua[ajuste])
    coef_entrada = _ajustar(x_clima[ajuste], entrada[ajuste])

    residuos = {
        "energia": pd.Series(_pct(no_ti, x_energia @ coef_energia)),
        "agua": pd.Series(_pct(agua, x_energia @ coef_agua)),
        "entrada": pd.Series(entrada - x_clima @ coef_entrada),
    }

    t_ref = s.loc[referencia, "t_exterior"]
    t_min, t_max = float(t_ref.min()), float(t_ref.max())

    limites: dict[str, float] = {}
    limites_media: dict[str, float] = {}
    for clave, r in residuos.items():
        fuera = ~s["t_exterior"].between(t_min, t_max)
        factor = np.where(fuera, 2.0, 1.0)
        max_calib = float(r.iloc[calibracion].abs().max()) if len(calibracion) else 0.0
        limite = max(max_calib * MARGEN, MINIMOS[clave])

        # EWMA calculada SIN las horas que ya salieron por umbral (sin cola).
        por_hora = r > limite * factor
        ewma = (
            r.where(~por_hora)
            .ewm(span=SPAN_EWMA, ignore_na=True)
            .mean()
            .ffill()
            .fillna(0.0)
        )
        max_media = float(ewma.iloc[calibracion].abs().max()) if len(calibracion) else 0.0
        limite_media = max(max_media * MARGEN, (2.0 / 3.0) * limite)

        limites[clave] = limite
        limites_media[clave] = limite_media

    return {
        "coef_energia": coef_energia,
        "coef_agua": coef_agua,
        "coef_entrada": coef_entrada,
        "limites": limites,
        "limites_media": limites_media,
        "t_min": t_min,
        "t_max": t_max,
    }


def _clasificar(o: pd.DataFrame, paso: float) -> pd.Series:
    """Cruza los excesos con el registro OT para asignar una de las 4 clases."""
    clase = pd.Series("normal", index=o.index, dtype=object)
    exceso = (o["alerta_umbral"] | o["alerta_media_4h"]).astype(bool)
    clase[exceso] = "escalon_sin_registro"

    horas = o["timestamp"]
    tramos_exceso = _tramos(exceso, horas, paso)
    ot = o["_ot"].fillna("normal")
    eventos = _tramos(ot != "normal", horas, paso)

    for inicio, fin in eventos:
        en_evento = (horas >= inicio) & (horas < fin)
        login = en_evento & (ot == "login_fallido")
        cambio = en_evento & (ot == "cambio_config_no_autorizado")

        # Un login fallido solo es intento si no hay un exceso físico en esa hora.
        clase[login & ~exceso] = "intento_acceso"
        # Un cambio no autorizado se marca siempre, con o sin efecto.
        clase[cambio] = "cambio_no_autorizado"

        # Efecto: un tramo de exceso que EMPIEZA dentro del evento o hasta 24 h
        # después de su fin. Uno que ya venía de antes no es causal.
        limite = fin + pd.Timedelta(hours=VENTANA_EFECTO_H)
        for e_ini, e_fin in tramos_exceso:
            if inicio <= e_ini <= limite:
                tramo = (horas >= e_ini) & (horas < e_fin)
                clase[tramo | cambio] = "incidente_ot"

    return clase


def _aplicar_sitio(s: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Calcula esperados, residuos, alertas y clase de un sitio."""
    # ``_preparar`` ya ordenó por (site_id, timestamp); solo alineamos posiciones.
    s = s.reset_index(drop=True)
    paso = _paso_horas(s["timestamp"])
    x_energia, x_clima = _matrices(s)
    no_ti = (s["kw_total"] - s["kw_ti"]).to_numpy(dtype=float)
    agua = s["agua_reposicion_l"].to_numpy(dtype=float)
    entrada = s["inlet_temp_c"].to_numpy(dtype=float)

    esperado_energia = x_energia @ params["coef_energia"]
    esperado_agua = x_energia @ params["coef_agua"]
    esperado_entrada = x_clima @ params["coef_entrada"]

    out = pd.DataFrame({
        "timestamp": s["timestamp"],
        "site_id": s["site_id"],
        "esperado_energia_no_ti_kwh": esperado_energia,
        "esperado_agua_l": esperado_agua,
        "esperado_entrada_c": esperado_entrada,
        "residuo_energia_pct": _pct(no_ti, esperado_energia),
        "residuo_agua_pct": _pct(agua, esperado_agua),
        "residuo_entrada_c": entrada - esperado_entrada,
    })

    clima_no_visto = ~s["t_exterior"].between(params["t_min"], params["t_max"])
    factor = np.where(clima_no_visto, 2.0, 1.0)

    alerta_umbral = pd.Series(False, index=out.index)
    alerta_media = pd.Series(False, index=out.index)
    motivos: list[list[str]] = [[] for _ in range(len(out))]

    for clave in ("energia", "agua", "entrada"):
        r = out[_RESIDUOS[clave]].astype(float)
        limite = params["limites"][clave]
        limite_media = params["limites_media"][clave]

        por_hora = r > limite * factor
        ewma = (
            r.where(~por_hora)
            .ewm(span=SPAN_EWMA, ignore_na=True)
            .mean()
            .ffill()
            .fillna(0.0)
        )
        # La EWMA y la hora actual deben superar el umbral; una cola que ya
        # terminó no sigue alertando. Las horas que ya saltaron no cuentan.
        sostenido = (ewma > limite_media * factor) & (r > limite_media * factor) & ~por_hora

        alerta_umbral |= por_hora
        alerta_media |= sostenido

        for i in np.flatnonzero(por_hora.to_numpy()):
            motivos[i].append(
                f"{_NOMBRES[clave]} {r.iloc[i]:+.0f}{_UNIDADES[clave]} sobre lo esperado"
                if _UNIDADES[clave] == "%"
                else f"{_NOMBRES[clave]} {r.iloc[i]:+.1f}{_UNIDADES[clave]} sobre lo esperado"
            )
        for i in np.flatnonzero(sostenido.to_numpy()):
            if not por_hora.iloc[i]:
                motivos[i].append(
                    f"{_NOMBRES[clave]} {ewma.iloc[i]:+.0f}{_UNIDADES[clave]} "
                    "sobre lo esperado (media 4 h)"
                    if _UNIDADES[clave] == "%"
                    else f"{_NOMBRES[clave]} {ewma.iloc[i]:+.1f}{_UNIDADES[clave]} "
                    "sobre lo esperado (media 4 h)"
                )

    out["alerta_umbral"] = alerta_umbral.to_numpy()
    out["alerta_media_4h"] = alerta_media.to_numpy()
    out["clima_no_visto"] = clima_no_visto.to_numpy()
    out["_ot"] = s["ot_event"].to_numpy()
    out["clase"] = _clasificar(out, paso).to_numpy()

    motivos_finales = []
    for i, clase in enumerate(out["clase"]):
        fisica = bool(out["alerta_umbral"].iloc[i] or out["alerta_media_4h"].iloc[i])
        partes = list(motivos[i])
        if clase == "intento_acceso" and not fisica:
            partes.append("login fallido sin efecto físico")
        elif clase == "cambio_no_autorizado" and not fisica:
            partes.append("cambio de configuración no autorizado sin efecto físico")
        elif clase == "incidente_ot" and not fisica:
            partes.append("efecto físico en la ventana del evento OT")
        elif clase == "escalon_sin_registro" and not fisica:
            partes.append("exceso sin registro OT")
        if bool(out["clima_no_visto"].iloc[i]) and clase != "normal":
            partes.append("confianza baja: clima fuera de lo aprendido")
        motivos_finales.append("; ".join(partes))

    out["motivo"] = motivos_finales
    return out.drop(columns="_ot")


def entrenar(tabla: pd.DataFrame) -> dict[str, dict]:
    """Ajusta la línea base y calibra umbrales por sitio (sin inferir)."""
    df = _preparar(tabla)
    return {
        sitio: _ajustar_sitio(grupo)
        for sitio, grupo in df.groupby("site_id", sort=True)
    }


def detectar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sitio y hora con esperados, residuos, alertas y clase."""
    df = _preparar(tabla)
    partes = []
    for _, grupo in df.groupby("site_id", sort=True):
        params = _ajustar_sitio(grupo)
        partes.append(_aplicar_sitio(grupo, params))
    salida = pd.concat(partes, ignore_index=True)
    return salida[COLUMNAS_SALIDA]


def _medir_consumo(df: pd.DataFrame, repeticiones: int, ruta: Path) -> dict:
    """Mide con CodeCarbon 10 entrenamientos y 10 corridas completas."""
    desde_codecarbon = True
    try:
        from codecarbon import OfflineEmissionsTracker

        def _tracker():
            return OfflineEmissionsTracker(
                country_iso_code="MEX",
                save_to_file=False,
                log_level="error",
            )

        tracker = _tracker()
        tracker.start()
        for _ in range(repeticiones):
            entrenar(df)
        kg_train_total = float(tracker.stop())
        kwh_train_total = float(tracker.final_emissions_data.energy_consumed)

        tiempos: list[float] = []
        tracker = _tracker()
        tracker.start()
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            detectar(df)
            tiempos.append((time.perf_counter() - inicio) * 1000.0)
        tracker.stop()
        kwh_run_total = float(tracker.final_emissions_data.energy_consumed)

        kwh_entrenamiento = kwh_train_total / repeticiones
        kg_co2e_entrenamiento = kg_train_total / repeticiones
        kwh_por_corrida = kwh_run_total / repeticiones
    except Exception:  # CodeCarbon puede no tener permisos en el CI
        desde_codecarbon = False
        tiempos = []
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            detectar(df)
            tiempos.append((time.perf_counter() - inicio) * 1000.0)
        mediana_s = statistics.median(tiempos) / 1000.0
        kwh_por_corrida = 30.0 * mediana_s / 3_600_000.0  # TDP supuesto: 30 W
        kwh_entrenamiento = kwh_por_corrida
        kg_co2e_entrenamiento = 0.0

    ms_mediana = statistics.median(tiempos)
    ms_desviacion = statistics.pstdev(tiempos) if len(tiempos) > 1 else 0.0

    nota = (
        "CodeCarbon en macOS estima con el TDP del CPU. "
        "Contar 8 760 corridas completas al año sobreestima el costo real: "
        "cada corrida incluye el ajuste de la línea base, que en producción "
        "se hace por temporada, no cada hora."
    )
    if not desde_codecarbon:
        nota += " No se pudo iniciar CodeCarbon; los kWh son una estimación con TDP de 30 W."

    consumo = {
        "kwh_entrenamiento": kwh_entrenamiento,
        "kwh_inferencia_anual": kwh_por_corrida * 8_760,
        "kg_co2e_entrenamiento": kg_co2e_entrenamiento,
        "fecha": date.today().isoformat(),
        "ms_mediana": ms_mediana,
        "ms_desviacion": ms_desviacion,
        "repeticiones": repeticiones,
        "nota": nota,
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(consumo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return consumo


def main() -> None:
    parser = argparse.ArgumentParser(description="Detector de anomalías de DripSafe (contrato 3 v2).")
    parser.add_argument(
        "--entrada", type=Path, default=Path("data/procesado/telemetria.csv"),
        help="telemetría del contrato v2",
    )
    parser.add_argument(
        "--salida", type=Path, default=Path("data/resultados/alertas.csv"),
        help="CSV de alertas por sitio y hora",
    )
    parser.add_argument(
        "--consumo", type=Path, default=Path("data/resultados/consumo_modelo.json"),
        help="JSON de consumo del modelo",
    )
    parser.add_argument("--sin-medir", action="store_true", help="no ejecutar CodeCarbon")
    parser.add_argument("--repeticiones", type=int, default=10, help="corridas para medir consumo")
    args = parser.parse_args()

    df = contrato.leer(args.entrada)
    problemas = contrato.validar(df)
    if problemas:
        print("La telemetría NO cumple el contrato:")
        for problema in problemas:
            print(f"  - {problema}")
        raise SystemExit(1)

    alertas = detectar(df)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    alertas.to_csv(args.salida, index=False)

    fisicas = alertas["alerta_umbral"] | alertas["alerta_media_4h"]
    print(f"{len(alertas)} filas → {args.salida}")
    print(f"Sitios: {sorted(alertas['site_id'].unique())}")
    print(f"Alertas físicas: {int(fisicas.sum())}")
    print("Clases:")
    for clase, conteo in alertas["clase"].value_counts().sort_index().items():
        print(f"  {clase}: {int(conteo)}")

    if args.sin_medir:
        print("Medición con CodeCarbon omitida (--sin-medir).")
        return

    consumo = _medir_consumo(df, max(1, args.repeticiones), args.consumo)
    print(f"Consumo → {args.consumo}")
    print(
        f"  {consumo['ms_mediana']:.1f} ms/corrida · "
        f"{consumo['kwh_inferencia_anual']:.6f} kWh/año"
    )


if __name__ == "__main__":
    main()
