"""Cálculos del dashboard sobre los datos del kit. Sin Streamlit, para poder probarlos.

Regla del kit (docs/METRICS.md): PUE y WUE siempre con SUMAS del periodo y del mismo
perímetro, nunca promediando los cocientes de cada hora. Sin filas, el resultado es None.

Las cifras OFICIALES salen de resultados/numeros_oficiales.json (Nico). Lo que se calcula
aquí es lo que el dashboard necesita para filtrar por sitio y periodo, y la vista previa
mientras llegan las cifras oficiales.
"""

import pandas as pd

from app.textos import EVENTOS_OT_TEXTO, ORDEN_CLASES

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Cómo se agrega cada variable por hora: 'suma', 'media' o un cociente (numerador, denominador).
VARIABLES = {
    "pue": ("energy_total_kwh", "energy_it_kwh"),
    "wue": ("water_l", "energy_it_kwh"),
    "energy_total_kwh": "suma",
    "energy_it_kwh": "suma",
    "energia_no_ti_kwh": "suma",
    "esperado_energia_no_ti_kwh": "suma",
    "water_l": "suma",
    "esperado_agua_l": "suma",
    "inlet_temp_c": "media",
    "esperado_entrada_c": "media",
    "outdoor_temp_c": "media",
    "load_pct": "media",
}


# ------------------------------------------------------------ indicadores

def metricas(df: pd.DataFrame) -> dict:
    """PUE, WUE y totales de un conjunto de filas (con sumas)."""
    it = float(df["energy_it_kwh"].sum())
    total = float(df["energy_total_kwh"].sum())
    agua = float(df["water_l"].sum())
    return {
        "pue": total / it if it > 0 else None,
        "wue": agua / it if it > 0 else None,
        "energia_it_kwh": it, "energia_total_kwh": total, "agua_l": agua, "filas": len(df),
    }


