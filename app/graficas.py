"""Gráficas de plotly con el estilo de los paneles «Time series» de Grafana.

Una sola escala Y por gráfica. La leyenda va en HTML debajo de la gráfica
(componentes.leyenda), con la media y el máximo como en Grafana.
"""

import plotly.graph_objects as go

from app.textos import CLASES

COLOR = {
    "serie": "#4c8bd6",
    "comparar": "#7d8794",
    "texto": "rgba(204,204,220,0.65)",
    "rejilla": "rgba(204,204,220,0.08)",
    "eje": "rgba(204,204,220,0.15)",
    "rojo": "#d0545f",
    "naranja": "#d39a2c",
    "amarillo": "#a8b3c4",
}
OPACIDAD_BANDA = {"rojo": 0.22, "naranja": 0.18, "amarillo": 0.14}
# Un color fijo por método en la evaluación (DripSafe en azul, las reglas del kit en gris).
COLOR_METODO = {"DripSafe": "#4c8bd6", "Reglas del kit": "#7d8794"}
# Un color fijo por sitio (nunca rojo ni naranja: esos son de las alertas).
COLOR_SITIO = {"SIM-A": "#4c8bd6", "SIM-B": "#8a7fc4", "SIM-C": "#3a9fa8", "Todos": "#4c8bd6"}
CONFIG = {"displayModeBar": False}  # sin la barra de herramientas de plotly


