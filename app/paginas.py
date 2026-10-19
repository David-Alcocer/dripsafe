"""Las seis secciones del dashboard, organizadas como dashboards de Grafana.

Cada sección = variables arriba, una fila de paneles Stat y luego filas plegables con
gráficas, listas y tablas. El HTML de los paneles sale de app/componentes.py y los
textos de app/textos.py. Las cifras salen de `d.numeros` (contrato 4) o de la telemetría.
"""

import math
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app import calculos, graficas
from app import componentes as c
from app.cargar import Datos, cifra
from app.textos import (
    BONO,
    DEMO,
    ESCENARIOS,
    HECHOS_ACUIFERO,
    IMPACTO_ACUIFERO,
    NOMBRES,
    PASOS_DEMO,
    RESPONSABLES,
    TECNICAS,
)

# Unidad y decimales con que se muestra cada variable.
UNIDADES = {
    "kw_ti": ("kW", 0), "kw_total": ("kW", 0), "kw_chiller": ("kW", 1), "kw_bombas": ("kW", 1),
    "kw_torre": ("kW", 1), "kw_enfriamiento": ("kW", 0), "kw_esperado_enfriamiento": ("kW", 0),
    "t_exterior": ("°C", 1), "t_suministro": ("°C", 2), "t_retorno": ("°C", 2), "setpoint_suministro": ("°C", 1),
    "flujo_m3h": ("m³/h", 1), "agua_reposicion_l": ("L", 0), "bomba_encendida": ("", 0), "calor_agua_kw": ("kW", 0),
}
# Umbrales del PUE: verde hasta 1.4, naranja hasta 1.6, rojo arriba.
PASOS_PUE = [(None, "verde"), (1.4, "naranja"), (1.6, "rojo")]
ANOTACIONES = [("atk", "Posible ataque", ["", ""]), ("inef", "Ineficiencia", ["", ""])]


@dataclass
class Vista:
    """Lo que se muestra según el periodo elegido arriba a la derecha."""
    tabla: pd.DataFrame
    eventos: pd.DataFrame
    texto: str  # por ejemplo: '08 oct al 14 oct 2026'


# ------------------------------------------------------------ utilidades

def ir(pagina: str) -> None:
    st.session_state.pagina = pagina
    st.rerun()


def fila(titulo: str, clave: str, abierta: bool = True):
    """Fila plegable de Grafana: agrupa paneles bajo un título."""
    return st.expander(titulo, expanded=abierta, key=f"fila-{clave}")


def rejilla(paneles: list[str], minimo: int = 190) -> None:
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


def ficha_escenario(d: Datos, nombre: str) -> dict:
    """Datos del manifiesto (técnica, descripción, huella) de un escenario."""
    for e in d.manifiesto.get("escenarios", []):
        if e["nombre"] == nombre:
            return e
    return {"tecnica": "", "nombre_tecnica": "", "descripcion": "", "huella": ""}


def items_alertas(d: Datos, eventos: pd.DataFrame) -> list[dict]:
    """Eventos para el panel «Alert list»: primero lo crítico, y dentro de cada tipo lo más reciente."""
    orden = eventos.assign(_p=(eventos["tipo_sugerido"] != "posible_ataque")).sort_values(
        ["_p", "inicio"], ascending=[True, False])
    items = []
    for _, e in orden.iterrows():
        f = ficha_escenario(d, e["escenario"])
        tecnica = f["tecnica"].replace(";", " + ")
        items.append({
            "tipo": e["tipo_sugerido"],
            "titulo": ESCENARIOS.get(e["escenario"], NOMBRES.get(e["variable_principal"], "Anomalía")),
            "detalle": (f"{tecnica} · " if tecnica else "") + NOMBRES.get(e["variable_principal"], "—"),
            "cuando": f'{calculos.fecha(e["inicio"])} · {calculos.duracion(e["horas"])}',
        })
    return items


