"""Dashboard de DripSafe.

Correr desde la raíz del repo:
    streamlit run app/main.py

Solo lee los archivos de los contratos (ver app/cargar.py). Si todavía no existen,
usa datos simulados y lo indica en la barra lateral («Simulado» en cada fuente).
Las secciones están en app/paginas.py y las piezas de HTML en app/componentes.py.
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

# ------------------------------------------------------------ barra lateral
with st.sidebar:
    st.html(f'<div class="brand"><img src="{logo}" width="40" height="40" alt=""><span>DripSafe</span></div>')
    for clave, (texto, icono) in SECCIONES.items():
        if st.button(texto, icon=icono, key=f"nav-{clave}", width="stretch",
                     type="primary" if clave == pagina else "tertiary"):
            paginas.ir(clave)

    st.html('<div class="sep"></div>')
    periodo = st.radio("Periodo", ["Semana de evaluación", "Dos semanas completas"], key="periodo")

    filas = "".join(
        f'<div class="src"><span>{NOMBRE_FUENTE.get(k, k)}</span>{c.etiqueta_simulado(v == "simulado")}</div>'
        for k, v in d.fuentes.items()
    )
    st.html(f'<div class="sep"></div><p class="side-h">Fuentes de datos</p>{filas}'
            f'<p class="side-foot">Cifras generadas con el commit '
            f'<span class="mono">{d.numeros.get("generado_con_commit", "—")}</span></p>')
    if st.button("Volver a cargar los datos", icon=":material/refresh:", type="tertiary"):
        st.cache_data.clear()
        st.rerun()

# ------------------------------------------------------------ periodo elegido
solo_evaluacion = periodo == "Semana de evaluación"
tabla = calculos.periodo(d.tabla, solo_evaluacion)
ini, fin = tabla["timestamp"].min(), tabla["timestamp"].max()
nombre_periodo = "Semana de evaluación" if solo_evaluacion else "Dos semanas"
vista = paginas.Vista(
    tabla=tabla,
    eventos=calculos.eventos(tabla),
    texto=f"{nombre_periodo} · {calculos.fecha(ini, False)} al {calculos.fecha(fin, False)} {fin.year}",
)

# ------------------------------------------------------------ encabezado y barra de estado
st.html(
    f'<div class="title"><div class="title-row"><img class="logo-lg" src="{logo}" width="64" height="64" '
    'alt="Logo de DripSafe: un rack de servidores con una gota de agua dentro de un anillo"><h1>DripSafe</h1></div>'
    "<p>Un vigilante para el enfriamiento del centro de datos: ahorra agua y energía, y detecta manipulaciones "
    "de sensores y PLCs.</p></div>"
)
minutos = round(d.tabla["timestamp"].diff().median().total_seconds() / 60)
n_ataques = int((vista.eventos["tipo_sugerido"] == "posible_ataque").sum())
n_inef = int((vista.eventos["tipo_sugerido"] == "ineficiencia").sum())
st.html(
    '<div class="statusbar">'
    f'<span class="sb-i"><span class="sb-k">Última lectura</span>{calculos.fecha(d.tabla["timestamp"].max())}</span>'
    f'<span class="sb-i"><span class="sb-k">Intervalo</span>{minutos} min</span>'
    f'<span class="sb-i"><span class="sb-k">Carga de TI</span>{c.numero(d.tabla["kw_ti"].mean())} kW promedio · Mérida</span>'
    f'<span class="sb-i sb-alert"><span class="sev-dot atk"></span>{n_ataques} posibles ataques</span>'
    f'<span class="sb-i"><span class="sev-dot inef"></span>{n_inef} ineficiencias</span>'
    "</div>"
)

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
