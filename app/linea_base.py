"""Vista previa del detector de la propuesta, para que el dashboard funcione antes de integrar.

NO es el detector oficial: ese lo construye Gadiel (G1) y las clases las define Guille (U1).
Cuando exista data/resultados/alertas.csv con estas mismas columnas, la app lo usa en lugar
de esta vista previa (app/cargar.py). Sigue la propuesta (§3.1–§3.3) en su forma más simple:

1. Línea base por sitio con mínimos cuadrados, ajustada con las primeras 48 h de referencia:
   energía no TI y agua  ~  1 + TI + TI·max(0, T − 20)
   temperatura de entrada ~  1 + max(0, T − 20)
2. Residuo = real − esperado (en % para energía y agua; en °C para la entrada).
3. Umbral = el mayor residuo de las 24 h de calibración × 1.5 (con un mínimo). Además, la media
   móvil de 4 h con su propio umbral, para excesos pequeños y sostenidos.
4. Fuera del rango de temperatura aprendido, el umbral se duplica y la alerta sale con
   «confianza baja» (nunca se apaga).
5. Clases: cruza los excesos con el registro OT (incidente, cambio, escalón, intento).

Las etiquetas del kit (scenario, simulated_anomaly) nunca entran aquí: solo `split`, para
separar ajuste y calibración.
"""

import numpy as np
import pandas as pd

HORAS_AJUSTE = 48
MARGEN = 1.5             # umbral = mayor residuo de calibración × 1.5
MINIMOS = {"energia": 3.0, "agua": 3.0, "entrada": 0.5}         # % · % · °C
MINIMOS_MEDIA = {"energia": 2.0, "agua": 2.0, "entrada": 0.3}
VENTANA_EFECTO_H = 24    # un exceso hasta 24 h después del evento OT cuenta como su efecto

COLUMNAS = [
    "timestamp", "site_id", "esperado_energia_no_ti_kwh", "esperado_agua_l", "esperado_entrada_c",
    "residuo_energia_pct", "residuo_agua_pct", "residuo_entrada_c",
    "alerta_umbral", "alerta_media_4h", "clima_no_visto", "clase", "motivo",
]


def _bisagra(t: pd.Series) -> pd.Series:
    """Grados por encima de 20 °C: el aire exterior ya no ayuda a enfriar."""
    return (t - 20).clip(lower=0)


