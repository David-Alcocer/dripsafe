"""Las ocho secciones del dashboard, organizadas como dashboards de Grafana.

Cada sección = variables arriba, una fila de paneles Stat y luego filas plegables con
gráficas, listas y tablas. Los datos son los del kit CIFOX (simulados). El HTML de los
paneles sale de app/componentes.py y los textos de app/textos.py.

Cada cifra dice de dónde sale (observado, medido, estimado, proyectado o ejemplo). Las
cifras oficiales vienen de resultados/numeros_oficiales.json; la app no las inventa.
"""

import math
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app import calculos, graficas
from app import componentes as c
from app.cargar import Datos, cifra, mas_debil, tipo_cifra
from app.textos import (
    BONO,
    CLASES,
    DEMO,
    EPOCAS,
    ESCENARIOS,
    ESTADO_TECNICA,
    EVENTOS_OT,
    EVENTOS_OT_TEXTO,
    HECHOS_ACUIFERO,
    IMPACTO_ACUIFERO,
    KIT_VS_EQUIPO,
    LIMITES,
    NOMBRE_VIGILADA,
    NOMBRES,
    PASOS_DEMO,
    SITIOS,
    TECNICAS,
    TIPOS_CIFRA,
    UNIDADES,
    VIGILADAS,
)

# Umbrales de color: PUE como la regla del kit (rojo arriba de 1.6); agua por kWh IT (rojo arriba de 1.5).
PASOS_PUE = [(None, "verde"), (1.4, "naranja"), (1.6, "rojo")]
PASOS_WUE = [(None, "verde"), (1.0, "naranja"), (1.5, "rojo")]
ANOTACIONES = [("atk", "Incidente o cambio OT", ["", ""]), ("inef", "Escalón sin registro", ["", ""])]


@dataclass
class Vista:
    """Lo que se muestra según el sitio y el periodo elegidos arriba."""
    tabla: pd.DataFrame       # filas del sitio y periodo elegidos
    tabla_sitio: pd.DataFrame  # filas del sitio elegido en TODO el periodo
    eventos: pd.DataFrame
    texto: str


# ------------------------------------------------------------ utilidades

def ir(pagina: str) -> None:
    st.session_state.pagina = pagina
    st.rerun()


def fila(titulo: str, clave: str, abierta: bool = True):
    """Fila plegable de Grafana: agrupa paneles bajo un título.

    La clave va en un contenedor alrededor (no en el expander) para funcionar también con
    Streamlit 1.51, la versión que validó el kit.
    """
    return st.container(key=f"fila-{clave}").expander(titulo, expanded=abierta)


def rejilla(paneles: list[str], minimo: int = 220) -> None:
    """Paneles en rejilla: tantas columnas como quepan, cada una de al menos `minimo` px."""
    st.html(f'<div class="rejilla" style="--min: {minimo}px">{"".join(paneles)}</div>')


def panel_grafica(clave: str, titulo: str, fig, leyenda: str = "", descripcion: str = ""):
    """Panel con una gráfica de plotly y la leyenda de Grafana debajo."""
    caja = st.container(border=True, key=f"panel-{clave}")
    caja.html(c.encabezado_panel(titulo, descripcion))
    caja.plotly_chart(fig, config=graficas.CONFIG, theme=None, width="stretch")
    if leyenda:
        caja.html(leyenda)
    return caja


def calculos_leyenda(serie: pd.Series, dec: int, unidad: str = "") -> list[str]:
    """Media y máximo, como la leyenda en modo tabla de Grafana."""
    u = f" {unidad}" if unidad else ""
    return [c.numero(serie.mean(), dec) + u, c.numero(serie.max(), dec) + u]


def leyenda_sitios(ancha: pd.DataFrame, dec: int, unidad: str = "", anotaciones: bool = True) -> str:
    filas = [(graficas.COLOR_SITIO.get(s, "#4c8bd6"), SITIOS.get(s, s), calculos_leyenda(ancha[s], dec, unidad))
             for s in ancha.columns]
    return c.leyenda(filas + (ANOTACIONES if anotaciones else []), ["Media", "Máx"])


def grande(texto: str, px: int = 24) -> str:
    """Valor de un Stat que es texto largo (no número): un poco más chico y puede ocupar varias líneas."""
    return f'<span style="font-size: {px}px; white-space: normal; display: inline-block">{texto}</span>'


def tiempo_corto(horas: float | None) -> tuple[str, str]:
    """Horas → (valor, unidad) legible: segundos, minutos u horas."""
    if horas is None:
        return "—", ""
    if horas * 3600 < 60:
        return c.numero(horas * 3600, 2), "s/año"
    if horas < 1:
        return c.numero(horas * 60, 1), "min/año"
    return c.numero(horas, 1), "h/año"


def con_tag(sub: str, tipo: str) -> str:
    """Subtítulo de un Stat con la etiqueta de procedencia al final."""
    return f'<span class="tags">{c.procedencia(tipo)}<span>{sub}</span></span>'


def tipo_de(d: Datos, clave: str) -> str:
    return tipo_cifra(d.numeros, clave, d.cifras_de_ejemplo)


def detector_tipo(d: Datos) -> str:
    """Las cifras que la app calcula con la salida del detector: estimadas, o vista previa."""
    return "estimado" if d.fuentes.get("detector") == "modelo" else "vista_previa"


def aviso_ejemplo(d: Datos) -> str:
    if not d.cifras_de_ejemplo:
        return ""
    return c.aviso("<b>Cifras de ejemplo.</b> Todavía no hay resultados oficiales verificados: "
                   "las cifras marcadas como <b>Ejemplo</b> son ficticias y solo prueban la interfaz. "
                   "Nunca van al pitch.")


def mostrar_aviso_ejemplo(d: Datos) -> None:
    aviso = aviso_ejemplo(d)
    if aviso:
        st.html(aviso)


def items_alertas(eventos: pd.DataFrame) -> list[dict]:
    """Eventos para el panel «Alert list»: ya vienen ordenados por gravedad y fecha."""
    return [{
        "clase": e["clase"],
        "titulo": f'{CLASES[e["clase"]][0]} · {e["sitio"]}',
        "detalle": e["motivo"],
        "cuando": f'{calculos.fecha(e["inicio"])} · {calculos.duracion(e["horas"])}',
    } for _, e in eventos.iterrows()]


