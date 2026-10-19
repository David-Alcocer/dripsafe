"""Dashboard de DripSafe, con la estructura de Grafana.

Correr desde la raíz del repo:
    streamlit run app/main.py

Solo lee los archivos de los contratos (ver app/cargar.py). Si todavía no existen,
usa datos simulados y lo indica en la barra lateral («Simulado» en cada fuente).
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

CARPETA = Path(__file__).parent
st.set_page_config(page_title="DripSafe", page_icon=str(CARPETA / "assets/logo.png"), layout="wide")
st.html(f"<style>{(CARPETA / 'estilo.css').read_text(encoding='utf-8')}\n{c.css_iconos()}</style>")

# clave: (texto en el menú, ícono de Material Symbols; vienen incluidos en Streamlit, funcionan sin internet)
SECCIONES = {
    "resumen": ("Resumen", ":material/dashboard:"),
    "demo": ("Demo de ataque", ":material/play_circle:"),
    "monitoreo": ("Monitoreo", ":material/monitoring:"),
    "ciber": ("Ciberseguridad OT", ":material/verified_user:"),
    "balance": ("Balance neto", ":material/bar_chart:"),
    "agua": ("Agua y acuífero", ":material/water_drop:"),
}
NOMBRE_FUENTE = {"escenarios": "Telemetría", "alertas": "Alertas del modelo", "numeros": "Números oficiales"}


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
        f'<div class="src"><span>{NOMBRE_FUENTE.get(k, k)}</span>{c.etiqueta_simulado(v == "simulado")}</div>'
        for k, v in d.fuentes.items()
    )
    st.html(f'<div class="sep"></div><p class="side-h">Fuentes de datos</p>{filas}'
            f'<p class="side-foot">Cifras del commit <span class="mono">{d.numeros.get("generado_con_commit", "—")}</span></p>')

# ------------------------------------------------------------ barra superior
periodos = {"evaluacion": True, "completo": False}
ini_ev = calculos.periodo(d.tabla, True)["timestamp"].min()
fin = d.tabla["timestamp"].max()
etiquetas = {
    "evaluacion": f"{calculos.fecha(ini_ev, False)} – {calculos.fecha(fin, False)} · evaluación",
    "completo": f"{calculos.fecha(d.tabla['timestamp'].min(), False)} – {calculos.fecha(fin, False)} · completo",
}

migas, tiempo, recargar, presentar = st.columns([6, 3, 0.6, 0.6], gap="small", vertical_alignment="center")
migas.html(c.migas(["Dashboards", "DripSafe", SECCIONES[pagina][0]]))
periodo = tiempo.selectbox("Periodo", list(periodos), format_func=etiquetas.get, key="periodo",
                           label_visibility="collapsed")
if recargar.button("", icon=":material/refresh:", help="Volver a cargar los datos", key="recargar", width="stretch"):
    st.cache_data.clear()
    st.rerun()
if presentar.button("", icon=":material/fullscreen_exit:" if kiosko else ":material/tv:", key="kiosko-btn",
                    help="Salir del modo presentación" if kiosko else "Modo presentación (pantalla completa)",
                    width="stretch"):
    st.session_state.kiosko = not kiosko
    st.rerun()

tabla = calculos.periodo(d.tabla, periodos[periodo])
vista = paginas.Vista(tabla=tabla, eventos=calculos.eventos(tabla), texto=etiquetas[periodo])

# ------------------------------------------------------------ sección elegida
if pagina == "resumen":
    paginas.resumen(d, vista)
elif pagina == "demo":
    paginas.demo(d)
elif pagina == "monitoreo":
    paginas.monitoreo(d, vista)
elif pagina == "ciber":
    paginas.ciberseguridad(d)
elif pagina == "balance":
    paginas.balance(d)
elif pagina == "agua":
    paginas.agua(d, vista)
