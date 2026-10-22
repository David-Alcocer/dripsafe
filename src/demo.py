"""Demo en terminal para el pitch (~1 min, corre sola).

Tres actos sobre la telemetría del kit, sin escribir nada en disco:

1. Aprende lo normal: ajusta la línea base de cada sitio y muestra su umbral.
2. Prueba sorpresa: mete una falla de energía no TI (+10 % por defecto, 4 h,
   sin evento OT) en una copia en memoria y la reproduce hora por hora,
   DripSafe contra la regla fija del kit (PUE 1.6, WUE 1.5, entrada 29 °C).
3. Marcador: episodios originales del kit, resultado de la falla y tiempo.

Si la falla no se detecta, la demo lo dice tal cual.

Uso:
    python -m src.demo
    python -m src.demo --falla 20
    python -m src.demo --rapido        # sin pausas, para ensayar
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

from src import contrato
from src.ataques import rejilla
from src.evaluacion import episodios
from src.evaluacion.reglas import reglas_fijas
from src.modelo import detector

ENTRADA = Path("data/procesado/telemetria.csv")
HORAS_FALLA = 4
DESFASE_H = 6          # horas desde el inicio de la evaluación, como la rejilla
CONTEXTO_H = 6         # horas normales antes y después de la falla
ANCHO_BARRA = 28
SITIO = "SIM-A"        # sitio de la prueba sorpresa

PAUSA = 0.2
CON_ENTER = True       # cada acto arranca al presionar Enter
CLASES = {"escalon_sin_registro": "escalón sin registro", "incidente_ot": "incidente OT con efecto"}


def _c(codigo: str, texto: str) -> str:
    return f"\033[{codigo}m{texto}\033[0m" if sys.stdout.isatty() else texto


def titulo(texto: str) -> None:
    print("\n" + _c("1;36", f"▸ {texto}"))


def esperar(segundos: float) -> None:
    time.sleep(segundos * PAUSA)


def siguiente(que_hace: str) -> None:
    """Explica en una línea el siguiente acto y espera Enter."""
    print("\n" + _c("2", f"  {que_hace}"))
    if CON_ENTER:
        input(_c("2", "  [Enter] →"))


def falla_fuera(motivo: str) -> None:
    print("\n" + _c("1;31", f"✗ {motivo}") + "\n")
    raise SystemExit(1)


def _barra(residuo: float, limite: float, escala: float, alerta: bool) -> str:
    llenas = int(round(max(residuo, 0.0) / escala * ANCHO_BARRA))
    marca = min(ANCHO_BARRA - 1, int(round(limite / escala * ANCHO_BARRA)))
    celdas = ["█" if i < llenas else ("┊" if i == marca else " ") for i in range(ANCHO_BARRA)]
    texto = "".join(celdas)
    return _c("1;31", texto) if alerta else _c("32", texto)


def acto_aprender(df: pd.DataFrame) -> dict[str, dict]:
    titulo("1 · Aprende lo normal")
    print("  Cada sitio aprende cuánto DEBERÍA gastar según su carga y la temperatura exterior.")
    esperar(2)
    inicio = time.perf_counter()
    params = detector.entrenar(df)
    ms = (time.perf_counter() - inicio) * 1000.0
    for sitio, p in params.items():
        umbral = _c("1", f"+{p['limites']['energia']:.1f} %")
        print(f"  {sitio}: {detector.HORAS_AJUSTE} h de ajuste + {detector.HORAS_CALIBRACION} h de "
              f"calibración → alerta si la energía no TI pasa de {umbral}")
        esperar(1.2)
    print(_c("2", f"  Entrenado en {ms:.1f} ms, en CPU, sin nube y sin GPU."))
    esperar(2.5)
    return params


def acto_falla(df: pd.DataFrame, sitio: str, falla: float, limite: float) -> dict:
    titulo(f"2 · Prueba sorpresa: energía no TI +{falla:g} % durante {HORAS_FALLA} h en {sitio}")
    print("  Una falla pequeña, sin registro OT. Así se ve una válvula atorada o un setpoint movido.")
    esperar(2)

    inyeccion = rejilla.Inyeccion(f"energia_+{falla:g}", "energia", "energia", falla, HORAS_FALLA,
                                  "falla", "", "escalon_sin_registro")
    s = rejilla._preparar(df)
    s = s[s["site_id"] == sitio].reset_index(drop=True)
    lugar = rejilla._lugar_limpio(s, inyeccion, DESFASE_H)
    if lugar is None:
        falla_fuera(f"No hay un lugar limpio en la evaluación de {sitio}.")
    copia, ficha = rejilla.aplicar(df, inyeccion, sitio, s.loc[lugar[0], "timestamp"])

    inicio = time.perf_counter()
    alertas = detector.detectar(copia)
    ms = (time.perf_counter() - inicio) * 1000.0
    regla = reglas_fijas(copia, horas_por_intervalo=1.0, unidad_energia="kwh_intervalo", incluir_ot=False)

    alertas = alertas[alertas["site_id"] == sitio].set_index("timestamp")
    regla = regla[regla["site_id"] == sitio].set_index("timestamp")
    datos = copia[copia["site_id"] == sitio].set_index("timestamp")
    paso = pd.Timedelta(hours=1)
    desde, hasta = ficha["inicio"] - CONTEXTO_H * paso, ficha["fin"] + CONTEXTO_H * paso
    ventana = alertas.loc[desde:hasta]
    escala = max(40.0, falla * 1.3, limite * 2)

    print()
    print(_c("2", f"  {'hora':5}  {'real':>6} {'esperado':>8}  {'exceso':>7}  "
                  f"{'(┊ = umbral DripSafe)':{ANCHO_BARRA}}  DripSafe  Regla fija"))
    for ts, fila in ventana.iterrows():
        real = datos.loc[ts, "kw_total"] - datos.loc[ts, "kw_ti"]
        residuo = float(fila["residuo_energia_pct"])
        fisica = bool(fila["alerta_umbral"] or fila["alerta_media_4h"])
        en_falla = ficha["inicio"] <= ts <= ficha["fin"]
        hora = _c("1;33", ts.strftime("%H:%M")) if en_falla else ts.strftime("%H:%M")
        ds = _c("1;31", "●  ALERTA") if fisica else _c("2", "○        ")
        rf = _c("1;31", "●") if bool(regla.loc[ts, "anomalia"]) else _c("2", "○")
        print(f"  {hora}  {real:6.1f} {fila['esperado_energia_no_ti_kwh']:8.1f}  {residuo:+6.1f}%  "
              f"{_barra(residuo, limite, escala, fisica)}  {ds}  {rf}")
        esperar(2.0)
    print(_c("2", "  Horas en amarillo: la falla inyectada. kWh de energía no TI por hora."))
    esperar(2)

    en_falla = alertas.loc[ficha["inicio"]:ficha["fin"]]
    fisicas = en_falla[en_falla["alerta_umbral"] | en_falla["alerta_media_4h"]]
    return {
        "detectada": not fisicas.empty,
        "horas_hasta": (fisicas.index.min() - ficha["inicio"]) / paso if not fisicas.empty else None,
        "clase": fisicas["clase"].iloc[0] if not fisicas.empty else "",
        "accion": fisicas["accion"].iloc[0] if not fisicas.empty else "",
        "regla": bool(regla.loc[ficha["inicio"]:ficha["fin"], "anomalia"].any()),
        "ms": ms,
    }


def acto_marcador(df: pd.DataFrame, falla: float, r: dict) -> None:
    titulo("3 · Marcador")
    alertas = detector.detectar(df).assign(anomalia=lambda d: d["clase"].ne("normal"))
    kit = episodios.episodios_desde_etiquetas(df, horas_por_intervalo=1.0)
    _, m = episodios.evaluar_episodios(df, alertas, kit, horas_por_intervalo=1.0)
    detectados = _c("1;32", f"{m['tp']} de {m['tp'] + m['fn']}")
    print(f"  Episodios originales del kit:  {detectados} detectados, "
          f"{_c('1;32' if m['fp'] == 0 else '1;31', str(m['fp']))} falsas alarmas "
          f"en {m['horas_limpias_sitio']:.0f} horas-sitio limpias")
    esperar(2)
    if r["detectada"]:
        cuando = "desde la primera hora" if r["horas_hasta"] == 0 else f"en la hora {r['horas_hasta'] + 1:.0f}"
        print(f"  Falla de +{falla:g} %:  DripSafe {_c('1;32', 'la detectó')} "
              f"{cuando} · regla fija: "
              f"{_c('1;32', 'también') if r['regla'] else _c('1;31', 'no la vio')}")
        print(f"  Clase: {CLASES.get(r['clase'], r['clase'])} → {r['accion']}")
    else:
        print(f"  Falla de +{falla:g} %:  DripSafe {_c('1;31', 'NO la detectó')} "
              f"(está por debajo de su umbral) · regla fija: {'sí' if r['regla'] else 'no'}")
    esperar(2)
    tiempo = _c("1", f"{r['ms']:.1f} ms")
    print(f"  Una corrida completa del detector: {tiempo} en esta laptop.")
    esperar(1.5)
    print("\n" + _c("1;33", "  DATOS SIMULADOS · kit CIFOX · DripSafe solo avisa; decide una persona.") + "\n")


def main() -> None:
    global PAUSA, CON_ENTER
    p = argparse.ArgumentParser(description="Demo en terminal de DripSafe para el pitch.")
    p.add_argument("--entrada", type=Path, default=ENTRADA, help="telemetría del contrato v2")
    p.add_argument("--falla", type=float, default=10.0, help="exceso de energía no TI en %% (1 a 200)")
    p.add_argument("--rapido", action="store_true", help="sin pausas ni Enter")
    a = p.parse_args()
    if a.rapido:
        PAUSA = 0.0
        CON_ENTER = False
    if not 1 <= a.falla <= 200:
        falla_fuera("--falla debe estar entre 1 y 200.")
    if not a.entrada.exists():
        falla_fuera(f"No encontré {a.entrada}. Genérala con:\n  .venv/bin/python -m src.datos.cargar "
                    f"--kit \"/ruta/al/kit/data/operaciones_simuladas.csv\" --salida {ENTRADA}")

    df = contrato.leer(a.entrada)
    problemas = contrato.validar(df)
    if problemas:
        falla_fuera("La telemetría no cumple el contrato: " + "; ".join(problemas))

    print(_c("1", "DripSafe · demo en vivo") + _c("2", "  (DATOS SIMULADOS)"))
    siguiente("Aprende el consumo normal de cada sitio con 72 h sin fallas.")
    params = acto_aprender(df)
    siguiente(f"Mete una falla de +{a.falla:g} % en una copia y la revisa hora por hora.")
    resultado = acto_falla(df, SITIO, a.falla, params[SITIO]["limites"]["energia"])
    siguiente("Cuenta aciertos y falsas alarmas en los datos originales del kit.")
    acto_marcador(df, a.falla, resultado)


if __name__ == "__main__":
    main()