def filas_eventos(eventos: pd.DataFrame) -> list[list[str]]:
    """Filas de la tabla de eventos: primero lo crítico, luego por fecha."""
    orden = eventos.assign(_p=(eventos["tipo_sugerido"] != "posible_ataque")).sort_values(["_p", "inicio"])
    return [[
        c.celda_severidad(e["tipo_sugerido"]),
        calculos.fecha(e["inicio"]),
        c.chip(e["tipo_sugerido"]),
        NOMBRES.get(e["variable_principal"], e["variable_principal"] or "—"),
        calculos.duracion(e["horas"]),
        ESCENARIOS.get(e["escenario"], e["escenario"] or "—"),
    ] for _, e in orden.iterrows()]


def grande(texto: str, px: int = 24) -> str:
    """Valor de un Stat que es texto largo (no número): un poco más chico."""
    return f'<span style="font-size: {px}px">{texto}</span>'


# ------------------------------------------------------------ resumen

def resumen(d: Datos, v: Vista) -> None:
    n = d.numeros
    pue_h = calculos.pue_por_hora(v.tabla)
    agua_h = calculos.por_hora(v.tabla, "agua_reposicion_l", "sum")
    enf_h = calculos.por_hora(v.tabla, "kw_enfriamiento")
    kwh, litros = cifra(n, "kwh_ahorrados_anual", 0), cifra(n, "litros_ahorrados_anual", 0)
    antes, despues = cifra(n, "pue_antes"), cifra(n, "pue_despues")
    n_atk = int((v.eventos["tipo_sugerido"] == "posible_ataque").sum())
    n_inef = int((v.eventos["tipo_sugerido"] == "ineficiencia").sum())

    # Arriba lo que se lee de un vistazo; abajo, en paneles anchos, los ahorros con su tendencia.
    rejilla([
        c.gauge("PUE con DripSafe", despues, 1.0, 2.0, PASOS_PUE, 3, sub=f"sin DripSafe: {c.numero(antes, 3)}",
                descripcion="Energía total entre energía de TI. Verde hasta 1.4, naranja hasta 1.6."),
        c.stat("Posibles ataques", str(n_atk), color="rojo" if n_atk else "verde", fondo=bool(n_atk),
               sub="eventos en el periodo"),
        c.stat("Ineficiencias", str(n_inef), color="naranja" if n_inef else "verde", sub="eventos en el periodo"),
        c.stat("Balance neto", c.numero(cifra(n, "balance_neto_veces")), "×", "verde",
               sub=f'El modelo gasta {c.numero(cifra(n, "kwh_modelo_anual"), 2)} kWh/año'),
        c.stat("Energía ahorrada", c.numero(kwh), "kWh/año", "azul", serie=enf_h.values, ancho=True,
               sub=f"{c.numero(kwh / (enf_h.mean() * 8760) * 100, 1)} % del enfriamiento anual"),
        c.stat("Agua ahorrada", c.numero(litros), "L/año", "azul", serie=agua_h.values, ancho=True,
               sub=f"{c.numero(litros / (agua_h.mean() * 8760) * 100, 1)} % de la reposición de la torre"),
    ], minimo=220)

    with fila("Eficiencia y alertas", "eficiencia"):
        izq, der = st.columns([2, 1], gap="small")
        with izq:
            panel_grafica("pue", "PUE por hora",
                          graficas.serie(pue_h.index, pue_h.values, "PUE", decimales=3, eventos=v.eventos, alto=280),
                          c.leyenda([("line", "PUE", calculos_leyenda(pue_h, 3))] + ANOTACIONES, ["Media", "Máx"]),
                          "Energía total entre energía de TI. Más bajo es mejor.")
        with der:
            caja = st.container(border=True, key="panel-alertas")
            caja.html(c.encabezado_panel("Alertas", "Primero las críticas; dentro de cada tipo, la más reciente."))
            caja.html(c.lista_alertas(items_alertas(d, v.eventos)[:6]))
            if caja.button("Ver todas en Monitoreo", icon=":material/arrow_forward:", type="tertiary"):
                ir("monitoreo")

    with fila("Detección", "deteccion"):
        izq, der = st.columns([1, 1], gap="small")
        det = d.deteccion
        with izq:
            st.html(c.panel("Ventana marcada por escenario", c.barras([
                (ESCENARIOS.get(x["escenario"], x["escenario"]), x["cobertura_pct"], 100,
                 ("rojo" if x["tipo"] == "ataque" else "naranja") if x["detectado"] else "gris",
                 f'{x["cobertura_pct"]:.0f} %')
                for _, x in det.iterrows()
            ]), "Qué parte de cada escenario simulado marcó el detector."))
        with der:
            atk = det[det["tipo"] == "ataque"]
            rejilla([
                c.stat("Escenarios detectados", str(cifra(n, "escenarios_detectados", "—")),
                       f'de {cifra(n, "escenarios_totales", "—")}', "verde"),
                c.stat("Ataques detectados", str(int(atk["detectado"].sum())), f"de {len(atk)}", "naranja",
                       sub="T0815 la atrapa una regla"),
                c.stat("Tiempo medio a la alerta", c.numero(det.loc[det["detectado"], "minutos_hasta_alerta"].mean()),
                       "min", "azul"),
                c.stat("Falsas alarmas", c.numero(cifra(n, "falsas_alarmas_por_dia"), 2), "por día", "verde"),
            ], minimo=170)


