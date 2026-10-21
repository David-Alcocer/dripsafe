"""Pruebas de pantalla del dashboard con AppTest (sin navegador), como las del kit CIFOX.

Siempre usan los datos de ejemplo de app/kit.py, nunca el CSV del kit. Si Streamlit no está
instalado (por ejemplo en el CI), se saltan.
"""

from pathlib import Path

import pytest

st = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from app import calculos, cargar, kit, linea_base  # noqa: E402
from app import componentes as c  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app" / "main.py")
SECCIONES = ["resumen", "demo", "monitoreo", "evaluacion", "ciber", "balance", "agua", "datos"]

# En Streamlit < 1.60 (la 1.51 del kit), AppTest falla al leer el estado de `segmented_control`
# (error de la herramienta de pruebas, no del dashboard). Esas pruebas se revisaron a mano en el navegador.
_version = tuple(int(x) for x in st.__version__.split(".")[:2])
apptest_con_grupos = pytest.mark.skipif(_version < (1, 60), reason="AppTest de Streamlit < 1.60 no lee segmented_control")


@pytest.fixture
def at(monkeypatch, tmp_path):
    monkeypatch.setenv("DRIPSAFE_KIT", str(tmp_path))  # sin kit: datos de ejemplo
    st.cache_data.clear()
    return AppTest.from_file(APP, default_timeout=60).run()


@pytest.fixture
def ejemplo():
    datos = kit.ejemplo()
    return cargar.unir(datos, linea_base.detectar(datos))


def html(at) -> str:
    return " ".join(e.proto.body for e in at.get("html"))


def ir(at, **estado):
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    return at.run()


def test_arranca_con_sello_y_aviso_de_datos_de_ejemplo(at):
    assert not at.exception
    texto = html(at)
    assert "DATOS SIMULADOS" in texto
    assert "No se encontró el kit CIFOX" in texto
    assert len(at.get("file_uploader")) == 0  # solo lee el CSV local, no recibe archivos


def test_cifras_de_ejemplo_siempre_avisadas(at):
    """Sin numeros_oficiales.json, cada cifra ficticia lleva la etiqueta «Ejemplo» y hay un aviso."""
    for pagina in ["resumen", "balance", "agua"]:
        ir(at, pagina=pagina)
        texto = html(at)
        assert "Cifras de ejemplo." in texto, pagina
        assert ">Ejemplo<" in texto, pagina


def test_procedencia_y_clases_visibles(at):
    texto = html(at)
    assert ">Ejemplo<" in texto
    assert ">Observado<" not in texto
    ir(at, pagina="ciber")
    texto = html(at)
    for nombre in ["Incidente OT con efecto", "Cambio no autorizado", "Escalón sin registro", "Intento de acceso"]:
        assert nombre in texto


def test_evaluacion_muestra_curva_y_empate(at):
    ir(at, pagina="evaluacion")
    texto = html(at)
    assert "Ejemplo ficticio." in texto
    assert "Detalle de la curva" in texto
    assert len(at.get("plotly_chart")) >= 2


@apptest_con_grupos
def test_todas_las_secciones_cargan(at):
    for pagina in SECCIONES:
        ir(at, pagina=pagina)
        assert not at.exception, pagina


def test_pue_del_panel_es_cociente_de_sumas(at, ejemplo):
    esperado = calculos.metricas(ejemplo[ejemplo["split"] == "evaluacion"])["pue"]
    assert c.numero(esperado, 3) in html(at)


@pytest.mark.parametrize("sitio", ["SIM-A", "SIM-B", "SIM-C"])
def test_filtro_por_sitio(at, ejemplo, sitio):
    ir(at, sitio=sitio)
    sel = ejemplo[(ejemplo["site_id"] == sitio) & (ejemplo["split"] == "evaluacion")]
    assert not at.exception
    assert c.numero(calculos.metricas(sel)["pue"], 3) in html(at)


def test_un_solo_dia_incluye_las_24_horas(at, ejemplo):
    dia = sorted(ejemplo["timestamp"].dt.date.unique())[3]
    ir(at, periodo=f"dia:{dia}")
    sel = ejemplo[ejemplo["timestamp"].dt.date == dia]
    assert sel["timestamp"].dt.hour.nunique() == 24
    assert not at.exception
    assert c.numero(calculos.metricas(sel)["pue"], 3) in html(at)


@apptest_con_grupos
def test_tabla_de_valores_con_y_sin_alertas(at, ejemplo):
    ev = ejemplo[ejemplo["split"] == "evaluacion"]
    ir(at, pagina="monitoreo")
    assert f'Registros ({int(ev["alerta"].sum())} de {len(ev)})' in html(at)
    at.checkbox(key="solo_alertas").uncheck().run()
    assert f"Registros ({len(ev)} de {len(ev)})" in html(at)
    assert "Comprobación con sumas" in html(at)


@apptest_con_grupos
def test_demo_recorre_los_tres_escenarios(at):
    ir(at, pagina="demo")
    for escenario in ["evento_ot", "fuga_agua", "ineficiencia"]:
        for paso in range(4):
            ir(at, demo_sel=escenario, paso=paso)
            assert not at.exception, (escenario, paso)
    assert "DripSafe solo avisa" in html(at)


def test_modo_presentacion(at):
    ir(at, kiosko=True)
    assert not at.exception
