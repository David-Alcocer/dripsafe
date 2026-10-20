"""Evaluación por episodio y por sitio conforme a la decisión D17.

Las ventanas verdaderas se suministran explícitamente o se derivan de las
etiquetas para el caso original del kit. Una alerta dentro de la ventana es
un TP; las alertas consecutivas fuera de ventanas forman un solo FP.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2

from src.metricas.impacto import _horas_validas


def _sitios_y_horas(df: pd.DataFrame, *, exigir_sitio: bool) -> pd.DataFrame:
    if "timestamp" not in df:
        raise ValueError("falta timestamp")
    if exigir_sitio and "site_id" not in df:
        raise ValueError("falta site_id para evaluar varios sitios")
    salida = df.copy()
    if "site_id" not in salida:
        salida["site_id"] = "sitio_unico"
    if salida["site_id"].isna().any():
        raise ValueError("site_id contiene valores ausentes")
    salida["timestamp"] = pd.to_datetime(salida["timestamp"], utc=True, errors="coerce")
    if salida["timestamp"].isna().any():
        raise ValueError("hay timestamps inválidos")
    if salida.duplicated(["site_id", "timestamp"]).any():
        raise ValueError("hay claves duplicadas por sitio y hora")
    return salida.sort_values(["site_id", "timestamp"]).reset_index(drop=True)


def episodios_desde_etiquetas(telemetria: pd.DataFrame, *,
                              horas_por_intervalo: float) -> pd.DataFrame:
    """Agrupa filas anómalas contiguas del kit sin unir sitios diferentes.

    Dos escenarios con nombre distinto son episodios distintos aunque sean
    contiguos. Una interrupción temporal también abre otro episodio.
    """
    _horas_validas(horas_por_intervalo)
    if "etiqueta_escenario" not in telemetria:
        raise ValueError("falta etiqueta_escenario")
    if "etiqueta_particion" not in telemetria:
        raise ValueError("falta etiqueta_particion")
    df = _sitios_y_horas(telemetria, exigir_sitio=False)
    df = df[df["etiqueta_particion"] == "evaluacion"]
    salto = pd.Timedelta(hours=horas_por_intervalo)
    episodios = []
    for sitio, grupo in df.groupby("site_id", sort=False):
        actual = None
        anterior = None
        for fila in grupo.itertuples(index=False):
            nombre = fila.etiqueta_escenario
            nombre = "" if pd.isna(nombre) else str(nombre)
            if not nombre or nombre == "base":
                actual = None
                anterior = fila.timestamp
                continue
            if actual is None or actual["nombre"] != nombre or fila.timestamp - anterior != salto:
                actual = {"site_id": sitio, "inicio": fila.timestamp, "fin": fila.timestamp,
                          "origen": "kit", "nombre": nombre}
                episodios.append(actual)
            else:
                actual["fin"] = fila.timestamp
            anterior = fila.timestamp
    return pd.DataFrame(episodios, columns=["site_id", "inicio", "fin", "origen", "nombre"])


def _ventanas(episodios: pd.DataFrame, *, varios_sitios: bool) -> pd.DataFrame:
    requeridas = {"inicio", "fin"}
    if not requeridas <= set(episodios):
        raise ValueError(f"faltan columnas de episodio: {sorted(requeridas - set(episodios))}")
    ventanas = episodios.copy()
    if varios_sitios and "site_id" not in ventanas:
        raise ValueError("cada episodio necesita site_id")
    if "site_id" not in ventanas:
        ventanas["site_id"] = "sitio_unico"
    if "origen" not in ventanas:
        ventanas["origen"] = "sin_especificar"
    for col in ("inicio", "fin"):
        ventanas[col] = pd.to_datetime(ventanas[col], utc=True, errors="coerce")
    if ventanas[["inicio", "fin", "site_id"]].isna().any().any():
        raise ValueError("episodio con sitio o fecha inválidos")
    if (ventanas["fin"] < ventanas["inicio"]).any():
        raise ValueError("episodio con fin anterior al inicio")

    # D17: las ventanas que se solapan cuentan una sola vez. La inyección
    # prevalece sobre un episodio original del kit si coinciden.
    unidas = []
    for sitio, grupo in ventanas.sort_values(["site_id", "inicio", "fin"]).groupby("site_id"):
        for fila in grupo.itertuples(index=False):
            if unidas and unidas[-1]["site_id"] == sitio and fila.inicio <= unidas[-1]["fin"]:
                ultima = unidas[-1]
                ultima["fin"] = max(ultima["fin"], fila.fin)
                if fila.origen == "inyeccion":
                    ultima["origen"] = "inyeccion"
            else:
                unidas.append({"site_id": sitio, "inicio": fila.inicio,
                               "fin": fila.fin, "origen": fila.origen})
    return pd.DataFrame(unidas, columns=["site_id", "inicio", "fin", "origen"])


def evaluar_episodios(telemetria: pd.DataFrame, alertas: pd.DataFrame,
                      episodios: pd.DataFrame, *, horas_por_intervalo: float,
                      confianza: float = 0.95) -> tuple[pd.DataFrame, dict]:
    """Cuenta TP/FN por ventana y FP por tramo de alertas en horas limpias.

    La telemetría puede incluir referencia, pero solo se puntúa evaluación.
    El IC exacto Poisson de FP/día supone episodios de falsa alarma
    independientes; con pocos días debe interpretarse con cautela.
    """
    _horas_validas(horas_por_intervalo)
    if not 0 < confianza < 1:
        raise ValueError("confianza debe estar entre 0 y 1")
    if "etiqueta_particion" not in telemetria:
        raise ValueError("falta etiqueta_particion")
    varios_sitios = "site_id" in telemetria
    datos = _sitios_y_horas(telemetria, exigir_sitio=False)
    avisos = _sitios_y_horas(alertas, exigir_sitio=varios_sitios)
    if "anomalia" not in avisos or avisos["anomalia"].isna().any():
        raise ValueError("faltan banderas anomalia válidas")
    if not avisos["anomalia"].map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("anomalia debe ser booleana")
    datos = datos[datos["etiqueta_particion"] == "evaluacion"].copy()
    if datos.empty:
        raise ValueError("no hay horas de evaluación")
    salto = pd.Timedelta(hours=horas_por_intervalo)
    for sitio, grupo in datos.groupby("site_id"):
        if not grupo["timestamp"].diff().iloc[1:].eq(salto).all():
            raise ValueError(f"horas incompletas en evaluación: {sitio}")
    datos = datos.merge(avisos[["site_id", "timestamp", "anomalia"]],
                        on=["site_id", "timestamp"], how="left", validate="one_to_one")
    if datos["anomalia"].isna().any():
        raise ValueError("faltan alertas en horas de evaluación")

    ventanas = _ventanas(episodios, varios_sitios=varios_sitios)
    desconocidos = set(ventanas["site_id"]) - set(datos["site_id"])
    if desconocidos:
        raise ValueError(f"episodios de sitios ausentes: {sorted(desconocidos)}")
    limpio = pd.Series(True, index=datos.index)
    filas = []
    for ep in ventanas.itertuples(index=False):
        mascara = ((datos["site_id"] == ep.site_id) &
                   datos["timestamp"].between(ep.inicio, ep.fin))
        horas_observadas = datos.loc[mascara, "timestamp"]
        horas_esperadas = pd.date_range(ep.inicio, ep.fin, freq=salto)
        if (horas_esperadas.empty or horas_esperadas[-1] != ep.fin or
                not horas_observadas.reset_index(drop=True).equals(pd.Series(horas_esperadas))):
            raise ValueError(f"episodio con horas incompletas: {ep.site_id} {ep.inicio}")
        limpio &= ~mascara
        marcas = datos.loc[mascara & datos["anomalia"], "timestamp"]
        filas.append({"site_id": ep.site_id, "inicio": ep.inicio, "fin": ep.fin,
                      "origen": ep.origen, "detectado": not marcas.empty,
                      "horas_hasta_detectar": ((marcas.iloc[0] - ep.inicio).total_seconds() / 3600
                                               if not marcas.empty else None)})

    # Un FP es un tramo continuo de horas limpias alertadas en un mismo sitio.
    falsas = datos[limpio & datos["anomalia"]].sort_values(["site_id", "timestamp"])
    fp = 0
    for _, grupo in falsas.groupby("site_id"):
        fp += int((grupo["timestamp"].diff().ne(salto)).sum())
    tp = sum(fila["detectado"] for fila in filas)
    fn = len(filas) - tp
    dias_limpios = float(limpio.sum() * horas_por_intervalo / 24)
    tasa = fp / dias_limpios if dias_limpios else None
    alpha = 1 - confianza
    ic = (None, None)
    if dias_limpios:
        inferior = 0.5 * chi2.ppf(alpha / 2, 2 * fp) / dias_limpios if fp else 0.0
        superior = 0.5 * chi2.ppf(1 - alpha / 2, 2 * (fp + 1)) / dias_limpios
        ic = (inferior, superior)
    resumen = {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "horas_evaluacion_sitio": len(datos) * horas_por_intervalo,
        "horas_limpias_sitio": limpio.sum() * horas_por_intervalo,
        "dias_limpios_sitio": dias_limpios,
        "falsas_alarmas_por_dia_sitio": tasa,
        "ic_falsas_alarmas_por_dia_sitio": ic,
    }
    return pd.DataFrame(filas, columns=["site_id", "inicio", "fin", "origen",
                                        "detectado", "horas_hasta_detectar"]), resumen