def filas_eventos(eventos: pd.DataFrame) -> list[list[str]]:
    """Filas de la tabla de eventos (ya ordenados por gravedad y fecha)."""
    return [[
        c.celda_severidad(e["clase"]),
        SITIOS.get(e["sitio"], e["sitio"]),
        calculos.fecha(e["inicio"]),
        calculos.duracion(e["horas"]),
        c.chip(e["clase"]),
        e["motivo"] + (' <span class="tag-sim">confianza baja</span>' if e["confianza_baja"] else ""),
        c.numero(e["exceso_kwh"], 1) if e["exceso_kwh"] else "—",
        ESCENARIOS.get(e["escenario"], "—") if e["escenario"] != "base" else "Ninguno (falsa alarma)",
    ] for _, e in eventos.iterrows()]


def serie_vigilada(t: pd.DataFrame, clave: str) -> tuple[pd.Series, pd.Series]:
    """Real y esperado por hora de una variable vigilada (suma de sitios, o media para la temperatura)."""
    real, esperado, _, _ = VIGILADAS[clave]
    r = calculos.serie_horaria(t, real, separar_sitios=False)["Todos"]
    e = calculos.serie_horaria(t, esperado, separar_sitios=False)["Todos"]
    return r, e


def grafica_vigilada(t: pd.DataFrame, clave: str, eventos, alto: int = 290):
    real, esperado = serie_vigilada(t, clave)
    columna = VIGILADAS[clave][0]
    u, dec = UNIDADES[columna]
    col_exceso = {"energia": "exceso_kwh", "agua": "exceso_l"}.get(clave)
    exceso = t.groupby("timestamp")[col_exceso].sum().reindex(real.index).values if col_exceso else None
    fig = graficas.real_vs_esperado(real.index, real.values, esperado.values, NOMBRES[columna], u, dec,
                                    eventos=eventos, alto=alto, exceso=exceso)
    ley = c.leyenda([("line", "Real", calculos_leyenda(real, dec, u)),
                     ("dash", "Esperado (línea base)", calculos_leyenda(esperado, dec, u))] + ANOTACIONES,
                    ["Media", "Máx"])
    return fig, ley


def conteo_clases(eventos: pd.DataFrame) -> dict:
    """Cuántos eventos tienen cada clase (un evento con logins y luego un cambio cuenta en las dos)."""
    return pd.Series([k for clases in eventos["clases"] for k in clases], dtype=object).value_counts().to_dict()


# ------------------------------------------------------------ resumen

def resumen(d: Datos, v: Vista) -> None:
    t = v.tabla
    m = calculos.metricas(t)
    ex = calculos.exceso(t)
    n = conteo_clases(v.eventos)
    ot = n.get("incidente_ot", 0) + n.get("cambio_no_autorizado", 0)
    tipo_det = detector_tipo(d)

    rejilla([
        c.gauge("PUE", m["pue"], 1.0, 2.0, PASOS_PUE, 3, sub=con_tag("Σ total ÷ Σ IT del periodo", "observado"),
                descripcion="Suma de energía total entre suma de energía IT del periodo. La regla fija del kit alerta arriba de 1.6."),
        c.stat("Incidentes y cambios OT", str(ot), color="rojo" if ot else "verde", fondo=bool(ot),
               sub=f'{n.get("incidente_ot", 0)} con efecto físico · {n.get("cambio_no_autorizado", 0)} sin efecto aún'),
        c.stat("Escalones sin registro", str(n.get("escalon_sin_registro", 0)),
               color="naranja" if n.get("escalon_sin_registro") else "verde",
               sub="exceso sin evento OT: revisar configuración primero"),
        c.stat("Intentos de acceso", str(n.get("intento_acceso", 0)),
               color="amarillo" if n.get("intento_acceso") else "verde", sub="logins fallidos sin efecto"),
        c.stat("Energía en exceso", c.numero(ex["kwh"], 1), "kWh", "naranja" if ex["kwh"] else "verde",
               sub=con_tag("energía no TI real − esperada en las alertas", tipo_det), ancho=True,
               serie=calculos.serie_horaria(t, "energia_no_ti_kwh", separar_sitios=False)["Todos"].values),
        c.stat("Agua en exceso", c.numero(ex["litros"]), "L", "naranja" if ex["litros"] else "verde",
               sub=con_tag("agua real − esperada en las alertas", tipo_det), ancho=True,
               serie=calculos.serie_horaria(t, "water_l", separar_sitios=False)["Todos"].values),
    ])

    with fila("Real contra esperado y alertas", "eficiencia"):
        izq, der = st.columns([2, 1], gap="small")
        with izq:
            fig, ley = grafica_vigilada(t, "energia", v.eventos)
            panel_grafica("vigilada", "Energía no TI: real contra lo esperado para su carga y clima", fig, ley,
                          "La línea punteada es la línea base aprendida en las horas de referencia de cada sitio. "
                          "El área naranja es el exceso.")
        with der:
            caja = st.container(border=True, key="panel-alertas")
            caja.html(c.encabezado_panel("Alertas", "Primero las más graves; dentro de cada clase, por fecha."))
            caja.html(c.lista_alertas(items_alertas(v.eventos)[:6]))
            if caja.button("Ver todas en Monitoreo", icon=":material/arrow_forward:", type="tertiary"):
                ir("monitoreo")

    with fila("Lo que aporta frente a las reglas fijas", "aporte"):
        curva = (d.numeros.get("curva_sensibilidad") or {}).get("filas") or []
        izq, der = st.columns([2, 1], gap="small")
        with izq:
            if curva:
                panel_grafica("curva-res", "Fallas detectadas según su tamaño",
                              graficas.curva(curva, "detectados", "Detectadas", alto=250, porcentaje=True),
                              f'<div class="tags">{c.procedencia(tipo_de(d, "curva_sensibilidad"))}'
                              f'<span class="txt-d">Rejilla fija de inyecciones (Nico, N2). Detalle en Evaluación.</span></div>',
                              "Porcentaje de fallas inyectadas que cada método detecta.")
            else:
                st.html(c.panel("Fallas detectadas según su tamaño", '<p class="txt-d">Pendiente: curva de N2 (Nico).</p>'))
        with der:
            horas = cifra(d.numeros, "equilibrio_horas")
            rejilla([
                c.stat("Umbral de equilibrio", *tiempo_corto(horas), "verde",
                       sub=con_tag("de exceso detectado pagan el detector un año", tipo_de(d, "equilibrio_horas"))),
                c.stat("PUE si se corta el exceso", c.numero(ex["pue_sin_exceso"], 3), color="azul",
                       sub=con_tag(f'hoy {c.numero(ex["pue"], 3)} · cota, no ahorro', tipo_det)),
            ], minimo=200)
    mostrar_aviso_ejemplo(d)