# ------------------------------------------------------------ demo de ataque

def demo(d: Datos) -> None:
    escenarios = {e["nombre"]: e for e in d.manifiesto["escenarios"]}
    nombres = list(escenarios)
    if st.session_state.get("demo_sel") not in nombres:
        st.session_state.demo_sel = "vista_repetida" if "vista_repetida" in nombres else nombres[0]
    st.session_state.setdefault("paso", 0)

    def mover(delta: int) -> None:
        st.session_state.paso = max(0, min(len(PASOS_DEMO) - 1, (st.session_state.get("paso") or 0) + delta))

    # Variables del dashboard: escenario y paso de la demo.
    var1, var2 = st.columns([2, 3], gap="small")
    elegido = var1.selectbox(
        "Escenario", nombres, key="demo_sel", on_change=lambda: st.session_state.update(paso=0),
        format_func=lambda x: f"{ESCENARIOS.get(x, x)} · {escenarios[x]['tecnica'].replace(';', ' + ') or 'Falla'}",
    )
    # Nombres cortos para que los 4 pasos quepan en una línea, como un grupo de botones de Grafana.
    cortos = ["Operador", "Física", "Detección", "Acción"]
    var2.segmented_control("Paso", list(range(len(PASOS_DEMO))), key="paso",
                           format_func=lambda i: f"{i + 1} · {cortos[i]}")
    paso = st.session_state.get("paso") or 0

    e = escenarios[elegido]
    tecnica = e["tecnica"].replace(";", " + ")
    st.html(f'<p class="lead"><b>{PASOS_DEMO[paso][0]}.</b> {PASOS_DEMO[paso][1]} '
            f'<span class="lead-m">{calculos.fecha(e["inicio"])} a {calculos.fecha(e["fin"])}</span></p>')

    guion = DEMO.get(elegido, {"operador": "kw_total", "evidencia": "kw_total", "comparar": None, "accion": ""})
    v = calculos.ventana(d.tabla, e["inicio"], e["fin"], margen_horas=4)
    ev = calculos.eventos(v) if paso >= 2 else None

    izq, der = st.columns(2, gap="small")
    with izq:
        op = guion["operador"]
        u, dec = UNIDADES.get(op, ("", 1))
        panel_grafica("op", f"Pantalla del operador · {NOMBRES.get(op, op)}",
                      graficas.serie(v["timestamp"], v[op], NOMBRES.get(op, op), u, dec, eventos=ev, alto=250,
                                     desde_cero=True),
                      c.leyenda([("line", NOMBRES.get(op, op), calculos_leyenda(v[op], dec, u))], ["Media", "Máx"]),
                      "Lo que muestra el SCADA. Es lo único que ve el operador.")
    with der:
        evi, comp = guion["evidencia"], guion["comparar"]
        if paso >= 1:
            u, dec = UNIDADES.get(evi, ("", 1))
            series = [("line", NOMBRES.get(evi, evi), calculos_leyenda(v[evi], dec, u))]
            if comp:
                series.append(("dash", NOMBRES.get(comp, comp), calculos_leyenda(v[comp], dec, u)))
            panel_grafica("ev", f"Otro sistema · {NOMBRES.get(evi, evi)}",
                          graficas.serie(v["timestamp"], v[evi], NOMBRES.get(evi, evi), u, dec, eventos=ev,
                                         comparar=v[comp] if comp else None, nombre_comparar=NOMBRES.get(comp, ""),
                                         alto=250, desde_cero=True),
                          c.leyenda(series, ["Media", "Máx"]),
                          "Una medición de un sistema distinto al SCADA (por ejemplo, el medidor de energía).")
        else:
            st.html(c.panel(f"Otro sistema · {NOMBRES.get(evi, evi)}",
                            '<div class="oculto">Se revela en el paso 2</div>'))

    paneles = [c.stat("Estado en el SCADA", grande("Normal", 28), color="verde", sub="lo que ve el operador")]
    if paso < 2:
        paneles.append(c.stat("DripSafe", grande("Analizando", 28), color="gris", sub="comparando la física"))
    else:
        fila_det = d.deteccion[d.deteccion["escenario"] == elegido]
        if len(fila_det) and bool(fila_det["detectado"].iloc[0]):
            minutos = fila_det["minutos_hasta_alerta"].iloc[0]
            tipo = ev["tipo_sugerido"].mode().iloc[0] if ev is not None and len(ev) else "posible_ataque"
            var = ev["variable_principal"].mode().iloc[0] if ev is not None and len(ev) else ""
            critica = tipo == "posible_ataque"
            paneles += [
                c.stat("DripSafe", grande("Posible ataque" if critica else "Ineficiencia", 28),
                       color="rojo" if critica else "naranja", fondo=True,
                       sub=f"alerta a los {c.numero(minutos)} min de empezar"),
                c.stat("Técnica MITRE ATT&CK for ICS", f'<span class="mono">{grande(tecnica or "—", 26)}</span>',
                       color="gris", sub=e["nombre_tecnica"] or "Falla de equipo"),
                c.stat("Variable que más pesó", grande(NOMBRES.get(var, var or "—"), 24), color="gris", sub=e["huella"]),
            ]
        else:
            paneles.append(c.stat("DripSafe", grande("Sin alerta del modelo", 24), color="amarillo",
                                  sub="este escenario lo atrapa una regla (docs/06)"))
    rejilla(paneles, minimo=220)

    if paso >= 3:
        st.html(c.aviso(
            f'<b>Qué hacer.</b> {guion["accion"]} DripSafe solo avisa; la decisión es del operador. '
            f'Detectarlo cuesta {c.numero(cifra(d.numeros, "kwh_modelo_anual"), 2)} kWh al año: '
            'el modelo corre en una laptop.'
        ))

    _, atras, adelante = st.columns([4, 1, 1], gap="small")
    atras.button("Anterior", icon=":material/chevron_left:", disabled=paso == 0, width="stretch",
                 on_click=mover, args=(-1,))
    adelante.button("Siguiente", icon=":material/chevron_right:", disabled=paso == len(PASOS_DEMO) - 1,
                    type="primary", width="stretch", on_click=mover, args=(1,))