def _base(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(
        height=alto,
        margin={"l": 4, "r": 8, "t": 4, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": COLOR["texto"], "size": 11},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#1c2430", "bordercolor": COLOR["eje"], "font": {"color": "#ccccdc"}},
        showlegend=False,
    )
    # Las horas del kit están en UTC: se muestran tal cual y la etiqueta emergente lo dice.
    fig.update_xaxes(showgrid=True, gridcolor=COLOR["rejilla"], linecolor=COLOR["eje"], tickformat="%d/%m\n%H:%M",
                     hoverformat="%d %b %H:%M UTC", zeroline=False)
    fig.update_yaxes(gridcolor=COLOR["rejilla"], zeroline=False, showline=False, automargin=True)
    return fig


def _anotaciones(fig: go.Figure, eventos) -> None:
    """Regiones de alerta como las anotaciones de Grafana: franja tenue y una marca de color abajo."""
    for _, e in eventos.iterrows():
        if e["clase"] not in CLASES:
            continue
        color = CLASES[e["clase"]][2]
        fig.add_vrect(x0=e["inicio"], x1=e["fin"], fillcolor=COLOR[color], opacity=OPACIDAD_BANDA[color],
                      line_width=0, layer="below")
        fig.add_shape(type="line", x0=e["inicio"], x1=e["fin"], y0=0, y1=0, yref="paper",
                      line={"color": COLOR[color], "width": 4})


def serie(x, y, nombre: str, unidad: str = "", decimales: int = 1, eventos=None, comparar=None,
          nombre_comparar: str = "Esperado", alto: int = 260, desde_cero: bool = False,
          etiquetas_y: dict | None = None) -> go.Figure:
    """Una variable en el tiempo, opcionalmente con su valor esperado y las regiones de alerta.

    `desde_cero`: el eje Y empieza en 0, para que el ruido normal no parezca un problema (demo).
    `etiquetas_y`: {valor: texto} para una variable por categorías (eventos OT), dibujada en escalones.
    """
    fig = go.Figure()
    if eventos is not None and len(eventos):
        _anotaciones(fig, eventos)
    formato = f"%{{y:,.{decimales}f}} {unidad}".strip()
    if comparar is not None:
        fig.add_trace(go.Scatter(x=x, y=comparar, name=nombre_comparar, mode="lines",
                                 line={"color": COLOR["comparar"], "width": 1.5, "dash": "dash"},
                                 hovertemplate=formato))
    fig.add_trace(go.Scatter(x=x, y=y, name=nombre, mode="lines",
                             line={"color": COLOR["serie"], "width": 1.5, "shape": "hv" if etiquetas_y else "linear"},
                             hovertemplate=formato))
    fig = _base(fig, alto)
    if desde_cero:
        fig.update_yaxes(rangemode="tozero")
    if etiquetas_y:
        fig.update_yaxes(tickvals=list(etiquetas_y), ticktext=list(etiquetas_y.values()),
                         range=[-0.3, max(etiquetas_y) + 0.3])
    return fig


def por_sitio(tabla_ancha, unidad: str = "", decimales: int = 1, eventos=None, alto: int = 280) -> go.Figure:
    """Una línea por sitio (columnas de `tabla_ancha`), cada una con su color fijo."""
    fig = go.Figure()
    if eventos is not None and len(eventos):
        _anotaciones(fig, eventos)
    formato = f"%{{y:,.{decimales}f}} {unidad}".strip()
    for sitio in tabla_ancha.columns:
        fig.add_trace(go.Scatter(x=tabla_ancha.index, y=tabla_ancha[sitio], name=sitio, mode="lines",
                                 line={"color": COLOR_SITIO.get(sitio, COLOR["serie"]), "width": 1.5},
                                 hovertemplate=f"{sitio}: {formato}<extra></extra>"))
    return _base(fig, alto)


def real_vs_esperado(x, real, esperado, nombre: str, unidad: str = "", decimales: int = 1, eventos=None,
                     alto: int = 280, color: str = "#4c8bd6", exceso=None) -> go.Figure:
    """Lo medido contra lo que la línea base esperaba para esa carga y ese clima.

    `exceso`: lo que va por encima de lo esperado SOLO en las horas con alerta; esa área se sombrea.
    """
    fig = go.Figure()
    if eventos is not None and len(eventos):
        _anotaciones(fig, eventos)
    formato = f"%{{y:,.{decimales}f}} {unidad}".strip()
    fig.add_trace(go.Scatter(x=x, y=esperado, name="Esperado", mode="lines", hovertemplate=formato,
                             line={"color": COLOR["comparar"], "width": 1.5, "dash": "dash"}))
    if exceso is not None:
        # El relleno «tonexty» pinta entre esta serie y la anterior (lo esperado): el exceso de las alertas.
        tope = [e + x_ for e, x_ in zip(esperado, exceso)]
        fig.add_trace(go.Scatter(x=x, y=tope, mode="lines", line={"width": 0}, fill="tonexty",
                                 fillcolor="rgba(211, 154, 44, 0.35)", hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=real, name="Real", mode="lines", hovertemplate=formato,
                             line={"color": color, "width": 1.6}))
    return _base(fig, alto)


def curva(filas, eje_y: str, titulo_y: str, alto: int = 260, porcentaje: bool = False) -> go.Figure:
    """Curva de sensibilidad: una línea por método, con la magnitud de la falla inyectada en el eje X."""
    fig = go.Figure()
    for metodo in dict.fromkeys(f["metodo"] for f in filas):
        puntos = sorted((f for f in filas if f["metodo"] == metodo), key=lambda f: f["magnitud_pct"])
        y = [(f["detectados"] / f["total"] * 100 if porcentaje else f[eje_y]) for f in puntos]
        fig.add_trace(go.Scatter(
            x=[f"+{f['magnitud_pct']}%" for f in puntos], y=y, name=metodo, mode="lines+markers",
            line={"color": COLOR_METODO.get(metodo, COLOR["serie"]), "width": 2}, marker={"size": 7},
            hovertemplate=f"{metodo}: %{{y:,.0f}}{' %' if porcentaje else ''}<extra></extra>"))
    fig = _base(fig, alto)
    fig.update_xaxes(type="category", tickformat="", hoverformat="", title_text="Exceso inyectado durante 4 h",
                     title_font={"size": 11})
    fig.update_yaxes(title_text=titulo_y, title_font={"size": 11}, rangemode="tozero")
    fig.update_layout(margin={"l": 4, "r": 8, "t": 4, "b": 36})
    if porcentaje:
        fig.update_yaxes(range=[0, 105], ticksuffix=" %")
    fig.update_layout(hovermode="x unified")
    return fig
