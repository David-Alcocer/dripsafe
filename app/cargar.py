"""Junta todo lo que muestra el dashboard: telemetría del kit, detector y cifras.

Fuentes, de la más oficial a la de respaldo:
- Telemetría: el CSV del kit CIFOX, leído FUERA del repo (app/kit.py). Si no está en la
  laptop (por ejemplo en el CI), se usan datos de ejemplo inventados con el mismo formato.
- Detector: data/resultados/alertas.csv (Gadiel construye, Guille clasifica), con las columnas
  de app/linea_base.COLUMNAS. Mientras no exista, la vista previa de app/linea_base.py.
- Cifras: app/ejemplos/numeros_ejemplo.json es la vista oficial plana generada
  desde resultados/numeros_oficiales.json. Sin kit, numeros_demo.json es ficticio.

El dashboard no inventa cifras oficiales: solo las muestra y dice de dónde salió cada una.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app import calculos, kit, linea_base

RAIZ = Path(__file__).resolve().parent.parent
RUTAS = {
    "alertas": RAIZ / "data/resultados/alertas.csv",
    "consumo": RAIZ / "data/resultados/consumo_modelo.json",
    "numeros": RAIZ / "resultados/numeros_oficiales.json",
    "leo": Path(__file__).resolve().parent / "ejemplos/numeros_ejemplo.json",
    "ejemplo": Path(__file__).resolve().parent / "ejemplos/numeros_demo.json",
}


@dataclass
class Datos:
    tabla: pd.DataFrame      # una fila por sitio y hora: telemetría + reglas del kit + detector
    eventos: pd.DataFrame    # alertas de DripSafe agrupadas en eventos por sitio
    evaluacion: dict         # {"dripsafe": (por escenario, resumen), "reglas": (…)}
    numeros: dict            # contrato 4 (oficial) o el ejemplo ficticio
    benchmarks: dict         # corridas de ejemplo del kit: reglas e Isolation Forest
    fuentes: dict = field(default_factory=dict)
    consumo: dict = field(default_factory=dict)   # contrato 3: consumo_modelo.json (CodeCarbon), si existe
    avisos: list = field(default_factory=list)    # problemas de formato que el dashboard debe mostrar

    @property
    def cifras_de_ejemplo(self) -> bool:
        return self.fuentes.get("numeros") != "oficial"


def _detector_oficial(avisos: list) -> pd.DataFrame | None:
    """La salida del detector del equipo, si ya existe y trae las columnas que la app necesita.

    Si el archivo existe pero tiene otro formato (por ejemplo, el contrato 3 anterior, sin
    site_id ni esperado), la app NO lo ignora en silencio: agrega un aviso visible y usa la vista previa.
    """
    if not RUTAS["alertas"].exists():
        return None
    al = pd.read_csv(RUTAS["alertas"])
    faltan = sorted(set(linea_base.COLUMNAS) - {"motivo"} - set(al.columns))
    if faltan:
        avisos.append(f"data/resultados/alertas.csv existe pero no trae las columnas que la app necesita "
                      f"({', '.join(faltan)}). Se usa la vista previa hasta acordar el contrato 3 (ver app/ejemplos/README.md).")
        return None
    al["timestamp"] = pd.to_datetime(al["timestamp"], utc=True)
    if "motivo" not in al.columns:
        al["motivo"] = ""
    al["motivo"] = al["motivo"].fillna("")
    # La acción sugerida la decide src/ot/clases.py (Guille); es opcional para no romper salidas viejas.
    al["accion"] = al["accion"].fillna("") if "accion" in al.columns else ""
    return al[linea_base.COLUMNAS + ["accion"]]


def unir(datos: pd.DataFrame, detector: pd.DataFrame) -> pd.DataFrame:
    """Telemetría + reglas del kit (para comparar) + salida del detector, con el exceso de cada hora."""
    t = kit.reglas(datos).rename(columns={"alerta": "alerta_reglas", "motivo": "motivo_reglas"})
    t = t.drop(columns="tipo_sugerido").merge(detector, on=["timestamp", "site_id"], how="left")
    t["clase"] = t["clase"].fillna("normal")
    t["motivo"] = t["motivo"].fillna("")
    t["accion"] = t["accion"].fillna("") if "accion" in t.columns else ""
    t["alerta"] = t["clase"] != "normal"
    t["energia_no_ti_kwh"] = t["energy_total_kwh"] - t["energy_it_kwh"]
    fisica = t["alerta_umbral"].fillna(False).astype(bool) | t["alerta_media_4h"].fillna(False).astype(bool)
    t["exceso_kwh"] = (t["energia_no_ti_kwh"] - t["esperado_energia_no_ti_kwh"]).clip(lower=0).where(fisica, 0.0)
    t["exceso_l"] = (t["water_l"] - t["esperado_agua_l"]).clip(lower=0).where(fisica, 0.0)
    t["clima_no_visto"] = t["clima_no_visto"].fillna(False).astype(bool)
    return t


def cargar() -> Datos:
    fuentes = {}
    if kit.disponible():
        datos, fuentes["telemetria"] = kit.leer(), "kit"
    else:
        datos, fuentes["telemetria"] = kit.ejemplo(), "ejemplo"

    # Las salidas del equipo se calculan con el kit: con datos de ejemplo no se mezclan (no cuadrarían).
    del_kit = fuentes["telemetria"] == "kit"
    avisos = []
    detector = _detector_oficial(avisos) if del_kit else None
    if detector is not None and del_kit:
        fuentes["detector"] = "modelo"
    else:
        detector, fuentes["detector"] = linea_base.detectar(datos), "vista_previa"
    tabla = unir(datos, detector)

    if del_kit and RUTAS["leo"].exists() and RUTAS["numeros"].exists():
        numeros = json.loads(RUTAS["leo"].read_text(encoding="utf-8"))
        canonico = json.loads(RUTAS["numeros"].read_text(encoding="utf-8"))
        from src.metricas.generar_numeros import plano
        if numeros.get("_ejemplo") is not False or numeros != plano(canonico):
            # El canónico manda. Si alguien regeneró solo uno de los dos, la demo no se cae: se usa la vista
            # calculada del canónico y se avisa en pantalla para correr `python -m src.pipeline` otra vez.
            numeros = plano(canonico)
            avisos.append("app/ejemplos/numeros_ejemplo.json no coincide con resultados/numeros_oficiales.json: "
                          "se muestran las cifras del canónico. Corre python -m src.pipeline para regenerar los dos.")
        fuentes["numeros"] = "oficial"
    else:
        numeros, fuentes["numeros"] = json.loads(RUTAS["ejemplo"].read_text(encoding="utf-8")), "ejemplo"

    evaluacion = {"dripsafe": calculos.evaluacion(tabla, "alerta"),
                  "reglas": calculos.evaluacion(tabla, "alerta_reglas")}
    consumo = {}
    if RUTAS["consumo"].exists() and del_kit:
        consumo = json.loads(RUTAS["consumo"].read_text(encoding="utf-8"))
    return Datos(tabla, calculos.eventos(tabla), evaluacion, numeros, kit.benchmarks(), fuentes, consumo, avisos)


METODOS = {"dripsafe": "DripSafe", "reglas_kit": "Reglas del kit"}


def _ruta(dato, *claves):
    """dato[c1][c2]…, o None si falta algún nivel."""
    for clave in claves:
        dato = dato.get(clave) if isinstance(dato, dict) else None
    return dato


def _nombre_inyeccion(nombre: str) -> str:
    """'energia_+20' → 'Energía +20 %'; 'cambio_sin_registro' → 'Cambio sin registro'."""
    if "_+" in nombre:
        variable, magnitud = nombre.split("_+")
        return f'{"Energía" if variable == "energia" else "Agua"} +{magnitud} %'
    return nombre.replace("_", " ").capitalize()


def adaptar_oficial(o: dict) -> dict:
    """Pasa numeros_oficiales.json (secciones anidadas, ver resultados/README.md) a las claves del dashboard.

    Las claves de primer nivel con «valor» pasan tal cual. De las secciones solo se toma lo que ya
    tiene datos: lo que sigue en null se queda «pendiente» en pantalla, nunca se inventa.
    """
    n = dict(o)
    rejilla = _ruta(o, "deteccion", "comparacion_contra_reglas_kit", "rejilla_inyecciones") or {}

    # Curva de sensibilidad: solo las inyecciones de energía de 4 h (energia_+10 … +80).
    curva = [f for f in rejilla.get("datos_curva") or [] if str(f.get("nombre", "")).startswith("energia_+")]
    if curva and "curva_sensibilidad" not in o:
        n["curva_sensibilidad"] = {"tipo": "observado", "nota": rejilla.get("nota", ""), "filas": [{
            "magnitud_pct": f["magnitud_pct"],
            "metodo": METODOS.get(f["metodo"], f["metodo"]),
            "detectados": round(f["pct_efectos_vistos"] * f["inyecciones"] / 100),
            "total": f["inyecciones"],
            "horas_hasta_detectar": f["mediana_horas_ver_efecto"],
            "kwh_no_vistos": f["no_visto"],
        } for f in curva]}

    # Robustez: la misma rejilla con más ruido, en % de efectos vistos (media y rango entre semillas).
    ruido = _ruta(o, "deteccion", "comparacion_contra_reglas_kit", "robustez_ruido") or {}
    if ruido.get("resultado") and "robustez" not in o:
        falsas = ruido.get("falsas_alarmas_por_dia_sitio_media")
        n["robustez"] = {"tipo": "observado", "filas": [{
            "condicion": f'Doble de ruido · {_nombre_inyeccion(f["nombre"])}',
            "metodo": METODOS.get(f["metodo"], f["metodo"]),
            "pct": f["pct_efectos_vistos_media"],
            "pct_min": f["pct_efectos_vistos_min"],
            "pct_max": f["pct_efectos_vistos_max"],
            "falsas_por_dia": falsas if f["metodo"] == "dripsafe" else None,
        } for f in ruido["resultado"]]}

    # Horas de respaldo del bono: {"umbral_27c": 2400, …} → filas por umbral.
    horas = _ruta(o, "bono_zero_freshwater", "horas_respaldo_mérida_al_año") or {}
    filas = [{"umbral_c": int(k.removeprefix("umbral_").removesuffix("c")), "horas_anio": v}
             for k, v in horas.items() if k.startswith("umbral_") and v is not None]
    if filas and "bono_horas_respaldo" not in o:
        n["bono_horas_respaldo"] = {"tipo": horas.get("tipo", "estimado"), "filas": filas,
                                    "nota": horas.get("nota", "")}
    return n


def cifra(numeros: dict, clave: str, defecto=None):
    """Valor de una cifra del contrato 4, o `defecto` si todavía no existe."""
    dato = numeros.get(clave)
    return dato["valor"] if isinstance(dato, dict) and "valor" in dato else defecto


# De la cifra más firme a la más débil. Una cifra calculada con otras hereda la más débil.
FIRMEZA = ["observado", "medido", "estimado", "proyectado", "vista_previa", "ejemplo", "pendiente"]


def mas_debil(*tipos: str) -> str:
    """La etiqueta más débil: algo calculado con una cifra de ejemplo también es de ejemplo."""
    return max(tipos, key=FIRMEZA.index)


def tipo_cifra(numeros: dict, clave: str, ejemplo: bool) -> str:
    """Qué tan firme es una cifra: el «tipo» del JSON, o «ejemplo» si el archivo es el de ejemplo."""
    if ejemplo:
        return "ejemplo"
    dato = numeros.get(clave)
    # Una cifra que el JSON oficial aún no trae (o trae en null) está pendiente, no es una vista previa.
    if not isinstance(dato, dict) or ("valor" in dato and dato["valor"] is None):
        return "pendiente"
    return dato.get("tipo", "estimado")