# ------------------------------------------------------------ monitoreo

def monitoreo(d: Datos, v: Vista) -> None:
    t = v.tabla
    variables = {
        "PUE por hora": (calculos.pue_por_hora(t), None, "", 3, "Energía total entre energía de TI."),
        "Enfriamiento (kW)": (calculos.por_hora(t, "kw_enfriamiento"),
                              calculos.por_hora(t, "kw_esperado_enfriamiento") if "kw_esperado_enfriamiento" in t else None,
                              "kW", 0, "Chiller + bombas + torre, contra lo esperado sin anomalías."),
        "Agua de reposición (L/h)": (calculos.por_hora(t, "agua_reposicion_l", "sum"), None, "L/h", 0,
                                     "Agua que entra a la torre de enfriamiento cada hora."),
        "Temperatura de retorno (°C)": (calculos.por_hora(t, "t_retorno"), None, "°C", 2,
                                        "Agua que regresa de los servidores."),
    }
    opciones = {"Todas": ("posible_ataque", "ineficiencia"), "Posibles ataques": ("posible_ataque",),
                "Ineficiencias": ("ineficiencia",)}

    var1, var2 = st.columns([2, 3], gap="small")
    elegida = var1.selectbox("Variable", list(variables), key="mon_var")
    filtro = var2.segmented_control("Tipo de alerta", list(opciones), default="Todas", key="filtro") or "Todas"
    ev = v.eventos[v.eventos["tipo_sugerido"].isin(opciones[filtro])]

    y, esperado, unidad, dec, desc = variables[elegida]
    series = [("line", elegida, calculos_leyenda(y, dec, unidad))]
    if esperado is not None:
        series.append(("dash", "Esperado sin anomalías", calculos_leyenda(esperado, dec, unidad)))
    panel_grafica("monitoreo", elegida,
                  graficas.serie(y.index, y.values, elegida, unidad, dec, eventos=ev,
                                 comparar=esperado.values if esperado is not None else None, alto=340),
                  c.leyenda(series + ANOTACIONES, ["Media", "Máx"]), desc)

    with fila(f"Eventos ({len(ev)})", "eventos"):
        st.html(c.panel("Eventos marcados por el detector", c.tabla(
            ["Severidad", "Inicio", "Tipo", "Variable principal", "Duración", "Escenario simulado"],
            filas_eventos(ev), numericas=(4,)), "Primero las críticas, luego por fecha."))