# ------------------------------------------------------------ demo de ataque

def _ventana_demo(d: Datos, sitio: str, inicio, fin) -> pd.DataFrame:
    """Horas del sitio alrededor del evento."""
    s = d.tabla[d.tabla["site_id"] == sitio]
    v = calculos.ventana(s, inicio, fin, margen_horas=12).copy()
    v["ot_codigo"] = v["ot_event"].map(EVENTOS_OT)
    return v


def demo(d: Datos) -> None:
    # Un evento por escenario del kit (el primero de cada uno). El escenario solo elige la historia.
    casos = {}
    for _, e in d.eventos.sort_values("inicio").iterrows():
        if e["escenario"] in DEMO and e["escenario"] not in casos:
            casos[e["escenario"]] = e
    if not casos:
        st.html(c.aviso("No hay eventos para la demo con los datos actuales."))
        return
    nombres = list(casos)
    if st.session_state.get("demo_sel") not in nombres:
        st.session_state.demo_sel = "evento_ot" if "evento_ot" in nombres else nombres[0]
    st.session_state.setdefault("paso", 0)

    def mover(delta: int) -> None:
        st.session_state.paso = max(0, min(len(PASOS_DEMO) - 1, (st.session_state.get("paso") or 0) + delta))

    # Escenario y paso en filas separadas: los cuatro pasos siempre caben, aun en pantallas angostas.
    var1, _ = st.columns([1, 1], gap="small")
    elegido = var1.selectbox(
        "Escenario", nombres, key="demo_sel", on_change=lambda: st.session_state.update(paso=0),
        format_func=lambda x: f"{ESCENARIOS[x]} · {SITIOS.get(casos[x]['sitio'], casos[x]['sitio'])}")
    cortos = ["Operador", "Real vs esperado", "Clase", "Acción"]
    st.segmented_control("Paso", list(range(len(PASOS_DEMO))), key="paso",
                         format_func=lambda i: f"{i + 1} · {cortos[i]}")
    paso = st.session_state.get("paso") or 0

    e, guion = casos[elegido], DEMO[elegido]
    st.html(f'<p class="lead"><b>{PASOS_DEMO[paso][0]}.</b> {PASOS_DEMO[paso][1]} '
            f'<span class="lead-m">{SITIOS.get(e["sitio"])} · {calculos.fecha(e["inicio"])} a '
            f'{calculos.fecha(e["fin"])} UTC</span></p>')

    v = _ventana_demo(d, e["sitio"], e["inicio"], e["fin"])
    ev = pd.DataFrame([e]) if paso >= 2 else None

    izq, der = st.columns(2, gap="small")
    with izq:
        col = guion["operador"]
        u, dec = UNIDADES[col]
        fig = graficas.serie(v["timestamp"], v[col], NOMBRES[col], u, dec, eventos=ev, alto=250, desde_cero=True)
        panel_grafica("op", f"Pantalla del operador · {NOMBRES[col]}", fig,
                      c.leyenda([("line", NOMBRES[col], calculos_leyenda(v[col], dec, u))], ["Media", "Máx"]),
                      "Lo que se vigila normalmente. En este escenario no muestra nada raro.")
    with der:
        nombre = NOMBRE_VIGILADA[guion["vigilada"]]
        if paso >= 1:
            fig, ley = grafica_vigilada(v, guion["vigilada"], ev, alto=250)
            panel_grafica("ev", f"{nombre}: real contra esperado", fig, ley,
                          "La línea punteada es lo que el sitio debería gastar con esa carga y ese clima.")
        else:
            st.html(c.panel(f"{nombre}: real contra esperado", '<div class="oculto">Se revela en el paso 2</div>'))

    if paso >= 1 and elegido == "evento_ot":
        fig = graficas.serie(v["timestamp"], v["ot_codigo"], NOMBRES["ot_codigo"], "", 0, eventos=ev, alto=180,
                             etiquetas_y={0: "Normal", 1: "Login fallido", 2: "Cambio config."})
        panel_grafica("ot", "Registro OT del sitio", fig, "", "Eventos ficticios del kit: no hay IP ni credenciales.")

    paneles = [c.stat("Estado en pantalla", grande("Normal", 28), color="verde", sub="lo que ve el operador")]
    if paso < 2:
        paneles.append(c.stat("DripSafe", grande("Comparando", 28), color="gris", sub="real contra esperado y registro OT"))
    else:
        nombre_clase, severidad, color, que, _ = CLASES[e["clase"]]
        exceso = (f'{c.numero(e["exceso_kwh"], 1)} kWh' if e["exceso_kwh"] >= 1
                  else f'{c.numero(e["exceso_l"])} L de agua' if e["exceso_l"] else "")
        paneles += [
            c.stat("DripSafe", grande(nombre_clase, 24), color=color, fondo=True, sub=f"severidad {severidad.lower()}"),
            c.stat("Motivo", grande(e["motivo"] or "evento OT", 18), color="gris",
                   sub=con_tag(f"exceso: {exceso}" if exceso else "sin exceso físico", detector_tipo(d))),
            c.stat("Técnica MITRE ATT&CK for ICS" if guion["tecnica"] else "Origen",
                   f'<span class="mono">{grande(guion["tecnica"] or "Sin registro", 22)}</span>', color="gris",
                   sub=guion["nombre_tecnica"]),
        ]
    rejilla(paneles, minimo=220)

    if paso >= 2:
        st.html(c.aviso(f"<b>Qué se ve.</b> {guion['huella']} {CLASES[e['clase']][3]}"))
    if paso >= 3:
        st.html(c.aviso(f"<b>Qué hacer.</b> {CLASES[e['clase']][4]} DripSafe solo avisa: la decisión es del operador."))

    _, atras, adelante = st.columns([4, 1, 1], gap="small")
    atras.button("Anterior", icon=":material/chevron_left:", disabled=paso == 0, width="stretch",
                 on_click=mover, args=(-1,))
    adelante.button("Siguiente", icon=":material/chevron_right:", disabled=paso == len(PASOS_DEMO) - 1,
                    type="primary", width="stretch", on_click=mover, args=(1,))


