"""Pruebas exploratorias de un atacante más cuidadoso (fuera de la rejilla fijada).

NO son parte de la rejilla de docs/06 §5 ni de numeros_oficiales.json: se
escribieron el 21 de octubre, después de ver los resultados de la rejilla, para
responder con datos tres preguntas probables del jurado (docs/06 §6b):

1. ¿Qué tan pequeño tiene que ser un exceso para que DripSafe no lo vea?
   `piso()` lee los umbrales que calibró el detector congelado.
2. ¿Y si el atacante sube la energía poco a poco? `rampas()` sube la energía
   no TI desde 0 % un poco cada hora durante 36 h.
3. ¿Y si ataca en una ola de calor, fuera del clima que aprendió el detector?
   `calor()` sube la temperatura de 4 tardes por encima de lo aprendido (ahí el
   umbral se duplica) y agrega exactamente el consumo extra que la línea base
   espera por ese calor; encima va el ataque.

Igual que la rejilla: solo se tocan horas de evaluación de copias, el detector
aprende exactamente lo mismo en cada copia (se verifica) y solo salen agregados.

    python -m src.ataques.exploratorias --kit RUTA/operaciones_simuladas.csv
    python -m src.ataques.exploratorias --ejemplo     # sin el kit: datos inventados
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import contrato
from src.ataques import correr_rejilla, rejilla
from src.modelo import detector

PENDIENTES_PCT_H = (0.25, 0.5, 1.0)   # cuánto sube la energía no TI cada hora
RAMPA_H = 36
HORAS_TARDE = (12, 13, 14, 15)        # las horas más calientes del día simulado
CALOR_SOBRE_MAXIMO_C = 1.0            # grados por encima de lo más caliente que aprendió
ATAQUES_CALOR_PCT = (0, 10, 15, 20, 30)

_RAMPA = rejilla.Inyeccion("rampa", "rampa", "energia", 0, RAMPA_H, "ataque", "T0836", "escalon_sin_registro")


def _fisica(alertas: pd.DataFrame) -> np.ndarray:
    return (alertas["alerta_umbral"] | alertas["alerta_media_4h"]).to_numpy(dtype=bool)


def _detectar_igual(base_params: dict, copia: pd.DataFrame) -> pd.DataFrame:
    """Corre el detector en la copia, comprobando que aprendió lo mismo que en la base."""
    if not correr_rejilla._mismos_parametros(base_params, detector.entrenar(copia)):
        raise AssertionError("La prueba cambió lo que aprende el detector: tocó ajuste o calibración")
    return detector.detectar(copia).reset_index(drop=True)


def piso(params: dict) -> pd.DataFrame:
    """Umbral por hora y por media de 4 h de cada sitio y variable (en % o °C)."""
    filas = [{"site_id": sitio, "variable": var, "umbral_hora": round(p["limites"][var], 2),
              "umbral_media_4h": round(p["limites_media"][var], 2),
              "unidad": "°C" if var == "entrada" else "%"}
             for sitio, p in params.items() for var in ("energia", "agua", "entrada")]
    return pd.DataFrame(filas)


def rampas(base: pd.DataFrame, params: dict, pendientes=PENDIENTES_PCT_H,
           inicios_h=rejilla.INICIOS_H, largo_h: int = RAMPA_H) -> pd.DataFrame:
    """Una rampa por copia: la energía no TI sube `pendiente` % cada hora durante `largo_h` horas."""
    inyeccion = _RAMPA if largo_h == RAMPA_H else rejilla.Inyeccion(
        "rampa", "rampa", "energia", 0, largo_h, "ataque", "T0836", "escalon_sin_registro")
    paso_h = contrato.intervalo_horas(base[base["site_id"] == base["site_id"].iloc[0]])
    filas = []
    for pendiente in pendientes:
        for sitio in sorted(base["site_id"].unique()):
            s = base[base["site_id"] == sitio]
            usados: set[int] = set()
            for desfase in inicios_h:
                lugar = rejilla._lugar_limpio(s.reset_index(drop=True), inyeccion, desfase, usados)
                if lugar is None:
                    filas.append({"pendiente_pct_h": pendiente, "site_id": sitio, "desfase_h": desfase,
                                  "omitida": True})
                    continue
                p, _ = lugar
                usados.add(p)
                idx = s.index[p:p + largo_h]
                pct = pendiente * np.arange(1, len(idx) + 1)
                copia = base.copy()
                no_ti = (copia.loc[idx, "kw_total"] - copia.loc[idx, "kw_ti"]).to_numpy(dtype=float)
                delta = no_ti * pct / 100.0
                copia.loc[idx, "kw_total"] = copia.loc[idx, "kw_total"].to_numpy(dtype=float) + delta
                al = _detectar_igual(params, copia)
                vistas = np.flatnonzero(_fisica(al)[idx])
                fila = {"pendiente_pct_h": pendiente, "site_id": sitio, "desfase_h": desfase,
                        "omitida": False, "vista": len(vistas) > 0}
                if len(vistas):
                    k = int(vistas[0])
                    fila.update(horas_hasta_ver=k * paso_h, pct_al_ver=float(pct[k]),
                                kwh_antes_de_ver=float(delta[:k].sum() * paso_h),
                                clase_al_ver=al.loc[idx[k], "clase"])
                filas.append(fila)
    return pd.DataFrame(filas)


def calor(base: pd.DataFrame, params: dict, ataques_pct=ATAQUES_CALOR_PCT,
          horas_tarde=HORAS_TARDE) -> pd.DataFrame:
    """Ataques de energía en tardes con calor fuera de lo aprendido (umbral ×2).

    El calor se agrega «perfecto»: la energía, el agua y la temperatura de entrada suben
    exactamente lo que la línea base del detector espera por esos grados. Así se aísla el
    efecto del umbral duplicado. Con ataque 0 % mide si el calor solo genera falsas alarmas.
    """
    filas = []
    for sitio in sorted(base["site_id"].unique()):
        s = base[base["site_id"] == sitio]
        p = params[sitio]
        evaluacion = s[s["etiqueta_particion"] == "evaluacion"]
        for dia, g in evaluacion.groupby(evaluacion["timestamp"].dt.date):
            idx = g.index[g["timestamp"].dt.hour.isin(horas_tarde)]
            pos = [s.index.get_loc(i) for i in idx]
            if len(idx) != len(horas_tarde):
                continue
            # Mismo criterio que la rejilla: lejos de las anomalías y de los eventos OT del kit.
            lejos = s.iloc[max(0, pos[0] - rejilla.MARGEN_H):pos[-1] + 1 + rejilla.MARGEN_H]
            previo = s.iloc[max(0, pos[0] - rejilla.SIN_OT_PREVIO_H):pos[-1] + 1]
            if (lejos["etiqueta_escenario"] != "").any() or (previo["ot_event"] != "normal").any():
                continue
            for ataque in ataques_pct:
                copia = base.copy()
                antes = copia.loc[idx]
                despues = antes.copy()
                despues["t_exterior"] = np.maximum(antes["t_exterior"], p["t_max"] + CALOR_SOBRE_MAXIMO_C)
                xe0, xc0 = detector._matrices(antes)
                xe1, xc1 = detector._matrices(despues)
                copia.loc[idx, "t_exterior"] = despues["t_exterior"]
                copia.loc[idx, "kw_total"] += (xe1 - xe0) @ p["coef_energia"]
                copia.loc[idx, "agua_reposicion_l"] += (xe1 - xe0) @ p["coef_agua"]
                copia.loc[idx, "inlet_temp_c"] += (xc1 - xc0) @ p["coef_entrada"]
                no_ti = copia.loc[idx, "kw_total"] - copia.loc[idx, "kw_ti"]
                copia.loc[idx, "kw_total"] += no_ti * ataque / 100.0
                al = _detectar_igual(params, copia)
                horas = [s.index.get_loc(i) for i in idx]
                del_sitio = al.index[al["site_id"] == sitio]
                fila_al = al.loc[del_sitio[horas]]
                filas.append({"site_id": sitio, "dia": str(dia), "ataque_pct": ataque,
                              "vista": bool(_fisica(fila_al).any()),
                              "horas_fuera_de_clima": int(fila_al["clima_no_visto"].sum())})
    return pd.DataFrame(filas)


def resumen(params: dict, r: pd.DataFrame, c: pd.DataFrame) -> dict:
    """Solo agregados: nada de filas del kit."""
    hechas = r[~r["omitida"]]
    por_pendiente = []
    for pendiente, g in hechas.groupby("pendiente_pct_h"):
        v = g[g["vista"]]
        por_pendiente.append({
            "pendiente_pct_h": float(pendiente), "rampas": int(len(g)), "vistas": int(len(v)),
            "omitidas": int(r[(r["pendiente_pct_h"] == pendiente) & r["omitida"]].shape[0]),
            "horas_hasta_ver_mediana": float(v["horas_hasta_ver"].median()) if len(v) else None,
            "horas_hasta_ver_max": float(v["horas_hasta_ver"].max()) if len(v) else None,
            "pct_al_ver_mediana": float(v["pct_al_ver"].median()) if len(v) else None,
            "pct_al_ver_max": float(v["pct_al_ver"].max()) if len(v) else None,
            "kwh_antes_de_ver_mediana": round(float(v["kwh_antes_de_ver"].median()), 1) if len(v) else None,
            "kwh_antes_de_ver_max": round(float(v["kwh_antes_de_ver"].max()), 1) if len(v) else None,
            "clase_escalon_pct": round(float((v["clase_al_ver"] == "escalon_sin_registro").mean() * 100), 1)
            if len(v) else None,
        })
    por_ataque = [{"ataque_pct": int(a), "tardes": int(len(g)), "vistas": int(g["vista"].sum()),
                   "horas_fuera_de_clima_pct": round(float(g["horas_fuera_de_clima"].sum()
                                                           / (len(g) * len(HORAS_TARDE)) * 100), 1)}
                  for a, g in c.groupby("ataque_pct")]
    return {
        "_meta": {"aviso": "DATOS SIMULADOS · pruebas exploratorias, fuera de la rejilla fijada y de "
                           "numeros_oficiales.json. Solo para preguntas del jurado (docs/06 §6b).",
                  "rampa_h": RAMPA_H, "horas_tarde": list(HORAS_TARDE),
                  "calor_sobre_maximo_c": CALOR_SOBRE_MAXIMO_C},
        "piso": piso(params).to_dict(orient="records"),
        "rampas": por_pendiente,
        "calor": por_ataque,
    }


def correr(telemetria: pd.DataFrame) -> dict:
    base = rejilla._preparar(telemetria)
    params = detector.entrenar(base)
    return resumen(params, rampas(base, params), calor(base, params))


def main() -> None:
    p = argparse.ArgumentParser(description="Pruebas exploratorias: piso, rampa lenta y ataque con calor.")
    fuente = p.add_mutually_exclusive_group()
    fuente.add_argument("--entrada", type=Path, default=Path("data/procesado/telemetria.csv"))
    fuente.add_argument("--kit", type=Path, help="CSV crudo del kit (se carga con src.datos.cargar)")
    fuente.add_argument("--ejemplo", action="store_true", help="datos INVENTADOS con el formato del kit")
    p.add_argument("--salida", type=Path, default=Path("data/resultados/exploratorias.json"))
    a = p.parse_args()
    r = correr(correr_rejilla._leer(a))
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.DataFrame(r["piso"]).to_string(index=False))
    print(pd.DataFrame(r["rampas"]).to_string(index=False))
    print(pd.DataFrame(r["calor"]).to_string(index=False))
    print(f"Agregados → {a.salida}")


if __name__ == "__main__":
    main()