# ------------------------------------------------------------ ciberseguridad

def ciberseguridad(d: Datos) -> None:
    det = d.deteccion
    ataques = det[det["tipo"] == "ataque"]
    r = d.resumen_deteccion
    rejilla([
        c.stat("Escenarios detectados", str(r["escenarios_detectados"]), f'de {r["escenarios_totales"]}', "verde",
               sub=f"{len(ataques)} ataques y {len(det) - len(ataques)} fallas simulados"),
        c.stat("Ataques detectados", str(int(ataques["detectado"].sum())), f"de {len(ataques)}", "naranja",
               sub="la denegación de vista la atrapa una regla"),
        c.stat("Tiempo medio a la alerta", c.numero(det.loc[det["detectado"], "minutos_hasta_alerta"].mean()), "min",
               "azul", sub="desde que empieza el escenario"),
        c.stat("Falsas alarmas", c.numero(r["falsas_alarmas_por_dia"], 2), "por día", "verde",
               sub="en horas normales"),
    ])

    with fila("Detección por escenario", "det"):
        izq, der = st.columns([2, 3], gap="small")
        with izq:
            st.html(c.panel("Ventana marcada", c.barras([
                (ESCENARIOS.get(x["escenario"], x["escenario"]), x["cobertura_pct"], 100,
                 ("rojo" if x["tipo"] == "ataque" else "naranja") if x["detectado"] else "gris",
                 f'{x["cobertura_pct"]:.0f} %')
                for _, x in det.iterrows()
            ]), "Qué parte de la ventana de cada escenario marcó el detector."))
        with der:
            filas = [[
                ESCENARIOS.get(x["escenario"], x["escenario"]),
                c.chip(x["tipo"]),
                f'<span class="mono">{x["tecnica"].replace(";", " + ") or "—"}</span>',
                c.chip("si" if x["detectado"] else "no"),
                c.numero(x["minutos_hasta_alerta"]) if x["detectado"] else "—",
            ] for _, x in det.iterrows()]
            st.html(c.panel("Resultado por escenario", c.tabla(
                ["Escenario", "Tipo", "Técnica", "Detectado", "Minutos a la alerta"], filas, numericas=(4,)),
                "Salida de src/ataques/evaluar.py: la evidencia del criterio de ciberseguridad."))

    with fila("Técnicas de MITRE ATT&CK for ICS", "attack"):
        rejilla([
            c.panel(f"{i} · {nom}", f'<p class="txt-d">{que}</p><p class="txt">{como}</p>')
            for i, nom, que, como in TECNICAS
        ], minimo=300)

    with fila("Guía de operación", "guia"):
        rejilla([
            c.panel("¿Falla o ataque?",
                    '<div class="cmp">'
                    f'<div>{c.chip("ineficiencia")}<ul class="clean"><li>Cambia la física de forma '
                    '<b>gradual y coherente</b></li><li>Afecta a varias variables a la vez</li>'
                    '<li>Ejemplo: el intercambiador se ensucia</li></ul></div>'
                    f'<div>{c.chip("posible_ataque")}<ul class="clean"><li>Lecturas que '
                    '<b>no cuadran con la física</b></li><li>Cambios bruscos o fuera de horario</li>'
                    '<li>Ejemplo: caudal normal con la bomba casi apagada</li></ul></div></div>'),
            c.panel("Cómo se instala sin abrir una puerta nueva",
                    '<ul class="clean">'
                    '<li><b>Solo lee:</b> recibe una copia del tráfico (puerto espejo o diodo de datos) y nunca manda órdenes.</li>'
                    '<li><b>Alerta a una persona:</b> no actúa solo sobre la planta.</li>'
                    '<li><b>Vive en su propia zona</b> de red, sin salida a internet.</li>'
                    '<li><b>Se entrena con periodos verificados como limpios</b> y cada versión queda registrada.</li></ul>',
                    "Basado en ISA/IEC 62443."),
        ], minimo=360)


