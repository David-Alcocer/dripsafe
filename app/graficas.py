"""Gráficas de plotly del dashboard. Cada función recibe datos y regresa una figura.

Colores: paleta Grafana (azul para la serie, gris para lo esperado)
y colores de estado reservados para las alertas. Una sola escala Y por gráfica.
Las leyendas van en HTML en el encabezado de cada tarjeta (ver componentes.leyenda).
"""

import plotly.graph_objects as go

COLOR = {
    "serie": "#5794f2",
    "comparar": "#898781",
    "texto": "#9fa1a8",
    "rejilla": "#262a30",
    "eje": "#34383e",
    "normal": "#73bf69",
    "ineficiencia": "#ff9830",
    "posible_ataque": "#f2495c",
}
OPACIDAD_BANDA = {"posible_ataque": 0.30, "ineficiencia": 0.26}
CONFIG = {"displayModeBar": False}  # sin la barra de herramientas de plotly


def _base(fig: go.Figure, alto: int) -> go.Figure:
    fig.update_layout(
        height=alto,
        margin={"l": 4, "r": 8, "t": 8, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": COLOR["texto"], "size": 12},
        hovermode="x unified",
        hoverlabel={"bgcolor": "#22252b", "bordercolor": COLOR["eje"], "font": {"color": "#f0efec"}},
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, linecolor=COLOR["eje"], tickcolor=COLOR["eje"], tickformat="%d %b\n%H:%M")
    fig.update_yaxes(gridcolor=COLOR["rejilla"], zeroline=False, showline=False, automargin=True)
    return fig


def _bandas(fig: go.Figure, eventos) -> None:
    """Franjas de color detrás de la serie: naranja = ineficiencia, rojo = posible ataque."""
    for _, e in eventos.iterrows():
        tipo = e["tipo_sugerido"]
        if tipo in OPACIDAD_BANDA:
            fig.add_vrect(x0=e["inicio"], x1=e["fin"], fillcolor=COLOR[tipo], opacity=OPACIDAD_BANDA[tipo],
                          line_width=0, layer="below")


def serie(x, y, nombre: str, unidad: str = "", decimales: int = 1, eventos=None, comparar=None,
          nombre_comparar: str = "Esperado", alto: int = 280, desde_cero: bool = False) -> go.Figure:
    """Una variable en el tiempo, opcionalmente con su valor esperado y las franjas de alerta.

    `desde_cero`: el eje Y empieza en 0, para que el ruido normal no parezca un problema (demo).
    """
    fig = go.Figure()
    if eventos is not None and len(eventos):
        _bandas(fig, eventos)
    formato = f"%{{y:,.{decimales}f}} {unidad}".strip()
    if comparar is not None:
        fig.add_trace(go.Scatter(x=x, y=comparar, name=nombre_comparar, mode="lines",
                                 line={"color": COLOR["comparar"], "width": 2, "dash": "dot"},
                                 hovertemplate=formato))
    fig.add_trace(go.Scatter(x=x, y=y, name=nombre, mode="lines", line={"color": COLOR["serie"], "width": 2},
                             hovertemplate=formato))
    fig = _base(fig, alto)
    if desde_cero:
        fig.update_yaxes(rangemode="tozero")
    return fig
