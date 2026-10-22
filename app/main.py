"""Dashboard de DripSafe, con la estructura de Grafana, sobre el kit CIFOX.

Correr desde la raíz del repo:
    streamlit run app/main.py

Lee el CSV del kit desde fuera del repo (app/kit.py; nunca se sube a GitHub). Si no lo
encuentra, usa datos de ejemplo con el mismo formato y lo indica arriba. La barra lateral
dice de dónde sale cada cosa: telemetría, detector (del equipo o vista previa) y cifras.
Las secciones están en app/paginas.py y los paneles en app/componentes.py.
"""

import sys
from pathlib import Path

# `streamlit run app/main.py` solo agrega app/ a la ruta de búsqueda; agregamos la raíz
# para poder importar `src` y `app` igual que en las pruebas.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from app import calculos, paginas
from app import componentes as c
from app.cargar import cargar
from app.textos import SITIOS

CARPETA = Path(__file__).parent
st.set_page_config(page_title="DripSafe", page_icon=str(CARPETA / "assets/logo.png"), layout="wide")
st.html(f"<style>{(CARPETA / 'estilo.css').read_text(encoding='utf-8')}\n{c.css_iconos()}</style>")

# clave: (texto en el menú, ícono de Material Symbols; vienen incluidos en Streamlit, funcionan sin internet)
SECCIONES = {
    "resumen": ("Resumen", ":material/dashboard:"),
    "demo": ("Demo de ataque", ":material/play_circle:"),
    "monitoreo": ("Monitoreo", ":material/monitoring:"),
    "evaluacion": ("Evaluación", ":material/fact_check:"),
    "ciber": ("Ciberseguridad OT", ":material/verified_user:"),
    "balance": ("Balance neto", ":material/bar_chart:"),
    "agua": ("Agua y acuífero", ":material/water_drop:"),
    "datos": ("Datos y supuestos", ":material/description:"),
}
FUENTES = {
    "telemetria": ("Telemetría", {"kit": ("Kit CIFOX", "sim"), "ejemplo": ("Ejemplo", "sim")}),
    "detector": ("Detector", {"vista_previa": ("Vista previa", "sim"), "modelo": ("Del equipo", "ok")}),
    "numeros": ("Cifras", {"pendiente": ("Pendiente", "sim"), "oficial": ("Oficial", "ok")}),
}
PERIODOS = {"evaluacion": "evaluación", "completo": "completo", "referencia": "referencia"}


@st.cache_data(show_spinner="Cargando datos…")
def datos_en_cache():
    return cargar()


d = datos_en_cache()
logo = c.logo_base64(CARPETA / "assets/logo.png")
pagina = st.session_state.setdefault("pagina", "resumen")
kiosko = st.session_state.setdefault("kiosko", False)

# Modo presentación (como el modo kiosko de Grafana): sin barra lateral ni encabezado de Streamlit.
if kiosko:
    st.html("<style>section[data-testid='stSidebar'], header[data-testid='stHeader'], "
            "[data-testid='stSidebarCollapsedControl'] { display: none !important; }"
            ".block-container { padding-top: 1.5rem; }</style>")

# ------------------------------------------------------------ barra lateral
with st.sidebar:
    st.html(f'<div class="brand"><img src="{logo}" width="32" height="32" alt=""><span>DripSafe</span></div>'
            '<p class="side-h">Dashboards</p>')
    for clave, (texto, icono) in SECCIONES.items():
        if st.button(texto, icon=icono, key=f"nav-{clave}", width="stretch",
                     type="primary" if clave == pagina else "tertiary"):
            paginas.ir(clave)

    filas = "".join(
        f'<div class="src"><span>{nombre}</span>{c.etiqueta(*estados.get(d.fuentes.get(k), ("—", "sim")))}</div>'
        for k, (nombre, estados) in FUENTES.items()
    )
    st.html(f'<div class="sep"></div><p class="side-h">Fuentes de datos</p>{filas}'
            '<p class="side-foot">Los datos del kit se leen fuera del repo y nunca se suben a GitHub.</p>')

