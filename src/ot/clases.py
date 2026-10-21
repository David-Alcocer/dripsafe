"""Las cuatro clases OT de DripSafe: tabla de decisión (D16 · U1 · issue #30).

El detector (src/modelo/detector.py) encuentra excesos físicos por sitio y hora:
energía no TI, agua o temperatura de entrada por encima de lo esperado. Este
módulo cruza esos excesos con el registro OT (`ot_event`) y decide la clase, su
prioridad y la acción sugerida. Es la única implementación de las reglas: el
detector la llama y el dashboard muestra lo que sale de aquí.

La tabla completa, con los casos ambiguos y su respuesta, está en
docs/06-ciberseguridad-ot.md §4. Cada caso tiene su prueba en tests/test_clases.py.

Definiciones (todas por sitio):
- Exceso: hora con alerta por umbral o por media de 4 h, en cualquier variable.
- Tramo de exceso: horas seguidas con exceso.
- Evento OT: horas seguidas con `ot_event` distinto de "normal".
- Ventana de efecto: desde la primera hora del evento hasta 24 h después de su
  última hora. Si el evento ocupa la hora de las 04:00, cuentan los excesos que
  empiecen entre las 04:00 y las 04:00 del día siguiente.
- Un tramo es CAUSADO por un evento si EMPIEZA dentro de su ventana. Si ya venía
  de antes y el evento cae a la mitad, es COINCIDENTE, NO CAUSAL.

Precedencia (gana la más grave): incidente_ot > cambio_no_autorizado >
escalon_sin_registro > intento_acceso > normal. Ninguna regla baja una clase ya
asignada a una hora.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VENTANA_EFECTO_H = 24

NORMAL = "normal"
LOGIN = "login_fallido"
CAMBIO = "cambio_config_no_autorizado"

# De la más grave a la menos grave. El dashboard las muestra en este orden.
CLASES = ["incidente_ot", "cambio_no_autorizado", "escalon_sin_registro", "intento_acceso"]

PRIORIDAD = {
    "incidente_ot": "maxima",
    "cambio_no_autorizado": "alta",
    "escalon_sin_registro": "alta",
    "intento_acceso": "media",
    NORMAL: "",
}

ACCION = {
    "incidente_ot": "Restaurar la configuración aprobada y pasar a modo seguro manual; "
                    "confirmar en sitio.",
    "cambio_no_autorizado": "Comparar contra la configuración aprobada y vigilar 24 h: "
                            "el efecto puede llegar con el siguiente pico de calor.",
    "escalon_sin_registro": "Comparar los setpoints contra la versión aprobada antes de "
                            "mandar a mantenimiento: puede ser un cambio sin registro.",
    "intento_acceso": "Revisar accesos y cuentas; un login fallido no prueba una intrusión.",
    NORMAL: "",
}
ACCION_AGUA = " Como el exceso es de agua, inspección física en paralelo (posible fuga)."

_TIPO_EVENTO = {LOGIN: "login fallido", CAMBIO: "cambio de configuración no autorizado"}

# Rango numérico para aplicar la precedencia con un máximo.
_RANGO = {c: len(CLASES) - i for i, c in enumerate(CLASES)}
_RANGO[NORMAL] = 0
_CLASE_DE_RANGO = {r: c for c, r in _RANGO.items()}

COLUMNAS_ENTRADA = ["timestamp", "alerta_umbral", "alerta_media_4h", "ot_event"]
COLUMNAS_SALIDA = ["clase", "prioridad", "accion", "causalidad", "evento_ot_inicio", "forma", "nota_ot"]


def _paso(horas: pd.Series) -> pd.Timedelta:
    """Intervalo mediano entre filas; 1 h si no se puede calcular."""
    paso = horas.diff().median()
    return pd.Timedelta(hours=1) if pd.isna(paso) or paso <= pd.Timedelta(0) else paso


def _tramos(mascara: np.ndarray, horas: pd.Series, paso: pd.Timedelta) -> list[tuple[int, int]]:
    """Posiciones [inicio, fin] (ambas incluidas) de horas seguidas con la máscara activa.

    Un hueco en el tiempo (falta una hora) corta el tramo aunque las filas estén juntas.
    """
    posiciones = np.flatnonzero(mascara)
    if len(posiciones) == 0:
        return []
    tramos = []
    inicio = anterior = int(posiciones[0])
    for p in posiciones[1:]:
        p = int(p)
        if p != anterior + 1 or horas.iloc[p] - horas.iloc[anterior] > 1.5 * paso:
            tramos.append((inicio, anterior))
            inicio = p
        anterior = p
    tramos.append((inicio, anterior))
    return tramos


def _tipo(ot: np.ndarray, a: int, b: int) -> str:
    """Tipo del evento para los textos: el cambio pesa más que el login."""
    return CAMBIO if (ot[a:b + 1] == CAMBIO).any() else LOGIN


def _hora(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%d %H:%M")


def _clasificar_sitio(s: pd.DataFrame, ventana: pd.Timedelta) -> pd.DataFrame:
    n = len(s)
    horas = pd.to_datetime(s["timestamp"]).reset_index(drop=True)
    paso = _paso(horas)
    umbral = s["alerta_umbral"].to_numpy(dtype=bool)
    exceso = umbral | s["alerta_media_4h"].to_numpy(dtype=bool)
    agua = s["exceso_agua"].to_numpy(dtype=bool) if "exceso_agua" in s else np.zeros(n, bool)
    ot = s["ot_event"].fillna(NORMAL).astype(str).to_numpy()

    rango = np.zeros(n, dtype=int)
    causalidad = np.full(n, "", dtype=object)
    evento_inicio = pd.Series(pd.NaT, index=range(n), dtype=horas.dtype)
    forma = np.full(n, "", dtype=object)
    nota = np.full(n, "", dtype=object)

    def subir(desde: int, hasta: int, clase: str, mascara: np.ndarray | None = None) -> None:
        """Sube la clase de un tramo de horas; nunca la baja (precedencia)."""
        seg = slice(desde, hasta + 1)
        nuevo = np.where(mascara if mascara is not None else True, _RANGO[clase], 0)
        rango[seg] = np.maximum(rango[seg], nuevo)

    tramos = _tramos(exceso, horas, paso)
    eventos = _tramos(ot != NORMAL, horas, paso)

    # Regla de oro 1: todo exceso sin explicar es escalón sin registro, nunca mantenimiento directo.
    for i, j in tramos:
        forma[i:j + 1] = "escalon" if umbral[i] else "gradual"
        subir(i, j, "escalon_sin_registro")

    # El evento en sus propias horas. Regla de oro 2: un cambio no autorizado nunca es «sin urgencia».
    for a, b in eventos:
        seg = slice(a, b + 1)
        subir(a, b, "cambio_no_autorizado", ot[seg] == CAMBIO)
        subir(a, b, "intento_acceso", (ot[seg] == LOGIN) & ~exceso[seg])
        con_exceso = (ot[seg] == LOGIN) & exceso[seg]
        nota[seg] = np.where(con_exceso, "hubo un login fallido en esta hora", nota[seg])

    # Atribución: el tramo debe EMPEZAR dentro de la ventana de algún evento.
    for i, j in tramos:
        inicio = horas.iloc[i]
        causantes = [(a, b) for a, b in eventos if horas.iloc[a] <= inicio <= horas.iloc[b] + ventana]
        if causantes:
            # Se prefiere el evento con cambio de configuración; entre iguales, el más reciente.
            a, b = max(causantes, key=lambda e: (_tipo(ot, *e) == CAMBIO, horas.iloc[e[0]]))
            subir(i, j, "incidente_ot")
            causalidad[i:j + 1] = "causal"
            evento_inicio.iloc[i:j + 1] = horas.iloc[a]
            retraso = (inicio - horas.iloc[a]) / pd.Timedelta(hours=1)
            nota[i:j + 1] = (f"empezó {retraso:g} h después del {_TIPO_EVENTO[_tipo(ot, a, b)]} "
                             f"de las {_hora(horas.iloc[a])} UTC")
            # El propio cambio de configuración sube a incidente: ya se vio su efecto.
            cambio = np.zeros(n, dtype=bool)
            cambio[a:b + 1] = ot[a:b + 1] == CAMBIO
            subir(a, b, "incidente_ot", cambio[a:b + 1])
            evento_inicio[cambio] = horas.iloc[a]
            nota[cambio] = f"con efecto físico {retraso:g} h después"
            continue
        # Un evento que cae a la mitad de un exceso que ya venía de antes no lo causó.
        coincidentes = [(a, b) for a, b in eventos if inicio < horas.iloc[a] <= horas.iloc[j]]
        if coincidentes:
            a, b = coincidentes[0]
            causalidad[i:j + 1] = "coincidente_no_causal"
            evento_inicio.iloc[i:j + 1] = horas.iloc[a]
            nota[i:j + 1] = (f"coincide con un {_TIPO_EVENTO[_tipo(ot, a, b)]} de las "
                             f"{_hora(horas.iloc[a])} UTC, pero el exceso ya venía de antes: "
                             "no causal")

    clase = np.array([_CLASE_DE_RANGO[r] for r in rango], dtype=object)
    accion = np.array([ACCION[c] for c in clase], dtype=object)
    agua_escalon = (clase == "escalon_sin_registro") & agua
    accion[agua_escalon] = accion[agua_escalon] + ACCION_AGUA
    forma[clase == NORMAL] = ""

    return pd.DataFrame({
        "clase": clase,
        "prioridad": [PRIORIDAD[c] for c in clase],
        "accion": accion,
        "causalidad": causalidad,
        "evento_ot_inicio": evento_inicio.to_numpy(),
        "forma": forma,
        "nota_ot": nota,
    }, index=s.index)


def clasificar(tabla: pd.DataFrame, ventana_h: float = VENTANA_EFECTO_H) -> pd.DataFrame:
    """Clase, prioridad y acción para cada fila (sitio y hora) de `tabla`.

    `tabla` necesita las columnas de COLUMNAS_ENTRADA. `site_id` y `exceso_agua`
    son opcionales: sin `site_id` todo se trata como un solo sitio. Regresa un
    DataFrame con el mismo índice y las columnas de COLUMNAS_SALIDA.
    """
    faltan = [c for c in COLUMNAS_ENTRADA if c not in tabla.columns]
    if faltan:
        raise ValueError(f"Faltan columnas para clasificar: {faltan}")
    ventana = pd.Timedelta(hours=ventana_h)
    sitios = tabla["site_id"] if "site_id" in tabla else pd.Series("sitio_unico", index=tabla.index)
    partes = []
    for _, grupo in tabla.groupby(sitios, sort=False):
        orden = pd.to_datetime(grupo["timestamp"]).sort_values(kind="stable").index
        partes.append(_clasificar_sitio(grupo.loc[orden], ventana))
    if not partes:
        return pd.DataFrame(columns=COLUMNAS_SALIDA, index=tabla.index)
    return pd.concat(partes).loc[tabla.index, COLUMNAS_SALIDA]


def coincidencias_al_azar(alertas: pd.DataFrame, ventanas_h=(1, 4, 8, 12, 24)) -> pd.DataFrame:
    """¿Qué tan seguido un evento OT puesto al azar «encuentra» un exceso que no causó?

    Para cada sitio y cada hora posible, simula un evento OT de 1 h y revisa si
    algún tramo de exceso EMPIEZA dentro de su ventana, que es justo lo que la
    regla llamaría «incidente OT con efecto». Solo cuentan las horas cuya
    ventana completa cabe en los datos. Pásale las alertas de un periodo sin
    eventos inyectados (por ejemplo, la evaluación original del kit).

    Regresa una fila por sitio y ventana, más el total, con el porcentaje de
    eventos al azar que se habrían atribuido a un exceso por pura coincidencia.
    """
    faltan = [c for c in ["timestamp", "alerta_umbral", "alerta_media_4h"] if c not in alertas]
    if faltan:
        raise ValueError(f"Faltan columnas: {faltan}")
    sitios = alertas["site_id"] if "site_id" in alertas else pd.Series("sitio_unico", index=alertas.index)
    filas = []
    for sitio, grupo in alertas.groupby(sitios, sort=True):
        grupo = grupo.sort_values("timestamp", kind="stable")
        horas = pd.to_datetime(grupo["timestamp"]).reset_index(drop=True)
        exceso = (grupo["alerta_umbral"].to_numpy(dtype=bool)
                  | grupo["alerta_media_4h"].to_numpy(dtype=bool))
        inicios = horas.iloc[[i for i, _ in _tramos(exceso, horas, _paso(horas))]]
        for w in ventanas_h:
            ventana = pd.Timedelta(hours=w)
            candidatos = horas[horas + ventana <= horas.iloc[-1]] if len(horas) else horas
            aciertos = sum(bool(((inicios >= t) & (inicios <= t + ventana)).any()) for t in candidatos)
            filas.append({"site_id": sitio, "ventana_h": w, "eventos_simulados": len(candidatos),
                          "atribuciones_al_azar": aciertos, "tramos_de_exceso": len(inicios)})
    tabla = pd.DataFrame(filas, columns=["site_id", "ventana_h", "eventos_simulados",
                                         "atribuciones_al_azar", "tramos_de_exceso"])
    if not tabla.empty:
        total = tabla.groupby("ventana_h", as_index=False)[
            ["eventos_simulados", "atribuciones_al_azar", "tramos_de_exceso"]].sum()
        total.insert(0, "site_id", "TOTAL")
        tabla = pd.concat([tabla, total], ignore_index=True)
    simulados = tabla["eventos_simulados"].replace(0, np.nan)
    tabla["prob_pct"] = (100 * tabla["atribuciones_al_azar"] / simulados).round(1)
    return tabla