# ------------------------------------------------------------ monitoreo

def monitoreo(d: Datos, v: Vista) -> None:
    variables = {**{k: f"{n} · real contra esperado" for k, n in NOMBRE_VIGILADA.items()},
                 "pue": "PUE por sitio", "wue": "Agua por energía IT por sitio",
                 "load_pct": "Carga por sitio", "outdoor_temp_c": "Temperatura exterior por sitio"}
    opciones = {"Todas": tuple(CLASES), "OT": ("incidente_ot", "cambio_no_autorizado", "intento_acceso"),
                "Sin registro": ("escalon_sin_registro",)}
    var1, var2 = st.columns([2, 3], gap="small")
    elegida = var1.selectbox("Variable", list(variables), format_func=variables.get, key="mon_var")
    filtro = var2.segmented_control("Clase de alerta", list(opciones), default="Todas", key="filtro") or "Todas"
    ev = v.eventos[v.eventos["clase"].isin(opciones[filtro])]

    if elegida in VIGILADAS:
        fig, ley = grafica_vigilada(v.tabla, elegida, ev, alto=340)
        panel_grafica("monitoreo", variables[elegida], fig, ley,
                      "Con «Todos los sitios», la energía y el agua se suman y la temperatura se promedia. Horas en UTC.")
    else:
        u, dec = UNIDADES[elegida]
        ancha = calculos.serie_horaria(v.tabla, elegida)
        panel_grafica("monitoreo", variables[elegida], graficas.por_sitio(ancha, u, dec, eventos=ev, alto=340),
                      leyenda_sitios(ancha, dec, u), "Cada franja es un evento del detector. Horas en UTC.")

    with fila(f"Eventos ({len(ev)})", "eventos"):
        st.html(c.panel("Eventos marcados por DripSafe", c.tabla(
            ["Severidad", "Sitio", "Inicio (UTC)", "Duración", "Clase", "Motivo", "Exceso (kWh)", "Escenario del kit"],
            filas_eventos(ev), numericas=(3, 6)),
            "La última columna es la respuesta correcta del kit: solo sirve para evaluar, el detector no la ve."))

    with fila("Tabla de valores", "valores"):
        tabla_de_valores(v.tabla)


def tabla_de_valores(t: pd.DataFrame) -> None:
    """Los registros hora por hora y la comprobación del PUE con sumas (recorrido de la guía del kit)."""
    m = calculos.metricas(t)
    st.html(c.aviso(
        f'<b>Comprobación con sumas.</b> Σ energía total {c.numero(m["energia_total_kwh"])} kWh ÷ '
        f'Σ energía IT {c.numero(m["energia_it_kwh"])} kWh = <b>PUE {c.numero(m["pue"], 3)}</b> · '
        f'Σ agua {c.numero(m["agua_l"])} L ÷ Σ energía IT = <b>{c.numero(m["wue"], 3)} L/kWh</b> '
        f'({m["filas"]} registros del filtro de arriba).'))
    solo = st.checkbox("Mostrar solo registros con alerta", value=True, key="solo_alertas")
    filas = t[t["alerta"]] if solo else t
    cuerpo = [[
        calculos.fecha(x["timestamp"]), SITIOS.get(x["site_id"], x["site_id"]),
        c.numero(x["energy_it_kwh"], 1), c.numero(x["energy_total_kwh"], 1), c.numero(x["pue"], 3),
        c.numero(x["energia_no_ti_kwh"], 1), c.numero(x["esperado_energia_no_ti_kwh"], 1),
        c.numero(x["water_l"], 1), c.numero(x["esperado_agua_l"], 1), c.numero(x["inlet_temp_c"], 1),
        EVENTOS_OT_TEXTO.get(x["ot_event"], "—"), c.chip(x["clase"]) if x["alerta"] else "—",
    ] for _, x in filas.sort_values(["timestamp", "site_id"]).iterrows()]
    st.html(c.panel(f"Registros ({len(filas)} de {len(t)})", c.tabla(
        ["Hora (UTC)", "Sitio", "Energía IT", "Energía total", "PUE", "No TI real", "No TI esperada",
         "Agua real (L)", "Agua esperada (L)", "Entrada (°C)", "Evento OT", "Clase"],
        cuerpo, numericas=(2, 3, 4, 5, 6, 7, 8, 9)) if cuerpo else '<p class="txt-d">No hay registros con alerta en este filtro.</p>',
        "Una fila por sitio y hora; energías en kWh. El PUE de cada fila es solo de esa hora: el del periodo se calcula con sumas."))


# ------------------------------------------------------------ evaluación

def _fila_resumen(nombre: str, r: dict, nota: str, tag: str) -> list[str]:
    return [nombre, str(r["tp"]), str(r["fp"]), str(r["fn"]),
            f'{r["precision"]:.0%}' if r["precision"] is not None else "—",
            f'{r["recall"]:.0%}' if r["recall"] is not None else "—",
            c.numero(r["falsas_por_dia"], 2) if r["falsas_por_dia"] is not None else "—",
            f'<span class="tags">{tag}<span>{nota}</span></span>']