def _ajustar(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Mínimos cuadrados: los coeficientes que mejor explican y con las columnas de x."""
    return np.linalg.lstsq(x, y, rcond=None)[0]


def _matrices(s: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    uno = np.ones(len(s))
    h = _bisagra(s["outdoor_temp_c"]).to_numpy()
    it = s["energy_it_kwh"].to_numpy()
    return np.column_stack([uno, it, it * h]), np.column_stack([uno, h])


def _sitio(s: pd.DataFrame) -> pd.DataFrame:
    """Línea base, residuos y banderas de un sitio (filas ordenadas por hora)."""
    s = s.sort_values("timestamp").reset_index(drop=True)
    ref = s.index[s["split"] == "referencia"]
    ajuste, calib = ref[:HORAS_AJUSTE], ref[HORAS_AJUSTE:]

    x_ti, x_clima = _matrices(s)
    no_ti = (s["energy_total_kwh"] - s["energy_it_kwh"]).to_numpy()
    out = pd.DataFrame({"timestamp": s["timestamp"], "site_id": s["site_id"]})
    out["esperado_energia_no_ti_kwh"] = x_ti @ _ajustar(x_ti[ajuste], no_ti[ajuste])
    out["esperado_agua_l"] = x_ti @ _ajustar(x_ti[ajuste], s["water_l"].to_numpy()[ajuste])
    out["esperado_entrada_c"] = x_clima @ _ajustar(x_clima[ajuste], s["inlet_temp_c"].to_numpy()[ajuste])

    def pct(real, esperado):
        esperado = pd.Series(esperado)
        return ((pd.Series(real) - esperado) / esperado.where(esperado > 0) * 100).to_numpy()

    out["residuo_energia_pct"] = pct(no_ti, out["esperado_energia_no_ti_kwh"])
    out["residuo_agua_pct"] = pct(s["water_l"], out["esperado_agua_l"])
    out["residuo_entrada_c"] = s["inlet_temp_c"] - out["esperado_entrada_c"]

    # Clima no visto: temperatura fuera del rango de ajuste y calibración (el umbral se duplica).
    t_ref = s.loc[ref, "outdoor_temp_c"]
    out["clima_no_visto"] = ~s["outdoor_temp_c"].between(t_ref.min(), t_ref.max())
    factor = np.where(out["clima_no_visto"], 2.0, 1.0)

    umbral = pd.Series(False, index=out.index)
    media = pd.Series(False, index=out.index)
    motivos = [[] for _ in range(len(out))]
    for clave, col, unidad in [("energia", "residuo_energia_pct", "%"), ("agua", "residuo_agua_pct", "%"),
                               ("entrada", "residuo_entrada_c", " °C")]:
        r = out[col].fillna(0)
        m4 = r.rolling(4, min_periods=4).mean().fillna(0)
        lim = max(r[calib].abs().max() * MARGEN, MINIMOS[clave])
        lim_m = max(m4[calib].abs().max() * MARGEN, MINIMOS_MEDIA[clave])
        por_hora = r > lim * factor
        # Sostenido: la media de 4 h pasa su umbral Y la hora actual también va por encima de él
        # (así la cola de un exceso que ya terminó no sigue alertando).
        sostenido = (m4 > lim_m * factor) & (r > lim_m * factor)
        umbral |= por_hora
        media |= sostenido
        nombre = {"energia": "energía no TI", "agua": "agua", "entrada": "entrada"}[clave]
        for i in np.flatnonzero((por_hora | sostenido).to_numpy()):
            valor, sufijo = (r.iloc[i], "") if por_hora.iloc[i] else (m4.iloc[i], " (media 4 h)")
            cifra = f"{valor:+.0f}%" if unidad == "%" else f"{valor:+.1f}{unidad}"
            motivos[i].append(f"{nombre} {cifra} sobre lo esperado{sufijo}")
    out["alerta_umbral"] = umbral.to_numpy()
    out["alerta_media_4h"] = media.to_numpy()
    out["motivo"] = [
        "; ".join(m) + (" · confianza baja: clima fuera de lo aprendido" if m and out["clima_no_visto"].iloc[i] else "")
        for i, m in enumerate(motivos)
    ]
    out["_ot"] = s["ot_event"].to_numpy()
    return out


def _tramos(mascara: pd.Series, horas: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Horas seguidas donde la máscara es verdadera: [(inicio, fin_exclusivo)]."""
    sel = horas[mascara.to_numpy()]
    if sel.empty:
        return []
    grupo = (sel.diff() > pd.Timedelta(hours=1)).cumsum()
    return [(g.iloc[0], g.iloc[-1] + pd.Timedelta(hours=1)) for _, g in sel.groupby(grupo)]


def _clasificar(o: pd.DataFrame) -> pd.Series:
    """Clase de cada hora de un sitio según la tabla de decisión de la propuesta (§3.3)."""
    clase = pd.Series("normal", index=o.index, dtype=object)
    horas = o["timestamp"]
    exceso = o["alerta_umbral"] | o["alerta_media_4h"]
    tramos_exceso = _tramos(exceso, horas)

    # Primero lo que no tiene registro: todo exceso es «escalón sin registro» hasta que un evento lo explique.
    clase[exceso] = "escalon_sin_registro"

    ot = o["_ot"] != "normal"
    for inicio, fin in _tramos(ot, horas):
        en_evento = (horas >= inicio) & (horas < fin)
        cambio = (o.loc[en_evento, "_ot"] == "cambio_config_no_autorizado").any()
        clase[en_evento & (o["_ot"] == "login_fallido")] = "intento_acceso"
        clase[en_evento & (o["_ot"] == "cambio_config_no_autorizado")] = "cambio_no_autorizado"
        # Efecto: un tramo de exceso que EMPIEZA dentro de [inicio, fin + 24 h]. Uno que ya venía de
        # antes es «coincidente, no causal» y se queda como escalón.
        limite = fin + pd.Timedelta(hours=VENTANA_EFECTO_H)
        for e_ini, e_fin in tramos_exceso:
            if inicio <= e_ini <= limite:
                tramo = (horas >= e_ini) & (horas < e_fin)
                clase[tramo | (en_evento & cambio)] = "incidente_ot"
    return clase


def detectar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sitio y hora con lo esperado, los residuos, las banderas y la clase."""
    partes = []
    for _, s in tabla.groupby("site_id", sort=True):
        o = _sitio(s)
        o["clase"] = _clasificar(o)
        partes.append(o.drop(columns="_ot"))
    return pd.concat(partes, ignore_index=True)[COLUMNAS]
