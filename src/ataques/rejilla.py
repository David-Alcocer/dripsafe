"""Rejilla fija de inyecciones sobre el formato del kit (propuesta v7 §4 · U1 · #30).

Toma la telemetría del contrato v2 (varios sitios, una fila por sitio y hora) y
crea COPIAS con UNA inyección cada una, siempre dentro de `evaluacion`. Las
horas de ajuste y calibración no se tocan, así que el detector aprende lo mismo
en todas las copias (detector congelado, G2). La rejilla está escrita en
docs/06 §5 desde antes de correrla sobre el kit; cambiarla después de ver
resultados sería hacer trampa.

Qué se inyecta (REJILLA):
- Energía no TI +10, +20, +40 y +80 % durante 4 h, sin evento OT.
- Agua +25 y +50 % durante 4 h, sin evento OT.
- Cambio sin registro: energía no TI +20 % durante 12 h, sin evento OT. Debe
  caer en «escalón sin registro», nunca en mantenimiento directo.
- Cambio con efecto: un `cambio_config_no_autorizado` y, 8 h después,
  energía no TI +20 % durante 12 h. Debe caer en «incidente OT con efecto».

Dónde: en cada sitio, a 6, 18, 30, 42, 54 y 66 h del inicio de la evaluación
(INICIOS_H), para cubrir noche, mañana y tarde. Si ahí estorba una anomalía
original del kit o un evento OT del kit en las 24 h previas, se recorre hora
por hora hasta encontrar lugar limpio y se anota cuánto se recorrió. Un lugar
ya usado por la misma inyección en el mismo sitio no se repite.

Nada de esto toca sistemas reales: solo cambia números en copias de un
DataFrame (regla 18 de la convocatoria). Las respuestas correctas van en las
columnas `etiqueta_*`, que el detector nunca lee.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src import contrato

INICIOS_H = (6, 18, 30, 42, 54, 66)
MARGEN_H = 2           # horas limpias antes y después de la inyección
SIN_OT_PREVIO_H = 24   # sin eventos OT del kit en las 24 h previas (no confundir la clase)

# Robustez (prueba c): el kit trae ruido uniforme de ±1.5 % de la energía TI sobre la
# energía total (desviación de 0.87 %). Sumar ruido gaussiano de 1.5 % la duplica.
# El agua del kit no trae ruido; se le pone ±4 % uniforme.
RUIDO_ENERGIA_PCT_TI = 1.5
RUIDO_AGUA_PCT = 4.0


@dataclass(frozen=True)
class Inyeccion:
    nombre: str
    grupo: str              # energia, agua, cambio_sin_registro, cambio_con_efecto
    variable: str           # energia (no TI) o agua
    magnitud_pct: float
    horas: int              # duración del exceso
    tipo: str               # etiqueta_tipo: falla o ataque
    tecnica: str            # ATT&CK for ICS, o "" si no aplica
    clase_esperada: str     # lo que debería decir src/ot/clases.py
    evento_ot: str = ""     # si no está vacío, se escribe en la primera hora
    retraso_h: int = 0      # horas entre el evento OT y el inicio del exceso

    @property
    def largo_h(self) -> int:
        return self.retraso_h + self.horas


REJILLA = [
    *[Inyeccion(f"energia_+{m}", "energia", "energia", m, 4, "falla", "", "escalon_sin_registro")
      for m in (10, 20, 40, 80)],
    *[Inyeccion(f"agua_+{m}", "agua", "agua", m, 4, "falla", "", "escalon_sin_registro")
      for m in (25, 50)],
    Inyeccion("cambio_sin_registro", "cambio_sin_registro", "energia", 20, 12, "ataque", "T0836",
              "escalon_sin_registro"),
    Inyeccion("cambio_con_efecto", "cambio_con_efecto", "energia", 20, 12, "ataque", "T0836",
              "incidente_ot", evento_ot="cambio_config_no_autorizado", retraso_h=8),
]
POR_NOMBRE = {i.nombre: i for i in REJILLA}

_COLUMNAS = {"energia": "kw_total", "agua": "agua_reposicion_l"}


def _preparar(telemetria: pd.DataFrame) -> pd.DataFrame:
    """Copia ordenada por sitio y hora, con las etiquetas que hagan falta."""
    problemas = contrato.validar(telemetria)
    if problemas:
        raise ValueError("La telemetría no cumple el contrato: " + "; ".join(problemas))
    faltan = [c for c in ["site_id", "ot_event", "etiqueta_particion", "agua_reposicion_l"]
              if c not in telemetria]
    if faltan:
        raise ValueError(f"La rejilla necesita el formato del kit (contrato v2); faltan {faltan}")
    df = telemetria.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ["etiqueta_escenario", "etiqueta_tecnica"]:
        if col not in df:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    if "etiqueta_tipo" not in df:
        df["etiqueta_tipo"] = "normal"
    df["etiqueta_tipo"] = df["etiqueta_tipo"].fillna("normal")
    df["ot_event"] = df["ot_event"].fillna("normal").astype(str)
    for col in ["kw_ti", "kw_total", "agua_reposicion_l"]:
        df[col] = df[col].astype(float)
    return df.sort_values(["site_id", "timestamp"], kind="stable").reset_index(drop=True)


def con_ruido(telemetria: pd.DataFrame, semilla: int,
              energia_pct_ti: float = RUIDO_ENERGIA_PCT_TI,
              agua_pct: float = RUIDO_AGUA_PCT) -> pd.DataFrame:
    """Prueba de robustez (c): más ruido en TODAS las horas, como sensores peores.

    Se aplica a ajuste, calibración y evaluación por igual. La energía total
    nunca queda por debajo de la de TI ni el agua por debajo de cero.
    """
    df = _preparar(telemetria)
    rng = np.random.default_rng(semilla)
    no_ti = df["kw_total"] - df["kw_ti"]
    ruido = rng.normal(0.0, energia_pct_ti / 100.0, len(df)) * df["kw_ti"]
    df["kw_total"] = df["kw_ti"] + (no_ti + ruido).clip(lower=0.0)
    df["agua_reposicion_l"] = (df["agua_reposicion_l"]
                               * (1 + rng.uniform(-agua_pct, agua_pct, len(df)) / 100.0)).clip(lower=0.0)
    return df


def _lugar_limpio(s: pd.DataFrame, inyeccion: Inyeccion, desfase_h: int,
                  usados: set[int] = frozenset()) -> tuple[int, int] | None:
    """Posición de inicio en el sitio `s` y cuántas horas se recorrió; None si no cabe."""
    evaluacion = np.flatnonzero((s["etiqueta_particion"] == "evaluacion").to_numpy())
    if len(evaluacion) == 0:
        return None
    escenario = (s["etiqueta_escenario"] != "").to_numpy()
    ot_kit = (s["ot_event"] != "normal").to_numpy()
    primera, ultima = int(evaluacion[0]), int(evaluacion[-1])
    deseado = primera + desfase_h
    for p in range(deseado, ultima - inyeccion.largo_h + 2):
        if p in usados:
            continue
        fin = p + inyeccion.largo_h          # exclusivo
        if escenario[max(0, p - MARGEN_H):min(len(s), fin + MARGEN_H)].any():
            continue
        if ot_kit[max(0, p - SIN_OT_PREVIO_H):fin].any():
            continue
        if (s["etiqueta_particion"].iloc[p:fin] != "evaluacion").any():
            continue
        return p, p - deseado
    return None


def aplicar(telemetria: pd.DataFrame, inyeccion: Inyeccion, sitio: str,
            inicio: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Copia de `telemetria` con una inyección que empieza en `inicio` (hora del evento OT,
    o del exceso si no hay evento). Regresa (copia, ficha)."""
    df = _preparar(telemetria)
    horas_intervalo = contrato.intervalo_horas(df[df["site_id"] == sitio])
    paso = pd.Timedelta(hours=horas_intervalo)
    inicio = pd.Timestamp(inicio)
    inicio_efecto = inicio + inyeccion.retraso_h * pd.Timedelta(hours=1)
    fin_efecto = inicio_efecto + inyeccion.horas * pd.Timedelta(hours=1)   # exclusivo

    del_sitio = df["site_id"] == sitio
    efecto = del_sitio & (df["timestamp"] >= inicio_efecto) & (df["timestamp"] < fin_efecto)
    episodio = del_sitio & (df["timestamp"] >= inicio) & (df["timestamp"] < fin_efecto)
    if int(efecto.sum()) != round(inyeccion.horas / horas_intervalo):
        raise ValueError(f"La inyección {inyeccion.nombre} no cabe completa en {sitio} desde {inicio}")
    if (df.loc[episodio, "etiqueta_particion"] != "evaluacion").any():
        raise ValueError("Solo se inyecta en evaluación: ajuste y calibración no se tocan")

    factor = inyeccion.magnitud_pct / 100.0
    if inyeccion.variable == "energia":
        delta = (df.loc[efecto, "kw_total"] - df.loc[efecto, "kw_ti"]) * factor
        df.loc[efecto, "kw_total"] += delta
    else:
        delta = df.loc[efecto, "agua_reposicion_l"] * factor
        df.loc[efecto, "agua_reposicion_l"] += delta
    if inyeccion.evento_ot:
        df.loc[del_sitio & (df["timestamp"] == inicio), "ot_event"] = inyeccion.evento_ot

    df.loc[episodio, "etiqueta_escenario"] = inyeccion.nombre
    df.loc[episodio, "etiqueta_tipo"] = inyeccion.tipo
    df.loc[episodio, "etiqueta_tecnica"] = inyeccion.tecnica

    horas_episodio = df.loc[episodio, "timestamp"]
    ficha = {
        **asdict(inyeccion),
        "site_id": sitio,
        "inicio": horas_episodio.min(),
        "fin": horas_episodio.max(),           # última hora (incluida), como en D17
        "inicio_efecto": inicio_efecto,
        "energia_inyectada_kwh": float(delta.sum() * horas_intervalo) if inyeccion.variable == "energia" else 0.0,
        "agua_inyectada_l": float(delta.sum()) if inyeccion.variable == "agua" else 0.0,
        "_delta_por_hora": pd.Series(delta.to_numpy() * (horas_intervalo if inyeccion.variable == "energia" else 1.0),
                                     index=df.loc[efecto, "timestamp"].to_numpy()),
        "_paso": paso,
    }
    return df, ficha


