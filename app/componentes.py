"""Piezas de HTML con el estilo de los paneles de Grafana: Stat, Gauge, Bar gauge, lista de alertas y tablas.

Cada función regresa un texto HTML que paginas.py muestra con `st.html`.
No importa Streamlit, así que se puede probar sin abrir el dashboard.
Las clases CSS están en app/estilo.css.

Streamlit borra las etiquetas <svg> del HTML. Por eso los íconos son máscaras CSS
y las mini gráficas y el medidor son imágenes SVG (data URI).
"""

import base64
import math
from html import escape
from pathlib import Path
from urllib.parse import quote

from app.textos import CLASES, TIPOS_CIFRA

# Colores de umbral (paleta profesional sobria; mismos valores que app/estilo.css y app/graficas.py).
COLORES = {
    "verde": "#3fa37a", "amarillo": "#a8b3c4", "naranja": "#d39a2c", "rojo": "#d0545f",
    "azul": "#4c8bd6", "gris": "#ccccdc", "morado": "#8a7fc4",
}
# Clase CSS de la etiqueta de procedencia de cada tipo de cifra.
_TAG_TIPO = {"observado": "ok", "medido": "ok", "estimado": "est", "proyectado": "proy", "ejemplo": "sim",
             "vista_previa": "sim", "pendiente": "sim"}

# ------------------------------------------------------------ íconos (estilo Lucide, sin emojis)
_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' "
        "stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'>{p}</svg>")
_TRAZOS = {
    "alerta": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
              '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "abajo": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "palomita": '<path d="M20 6 9 17l-5-5"/>',
    "tache": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "ok": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "medidor": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "campana": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "derecha": '<path d="m9 18 6-6-6-6"/>',
}


def _uri_svg(svg: str) -> str:
    return "data:image/svg+xml;utf8," + quote(svg)


def css_iconos() -> str:
    """Una regla CSS por ícono: la máscara con su dibujo (main.py la inyecta)."""
    reglas = []
    for nombre, trazo in _TRAZOS.items():
        uri = _uri_svg(_SVG.format(p=trazo.replace('"', "'")))
        reglas.append(f'.ico-{nombre}{{-webkit-mask-image:url("{uri}");mask-image:url("{uri}")}}')
    return "\n".join(reglas)


def icono(nombre: str, tamano: int = 14) -> str:
    return f'<span class="ico ico-{nombre}" style="width: {tamano}px; height: {tamano}px" aria-hidden="true"></span>'


# ------------------------------------------------------------ utilidades

