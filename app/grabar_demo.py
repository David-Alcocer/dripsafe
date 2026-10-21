"""Graba el video de respaldo de la demo (#20) recorriendo el dashboard como en el pitch.

Uso (con el dashboard corriendo en otra terminal: streamlit run app/main.py):
    pip install playwright && playwright install chromium     # una sola vez
    python app/grabar_demo.py --salida ~/hackathon/video-respaldo

El video muestra los datos del kit: se guarda FUERA del repo y nunca se sube a GitHub.
Sigue el recorrido de docs/08-pitch.md en modo presentación, a 1920×1080, con pausas para
narrar encima.

No graba mientras resultados/numeros_oficiales.json no exista o siga siendo el borrador con valores de
ejemplo: un video de respaldo con cifras de ejemplo podría pasar por resultados. Para un borrador de prueba, usar --borrador (el archivo
queda marcado como BORRADOR). El video final se graba después del congelamiento del 21 a las 20:00.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

NUMEROS_OFICIALES = Path(__file__).resolve().parent.parent / "resultados" / "numeros_oficiales.json"


def hay_cifras_oficiales(ruta: Path = NUMEROS_OFICIALES) -> bool:
    """El JSON existe y no es el borrador con valores de ejemplo (misma regla que app/cargar.py)."""
    if not ruta.exists():
        return False
    meta = json.loads(ruta.read_text(encoding="utf-8")).get("_meta", {})
    return not (meta.get("generado_con_commit") == "ejemplo-sin-commit"
                or "VALORES DE EJEMPLO" in meta.get("aviso", "").upper())

# (qué hacer, segundos de pausa para narrar)
RECORRIDO = [
    ("Resumen", 12),
    ("Demo de ataque", 6),
    ("paso:2 · Real vs esperado", 8),
    ("paso:3 · Clase", 9),
    ("paso:4 · Acción", 8),
    ("escenario:Ineficiencia energética", 4),
    ("paso:2 · Real vs esperado", 6),
    ("paso:3 · Clase", 8),
    ("paso:4 · Acción", 6),
    ("Evaluación", 12),
    ("Balance neto", 12),
    ("Agua y acuífero", 10),
]


def grabar(url: str, salida: Path, nombre: str = "dripsafe-demo.webm") -> Path:
    salida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chromium")
        contexto = navegador.new_context(viewport={"width": 1920, "height": 1080},
                                         record_video_dir=str(salida), record_video_size={"width": 1920, "height": 1080})
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="networkidle")
        pagina.wait_for_selector(".rejilla", timeout=60_000)
        menu = {}
        for texto in ["Resumen", "Demo de ataque", "Evaluación", "Balance neto", "Agua y acuífero"]:
            menu[texto] = pagina.get_by_role("button", name=texto)

        def ir(texto: str) -> None:
            menu[texto].click()
            pagina.wait_for_timeout(1500)

        # Primero se navega con la barra lateral; el modo presentación la oculta, así que se activa
        # después de cada cambio de sección y se desactiva antes del siguiente.
        for accion, pausa in RECORRIDO:
            if accion.startswith("paso:"):
                pagina.get_by_text(accion.removeprefix("paso:"), exact=True).click()
            elif accion.startswith("escenario:"):
                pagina.locator(".st-key-demo_sel").click()  # el selector «Escenario» de la demo
                pagina.get_by_role("option").filter(has_text=accion.removeprefix("escenario:")).first.click()
            else:
                presentacion = pagina.locator(".st-key-kiosko-btn button").first  # el botón de pantalla, arriba a la derecha
                if pagina.locator("[data-testid='stSidebar']").is_hidden():
                    presentacion.click()
                    pagina.wait_for_timeout(1000)
                ir(accion)
                presentacion.click()
            pagina.mouse.move(960, 1070)  # el puntero fuera de los botones, para que no salgan sus ayudas
            pagina.wait_for_timeout(pausa * 1000)

        video = pagina.video.path()
        contexto.close()
        navegador.close()
    final = salida / nombre
    Path(video).replace(final)
    return final


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Graba el video de respaldo de la demo.")
    p.add_argument("--url", default="http://127.0.0.1:8501")
    p.add_argument("--salida", type=Path, default=Path.home() / "hackathon" / "video-respaldo")
    p.add_argument("--borrador", action="store_true", help="grabar aunque las cifras sean de ejemplo (queda marcado)")
    a = p.parse_args()
    oficiales = hay_cifras_oficiales()
    if not oficiales and not a.borrador:
        raise SystemExit("resultados/numeros_oficiales.json todavía es el borrador con valores de ejemplo: el video "
                         "mostraría cifras de ejemplo. Usa --borrador para una prueba.")
    nombre = "dripsafe-demo.webm" if oficiales else "dripsafe-demo-BORRADOR-cifras-ejemplo.webm"
    print(f"Video: {grabar(a.url, a.salida.expanduser(), nombre)}")