def generar(telemetria: pd.DataFrame, rejilla=REJILLA, inicios_h=INICIOS_H):
    """Recorre la rejilla completa. Produce (copia, ficha) por inyección, más las omitidas.

    Uso: `for copia, ficha in generar(df): ...`. Las omitidas (no hubo lugar limpio)
    salen con `copia=None` y `ficha["omitida"]` con el motivo.
    """
    df = _preparar(telemetria)
    for sitio, s in df.groupby("site_id", sort=True):
        s = s.reset_index(drop=True)
        for inyeccion in rejilla:
            usados: set[int] = set()
            for desfase in inicios_h:
                lugar = _lugar_limpio(s, inyeccion, desfase, usados)
                base = {**asdict(inyeccion), "site_id": sitio, "desfase_h": desfase}
                if lugar is None:
                    yield None, {**base, "omitida": "no hay un lugar limpio en la evaluación"}
                    continue
                p, recorrido = lugar
                usados.add(p)
                copia, ficha = aplicar(df, inyeccion, sitio, s["timestamp"].iloc[p])
                yield copia, {**ficha, "desfase_h": desfase, "recorrido_h": recorrido}


def ficha_publica(ficha: dict) -> dict:
    """La ficha sin los campos internos y con fechas en texto, lista para el manifiesto."""
    salida = {}
    for clave, valor in ficha.items():
        if clave.startswith("_"):
            continue
        salida[clave] = str(valor) if isinstance(valor, pd.Timestamp) else valor
    return salida