def evaluacion(d: Datos) -> None:
    _, rd = d.evaluacion["dripsafe"]
    _, rr = d.evaluacion["reglas"]
    curva = (d.numeros.get("curva_sensibilidad") or {}).get("filas") or []
    tipo_curva = tipo_de(d, "curva_sensibilidad")

    rejilla([
        c.stat("DripSafe en el kit", f'{rd["escenarios_detectados"]}/{rd["escenarios_totales"]}', "escenarios", "azul",
               sub=con_tag(f'{rd["tp"]} horas acertadas · {rd["fp"]} falsas', detector_tipo(d))),
        c.stat("Reglas fijas del kit", f'{rr["escenarios_detectados"]}/{rr["escenarios_totales"]}', "escenarios", "gris",
               sub=con_tag(f'{rr["tp"]} horas acertadas · {rr["fp"]} falsas', "observado")),
        c.stat("Punto ciego de las reglas", c.numero(cifra(d.numeros, "punto_ciego_pct")), "%", "naranja",
               sub=con_tag("más energía de enfriamiento en el sitio líquido sin cruzar PUE 1.6",
                           tipo_de(d, "punto_ciego_pct"))),
    ], minimo=260)
    st.html(c.aviso("<b>En los 3 episodios anómalos del kit (21 horas) se espera un empate</b> y se reporta tal cual: "
                    "el kit los diseñó para que las reglas los vean. El aporte se mide con fallas más pequeñas, "
                    "en la curva de abajo."))

    with fila("Curva de sensibilidad (rejilla fija de inyecciones)", "curva"):
        if curva:
            izq, der = st.columns(2, gap="small")
            with izq:
                panel_grafica("curva", "Fallas detectadas según su tamaño",
                              graficas.curva(curva, "detectados", "Detectadas", porcentaje=True),
                              f'<div class="tags">{c.procedencia(tipo_curva)}</div>',
                              "Exceso de energía no TI inyectado durante 4 h en copias de la evaluación.")
            with der:
                panel_grafica("no-vistos", "Energía que nadie vio",
                              graficas.curva(curva, "kwh_no_vistos", "kWh no vistos"),
                              f'<div class="tags">{c.procedencia(tipo_curva)}</div>',
                              "kWh de exceso que ocurrieron antes de que cada método alertara, o sin que alertara nunca.")
            st.html(c.panel("Detalle de la curva", c.tabla(
                ["Exceso inyectado", "Método", "Detectadas", "Horas hasta detectar", "kWh no vistos"],
                [[f'+{f["magnitud_pct"]} %', f["metodo"], f'{f["detectados"]} de {f["total"]}',
                  c.numero(f["horas_hasta_detectar"]) if f["horas_hasta_detectar"] is not None else "nunca",
                  c.numero(f["kwh_no_vistos"])] for f in curva], numericas=(2, 3, 4)),
                (d.numeros.get("curva_sensibilidad") or {}).get("nota", "")))
        else:
            st.html(c.panel("Curva de sensibilidad", '<p class="txt-d">Pendiente: N2 (Nico) con la rejilla de U2 (Guille).</p>'))

    with fila("Comparación en las horas de evaluación", "comparacion"):
        filas = [
            _fila_resumen("DripSafe", rd, "vista previa de la app" if detector_tipo(d) == "vista_previa"
                          else "salida del detector", c.procedencia(detector_tipo(d))),
            _fila_resumen("Reglas fijas del kit", rr, "PUE > 1.6, agua > 1.5, entrada > 29 °C o evento OT",
                          c.procedencia("observado")),
        ]
        if_kit = d.benchmarks.get("isolation_forest")
        if if_kit:
            s = if_kit["scores"]
            filas.append([
                "Isolation Forest del kit", str(s["tp"]), str(s["fp"]), str(s["fn"]), f'{s["precision"]:.0%}',
                f'{s["recall"]:.0%}', "—", f'<span class="tags">{c.procedencia("observado")}'
                '<span>corrida de ejemplo del kit; 6 variables, sin OT</span></span>'])
        st.html(c.panel("Por hora, en las 96 h de evaluación", c.tabla(
            ["Método", "Aciertos", "Falsas", "Omitidas", "Precisión", "Recall", "Falsas por día", "Nota"],
            filas, numericas=(1, 2, 3, 4, 5, 6)),
            "Las etiquetas del kit solo se usan aquí, para calificar. Nunca entran al detector."))
        robustez = (d.numeros.get("robustez") or {}).get("filas") or []
        if robustez:
            st.html(c.panel("Robustez (+20 % durante 4 h)", c.tabla(
                ["Condición", "Método", "Detectadas", "Falsas por día"],
                [[f["condicion"], f["metodo"], f'{f["detectados"]} de {f["total"]}', c.numero(f["falsas_por_dia"], 1)]
                 for f in robustez], numericas=(2, 3)),
                "El agua del kit no tiene ruido: la prueba agrega ruido para no detectar algo trivial."))
    mostrar_aviso_ejemplo(d)


# ------------------------------------------------------------ ciberseguridad

def ciberseguridad(d: Datos, v: Vista) -> None:
    ot = v.tabla[v.tabla["ot_event"] != "normal"]
    n = conteo_clases(v.eventos)
    rejilla([c.stat(CLASES[k][0], str(n.get(k, 0)), color=CLASES[k][2] if n.get(k) else "verde",
                    sub=f"severidad {CLASES[k][1].lower()}") for k in CLASES], minimo=200)

    with fila("Las cuatro clases de alerta", "clases"):
        st.html(c.panel("Tabla de decisión", c.tabla(
            ["Clase", "Severidad", "Cuándo", "Acción sugerida"],
            [[c.chip(k), sev, cuando, accion] for k, (_, sev, _, cuando, accion) in CLASES.items()]),
            "Propuesta del equipo (Guille, U1). Ningún exceso sin explicar va directo a mantenimiento, "
            "y ningún cambio no autorizado es «sin urgencia»."))

    with fila("Registro de eventos OT", "ot"):
        filas = [[calculos.fecha(x["timestamp"]), SITIOS.get(x["site_id"], x["site_id"]),
                  EVENTOS_OT_TEXTO.get(x["ot_event"], x["ot_event"]),
                  '<span class="mono">T0859</span>' if x["ot_event"] == "login_fallido" else '<span class="mono">T0836</span>',
                  c.chip(x["clase"]) if x["alerta"] else "—"]
                 for _, x in ot.sort_values("timestamp").iterrows()]
        st.html(c.panel("Eventos OT en orden", c.tabla(["Hora (UTC)", "Sitio", "Evento", "Técnica (propuesta)", "Clase"],
                                                       filas) if filas else '<p class="txt-d">Sin eventos OT.</p>',
                        "Eventos ficticios del kit: no hay IP, credenciales ni herramientas ofensivas."))

    with fila("Técnicas de MITRE ATT&CK for ICS", "attack"):
        rejilla([
            c.panel(f"{i} · {nom}",
                    f'<p class="txt-d">{que}</p><p class="txt">{como}</p>'
                    f'<p class="txt-tag">{c.etiqueta(*ESTADO_TECNICA[estado])}</p>')
            for i, nom, que, como, estado in TECNICAS
        ], minimo=300)

    with fila("Guía de operación", "guia"):
        rejilla([
            c.panel("Dos reglas de oro",
                    '<ul class="clean">'
                    '<li><b>Ningún exceso sin explicar va directo a mantenimiento.</b> Un setpoint cambiado sin dejar '
                    'registro se ve igual que una falla brusca: primero se revisa la configuración.</li>'
                    '<li><b>Ningún cambio no autorizado es «sin urgencia».</b> Puede notarse hasta el siguiente pico '
                    'de calor, o ser un cambio de límites de alarma que nunca mueve la física.</li></ul>'),
            c.panel("Cómo se instala sin abrir una puerta nueva",
                    '<ul class="clean">'
                    '<li><b>Solo lee:</b> recibe una copia de los datos y nunca manda órdenes.</li>'
                    '<li><b>Alerta a una persona:</b> un login fallido no prueba un ataque; requiere revisión humana.</li>'
                    '<li><b>Vive en su propia zona</b> de red, sin salida a internet.</li>'
                    '<li><b>Se entrena con horas de referencia</b> verificadas como limpias.</li></ul>',
                    "Basado en ISA/IEC 62443."),
        ], minimo=360)