# ------------------------------------------------------------ balance neto

def _posicion_log(valor: float) -> float:
    """Posición (0 a 100) en una escala logarítmica de 0.1 a 100 000."""
    return max(0.0, min(100.0, (math.log10(valor) + 1) / 6 * 100))


def balance(d: Datos) -> None:
    n = d.numeros
    gasto, ahorro = cifra(n, "kwh_modelo_anual", 0), cifra(n, "kwh_ahorrados_anual", 0)
    rejilla([
        c.stat("El modelo gasta", c.numero(gasto, 2), "kWh/año", "gris", sub="entrenamiento + inferencia (CodeCarbon)"),
        c.stat("DripSafe ahorra", c.numero(ahorro), "kWh/año", "azul", sub="enfriamiento que se deja de desperdiciar"),
        c.stat("Balance neto", f'+{c.numero(cifra(n, "balance_neto_kwh"))}', "kWh/año", "verde",
               sub=f'{c.numero(cifra(n, "balance_neto_veces"))} veces lo que consume'),
        c.stat("CO₂ del modelo", c.numero(cifra(n, "kg_co2e_modelo"), 4), "kg CO₂e", "verde", sub="por entrenamiento"),
    ])

    with fila("Lo que gasta contra lo que ahorra", "barras"):
        if gasto and ahorro:
            marcas = "".join(f'<span style="left: {_posicion_log(x):.1f}%">{"0.1" if x < 1 else c.numero(x)}</span>'
                             for x in (0.1, 1, 10, 100, 1000, 10000, 100000))
            st.html(c.panel("kWh por año (escala logarítmica)", c.barras([
                ("Lo que gasta el modelo", _posicion_log(gasto), 100, "gris", f"{c.numero(gasto, 2)} kWh/año"),
                ("Lo que ahorra DripSafe", _posicion_log(ahorro), 100, "azul", f"{c.numero(ahorro)} kWh/año"),
            ]) + f'<div class="logax">{marcas}</div>', "La diferencia es de varios órdenes de magnitud."))

    with fila("Cálculo y trazabilidad", "calculo"):
        izq, der = st.columns(2, gap="small")
        with izq:
            st.html(c.panel("Cómo se calcula",
                            '<div class="formula"><span>ahorro = Σ (enfriamiento real − esperado) durante las alertas</span>'
                            '<span>ahorro_anual = ahorro × 365 / días evaluados</span>'
                            '<span>balance = ahorro_anual − kWh del modelo</span>'
                            '<span>agua = kWh evitados × L por kWh de calor + reposición evitada</span></div>'
                            '<p class="txt-d">Si el operador corrige en cuanto llega la alerta, ese desperdicio se evita.</p>',
                            "Fórmulas de docs/05-solucion-tecnica.md."))
        with der:
            simulado = d.fuentes.get("numeros") == "simulado"
            filas = [[f'<span class="mono">{k}</span>',
                      c.numero(x["valor"], 3 if isinstance(x["valor"], float) and x["valor"] < 10 else 0),
                      RESPONSABLES.get(k, x.get("responsable", "—")), c.etiqueta_simulado(simulado)]
                     for k, x in n.items() if isinstance(x, dict) and isinstance(x.get("valor"), (int, float))]
            st.html(c.panel("De dónde sale cada número", c.tabla(["Cifra", "Valor", "Responsable", "Estado"], filas,
                                                                  numericas=(1,)),
                            "Todo sale de resultados/numeros_oficiales.json."))


