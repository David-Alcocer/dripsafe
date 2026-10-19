"""Gráficas de plotly con el estilo de los paneles «Time series» de Grafana.

Una sola escala Y por gráfica. La leyenda va en HTML debajo de la gráfica
(componentes.leyenda), con la media y el máximo como en Grafana.
"""

import plotly.graph_objects as go

COLOR = {
    "serie": "#5794f2",
    "comparar": "#8e8e8e",
    "texto": "rgba(204,204,220,0.65)",
    "rejilla": "rgba(204,204,220,0.08)",
    "eje": "rgba(204,204,220,0.15)",
    "ineficiencia": "#ff9830",
    "posible_ataque": "#f2495c",
}
OPACIDAD_BANDA = {"posible_ataque": 0.22, "ineficiencia": 0.18}
CONFIG = {"displayModeBar": False}  # sin la barra de herramientas de plotly


def _base(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(
        height=alto,
        margin={"l": 4, "r": 8, "t": 4, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": COLOR["texto"], "size": 11},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#22252b", "bordercolor": COLOR["eje"], "font": {"color": "#ccccdc"}},
        showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=COLOR["rejilla"], linecolor=COLOR["eje"], tickformat="%d/%m\n%H:%M",
                     zeroline=False)
    fig.update_yaxes(gridcolor=COLOR["rejilla"], zeroline=False, showline=False, automargin=True)
    return fig


def _anotaciones(fig: go.Figure, eventos) -> None:
    """Regiones de alerta como las anotaciones de Grafana: franja tenue y una marca de color abajo."""
    for _, e in eventos.iterrows():
        tipo = e["tipo_sugerido"]
        if tipo in OPACIDAD_BANDA:
            fig.add_vrect(x0=e["inicio"], x1=e["fin"], fillcolor=COLOR[tipo], opacity=OPACIDAD_BANDA[tipo],
                          line_width=0, layer="below")
            fig.add_shape(type="line", x0=e["inicio"], x1=e["fin"], y0=0, y1=0, yref="paper",
                          line={"color": COLOR[tipo], "width": 4})


def serie(x, y, nombre: str, unidad: str = "", decimales: int = 1, eventos=None, comparar=None,
          nombre_comparar: str = "Esperado", alto: int = 260, desde_cero: bool = False) -> go.Figure:
    """Una variable en el tiempo, opcionalmente con su valor esperado y las regiones de alerta.

    `desde_cero`: el eje Y empieza en 0, para que el ruido normal no parezca un problema (demo).
    """
    fig = go.Figure()
    if eventos is not None and len(eventos):
        _anotaciones(fig, eventos)
    formato = f"%{{y:,.{decimales}f}} {unidad}".strip()
    if comparar is not None:
        fig.add_trace(go.Scatter(x=x, y=comparar, name=nombre_comparar, mode="lines",
                                 line={"color": COLOR["comparar"], "width": 1.5, "dash": "dash"},
                                 hovertemplate=formato))
    fig.add_trace(go.Scatter(x=x, y=y, name=nombre, mode="lines", line={"color": COLOR["serie"], "width": 1.5},
                             hovertemplate=formato))
    fig = _base(fig, alto)
    if desde_cero:
        fig.update_yaxes(rangemode="tozero")
    return fig