# ------------------------------------------------------------ balance neto

def _posicion_log(valor: float) -> float:
    """Posición (0 a 100) en una escala logarítmica de 0.0001 a 1 000 000."""
    return max(0.0, min(100.0, (math.log10(max(valor, 1e-9)) + 4) / 10 * 100))


def balance(d: Datos, v: Vista) -> None:
    # Costo del detector: tiempo medido por el equipo (Gadiel, G3) o, mientras tanto, la corrida del kit.
    ms = cifra(d.numeros, "detector_cpu_ms")
    if ms is not None:
        segundos, tipo_t, origen_t = ms / 1000, tipo_de(d, "detector_cpu_ms"), "medición del equipo"
    else:
        segundos = d.benchmarks.get("isolation_forest", {}).get("wall_seconds", 1.0)
        tipo_t, origen_t = "observado", "corrida de ejemplo del kit"

    st.html('<p class="lead"><b>Supuestos editables.</b> El tiempo de CPU se mide; la energía y el CO₂ del detector se '
            '<b>estiman</b> con watts y gCO₂e/kWh supuestos. Cambia los valores para ver qué tan sensible es el balance.</p>')
    v1, v2, v3 = st.columns(3, gap="small")
    watts = v1.number_input("Potencia supuesta (W)", 1.0, 500.0, 30.0, 5.0)
    factor = v2.number_input("Emisión (gCO₂e/kWh)", 1.0, 1500.0, 450.0, 25.0,
                             help="Usar el factor vigente del SEN (CRE/SEMARNAT) cuando esté en el JSON oficial.")
    corridas = v3.number_input("Corridas al año", 1, 1_000_000, 8760, 100, help="8 760 = una corrida cada hora")

    costo = calculos.consumo_detector(segundos, watts, factor, int(corridas))
    tipo_costo = mas_debil("estimado", tipo_t)
    origen_costo = f"{watts:g} W × {c.numero(corridas)} corridas"
    if d.consumo.get("kwh_inferencia_anual") is not None:
        # Contrato 3: medición de Gadiel con CodeCarbon (en macOS, CodeCarbon estima la potencia).
        costo["kwh_anio"] = d.consumo["kwh_inferencia_anual"] + d.consumo.get("kwh_entrenamiento", 0)
        tipo_costo, origen_costo = "estimado", "CodeCarbon (consumo_modelo.json)"
    ex = calculos.exceso(v.tabla_sitio[v.tabla_sitio["split"] == "evaluacion"])
    horas = calculos.equilibrio(costo["kwh_anio"], ex["kwh_por_hora"])
    tipo_equilibrio = mas_debil(tipo_costo, detector_tipo(d))

    rejilla([
        c.stat("Tiempo del detector", c.numero(segundos * 1000, 1), "ms", "gris",
               sub=con_tag(f"por corrida · {origen_t}", tipo_t)),
        c.stat("Energía del detector", c.numero(costo["kwh_anio"], 4), "kWh/año", "gris",
               sub=con_tag(origen_costo, tipo_costo)),
        c.stat("Exceso por hora de alerta", c.numero(ex["kwh_por_hora"], 1), "kWh", "naranja",
               sub=con_tag("energía no TI sobre lo esperado, evaluación", detector_tipo(d))),
        c.stat("Umbral de equilibrio", *tiempo_corto(horas), "verde",
               sub=con_tag("de exceso detectado pagan la energía del detector", tipo_equilibrio)),
    ])
    st.html(c.aviso("<b>El número central es el umbral de equilibrio.</b> No depende de que el ahorro proyectado sea "
                    "exacto: basta con que DripSafe detecte a tiempo unos segundos de exceso al año para pagar su "
                    "propia energía.", "ok"))

    with fila("Escenario anual (proyectado, editable)", "escenario"):
        param = ((d.numeros.get("escenario_anual") or {}).get("parametros")) or {}
        e1, e2, e3, e4 = st.columns(4, gap="small")
        fallas = e1.number_input("Fallas al año", 0, 365, int(param.get("fallas", 6)), 1)
        pct = e2.number_input("Exceso por falla (%)", 1.0, 200.0, float(param.get("exceso_pct", 20)), 5.0)
        sin = e3.number_input("Horas sin DripSafe", 1.0, 2000.0, float(param.get("horas_sin", 72)), 12.0,
                              help="Horas que tarda alguien en notar la falla sin DripSafe")
        con = e4.number_input("Horas con DripSafe", 0.0, 200.0, float(param.get("horas_con", 4)), 1.0,
                              help="Horas hasta corregirla con la alerta de DripSafe")
        base = v.tabla_sitio[v.tabla_sitio["split"] == "referencia"]
        horas_sitio = base["timestamp"].nunique() or 1
        no_ti_h = base["energia_no_ti_kwh"].sum() / horas_sitio
        agua_h = base.loc[base["cooling_type"] == "evaporativa", "water_l"].sum() / horas_sitio
        esc = calculos.escenario_anual(int(fallas), pct, sin, con, no_ti_h, agua_h)
        rejilla([
            c.stat("Energía evitada", c.numero(esc["kwh"]), "kWh/año", "azul", sub=con_tag(
                f'{c.numero(esc["horas_evitadas"])} h de exceso evitadas', "proyectado")),
            c.stat("Agua evitada", c.numero(esc["litros"]), "L/año", "azul",
                   sub=con_tag("solo sitios evaporativos", "proyectado")),
        ], minimo=320)
        st.html(c.aviso("<b>Proyección, no ahorro observado.</b> Usa la energía no TI y el agua por hora de las horas de "
                        "referencia del sitio elegido arriba. Cambia los supuestos para ver el rango."))

    with fila("Lo que cuesta contra lo que ahorra", "barras"):
        marcas = "".join(f'<span style="left: {_posicion_log(x):.1f}%">{c.numero(x, 4 if x < 1 else 0)}</span>'
                         for x in (0.0001, 0.01, 1, 100, 10000, 1000000))
        st.html(c.panel("kWh por año (escala logarítmica)", c.barras([
            ("Energía estimada del detector", _posicion_log(costo["kwh_anio"]), 100, "gris",
             f'{c.numero(costo["kwh_anio"], 4)} kWh'),
            ("Energía evitada (escenario)", _posicion_log(esc["kwh"]), 100, "azul", f'{c.numero(esc["kwh"])} kWh'),
        ]) + f'<div class="logax">{marcas}</div>'))
        def equilibrio_texto(w: float, k: int) -> str:
            valor, unidad = tiempo_corto(calculos.equilibrio(calculos.consumo_detector(segundos, w, factor, k)["kwh_anio"],
                                                             ex["kwh_por_hora"]))
            return f"{valor} {unidad.removesuffix('/año')}"

        sens = [[f"{w:g} W"] + [equilibrio_texto(w, k) for k in (8760, 35040, 525600)] for w in (10, 30, 65, 150)]
        st.html(c.panel("Sensibilidad del umbral de equilibrio", c.tabla(
            ["Potencia supuesta", "Cada hora", "Cada 15 min", "Cada minuto"], sens, numericas=(1, 2, 3)),
            "Tiempo de exceso detectado al año que paga la energía del detector, con distintos supuestos de potencia "
            "y frecuencia. Aun en el peor caso, sigue siendo poco."))

    with fila("De dónde sale cada número", "calculo"):
        izq, der = st.columns(2, gap="small")
        with izq:
            st.html(c.panel("Cómo se calcula",
                            '<div class="formula"><span>energía_detector = W supuestos × segundos ÷ 3 600 000 × corridas</span>'
                            '<span>CO₂ = energía_detector × gCO₂e/kWh supuestos</span>'
                            '<span>exceso = energía no TI real − esperada (horas con alerta física)</span>'
                            '<span>equilibrio = energía_detector ÷ exceso por hora</span>'
                            '<span>escenario = fallas × (horas sin − horas con) × exceso % × energía no TI por hora</span></div>'
                            '<p class="txt-d">Mismo método de energía que tools/compare_detectors.py del kit. No incluye '
                            'fabricación, red, almacenamiento ni agua del detector.</p>'))
        with der:
            filas = [[f'<span class="mono">{k}</span>',
                      c.numero(x["valor"], 4 if abs(x["valor"]) < 1 else 2 if abs(x["valor"]) < 10 else 0) + f' {x.get("unidad", "")}',
                      x.get("responsable", "—"), c.procedencia(tipo_de(d, k))]
                     for k, x in d.numeros.items() if isinstance(x, dict) and isinstance(x.get("valor"), (int, float))]
            st.html(c.panel("Cifras del contrato 4", c.tabla(["Cifra", "Valor", "Responsable", "Tipo"], filas, numericas=(1,)),
                            "Las cifras del pitch salen solo de resultados/numeros_oficiales.json."))
    mostrar_aviso_ejemplo(d)