# ------------------------------------------------------------ agua y acuífero

def agua(d: Datos, v: Vista) -> None:
    agua_h = calculos.por_hora(v.tabla, "agua_reposicion_l", "sum")
    rejilla([
        c.stat("Agua ahorrada", c.numero(cifra(d.numeros, "litros_ahorrados_anual")), "L/año", "azul",
               sub="reposición que deja de salir del acuífero"),
        c.stat("Reposición promedio", c.numero(agua_h.mean()), "L/h", "azul", serie=agua_h.values,
               sub="torre de enfriamiento"),
        c.stat("WUE actual", "[WUE]", "L/kWh", "gris", sub="pendiente: sale del kit (Nico, #15)"),
        c.stat("Agua potable con el bono", "0", "L", "verde", sub="meta del enfriamiento híbrido"),
    ])

    panel_grafica("agua", "Agua de reposición por hora",
                  graficas.serie(agua_h.index, agua_h.values, "Reposición", "L/h", 0, eventos=v.eventos, alto=260),
                  c.leyenda([("line", "Agua de reposición", calculos_leyenda(agua_h, 0, "L/h"))] + ANOTACIONES,
                            ["Media", "Máx"]),
                  "La fuga simulada se ve como agua extra sin calor extra que disipar.")

    with fila("Acuífero de Yucatán", "acuifero"):
        rejilla([c.panel(t, f'<p class="txt">{x}</p>') for t, x in HECHOS_ACUIFERO], minimo=280)
        st.html(c.panel("Impacto de DripSafe en el acuífero",
                        c.tabla(["Aspecto", "Pregunta", "Cómo ayuda DripSafe"],
                                [[f"<b>{a}</b>", p, x] for a, p, x in IMPACTO_ACUIFERO]),
                        "Fuentes por citar antes del pitch (Nico, #13)."))

    with fila("Bono · Cero agua dulce", "bono"):
        st.html(c.panel("Enfriamiento híbrido", c.tabla(
            ["Opción", "Ventaja", "Desventaja en Yucatán"], [[f"<b>{o}</b>", ve, de] for o, ve, de, _ in BONO],
            resaltar=tuple(i for i, b in enumerate(BONO) if b[3]))
            + c.aviso("La IA <b>recomienda</b> cuándo activar el respaldo con agua tratada y el operador "
                      "<b>confirma</b>. Así nadie que engañe al modelo controla el enfriamiento."),
            "Circuito cerrado como base y agua residual tratada solo en picos de calor."))
