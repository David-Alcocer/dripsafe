"""Piezas de HTML del dashboard: tarjetas de métricas, etiquetas, tablas y barras.

Cada función regresa un texto HTML que main.py y paginas.py muestran con `st.html`.
No importa Streamlit, así que se puede probar sin abrir el dashboard.
Las clases CSS están en app/estilo.css.
"""

import base64
import math
from html import escape
from pathlib import Path
from urllib.parse import quote

# Íconos de línea (estilo Lucide), sin emojis.
# Streamlit borra las etiquetas <svg> del HTML, así que cada ícono es un <span> pintado con
# `currentColor` y recortado con una máscara CSS (ver css_iconos, que main.py inyecta).
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
    "pantalla": '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
    "rayo": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 '
            '.78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "medidor": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
}


def _uri_svg(svg: str) -> str:
    return "data:image/svg+xml;utf8," + quote(svg)


def css_iconos() -> str:
    """Una regla CSS por ícono: la máscara con su dibujo."""
    reglas = []
    for nombre, trazo in _TRAZOS.items():
        uri = _uri_svg(_SVG.format(p=trazo.replace('"', "'")))
        reglas.append(f'.ico-{nombre}{{-webkit-mask-image:url("{uri}");mask-image:url("{uri}")}}')
    return "\n".join(reglas)


def icono(nombre: str, tamano: int = 14) -> str:
    return f'<span class="ico ico-{nombre}" style="width: {tamano}px; height: {tamano}px" aria-hidden="true"></span>'


def numero(valor, decimales: int = 0) -> str:
    """1234567.8 → '1 234 568' (espacio fino entre miles, punto decimal)."""
    if valor is None:
        return "—"
    entero, _, dec = f"{valor:,.{decimales}f}".partition(".")
    entero = entero.replace(",", " ")
    return f"{entero}.{dec}" if dec else entero


def logo_base64(ruta: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode()


# ------------------------------------------------------------ métricas

def chispa(valores) -> str:
    """Mini gráfica de tendencia (sparkline): un SVG dentro de una <img>, en el azul de la serie."""
    v = [x for x in valores if not math.isnan(x)]
    if len(v) < 2:
        return ""
    mn, mx = min(v), max(v)
    rango = (mx - mn) or 1
    puntos = " ".join(
        f"{'L' if i else 'M'}{i / (len(v) - 1) * 200:.1f} {38 - (x - mn) / rango * 36:.1f}" for i, x in enumerate(v)
    )
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 40' preserveAspectRatio='none'>"
           f"<path d='{puntos}' fill='none' stroke='#5794f2' stroke-width='1.6' stroke-linejoin='round'/></svg>")
    return f'<img class="spark" src="{_uri_svg(svg)}" alt="">'


def delta(texto: str) -> str:
    return f'<span class="delta good">{icono("abajo")}{escape(texto)}</span>'


def metrica(etiqueta: str, valor: str, unidad: str = "", contexto: str = "", extra: str = "",
            principal: bool = False) -> str:
    """Tarjeta de métrica: etiqueta discreta, número grande y contexto debajo.

    `valor` y `extra` ya vienen en HTML (para poder resaltar partes del número o poner una chispa).
    """
    clase = "metric hero" if principal else "metric"
    u = f"<small>{escape(unidad)}</small>" if unidad else ""
    c = f'<span class="m-c">{escape(contexto)}</span>' if contexto else ""
    return f'<div class="{clase}"><span class="m-l">{escape(etiqueta)}</span><span class="m-v">{valor}{u}</span>{c}{extra}</div>'


def fila_metricas(tarjetas: list[str], clase: str = "grid4") -> str:
    return f'<div class="{clase}">{"".join(tarjetas)}</div>'


# ------------------------------------------------------------ etiquetas

def chip(tipo: str) -> str:
    """Etiqueta con ícono y texto (el color nunca va solo)."""
    fichas = {
        "posible_ataque": ("atk", "alerta", "Posible ataque"),
        "ineficiencia": ("inef", "medidor", "Ineficiencia"),
        "ataque": ("atk", "alerta", "Ataque"),
        "falla": ("falla", "medidor", "Falla"),
        "si": ("ok", "palomita", "Sí"),
        "no": ("no", "tache", "No"),
    }
    clase, ico, texto = fichas[tipo]
    return f'<span class="chip {clase}">{icono(ico, 12)}{texto}</span>'


def severidad(tipo: str) -> str:
    if tipo == "posible_ataque":
        return '<span class="sev crit">Crítica</span>'
    return '<span class="sev media">Media</span>'


def etiqueta_simulado(simulado: bool) -> str:
    return '<span class="tag-sim">Simulado</span>' if simulado else '<span class="tag-ok">Oficial</span>'


def leyenda(*items: tuple[str, str]) -> str:
    """items = (clase de la muestra, texto). Clases: line, dash, atk, inef."""
    partes = "".join(f'<span><i class="sw {c}"></i>{escape(t)}</span>' for c, t in items)
    return f'<div class="legend">{partes}</div>'


def encabezado(titulo: str, subtitulo: str = "", derecha: str = "", ico: str = "") -> str:
    i = icono(ico, 18) if ico else ""
    sub = f"<p>{subtitulo}</p>" if subtitulo else ""
    return f'<div class="card-h"><div><h3>{i}{escape(titulo)}</h3>{sub}</div>{derecha}</div>'


def aviso(texto_html: str, tipo: str = "info") -> str:
    ico = "ok" if tipo == "ok" else "info"
    return f'<div class="alert {tipo}">{icono(ico, 20)}<div>{texto_html}</div></div>'


# ------------------------------------------------------------ tablas y barras

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
    return f'<div class="tbl-wrap"><table><thead><tr>{th}</tr></thead><tbody>{cuerpo}</tbody></table></div>'


def progreso(pct: float) -> str:
    return (f'<div class="prog"><div class="prog-t"><div class="prog-b" style="width: {pct:.0f}%"></div></div>'
            f"<span>{pct:.0f} %</span></div>")