# ------------------------------------------------------------ agua y acuífero

def agua(d: Datos, v: Vista) -> None:
    m = calculos.metricas(v.tabla)
    ex = calculos.exceso(v.tabla)
    rejilla([
        c.stat("Agua por energía IT", c.numero(m["wue"], 2), "L/kWh", c.umbral(m["wue"], PASOS_WUE),
               sub=con_tag("Σ agua ÷ Σ energía IT", "observado")),
        c.stat("Agua captada", c.numero(m["agua_l"]), "L", "azul", sub=con_tag("en el periodo y sitios elegidos", "observado")),
        c.stat("Agua en exceso", c.numero(ex["litros"]), "L", "naranja" if ex["litros"] else "verde",
               sub=con_tag("real − esperada durante las alertas", detector_tipo(d))),
        c.stat("Agua por kWh IT sin el exceso", c.numero(ex["wue_sin_exceso"], 2), "L/kWh", "azul",
               sub=con_tag(f'hoy {c.numero(ex["wue"], 2)} · cota si se corta en cada alerta', detector_tipo(d))),
    ])

    with fila("Agua: real contra esperado", "agua-rve"):
        izq, der = st.columns([3, 2], gap="small")
        with izq:
            fig, ley = grafica_vigilada(v.tabla, "agua", v.eventos, alto=270)
            panel_grafica("agua", "Agua captada: real contra esperado", fig, ley,
                          "Una fuga se ve como agua por encima de lo esperado sin carga extra.")
        with der:
            comp = calculos.por_sitio(d.tabla[d.tabla["timestamp"].isin(v.tabla["timestamp"])])
            maximo = max(comp["wue"].max(), 0.01)
            st.html(c.panel("Agua por kWh IT de cada sitio", c.barras([
                (SITIOS.get(r["sitio"], r["sitio"]), r["wue"], maximo, graficas.COLOR_SITIO[r["sitio"]],
                 f'{c.numero(r["wue"], 2)} L/kWh') for _, r in comp.iterrows()])
                + c.aviso("El ahorro de agua depende del tipo de enfriamiento: es grande en el evaporativo y casi "
                          "nulo en el de aire. Los sitios son simulados: la diferencia no prueba que una tecnología sea mejor.")))

    with fila("Acuífero de Yucatán", "acuifero"):
        rejilla([c.panel(t, f'<p class="txt">{x}</p>') for t, x in HECHOS_ACUIFERO], minimo=280)
        st.html(c.panel("Impacto de DripSafe en el acuífero",
                        c.tabla(["Aspecto", "Pregunta", "Cómo ayuda DripSafe"],
                                [[f"<b>{a}</b>", q, x] for a, q, x in IMPACTO_ACUIFERO]),
                        "Fuentes por citar antes del pitch (Guille, #13; ver ~/hackathon/Papers)."))

    with fila("Las épocas del año en Yucatán", "epocas"):
        st.html(c.panel("Por qué una sola semana no basta", c.tabla(
            ["Época", "Meses", "Clima", "Qué le pasa al enfriamiento"],
            [[f"<b>{e}</b>", m_, cl, ef] for e, m_, cl, ef in EPOCAS])
            + c.aviso("El kit cubre una semana de octubre con 15 a 31 °C. DripSafe usa una línea base por época que se "
                      "recalibra cada semana; fuera del clima aprendido duplica el margen y alerta con «confianza baja», "
                      "sin apagar nunca las alertas."),
            "Rangos por confirmar con las normales y datos horarios del SMN o ERA5."))

    with fila("Bono · Cero agua potable", "bono"):
        izq, der = st.columns([3, 2], gap="small")
        with izq:
            st.html(c.panel("Enfriamiento propuesto", c.tabla(
                ["Pieza", "Qué es", "Costo o límite"], [[f"<b>{o}</b>", q, x] for o, q, x, _ in BONO],
                resaltar=tuple(i for i, b in enumerate(BONO) if b[3]))
                + c.aviso("La IA <b>recomienda</b> qué respaldo usar y el operador <b>confirma</b>. Una regla verifica "
                          "que el medidor de agua potable del enfriamiento marque cero."),
                "Para obra nueva o renovación. Referencias: Microsoft 2024 (sin evaporación), Google Douglas County "
                "(agua residual tratada), ASHRAE (clases W32/W40/W45)."))
        with der:
            horas = (d.numeros.get("bono_horas_respaldo") or {}).get("filas") or []
            maximo = max([f["horas_anio"] for f in horas] or [1])
            cuerpo = (c.barras([(f'Arriba de {f["umbral_c"]} °C', f["horas_anio"], maximo, "morado",
                                 f'{c.numero(f["horas_anio"])} h') for f in horas])
                      + f'<div class="tags">{c.procedencia(tipo_de(d, "bono_horas_respaldo"))}'
                        '<span class="txt-d">Mérida, clase W40</span></div>') if horas else \
                '<p class="txt-d">Pendiente: horas de respaldo por época (Misael, bono).</p>'
            st.html(c.panel("Horas de respaldo al año", cuerpo,
                            "Horas en que el enfriador seco no basta y entra el chiller de apoyo (sube el PUE)."))
    mostrar_aviso_ejemplo(d)


