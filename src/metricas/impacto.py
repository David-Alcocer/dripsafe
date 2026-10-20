"""Métricas reproducibles de impacto sobre tablas; datos del kit simulados.

``kw_ti`` y ``kw_total`` conservan los nombres del contrato. En el kit horario
son kWh por intervalo; en sintéticos pueden ser kW promedio. El modo se
declara para evitar una conversión implícita. El agua es captación in situ.
"""

import math
from typing import Literal

import numpy as np
import pandas as pd

UnidadEnergia = Literal["kwh_intervalo", "kw_promedio"]


def _horas_validas(horas_por_intervalo: float) -> None:
    if not math.isfinite(horas_por_intervalo) or horas_por_intervalo <= 0:
        raise ValueError("horas_por_intervalo debe ser positivo y finito")


def _factor_energia(unidad_energia: UnidadEnergia, horas_por_intervalo: float) -> float:
    _horas_validas(horas_por_intervalo)
    if unidad_energia == "kwh_intervalo":
        return 1.0
    if unidad_energia == "kw_promedio":
        return horas_por_intervalo
    raise ValueError("unidad_energia debe ser kwh_intervalo o kw_promedio")


def _numeros(df: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    faltantes = set(columnas) - set(df.columns)
    if faltantes:
        raise ValueError(f"faltan columnas: {sorted(faltantes)}")
    valores = df[columnas].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(valores.to_numpy(dtype=float)).all():
        raise ValueError(f"hay valores ausentes o no finitos en {columnas}")
    return valores


def _claves(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df:
        raise ValueError("falta timestamp")
    tabla = df.copy()
    if "site_id" not in tabla:
        tabla["site_id"] = "sitio_unico"
    if tabla["site_id"].isna().any():
        raise ValueError("site_id contiene valores ausentes")
    tabla["timestamp"] = pd.to_datetime(tabla["timestamp"], utc=True, errors="coerce")
    if tabla["timestamp"].isna().any():
        raise ValueError("hay timestamps inválidos")
    if tabla.duplicated(["site_id", "timestamp"]).any():
        raise ValueError("hay claves duplicadas por sitio y hora")
    return tabla


def pue_wue_por_sitio(
    telemetria: pd.DataFrame, *, particion: str,
    unidad_energia: UnidadEnergia, horas_por_intervalo: float,
) -> pd.DataFrame:
    """Cocientes de sumas por sitio y partición; WUE es captación in situ/IT.

    El fin del periodo es la marca del último intervalo observado (inclusivo).
    Sin medidor de agua, WUE queda ausente; sin energía TI, el ratio no existe.
    """
    factor = _factor_energia(unidad_energia, horas_por_intervalo)
    if "etiqueta_particion" not in telemetria:
        raise ValueError("falta etiqueta_particion")
    if not isinstance(particion, str) or not particion:
        raise ValueError("particion debe ser una etiqueta no vacía")
    tabla = _claves(telemetria)
    tabla = tabla.loc[tabla["etiqueta_particion"] == particion].copy()
    if tabla.empty:
        raise ValueError(f"no hay filas en la partición {particion}")

    columnas = ["kw_ti", "kw_total"]
    if "agua_reposicion_l" in tabla:
        columnas.append("agua_reposicion_l")
    valores = _numeros(tabla, columnas)
    if (valores < 0).any().any():
        raise ValueError("energía y agua deben ser no negativas")
    if (valores["kw_total"] < valores["kw_ti"]).any():
        raise ValueError("kw_total no puede ser menor que kw_ti")
    tabla[columnas] = valores

    filas = []
    for sitio, grupo in tabla.groupby("site_id", sort=True):
        energia_it = float(grupo["kw_ti"].sum() * factor)
        if energia_it <= 0:
            raise ValueError(f"energía de TI nula en {sitio}")
        energia_total = float(grupo["kw_total"].sum() * factor)
        agua = float(grupo["agua_reposicion_l"].sum()) if "agua_reposicion_l" in grupo else None
        filas.append({
            "site_id": sitio,
            "particion": particion,
            "periodo_inicio": grupo["timestamp"].min(),
            "periodo_fin": grupo["timestamp"].max(),
            "n_intervalos": len(grupo),
            "unidad_energia_entrada": unidad_energia,
            "energia_it_kwh": energia_it,
            "energia_total_kwh": energia_total,
            "agua_in_situ_l": agua,
            "pue": energia_total / energia_it,
            "wue_in_situ_l_kwh": agua / energia_it if agua is not None else None,
        })
    return pd.DataFrame(filas)


def exceso_no_ti(
    telemetria: pd.DataFrame, alertas: pd.DataFrame, *,
    columna_esperado: str, unidad_energia: UnidadEnergia,
    horas_por_intervalo: float, columna_esperado_agua: str | None = None,
) -> pd.DataFrame:
    """Residuos de todas las horas de evaluación, con o sin alerta.

    La predicción de energía representa consumo *no TI* esperado de la misma
    hora y unidad de la entrada. Las banderas indican coincidencia con una
    alerta, no causalidad, corrección ni ahorro observado.
    """
    factor = _factor_energia(unidad_energia, horas_por_intervalo)
    if "etiqueta_particion" not in telemetria:
        raise ValueError("falta etiqueta_particion")
    if ("site_id" in telemetria) != ("site_id" in alertas):
        raise ValueError("telemetría y alertas deben incluir site_id juntas")
    if columna_esperado_agua is not None and columna_esperado_agua == columna_esperado:
        raise ValueError("las columnas esperadas de energía y agua deben ser distintas")
    datos = _claves(telemetria)
    avisos = _claves(alertas)
    datos = datos.loc[datos["etiqueta_particion"] == "evaluacion"].copy()
    if datos.empty:
        raise ValueError("no hay horas de evaluación")
    if "anomalia" not in avisos:
        raise ValueError("faltan banderas anomalia válidas")

    datos_numericos = ["kw_ti", "kw_total"]
    esperados_numericos = [columna_esperado]
    if columna_esperado_agua is not None:
        datos_numericos.append("agua_reposicion_l")
        esperados_numericos.append(columna_esperado_agua)
    datos[datos_numericos] = _numeros(datos, datos_numericos)
    avisos[esperados_numericos] = _numeros(avisos, esperados_numericos)
    if (datos[datos_numericos] < 0).any().any() or (avisos[esperados_numericos] < 0).any().any():
        raise ValueError("energía o agua real/esperada debe ser no negativa")
    if (datos["kw_total"] < datos["kw_ti"]).any():
        raise ValueError("kw_total no puede ser menor que kw_ti")

    claves = ["site_id", "timestamp"]
    columnas_datos = claves + datos_numericos
    if "ot_event" in datos:
        if datos["ot_event"].isna().any():
            raise ValueError("ot_event contiene valores ausentes")
        columnas_datos.append("ot_event")
    tabla = datos[columnas_datos].merge(
        avisos[claves + ["anomalia"] + esperados_numericos],
        on=claves, how="left", validate="one_to_one", indicator=True,
    )
    if (tabla["_merge"] != "both").any():
        raise ValueError("faltan alertas o predicciones para alguna hora de evaluación")
    if not tabla["anomalia"].map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("anomalia debe contener solo booleanos")

    residuo_energia = ((tabla["kw_total"] - tabla["kw_ti"])
                       - tabla[columna_esperado]) * factor
    salida = tabla[claves].copy()
    salida["coincide_alerta"] = tabla["anomalia"].astype(bool)
    salida["coincide_evento_ot"] = (
        tabla["ot_event"].ne("normal") if "ot_event" in tabla
        else pd.Series(False, index=tabla.index)
    )
    salida["residuo_no_ti_kwh"] = residuo_energia
    salida["exceso_no_ti_estimado_kwh"] = residuo_energia.clip(lower=0)
    salida["exceso_no_ti_con_alerta_kwh"] = salida["exceso_no_ti_estimado_kwh"].where(
        salida["coincide_alerta"], 0.0,
    )
    salida["exceso_no_ti_sin_alerta_kwh"] = salida["exceso_no_ti_estimado_kwh"].where(
        ~salida["coincide_alerta"], 0.0,
    )
    if columna_esperado_agua is not None:
        residuo_agua = tabla["agua_reposicion_l"] - tabla[columna_esperado_agua]
        salida["residuo_agua_in_situ_l"] = residuo_agua
        salida["exceso_agua_in_situ_estimado_l"] = residuo_agua.clip(lower=0)
        salida["exceso_agua_con_alerta_l"] = salida["exceso_agua_in_situ_estimado_l"].where(
            salida["coincide_alerta"], 0.0,
        )
        salida["exceso_agua_sin_alerta_l"] = salida["exceso_agua_in_situ_estimado_l"].where(
            ~salida["coincide_alerta"], 0.0,
        )
    return salida