def numero(valor, decimales: int = 0) -> str:
    """1234567.8 → '1 234 568' (espacio fino entre miles, punto decimal)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    entero, _, dec = f"{valor:,.{decimales}f}".partition(".")
    entero = entero.replace(",", " ")
    return f"{entero}.{dec}" if dec else entero


def logo_base64(ruta: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


def umbral(valor, pasos: list[tuple[float | None, str]]) -> str:
    """Color según umbrales, como en Grafana: [(None, 'verde'), (1.4, 'naranja'), (1.6, 'rojo')]."""
    color = pasos[0][1]
    for limite, c in pasos[1:]:
        if valor is not None and valor >= limite:
            color = c
    return color


def migas(partes: list[str]) -> str:
    """Ruta de navegación: Inicio › Dashboards › DripSafe › Resumen."""
    sep = icono("derecha", 12)
    previas = "".join(f"<span>{escape(p)}</span>{sep}" for p in partes[:-1])
    return f'<nav class="migas" aria-label="Ruta">{previas}<b>{escape(partes[-1])}</b></nav>'


# ------------------------------------------------------------ paneles

def panel(titulo: str, cuerpo: str, descripcion: str = "", clase: str = "", estilo: str = "") -> str:
    """Panel de Grafana: barra de título pequeña y el contenido debajo."""
    info = (f'<span class="panel-info" title="{escape(descripcion)}">{icono("info", 13)}</span>'
            if descripcion else "")
    st = f' style="{estilo}"' if estilo else ""
    return (f'<section class="panel {clase}"{st}><header class="panel-h"><h3>{escape(titulo)}</h3>{info}</header>'
            f'<div class="panel-b">{cuerpo}</div></section>')


def encabezado_panel(titulo: str, descripcion: str = "") -> str:
    """Solo la barra de título, para paneles que llevan una gráfica de Streamlit debajo."""
    info = (f'<span class="panel-info" title="{escape(descripcion)}">{icono("info", 13)}</span>'
            if descripcion else "")
    return f'<header class="panel-h"><h3>{escape(titulo)}</h3>{info}</header>'


def chispa(valores, color: str = "azul") -> str:
    """Mini gráfica de área (sparkline) al pie de un panel Stat."""
    v = [x for x in valores if not math.isnan(x)]
    if len(v) < 2:
        return ""
    hexa = COLORES.get(color, color)
    mn, mx = min(v), max(v)
    rango = (mx - mn) or 1
    pts = [(i / (len(v) - 1) * 200, 38 - (x - mn) / rango * 34) for i, x in enumerate(v)]
    linea = " ".join(f"{'L' if i else 'M'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 40' preserveAspectRatio='none'>"
           f"<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{hexa}' "
           f"stop-opacity='0.35'/><stop offset='1' stop-color='{hexa}' stop-opacity='0'/></linearGradient></defs>"
           f"<path d='{linea} L200 40 L0 40 Z' fill='url(#g)'/>"
           f"<path d='{linea}' fill='none' stroke='{hexa}' stroke-width='1.4'/></svg>")
    return f'<img class="stat-spark" src="{_uri_svg(svg)}" alt="">'


def stat(titulo: str, valor: str, unidad: str = "", color: str = "azul", sub: str = "", serie=None,
         fondo: bool = False, descripcion: str = "", ancho: bool = False) -> str:
    """Panel Stat: número grande coloreado por umbral y, opcional, la tendencia al pie.

    `fondo=True` pinta todo el panel del color (modo «background» de Grafana) para lo más urgente.
    `ancho=True` ocupa dos columnas de la rejilla (para que la tendencia se lea mejor).
    """
    hexa = COLORES.get(color, color)
    u = f'<span class="stat-u">{escape(unidad)}</span>' if unidad else ""
    s = f'<div class="stat-s">{sub}</div>' if sub else ""
    clase = "stat ancho" if ancho else "stat"
    if fondo:
        estilo = f"background: linear-gradient(120deg, {hexa}, color-mix(in srgb, {hexa} 70%, #000))"
        cuerpo = f'<div class="stat-v" style="color: #fff">{valor}{u}</div>{s}'
        return panel(titulo, cuerpo, descripcion, clase + " fondo", estilo)
    cuerpo = f'<div class="stat-v" style="color: {hexa}">{valor}{u}</div>{s}{chispa(serie, color) if serie is not None else ""}'
    return panel(titulo, cuerpo, descripcion, clase)


def gauge(titulo: str, valor: float, minimo: float, maximo: float, pasos: list[tuple[float | None, str]],
          decimales: int = 2, sub: str = "", descripcion: str = "") -> str:
    """Panel Gauge: arco de 240° con los umbrales en un anillo delgado por fuera."""
    def punto(fr, r):
        ang = math.radians(210 - 240 * fr)  # de 210° (abajo a la izquierda) a -30° (abajo a la derecha)
        return 100 + r * math.cos(ang), 100 - r * math.sin(ang)

    def arco(f0, f1, r, color, grosor):
        f0, f1 = max(0.0, min(1.0, f0)), max(0.0, min(1.0, f1))
        if f1 - f0 < 1e-4:
            return ""
        (x0, y0), (x1, y1) = punto(f0, r), punto(f1, r)
        grande = 1 if (f1 - f0) * 240 > 180 else 0
        return (f"<path d='M{x0:.2f} {y0:.2f} A{r} {r} 0 {grande} 1 {x1:.2f} {y1:.2f}' fill='none' "
                f"stroke='{color}' stroke-width='{grosor}'/>")

    def fr(x):
        """Qué fracción del arco ocupa el valor x (0 = inicio, 1 = final)."""
        return (x - minimo) / (maximo - minimo)

    color = COLORES[umbral(valor, pasos)]
    limites = [minimo] + [p[0] for p in pasos[1:]] + [maximo]
    anillo = "".join(arco(fr(limites[i]), fr(limites[i + 1]) - 0.004, 88, COLORES[pasos[i][1]], 4)
                     for i in range(len(pasos)))
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 160'>"
           f"{anillo}{arco(0, 1, 74, 'rgba(204,204,220,0.10)', 16)}{arco(0, fr(valor), 74, color, 16)}</svg>")
    cuerpo = (f'<div class="gauge"><img src="{_uri_svg(svg)}" alt=""><div class="gauge-v" style="color: {color}">'
              f'{numero(valor, decimales)}</div></div>{f"<div class=stat-s>{sub}</div>" if sub else ""}')
    return panel(titulo, cuerpo, descripcion, "stat")


def barras(filas: list[tuple[str, float, float, str, str]]) -> str:
    """Bar gauge horizontal: (etiqueta, valor, máximo, color, texto del valor)."""
    html = ""
    for etiqueta, valor, maximo, color, texto in filas:
        hexa = COLORES.get(color, color)
        pct = 0 if not maximo else max(0.0, min(100.0, valor / maximo * 100))
        html += (f'<div class="bg-r"><span class="bg-l">{escape(etiqueta)}</span><div class="bg-row">'
                 f'<div class="bg-t"><div class="bg-b" style="width: {pct:.1f}%; background: linear-gradient(90deg, '
                 f'color-mix(in srgb, {hexa} 25%, transparent), {hexa})"></div></div>'
                 f'<span class="bg-v" style="color: {hexa}">{texto}</span></div></div>')
    return f'<div class="bargauge">{html}</div>'


def lista_alertas(items: list[dict]) -> str:
    """Panel «Alert list»: cada item = {clase, titulo, detalle, cuando}."""
    if not items:
        return f'<div class="al-vacia">{icono("ok", 16)} Sin alertas en el periodo</div>'
    filas = ""
    for it in items:
        _, severidad, color, _, _ = CLASES[it["clase"]]
        clase = {"rojo": "crit", "naranja": "media", "amarillo": "baja"}[color]
        ico = "alerta" if color == "rojo" else "medidor"
        filas += (f'<div class="al-i"><span class="al-ico {clase}">{icono(ico, 14)}</span>'
                  f'<div class="al-c"><div class="al-t">{escape(it["titulo"])}</div>'
                  f'<div class="al-d"><span class="al-sev {clase}">{severidad}</span>{escape(it["detalle"])}</div>'
                  f'<div class="al-w">{escape(it["cuando"])}</div></div></div>')
    return f'<div class="alertlist">{filas}</div>'


def leyenda(series: list[tuple[str, str, str]], calculos: list[str] | None = None) -> str:
    """Leyenda de Grafana en modo tabla: (tipo de muestra, nombre, valores ya formateados por cálculo).

    tipo: 'line', 'dash', 'atk', 'inef', o un color '#rrggbb' (línea de ese color, para cada sitio).
    `calculos` son los encabezados, por ejemplo ['Media', 'Máx'].
    """
    def muestra(t: str) -> str:
        if t.startswith("#"):
            return f'<i class="sw line" style="background: {t}"></i>'
        return f'<i class="sw {t}"></i>'

    enc = "".join(f"<th>{c}</th>" for c in (calculos or []))
    filas = "".join(
        f"<tr><td>{muestra(t)}{escape(n)}</td>" + "".join(f"<td>{x}</td>" for x in vals) + "</tr>"
        for t, n, vals in series
    )
    return f'<table class="legend"><thead><tr><th></th>{enc}</tr></thead><tbody>{filas}</tbody></table>'


# ------------------------------------------------------------ texto, etiquetas y tablas

def chip(tipo: str) -> str:
    """Etiqueta con ícono y texto (el color nunca va solo). `tipo` puede ser una clase de alerta."""
    if tipo in CLASES:
        nombre, _, color, _, _ = CLASES[tipo]
        clase = {"rojo": "atk", "naranja": "inef", "amarillo": "baja"}[color]
        return f'<span class="chip {clase}">{icono("alerta" if color == "rojo" else "medidor", 12)}{escape(nombre)}</span>'
    fichas = {
        "si": ("ok", "palomita", "Sí"),
        "no": ("no", "tache", "No"),
    }
    clase, ico, texto = fichas[tipo]
    return f'<span class="chip {clase}">{icono(ico, 12)}{texto}</span>'


def celda_severidad(clase_alerta: str) -> str:
    """Celda con fondo de color (modo «color background» de las tablas de Grafana)."""
    _, severidad, color, _, _ = CLASES[clase_alerta]
    css = {"rojo": "crit", "naranja": "media", "amarillo": "baja"}[color]
    return f'<span class="cell-bg {css}">{severidad}</span>'


def etiqueta(texto: str, tipo: str = "sim") -> str:
    """Etiqueta pequeña: 'sim' (amarilla, ejemplo o provisional), 'ok' (verde), 'est' (azul) o 'proy' (morada)."""
    return f'<span class="tag-{tipo}">{escape(texto)}</span>'


def procedencia(tipo: str) -> str:
    """Etiqueta de qué tan firme es una cifra: observado, medido, estimado, proyectado o ejemplo."""
    texto, explicacion = TIPOS_CIFRA[tipo]
    return f'<span class="tag-{_TAG_TIPO[tipo]}" title="{escape(explicacion)}">{texto}</span>'


def etiqueta_simulado(simulado: bool) -> str:
    return etiqueta("Simulado") if simulado else etiqueta("Oficial", "ok")


def sello_simulado() -> str:
    """Sello «DATOS SIMULADOS» de la barra superior: la guía del kit pide tenerlo siempre visible."""
    return (f'<span class="sello-sim" title="Datos simulados del kit CIFOX: no son mediciones reales">'
            f'{icono("info", 11)}DATOS SIMULADOS</span>')


def aviso_fuerte(texto_html: str) -> str:
    """Aviso que no se puede pasar por alto (por ejemplo, datos que no son del kit)."""
    return f'<div class="alert fuerte" role="alert">{icono("alerta", 18)}<div>{texto_html}</div></div>'


def aviso(texto_html: str, tipo: str = "info") -> str:
    ico = "ok" if tipo == "ok" else "info"
    return f'<div class="alert {tipo}">{icono(ico, 18)}<div>{texto_html}</div></div>'


def tabla(columnas: list[str], filas: list[list[str]], numericas: tuple[int, ...] = (),
          resaltar: tuple[int, ...] = ()) -> str:
    """Tabla HTML. Las celdas ya vienen en HTML.

    `numericas`: índices de columna alineados a la derecha. `resaltar`: índices de fila con fondo de acento.
    """
    th = "".join(f'<th class="num">{c}</th>' if i in numericas else f"<th>{c}</th>" for i, c in enumerate(columnas))
    cuerpo = "".join(
        ('<tr class="rec">' if n in resaltar else "<tr>")
        + "".join(f'<td class="num">{v}</td>' if i in numericas else f"<td>{v}</td>" for i, v in enumerate(f))
        + "</tr>"
        for n, f in enumerate(filas)
    )
    return f'<div class="tbl-wrap"><table class="tabla"><thead><tr>{th}</tr></thead><tbody>{cuerpo}</tbody></table></div>'