# ------------------------------------------------------------ datos y supuestos

def datos(d: Datos) -> None:
    t = d.tabla
    ref, ev = t[t["split"] == "referencia"], t[t["split"] == "evaluacion"]
    del_kit = d.fuentes.get("telemetria") == "kit"
    rejilla([
        c.stat("Fuente", grande("Kit CIFOX" if del_kit else "Datos de ejemplo", 24), color="gris",
               sub="CSV simulado, leído fuera del repo" if del_kit else "el kit no está en esta laptop"),
        c.stat("Filas", c.numero(len(t)), color="azul", sub=f'{t["site_id"].nunique()} sitios × {t["timestamp"].nunique()} horas'),
        c.stat("Periodo", grande(f'{calculos.fecha(t["timestamp"].min(), False)} – {calculos.fecha(t["timestamp"].max(), False)}', 24),
               color="gris", sub="horas en UTC"),
        c.stat("Ajuste / calibración / prueba", f"48 / {ref['timestamp'].nunique() - 48} / {ev['timestamp'].nunique()}",
               "h", "gris", sub="la línea base sale solo de referencia"),
    ])

    with fila("Qué tan firme es cada cifra", "tipos"):
        st.html(c.panel("Etiquetas de procedencia", c.tabla(
            ["Etiqueta", "Qué significa"], [[c.procedencia(k), texto] for k, (_, texto) in TIPOS_CIFRA.items()]),
            "La guía del kit pide distinguir lo observado de lo estimado y lo proyectado."))

    with fila("Ficha de datos", "ficha"):
        filas = [
            ["energy_it_kwh, energy_total_kwh", "kWh por hora", "PUE y energía no TI (total − IT)", "Sí"],
            ["water_l", "L por hora", "Agua por kWh IT; línea base de agua", "Sí"],
            ["outdoor_temp_c, inlet_temp_c, load_pct", "°C, %", "Línea base por clima y carga", "Sí"],
            ["ot_event", "categoría", "Clases OT (intento, cambio, incidente)", "Sí"],
            ["split", "referencia / evaluación", "Separar ajuste, calibración y prueba", "Solo para separar"],
            ["scenario, simulated_anomaly", "etiqueta", "Solo para calificar el detector", "No, nunca"],
        ]
        st.html(c.panel("Columnas del kit", c.tabla(["Columna", "Unidad", "Uso en DripSafe", "¿Entra al detector?"], filas),
                        "Diccionario completo en docs/DATA_DICTIONARY.md del kit."))
        st.html(c.panel("Fórmulas", '<div class="formula">'
                        '<span>PUE = Σ energía total ÷ Σ energía IT (nunca el promedio de los PUE por hora)</span>'
                        '<span>Agua por kWh IT = Σ agua captada ÷ Σ energía IT</span>'
                        '<span>Línea base: energía no TI y agua ~ IT + IT · max(0, T − 20); entrada ~ max(0, T − 20)</span>'
                        '<span>Umbral = mayor residuo de calibración × 1.5; además la media de 4 h</span>'
                        '<span>Sin filas, el indicador no existe (no es cero)</span></div>'))

    with fila("Límites", "limites"):
        rejilla([c.panel(f"{i}. {titulo}", f'<p class="txt">{texto}</p>')
                 for i, (titulo, texto) in enumerate(LIMITES, start=1)], minimo=300)

    with fila("Qué venía en el kit y qué aporta DripSafe", "aporte"):
        rejilla([c.panel(titulo, '<ul class="clean">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
                 for titulo, items in KIT_VS_EQUIPO.items()], minimo=360)