# ------------------------------------------------------------ barra superior
t = d.tabla
etiquetas = {
    p: f"{calculos.fecha(s['timestamp'].min(), False)} – {calculos.fecha(s['timestamp'].max(), False)} · {texto}"
    for p, texto in PERIODOS.items()
    for s in [t if p == "completo" else t[t["split"] == p]]
}
# Además, cada día por separado (UTC, las 24 horas completas), como el filtro de fechas del kit.
for dia in sorted(t["timestamp"].dt.date.unique()):
    etiquetas[f"dia:{dia}"] = f"{calculos.fecha(dia, False)} · un día (UTC)"

# La ruta y el sello «DATOS SIMULADOS» comparten columna: así el sello nunca choca con los selectores.
migas, sitio_col, tiempo, recargar, presentar = st.columns(
    [3.4, 2.0, 2.6, 0.55, 0.55], gap="small", vertical_alignment="center")
migas.html(f'<div class="barra-izq">{c.migas(["DripSafe", SECCIONES[pagina][0]])}{c.sello_simulado()}</div>')
sitio = sitio_col.selectbox("Sitio", ["Todos", *sorted(t["site_id"].unique())], key="sitio",
                            format_func=lambda s: "Todos los sitios" if s == "Todos" else SITIOS.get(s, s),
                            label_visibility="collapsed")
periodo = tiempo.selectbox("Periodo", list(etiquetas), format_func=etiquetas.get, key="periodo",
                           label_visibility="collapsed")
if recargar.button("", icon=":material/refresh:", help="Volver a cargar los datos", key="recargar", width="stretch"):
    st.cache_data.clear()
    st.rerun()
if presentar.button("", icon=":material/fullscreen_exit:" if kiosko else ":material/tv:", key="kiosko-btn",
                    help="Salir del modo presentación" if kiosko else "Modo presentación (pantalla completa)",
                    width="stretch"):
    st.session_state.kiosko = not kiosko
    st.rerun()

tabla_sitio = t if sitio == "Todos" else t[t["site_id"] == sitio]
if periodo == "completo":
    tabla = tabla_sitio
elif periodo.startswith("dia:"):
    tabla = tabla_sitio[tabla_sitio["timestamp"].dt.date.astype(str) == periodo.removeprefix("dia:")]
else:
    tabla = tabla_sitio[tabla_sitio["split"] == periodo]
vista = paginas.Vista(tabla=tabla, tabla_sitio=tabla_sitio, eventos=calculos.eventos(tabla), texto=etiquetas[periodo])

# Si el kit no está en esta laptop, que nadie confunda los datos de ejemplo con los del kit.
if d.fuentes.get("telemetria") != "kit":
    st.html(c.aviso_fuerte(
        "<b>No se encontró el kit CIFOX en esta laptop.</b> Las gráficas y métricas calculadas desde la "
        "telemetría usan <b>datos de ejemplo inventados</b>. Las cifras consolidadas salen de "
        "<span class='mono'>resultados/numeros_oficiales.json</span> y corresponden al kit fijado; "
        "no se deben comparar con esas gráficas. Copia el kit a "
        "<span class='mono'>~/hackathon/Kit Stack Tecnológico/</span> "
        "o define la variable <span class='mono'>DRIPSAFE_KIT</span> con su carpeta (ver app/README.md)."))
for texto in d.avisos:
    st.html(c.aviso_fuerte(texto))
if tabla.empty:
    st.html(c.aviso("No hay datos para este sitio y periodo. Elige otro filtro arriba."))
    st.stop()

# ------------------------------------------------------------ sección elegida
if pagina == "resumen":
    paginas.resumen(d, vista)
elif pagina == "demo":
    paginas.demo(d)
elif pagina == "monitoreo":
    paginas.monitoreo(d, vista)
elif pagina == "evaluacion":
    paginas.evaluacion(d)
elif pagina == "ciber":
    paginas.ciberseguridad(d, vista)
elif pagina == "balance":
    paginas.balance(d, vista)
elif pagina == "agua":
    paginas.agua(d, vista)
elif pagina == "datos":
    paginas.datos(d)