def por_sitio(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sitio con su tipo de enfriamiento, PUE, WUE y totales."""
    filas = [{"sitio": s, "enfriamiento": g["cooling_type"].iloc[0], **metricas(g)} for s, g in df.groupby("site_id")]
    return pd.DataFrame(filas)


def serie_horaria(df: pd.DataFrame, variable: str, separar_sitios: bool = True) -> pd.DataFrame:
    """Tabla hora × sitio (o una sola columna «Todos») de una variable."""
    regla = VARIABLES[variable]
    claves = ["timestamp", "site_id"] if separar_sitios else ["timestamp"]
    if isinstance(regla, tuple):
        num, den = regla
        g = df.groupby(claves)[[num, den]].sum()
        s = g[num] / g[den]
    else:
        s = df.groupby(claves)[variable].agg("sum" if regla == "suma" else "mean")
    return s.unstack("site_id") if separar_sitios else s.to_frame("Todos")


def referencia(df: pd.DataFrame) -> pd.DataFrame:
    """PUE y WUE de cada sitio en las horas de referencia (sin anomalías)."""
    ref = df[df["split"] == "referencia"]
    return por_sitio(ref).set_index("sitio")[["pue", "wue"]]


# ------------------------------------------------------------ alertas y eventos

def _clase_principal(clases: pd.Series) -> str:
    """La clase más grave de un evento (orden de textos.CLASES)."""
    presentes = set(clases) - {"normal"}
    return next((c for c in ORDEN_CLASES if c in presentes), "normal")


def eventos(df: pd.DataFrame) -> pd.DataFrame:
    """Junta las horas con alerta de cada sitio en eventos (horas seguidas), con su clase más grave."""
    columnas = ["sitio", "inicio", "fin", "horas", "clase", "clases", "motivo", "escenario", "ot_event",
                "exceso_kwh", "exceso_l", "confianza_baja"]
    filas = []
    for sitio, g in df[df["alerta"]].sort_values("timestamp").groupby("site_id"):
        # Un evento nuevo empieza cuando hay más de una hora desde la alerta anterior.
        grupo = (g["timestamp"].diff() > pd.Timedelta(hours=1)).cumsum()
        for _, v in g.groupby(grupo):
            # El motivo del evento es el de su peor hora (la de mayor exceso), no la lista de todas.
            con_motivo = v[v["motivo"] != ""]
            pico = con_motivo.loc[(con_motivo["exceso_kwh"] + con_motivo["exceso_l"]).idxmax()] if len(con_motivo) else None
            # Los eventos OT en el orden en que ocurrieron: «Login fallido → Cambio de configuración…».
            ot = list(dict.fromkeys(EVENTOS_OT_TEXTO[x] for x in v["ot_event"] if x in EVENTOS_OT_TEXTO))
            filas.append({
                "sitio": sitio,
                "inicio": v["timestamp"].iloc[0],
                "fin": v["timestamp"].iloc[-1] + pd.Timedelta(hours=1),
                "horas": len(v),
                "clase": _clase_principal(v["clase"]),
                "clases": sorted(set(v["clase"]) - {"normal"}),
                "motivo": (f'pico: {pico["motivo"]}' if pico is not None else " → ".join(ot)),
                "escenario": v["scenario"].mode().iloc[0],
                "ot_event": " → ".join(ot),
                "exceso_kwh": float(v["exceso_kwh"].sum()),
                "exceso_l": float(v["exceso_l"].sum()),
                "confianza_baja": bool(v["clima_no_visto"].any()),
            })
    orden = {c: i for i, c in enumerate(ORDEN_CLASES)}
    salida = pd.DataFrame(filas, columns=columnas)
    return salida.assign(_p=salida["clase"].map(orden)).sort_values(["_p", "inicio"], ignore_index=True).drop(columns="_p")


def evaluacion(df: pd.DataFrame, columna: str = "alerta") -> tuple[pd.DataFrame, dict]:
    """Compara una columna de alertas con la respuesta correcta del kit, SOLO en evaluación.

    `simulated_anomaly` y `scenario` nunca se usan para detectar; aquí solo para calificar.
    Cuenta por hora (como el ejemplo del kit) y por episodio (un escenario detectado si al
    menos una de sus horas tiene alerta).
    """
    ev = df[df["split"] == "evaluacion"]
    alerta = ev[columna].astype(bool)
    anomala = ev["simulated_anomaly"] == 1
    filas = []
    for (sitio, escenario), v in ev[anomala].groupby(["site_id", "scenario"]):
        marcadas = v[v[columna].astype(bool)]
        filas.append({
            "sitio": sitio, "escenario": escenario, "horas": len(v), "detectadas": len(marcadas),
            "detectado": len(marcadas) > 0,
            "horas_hasta_alerta": (marcadas["timestamp"].iloc[0] - v["timestamp"].iloc[0]).total_seconds() / 3600
            if len(marcadas) else None,
        })
    tp, fp, fn = int((alerta & anomala).sum()), int((alerta & ~anomala).sum()), int((~alerta & anomala).sum())
    dias = ev["timestamp"].nunique() / 24 if len(ev) else 0
    return pd.DataFrame(filas), {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "falsas_por_dia": fp / dias if dias else None,
        "escenarios_detectados": sum(f["detectado"] for f in filas),
        "escenarios_totales": len(filas),
    }


# ------------------------------------------------------------ exceso, balance y escenario

def exceso(df: pd.DataFrame) -> dict:
    """Exceso de energía y agua sobre lo esperado durante las alertas (ESTIMADO con la línea base).

    `pue_sin_exceso` es una cota: el PUE que habría quedado si cada exceso se hubiera cortado en
    el momento de su alerta. No es un ahorro observado.
    """
    m = metricas(df)
    kwh, litros = float(df["exceso_kwh"].sum()), float(df["exceso_l"].sum())
    horas = int((df["exceso_kwh"] > 0).sum())
    return {
        "kwh": kwh, "litros": litros, "horas_con_exceso": horas,
        "kwh_por_hora": kwh / horas if horas else None,
        "pue": m["pue"], "wue": m["wue"],
        "pue_sin_exceso": (m["energia_total_kwh"] - kwh) / m["energia_it_kwh"] if m["energia_it_kwh"] else None,
        "wue_sin_exceso": (m["agua_l"] - litros) / m["energia_it_kwh"] if m["energia_it_kwh"] else None,
    }


def consumo_detector(segundos_por_corrida: float, watts: float, g_co2e_por_kwh: float,
                     corridas_por_anio: int) -> dict:
    """Energía y CO₂ ESTIMADOS del detector con supuestos visibles (como tools/compare_detectors.py)."""
    kwh_corrida = watts * segundos_por_corrida / 3_600_000
    kwh_anio = kwh_corrida * corridas_por_anio
    return {"kwh_corrida": kwh_corrida, "kwh_anio": kwh_anio, "kg_co2e_anio": kwh_anio * g_co2e_por_kwh / 1000}


def equilibrio(kwh_detector_anio: float, kwh_exceso_por_hora: float | None) -> float | None:
    """Horas de exceso que DripSafe debe detectar al año para pagar su propia energía."""
    if not kwh_exceso_por_hora:
        return None
    return kwh_detector_anio / kwh_exceso_por_hora


def escenario_anual(fallas: int, exceso_pct: float, horas_sin: float, horas_con: float,
                    no_ti_kwh_hora: float, agua_l_hora: float = 0.0) -> dict:
    """Ahorro PROYECTADO de un escenario editable (no es un ahorro observado).

    Cada año ocurren `fallas` excesos de `exceso_pct` % sobre la energía no TI (y sobre el agua).
    Sin DripSafe duran `horas_sin` hasta que alguien los nota; con DripSafe, `horas_con`.
    """
    horas = max(0.0, horas_sin - horas_con) * fallas
    return {"horas_evitadas": horas, "kwh": horas * no_ti_kwh_hora * exceso_pct / 100,
            "litros": horas * agua_l_hora * exceso_pct / 100}


# ------------------------------------------------------------ formato

def fecha(ts, con_hora: bool = True) -> str:
    """Timestamp → '14 oct 23:00' (o '14 oct' sin hora). Las horas del kit están en UTC."""
    ts = pd.Timestamp(ts)
    texto = f"{ts.day:02d} {MESES[ts.month - 1]}"
    return f"{texto} {ts:%H:%M}" if con_hora else texto


def duracion(horas: float) -> str:
    return f"{horas * 60:.0f} min" if horas < 1 else f"{horas:.0f} h"


def ventana(df: pd.DataFrame, inicio, fin, margen_horas: float = 12) -> pd.DataFrame:
    """Filas entre `inicio` y `fin`, con un margen antes y después para ver el contraste."""
    margen = pd.Timedelta(hours=margen_horas)
    t = df["timestamp"]
    return df[(t >= pd.Timestamp(inicio) - margen) & (t <= pd.Timestamp(fin) + margen)]
