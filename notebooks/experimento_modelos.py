"""Comparación justa de 6 detectores (protocolo de Leo) sobre el kit o una réplica.

Protocolo, por sitio:
  - ajuste: primeras 48 h de ``etiqueta_particion == "entrenamiento"``;
  - calibración de umbrales: las 24 h siguientes;
  - evaluación: las 96 h de ``evaluacion``.

Modelos:
  1. reglas fijas del kit (PUE > 1.6, agua > 1.5 L/kWh IT, entrada > 29 °C, OT);
  2. Isolation Forest con las 6 variables crudas;
  3. PCA T²/SPE;
  4. línea base + umbral;
  5. línea base + EWMA + Isolation Forest sobre residuos;
  6. línea base + umbral + EWMA sin cola.

El kit real NUNCA se copia al repo. Si no está en la ruta de siempre, se usa una
réplica sintética con los agregados publicados del kit (3 sitios × 168 h, PUE
1.2676, 21 h anómalas). Los resultados de la réplica NO son los del kit.

Uso:
    python notebooks/experimento_modelos.py
    python notebooks/experimento_modelos.py --kit "/ruta/al/operaciones_simuladas.csv"
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.datos.cargar import cargar  # noqa: E402
from src.modelo import detector  # noqa: E402

RUTA_KIT = (
    Path.home()
    / "hackathon"
    / "Kit Stack Tecnológico"
    / "Para participantes"
    / "Código y recursos"
    / "data"
    / "operaciones_simuladas.csv"
)
SITIOS = [
    ("SIM-A", "aire", 250.0, 0.33, 0.03),
    ("SIM-B", "evaporativa", 143.0, 0.21, 1.06),
    ("SIM-C", "liquida", 100.0, 0.17, 0.22),
]
COLS_CRUDAS = ["kw_ti", "kw_total", "agua_reposicion_l", "load_pct", "t_exterior", "inlet_temp_c"]
COLS_RESIDUOS = ["residuo_energia_pct", "residuo_agua_pct", "residuo_entrada_c"]


# --------------------------------------------------------------------------- datos


def replica_kit(semilla: int = 11) -> pd.DataFrame:
    """Réplica sintética con el formato y los agregados publicados del kit.

    No es el kit: solo imita sus 3 sitios, 168 h, ruido de ±1.5 % de la energía
    IT y las 21 h anómalas (SIM-A 8 h, SIM-B 8 h, SIM-C 5 h).
    """
    rng = np.random.default_rng(semilla)
    horas = pd.date_range("2026-10-12", periods=168, freq="h", tz="UTC")
    hora = horas.hour.to_numpy()
    filas = []

    for sitio, tipo, base, overhead, wue in SITIOS:
        perfil = 1.0 + 0.15 * np.sin(2 * np.pi * (hora - 9) / 24)
        it = base * perfil + rng.normal(0, base * 0.01, len(horas))
        exterior = 23.0 + 5.0 * np.sin(2 * np.pi * (hora - 9) / 24) + rng.normal(0, 0.3, len(horas))
        entrada = 22.5 + 0.10 * np.clip(exterior - 20.0, 0.0, None) + rng.normal(0, 0.15, len(horas))
        ruido = rng.uniform(-0.015, 0.015, len(horas)) * it
        total = it * (1.0 + overhead) + ruido
        agua = it * wue * (1.0 + rng.normal(0, 0.02, len(horas)))

        df = pd.DataFrame({
            "timestamp": horas,
            "site_id": sitio,
            "cooling_type": tipo,
            "kw_ti": it,
            "kw_total": total,
            "agua_reposicion_l": agua,
            "load_pct": it / base * 40.0,
            "t_exterior": exterior,
            "inlet_temp_c": entrada,
            "ot_event": "normal",
            "etiqueta_escenario": "",
            "etiqueta_tipo": "normal",
            "etiqueta_particion": np.where(
                np.arange(len(horas)) < 72, "entrenamiento", "evaluacion"
            ),
        })

        evaluacion = np.arange(72, 168)
        if sitio == "SIM-A":  # ineficiencia: energía no TI +107 %, entrada +6 °C
            idx = df.index[evaluacion[12:20]]
            no_ti = df.loc[idx, "kw_total"] - df.loc[idx, "kw_ti"]
            df.loc[idx, "kw_total"] = df.loc[idx, "kw_ti"] + no_ti * 2.07
            df.loc[idx, "inlet_temp_c"] += 6.0
            df.loc[idx, "etiqueta_escenario"] = "ineficiencia"
            df.loc[idx, "etiqueta_tipo"] = "falla"
        elif sitio == "SIM-B":  # fuga de agua: +150 %
            idx = df.index[evaluacion[40:48]]
            df.loc[idx, "agua_reposicion_l"] *= 2.5
            df.loc[idx, "etiqueta_escenario"] = "fuga_agua"
            df.loc[idx, "etiqueta_tipo"] = "falla"
        else:  # SIM-C: 3 login fallidos + 2 cambios de configuración, sin efecto
            idx = df.index[evaluacion[70:75]]
            df.loc[idx, "ot_event"] = ["login_fallido"] * 3 + ["cambio_config_no_autorizado"] * 2
            df.loc[idx, "etiqueta_escenario"] = "evento_ot"
            df.loc[idx, "etiqueta_tipo"] = "evento_ot"

        filas.append(df)

    return pd.concat(filas, ignore_index=True)


def cargar_entrada(ruta_kit: Path | None) -> tuple[pd.DataFrame, str]:
    """Carga el kit si existe; si no, usa la réplica. Nunca escribe filas del kit."""
    mapeo = json.loads((RAIZ / "config/columnas.json").read_text(encoding="utf-8"))
    if ruta_kit is not None:
        if not ruta_kit.exists():
            raise FileNotFoundError(f"No existe el CSV del kit: {ruta_kit}")
        return cargar(ruta_kit, mapeo), f"kit ({ruta_kit})"
    if RUTA_KIT.exists():
        return cargar(RUTA_KIT, mapeo), f"kit ({RUTA_KIT})"
    return replica_kit(), "réplica sintética (el kit no está en esta laptop)"


# --------------------------------------------------------------------------- ventanas


def _tramos(mascara: pd.Series, horas: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    seleccion = pd.Series(pd.to_datetime(horas))[mascara.to_numpy()].reset_index(drop=True)
    if seleccion.empty:
        return []
    grupo = (seleccion.diff() > pd.Timedelta(hours=1.5)).cumsum()
    return [(g.iloc[0], g.iloc[-1] + pd.Timedelta(hours=1)) for _, g in seleccion.groupby(grupo)]


def ventanas_originales(datos: pd.DataFrame) -> list[dict]:
    """Episodios etiquetados del kit (solo para calificar, nunca como entrada)."""
    ev = datos[datos["etiqueta_particion"] == "evaluacion"]
    salida = []
    for sitio, g in ev.groupby("site_id", sort=True):
        anomala = g["etiqueta_tipo"] != "normal"
        for inicio, fin in _tramos(anomala, g["timestamp"]):
            tramo = g[(g["timestamp"] >= inicio) & (g["timestamp"] < fin)]
            salida.append({
                "site_id": sitio,
                "inicio": inicio,
                "fin": fin,
                "tipo": tramo["etiqueta_tipo"].iloc[0],
                "escenario": tramo["etiqueta_escenario"].iloc[0],
            })
    return salida


def _indices_ventana(datos: pd.DataFrame, sitio: str, inicio: int, horas: int) -> pd.Index:
    """Índices de ``horas`` filas desde ``inicio`` horas después del inicio de evaluación."""
    horas_sitio = datos.loc[datos["site_id"] == sitio, "timestamp"].sort_values().reset_index(drop=True)
    t0 = horas_sitio.iloc[72 + inicio]
    return datos.index[
        (datos["site_id"] == sitio)
        & (datos["timestamp"] >= t0)
        & (datos["timestamp"] < t0 + pd.Timedelta(hours=horas))
    ]


def _inyectar_energia(datos: pd.DataFrame, sitio: str, inicio: int, pct: float, horas: int = 4) -> None:
    idx = _indices_ventana(datos, sitio, inicio, horas)
    no_ti = datos.loc[idx, "kw_total"] - datos.loc[idx, "kw_ti"]
    datos.loc[idx, "kw_total"] = datos.loc[idx, "kw_ti"] + no_ti * (1.0 + pct / 100.0)


def _inyectar_agua(datos: pd.DataFrame, sitio: str, inicio: int, pct: float, horas: int = 4) -> None:
    idx = _indices_ventana(datos, sitio, inicio, horas)
    datos.loc[idx, "agua_reposicion_l"] *= 1.0 + pct / 100.0


def _inyectar_rampa(datos: pd.DataFrame, sitio: str, inicio: int, pct_hora: float = 0.5) -> None:
    idx = _indices_ventana(datos, sitio, inicio, 24).sort_values()
    base = datos.loc[idx, "kw_total"] - datos.loc[idx, "kw_ti"]
    for k, i in enumerate(idx):
        datos.loc[i, "kw_total"] = datos.loc[i, "kw_ti"] + base.loc[i] * (
            1.0 + pct_hora / 100.0 * (k + 1)
        )


# --------------------------------------------------------------------------- modelos


def alertas_reglas(datos: pd.DataFrame) -> pd.Series:
    pue = datos["kw_total"] / datos["kw_ti"]
    wue = datos["agua_reposicion_l"] / datos["kw_ti"]
    return (
        (pue > 1.6)
        | (wue > 1.5)
        | (datos["inlet_temp_c"] > 29.0)
        | (datos["ot_event"] != "normal")
    )


def _if_por_sitio(datos: pd.DataFrame, columnas: list[str], cuantil: float) -> pd.Series:
    alerta = pd.Series(False, index=datos.index)
    for _, g in datos.groupby("site_id", sort=True):
        g = g.sort_values("timestamp")
        ref = g[g["etiqueta_particion"] == "entrenamiento"]
        ajuste, calibracion = ref.iloc[:48], ref.iloc[48:72]
        escalador = StandardScaler().fit(ajuste[columnas])
        modelo = IsolationForest(n_estimators=100, random_state=42, n_jobs=1).fit(
            escalador.transform(ajuste[columnas])
        )
        score_cal = modelo.decision_function(escalador.transform(calibracion[columnas]))
        umbral = float(np.quantile(score_cal, cuantil)) if len(score_cal) else 0.0
        score = modelo.decision_function(escalador.transform(g[columnas]))
        alerta.loc[g.index] = score < umbral
    return alerta


def alertas_if_crudo(datos: pd.DataFrame) -> pd.Series:
    return _if_por_sitio(datos, COLS_CRUDAS, cuantil=0.05)


def alertas_pca(datos: pd.DataFrame) -> pd.Series:
    alerta = pd.Series(False, index=datos.index)
    for _, g in datos.groupby("site_id", sort=True):
        g = g.sort_values("timestamp")
        ref = g[g["etiqueta_particion"] == "entrenamiento"]
        ajuste, calibracion = ref.iloc[:48], ref.iloc[48:72]
        escalador = StandardScaler().fit(ajuste[COLS_CRUDAS])
        pca = PCA(n_components=2).fit(escalador.transform(ajuste[COLS_CRUDAS]))

        def puntajes(
            tramo: pd.DataFrame, escalador=escalador, pca=pca
        ) -> tuple[np.ndarray, np.ndarray]:
            x = escalador.transform(tramo[COLS_CRUDAS])
            z = pca.transform(x)
            t2 = np.sum(z ** 2 / pca.explained_variance_, axis=1)
            spe = np.sum((x - pca.inverse_transform(z)) ** 2, axis=1)
            return t2, spe

        t2_cal, spe_cal = puntajes(calibracion)
        umbral_t2 = max(float(t2_cal.max()), 1e-9) * 1.5
        umbral_spe = max(float(spe_cal.max()), 1e-9) * 1.5
        t2, spe = puntajes(g)
        alerta.loc[g.index] = (t2 > umbral_t2) | (spe > umbral_spe)
    return alerta


def alertas_linea_base(datos: pd.DataFrame, con_ewma: bool = False) -> pd.Series:
    salida = detector.detectar(datos)
    alerta = salida["alerta_umbral"].astype(bool)
    if con_ewma:
        alerta |= salida["alerta_media_4h"].astype(bool)
    return alerta


def alertas_linea_if(datos: pd.DataFrame) -> pd.Series:
    salida = detector.detectar(datos)
    base = salida["alerta_umbral"].astype(bool) | salida["alerta_media_4h"].astype(bool)
    alerta_if = pd.Series(False, index=datos.index)
    for _, g in datos.groupby("site_id", sort=True):
        ref = g[g["etiqueta_particion"] == "entrenamiento"]
        ajuste, calibracion = ref.iloc[:48], ref.iloc[48:72]
        escalador = StandardScaler().fit(salida.loc[ajuste.index, COLS_RESIDUOS])
        modelo = IsolationForest(n_estimators=100, random_state=42, n_jobs=1).fit(
            escalador.transform(salida.loc[ajuste.index, COLS_RESIDUOS])
        )
        score_cal = modelo.decision_function(
            escalador.transform(salida.loc[calibracion.index, COLS_RESIDUOS])
        )
        umbral = float(np.quantile(score_cal, 0.03)) if len(score_cal) else 0.0
        score = modelo.decision_function(escalador.transform(salida.loc[g.index, COLS_RESIDUOS]))
        alerta_if.loc[g.index] = score < umbral
    return base | alerta_if


MODELOS = [
    ("Reglas fijas del kit", alertas_reglas),
    ("Isolation Forest (6 vars crudas)", alertas_if_crudo),
    ("PCA T²/SPE", alertas_pca),
    ("Línea base + umbral", lambda d: alertas_linea_base(d, con_ewma=False)),
    ("Línea base + EWMA + IF residuos", alertas_linea_if),
    ("Línea base + umbral + EWMA sin cola", lambda d: alertas_linea_base(d, con_ewma=True)),
]


# --------------------------------------------------------------------------- evaluación


def _falsas_por_dia(alerta: pd.Series, limpio: pd.Series) -> float:
    dias = float(limpio.sum()) / 24.0
    if dias <= 0:
        return 0.0
    return float((alerta & limpio).sum()) / dias


def evaluar_original(alerta: pd.Series, datos: pd.DataFrame, ventanas: list[dict]) -> dict:
    ev = datos["etiqueta_particion"] == "evaluacion"
    anomala = ev & (datos["etiqueta_tipo"] != "normal")
    limpio = ev & ~anomala

    fisicas = [v for v in ventanas if v["tipo"] == "falla"]
    detectados = 0
    for v in fisicas:
        en_ventana = (
            (datos["site_id"] == v["site_id"])
            & (datos["timestamp"] >= v["inicio"])
            & (datos["timestamp"] < v["fin"])
        )
        detectados += int(alerta[en_ventana].any())

    return {
        "episodios_detectados": detectados,
        "episodios_totales": len(fisicas),
        "horas_anomalas_detectadas": int((alerta & anomala).sum()),
        "horas_anomalas_totales": int(anomala.sum()),
        "falsas_por_dia": _falsas_por_dia(alerta, limpio),
    }


def _evaluar_inyecciones(
    funcion,
    datos: pd.DataFrame,
    inyecciones: list[dict],
    mascara_inyectada: pd.Series,
    con_ruido: bool = False,
) -> dict:
    copia = datos.copy()
    if con_ruido:
        rng = np.random.default_rng(99)
        evaluacion = copia["etiqueta_particion"] == "evaluacion"
        it = copia.loc[evaluacion, "kw_ti"].to_numpy()
        # Ruido gaussiano adicional solo en evaluación: misma desviación que el
        # ruido uniforme ±1.5 % del kit (0.015/sqrt(3)), es decir, el doble de
        # varianza, y ±4 % al agua. La referencia queda limpia.
        copia.loc[evaluacion, "kw_total"] = (
            copia.loc[evaluacion, "kw_total"]
            + rng.normal(0, 0.015 / np.sqrt(3.0) * it)
        )
        ruido_agua = rng.uniform(-0.04, 0.04, int(evaluacion.sum()))
        copia.loc[evaluacion, "agua_reposicion_l"] = (
            copia.loc[evaluacion, "agua_reposicion_l"] * (1.0 + ruido_agua)
        )

    for inyeccion in inyecciones:
        sitio = inyeccion["site_id"]
        inicio = inyeccion["inicio_eval"]
        if inyeccion["variable"] == "energia":
            _inyectar_energia(copia, sitio, inicio, inyeccion["magnitud"])
        elif inyeccion["variable"] == "agua":
            _inyectar_agua(copia, sitio, inicio, inyeccion["magnitud"])
        elif inyeccion["variable"] == "rampa":
            _inyectar_rampa(copia, sitio, inicio, inyeccion["magnitud"])

    alerta = funcion(copia)
    detectados = 0
    for inyeccion in inyecciones:
        horas = 24 if inyeccion["variable"] == "rampa" else 4
        idx = _indices_ventana(copia, inyeccion["site_id"], inyeccion["inicio_eval"], horas)
        detectados += int(alerta.loc[idx].any())

    ev = copia["etiqueta_particion"] == "evaluacion"
    original = ev & (copia["etiqueta_tipo"] != "normal")
    limpio = ev & ~original & ~mascara_inyectada
    return {
        "detectados": detectados,
        "total": len(inyecciones),
        "falsas_por_dia": _falsas_por_dia(alerta, limpio),
    }


def _inyecciones_energia(pct: float) -> list[dict]:
    return [
        {"variable": "energia", "magnitud": pct, "site_id": sitio, "inicio_eval": inicio}
        for sitio in ("SIM-A", "SIM-B", "SIM-C")
        for inicio in (4, 30, 60, 84)
    ]


def _inyecciones_agua(pct: float) -> list[dict]:
    return [
        {"variable": "agua", "magnitud": pct, "site_id": sitio, "inicio_eval": inicio}
        for sitio in ("SIM-A", "SIM-B", "SIM-C")
        for inicio in (4, 30, 60, 84)
    ]


def _inyecciones_rampa() -> list[dict]:
    # 24 h: solo caben las ventanas 4, 30 y 60 (la de 84 terminaría fuera de la evaluación).
    return [
        {"variable": "rampa", "magnitud": 0.5, "site_id": sitio, "inicio_eval": inicio}
        for sitio in ("SIM-A", "SIM-B", "SIM-C")
        for inicio in (4, 30, 60)
    ]


def _mascara_inyecciones(datos: pd.DataFrame, inyecciones: list[dict]) -> pd.Series:
    mascara = pd.Series(False, index=datos.index)
    for inyeccion in inyecciones:
        horas = 24 if inyeccion["variable"] == "rampa" else 4
        mascara.loc[_indices_ventana(
            datos, inyeccion["site_id"], inyeccion["inicio_eval"], horas
        )] = True
    return mascara


def _medir_tiempo(funcion, datos: pd.DataFrame, repeticiones: int = 5) -> float:
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion(datos)
        tiempos.append((time.perf_counter() - inicio) * 1000.0)
    return statistics.median(tiempos)


def ejecutar(datos: pd.DataFrame, fuente: str, repeticiones: int = 5) -> dict:
    ventanas = ventanas_originales(datos)
    resultados = {}

    for nombre, funcion in MODELOS:
        alerta = funcion(datos)
        original = evaluar_original(alerta, datos, ventanas)
        ms = _medir_tiempo(funcion, datos, repeticiones)

        fila = {**original, "ms": ms}
        for pct in (10, 20, 40, 80):
            inyecciones = _inyecciones_energia(pct)
            fila[f"energia_{pct}"] = _evaluar_inyecciones(
                funcion, datos, inyecciones, _mascara_inyecciones(datos, inyecciones)
            )
        for pct in (25, 50):
            inyecciones = _inyecciones_agua(pct)
            fila[f"agua_{pct}"] = _evaluar_inyecciones(
                funcion, datos, inyecciones, _mascara_inyecciones(datos, inyecciones)
            )
        inyecciones = _inyecciones_rampa()
        fila["rampa"] = _evaluar_inyecciones(
            funcion, datos, inyecciones, _mascara_inyecciones(datos, inyecciones)
        )
        inyecciones = _inyecciones_energia(20)
        fila["ruido_20"] = _evaluar_inyecciones(
            funcion, datos, inyecciones, _mascara_inyecciones(datos, inyecciones), con_ruido=True
        )
        resultados[nombre] = fila

    return {"fuente": fuente, "filas": resultados, "episodios": ventanas}


def imprimir_tabla(resultados: dict) -> None:
    print(f"\nFuente: {resultados['fuente']}")
    print(
        "| Modelo | Episodios del kit | Falsas/día | +10 % | +20 % | Rampa | "
        "Ruido +20 % (falsas/día) | Tiempo |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for nombre, f in resultados["filas"].items():
        ruido = f["ruido_20"]
        print(
            f"| {nombre} | {f['episodios_detectados']}/{f['episodios_totales']} | "
            f"{f['falsas_por_dia']:.2f} | "
            f"{f['energia_10']['detectados']}/{f['energia_10']['total']} | "
            f"{f['energia_20']['detectados']}/{f['energia_20']['total']} | "
            f"{f['rampa']['detectados']}/{f['rampa']['total']} | "
            f"{ruido['detectados']}/{ruido['total']} ({ruido['falsas_por_dia']:.2f}) | "
            f"{f['ms']:.0f} ms |"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Comparación justa de 6 detectores.")
    parser.add_argument("--kit", type=Path, default=None, help="CSV crudo del kit (opcional)")
    parser.add_argument(
        "--salida", type=Path, default=RAIZ / "data/resultados/experimento_modelos.json"
    )
    parser.add_argument("--repeticiones", type=int, default=5, help="corridas para medir tiempo")
    args = parser.parse_args()

    datos, fuente = cargar_entrada(args.kit)
    print(f"Datos: {fuente}")
    print(f"{len(datos)} filas · sitios {sorted(datos['site_id'].unique())}")
    if fuente.startswith("réplica"):
        print("AVISO: resultados de la réplica sintética, NO del kit real.")

    resultados = ejecutar(datos, fuente, max(1, args.repeticiones))
    imprimir_tabla(resultados)

    # Solo se guardan agregados, nunca filas del kit.
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"Agregados → {args.salida}")


if __name__ == "__main__":
    main()
