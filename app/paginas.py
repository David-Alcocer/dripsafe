"""Las seis secciones del dashboard. Cada función dibuja una sección con Streamlit.

El HTML de las tarjetas sale de app/componentes.py y los textos de app/textos.py.
Todas las cifras salen de `d.numeros` (contrato 4) o de la telemetría y las alertas.
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

# Unidad y decimales con que se muestra cada variable en las gráficas.
UNIDADES = {
    "kw_ti": ("kW", 0), "kw_total": ("kW", 0), "kw_chiller": ("kW", 1), "kw_bombas": ("kW", 1),
    "kw_torre": ("kW", 1), "kw_enfriamiento": ("kW", 0), "kw_esperado_enfriamiento": ("kW", 0),
    "t_exterior": ("°C", 1), "t_suministro": ("°C", 2), "t_retorno": ("°C", 2), "setpoint_suministro": ("°C", 1),
    "flujo_m3h": ("m³/h", 1), "agua_reposicion_l": ("L", 0), "bomba_encendida": ("", 0), "calor_agua_kw": ("kW", 0),
}
LEYENDA_ALERTAS = (("atk", "Posible ataque"), ("inef", "Ineficiencia"))


@dataclass
class Vista:
    """Lo que se muestra según el periodo elegido en la barra lateral."""
    tabla: pd.DataFrame
    eventos: pd.DataFrame
    texto: str  # por ejemplo: 'Semana de evaluación · 08 al 14 oct 2026'


# ------------------------------------------------------------ utilidades

def ir(pagina: str) -> None:
    st.session_state.pagina = pagina
    st.rerun()


def titulo_seccion(titulo: str, subtitulo: str) -> None:
    st.html(f'<div class="sec-h"><h2>{titulo}</h2><p>{subtitulo}</p></div>')


def tarjeta(clave: str, titulo: str, subtitulo: str = "", derecha: str = "", ico: str = ""):
    """Panel con borde (estilo Grafana). Regresa el contenedor para meterle gráficas o HTML."""
    caja = st.container(border=True, key=f"card-{clave}")
    caja.html(c.encabezado(titulo, subtitulo, derecha, ico))
    return caja


def grafica(caja, fig) -> None:
    caja.plotly_chart(fig, config=graficas.CONFIG, theme=None, width="stretch")


def ficha_escenario(d: Datos, nombre: str) -> dict:
    """Datos del manifiesto (técnica, descripción, huella) de un escenario."""
    for e in d.manifiesto.get("escenarios", []):
        if e["nombre"] == nombre:
            return e
    return {"tecnica": "", "nombre_tecnica": "", "descripcion": "", "huella": ""}


def filas_eventos(eventos: pd.DataFrame) -> list[list[str]]:
    """Primero lo crítico (posibles ataques), luego por fecha."""
    orden = eventos.assign(_p=(eventos["tipo_sugerido"] != "posible_ataque")).sort_values(["_p", "inicio"])
    return [[
        c.severidad(e["tipo_sugerido"]),
        calculos.fecha(e["inicio"]),
        c.chip(e["tipo_sugerido"]),
        NOMBRES.get(e["variable_principal"], e["variable_principal"] or "—"),
        calculos.duracion(e["horas"]),
        ESCENARIOS.get(e["escenario"], e["escenario"] or "—"),
    ] for _, e in orden.iterrows()]


# ------------------------------------------------------------ resumen

def resumen(d: Datos, v: Vista) -> None:
    n = d.numeros
    minutos = round(d.tabla["timestamp"].diff().median().total_seconds() / 60)
    titulo_seccion("Resumen", f"{v.texto} · intervalos de {minutos} minutos")

    # Alerta prioritaria: el posible ataque más reciente del periodo.
    ataques = v.eventos[v.eventos["tipo_sugerido"] == "posible_ataque"]
    if len(ataques):
        e = ataques.iloc[-1]
        f = ficha_escenario(d, e["escenario"])
        tecnica = f["tecnica"].replace(";", " + ")
        st.html(
            '<div class="priority" role="region" aria-label="Alerta prioritaria">'
            f'<div class="pr-badge">{c.icono("alerta", 24)}</div><div>'
            f'<div class="pr-top"><span class="sev crit">Severidad crítica</span><span class="pr-meta">'
            f'{calculos.fecha(e["inicio"])} · duró {calculos.duracion(e["horas"])} · '
            f'<span class="mono">{tecnica}</span> {f["nombre_tecnica"]}</span></div>'
            f'<div class="pr-title">Posible ataque: {ESCENARIOS.get(e["escenario"], e["escenario"])}</div>'
            f'<div class="pr-desc">{f["descripcion"]} {f["huella"]}</div></div></div>'
        )
    else:
        st.html(c.aviso("Sin posibles ataques en el periodo.", "ok"))

    pue_h = calculos.pue_por_hora(v.tabla)
    agua_h = calculos.por_hora(v.tabla, "agua_reposicion_l", "sum")
    kwh, litros = cifra(n, "kwh_ahorrados_anual", 0), cifra(n, "litros_ahorrados_anual", 0)
    pct_enf = kwh / (v.tabla["kw_enfriamiento"].mean() * 8760) * 100
    pct_agua = litros / (agua_h.mean() * 8760) * 100
    antes, despues = cifra(n, "pue_antes"), cifra(n, "pue_despues")

    st.html(c.fila_metricas([
        c.metrica("PUE · antes → después",
                  f'{c.numero(antes, 3)} <span class="arrow">→</span> <span class="accent">{c.numero(despues, 3)}</span>',
                  extra=f'<div class="m-row">{c.delta(c.numero(antes - despues, 3))}'
                        f'<span class="m-c">sin DripSafe → con DripSafe</span></div>{c.chispa(pue_h.values)}',
                  principal=True),
        c.metrica("Energía ahorrada", c.numero(kwh), "kWh/año",
                  extra=f'<div class="m-row">{c.delta(c.numero(pct_enf, 1) + " %")}'
                        '<span class="m-c">del enfriamiento anual</span></div>'),
        c.metrica("Agua ahorrada", c.numero(litros), "L/año",
                  extra=f'<div class="m-row">{c.delta(c.numero(pct_agua, 1) + " %")}'
                        f'<span class="m-c">de la reposición de la torre</span></div>{c.chispa(agua_h.values)}'),
        c.metrica("Balance neto", f'<span class="accent">{c.numero(cifra(n, "balance_neto_veces"))}</span>', "×",
                  f'El modelo gasta {c.numero(cifra(n, "kwh_modelo_anual"), 2)} kWh/año y ahorra {c.numero(kwh)} kWh/año'),
    ]))

    izq, der = st.columns([2, 1], gap="medium")
    with izq:
        caja = tarjeta("pue", "PUE por hora", "Energía total entre energía de TI. Más bajo es mejor.",
                       c.leyenda(("line", "PUE"), *LEYENDA_ALERTAS))
        grafica(caja, graficas.serie(pue_h.index, pue_h.values, "PUE", decimales=3, eventos=v.eventos))
    with der:
        caja = tarjeta("recientes", "Alertas recientes", "Las últimas que marcó el detector")
        items = "".join(
            f'<div class="feed-i"><div class="feed-r"><span class="feed-t">'
            f'{NOMBRES.get(e["variable_principal"], e["variable_principal"] or "—")}</span>{c.chip(e["tipo_sugerido"])}</div>'
            f'<span class="feed-m">{calculos.fecha(e["inicio"])} · {calculos.duracion(e["horas"])}</span></div>'
            for _, e in v.eventos.tail(5).iloc[::-1].iterrows()
        )
        caja.html(f'<div class="feed">{items}</div>')
        if caja.button("Ver todas en Monitoreo", width="stretch"):
            ir("monitoreo")

    st.html(c.fila_metricas([
        c.metrica("Escenarios detectados", str(cifra(n, "escenarios_detectados", "—")),
                  f'de {cifra(n, "escenarios_totales", "—")}', "ataques y fallas simulados"),
        c.metrica("Posibles ataques", str(len(ataques)), contexto="eventos marcados"),
        c.metrica("Ineficiencias", str((v.eventos["tipo_sugerido"] == "ineficiencia").sum()), contexto="eventos marcados"),
        c.metrica("Falsas alarmas", c.numero(cifra(n, "falsas_alarmas_por_dia"), 2), contexto="por día en horas normales"),
    ]))


# ------------------------------------------------------------ demo de ataque

def demo(d: Datos) -> None:
    escenarios = {e["nombre"]: e for e in d.manifiesto["escenarios"]}
    nombres = list(escenarios)
    por_defecto = nombres.index("vista_repetida") if "vista_repetida" in nombres else 0

    # El título va arriba del selector, pero depende del escenario elegido: se reserva su lugar.
    cabecera = st.empty()
    elegido = st.selectbox(
        "Escenario", nombres, index=por_defecto, key="demo_sel",
        format_func=lambda x: f"{ESCENARIOS.get(x, x)} · {escenarios[x]['tecnica'].replace(';', ' + ') or 'Falla'}",
    )
    if st.session_state.get("demo_escenario") != elegido:
        st.session_state.demo_escenario = elegido
        st.session_state.paso = 0
    paso = st.session_state.get("paso", 0)
    e = escenarios[elegido]
    tecnica = e["tecnica"].replace(";", " + ")
    with cabecera:
        titulo_seccion(
            "Demo de ataque",
            f'Escenario <b>{ESCENARIOS.get(elegido, elegido)}</b>'
            + (f' · MITRE ATT&amp;CK for ICS <span class="mono">{tecnica}</span>' if tecnica else " · falla de equipo")
            + f' · {calculos.fecha(e["inicio"])} a {calculos.fecha(e["fin"])}',
        )

    # Pasos: el activo en azul.
    for i, (col, (titulo, _)) in enumerate(zip(st.columns(len(PASOS_DEMO)), PASOS_DEMO)):
        if col.button(f"{i + 1} · {titulo}", key=f"paso-{i}", type="primary" if i == paso else "secondary",
                      width="stretch"):
            st.session_state.paso = i
            st.rerun()
    st.html(f'<p class="lead">{PASOS_DEMO[paso][1]}</p>')

    guion = DEMO.get(elegido, {"operador": "kw_total", "evidencia": "kw_total", "comparar": None, "accion": ""})
    v = calculos.ventana(d.tabla, e["inicio"], e["fin"], margen_horas=4)
    ev = calculos.eventos(v) if paso >= 2 else None

    izq, der = st.columns(2, gap="medium")
    with izq:
        op = guion["operador"]
        caja = tarjeta("op", "Pantalla del operador", f"{NOMBRES.get(op, op)}, lo que muestra el SCADA", ico="pantalla")
        u, dec = UNIDADES.get(op, ("", 1))
        grafica(caja, graficas.serie(v["timestamp"], v[op], NOMBRES.get(op, op), u, dec, eventos=ev, alto=240, desde_cero=True))
        if paso < 2:
            caja.html(c.aviso("Estado en el SCADA: <b>todo en rango</b>", "ok"))
    with der:
        evi, comp = guion["evidencia"], guion["comparar"]
        caja = tarjeta("ev", "Lo que mide otro sistema", f"{NOMBRES.get(evi, evi)}, un sistema distinto al SCADA",
                       ico="rayo")
        if paso >= 1:
            u, dec = UNIDADES.get(evi, ("", 1))
            grafica(caja, graficas.serie(v["timestamp"], v[evi], NOMBRES.get(evi, evi), u, dec, eventos=ev,
                                         comparar=v[comp] if comp else None,
                                         nombre_comparar=NOMBRES.get(comp, ""), alto=240, desde_cero=True))
        else:
            caja.html('<div class="hidden-box">Se revela en el paso 2</div>')

    if paso >= 2:
        fila = d.deteccion[d.deteccion["escenario"] == elegido]
        if len(fila) and bool(fila["detectado"].iloc[0]):
            minutos = fila["minutos_hasta_alerta"].iloc[0]
            tipo = ev["tipo_sugerido"].mode().iloc[0] if ev is not None and len(ev) else "posible_ataque"
            var = ev["variable_principal"].mode().iloc[0] if ev is not None and len(ev) else ""
            st.html(c.fila_metricas([
                c.metrica("Alerta", f'<span style="font-size: 26px">{"Posible ataque" if tipo == "posible_ataque" else "Ineficiencia"}</span>',
                          extra=f'<span class="chip {"atk" if tipo == "posible_ataque" else "inef"}" style="align-self: flex-start">'
                                f'{c.icono("alerta", 12)}a los {c.numero(minutos)} min de empezar</span>'),
                c.metrica("Técnica MITRE ATT&CK for ICS", f'<span class="mono" style="font-size: 24px">{tecnica or "—"}</span>',
                          contexto=e["nombre_tecnica"] or "Falla de equipo"),
                c.metrica("Variable que más pesó", f'<span style="font-size: 26px">{NOMBRES.get(var, var or "—")}</span>',
                          contexto=e["huella"]),
            ], "grid3"))
        else:
            st.html(c.aviso("<b>Sin alerta del modelo.</b> Este escenario lo atrapa una regla, no el Isolation "
                            "Forest (ver docs/06).", "info"))

    if paso >= 3:
        st.html(c.aviso(
            f'<b>Qué hacer.</b> {guion["accion"]} DripSafe solo avisa; la decisión es del operador.'
            f'<br><span class="info-sub">Detectarlo cuesta {c.numero(cifra(d.numeros, "kwh_modelo_anual"), 2)} kWh '
            'al año: el modelo corre en una laptop.</span>'
        ))

    atras, _, adelante = st.columns([1, 3, 1])
    if atras.button("Anterior", icon=":material/chevron_left:", disabled=paso == 0, width="stretch"):
        st.session_state.paso = paso - 1
        st.rerun()
    if adelante.button("Siguiente", icon=":material/chevron_right:", disabled=paso == len(PASOS_DEMO) - 1,
                       type="primary", width="stretch"):
        st.session_state.paso = paso + 1
        st.rerun()


# ------------------------------------------------------------ monitoreo

def monitoreo(d: Datos, v: Vista) -> None:
    titulo_seccion("Monitoreo", f"{v.texto} · cada franja es un evento que marcó el detector")
    opciones = {"Todas": ("posible_ataque", "ineficiencia"), "Posibles ataques": ("posible_ataque",),
                "Ineficiencias": ("ineficiencia",)}
    filtro = st.segmented_control("Tipo de alerta", list(opciones), default="Todas", key="filtro") or "Todas"
    ev = v.eventos[v.eventos["tipo_sugerido"].isin(opciones[filtro])]

    t = v.tabla
    graficas_mon = [
        ("PUE por hora", "Energía total entre energía de TI", calculos.pue_por_hora(t), None, "", 3),
        ("Enfriamiento", "Chiller + bombas + torre, contra lo esperado sin anomalías",
         calculos.por_hora(t, "kw_enfriamiento"),
         calculos.por_hora(t, "kw_esperado_enfriamiento") if "kw_esperado_enfriamiento" in t else None, "kW", 0),
        ("Agua de reposición", "Agua que entra a la torre de enfriamiento cada hora",
         calculos.por_hora(t, "agua_reposicion_l", "sum"), None, "L/h", 0),
        ("Temperatura de retorno", "Agua que regresa de los servidores", calculos.por_hora(t, "t_retorno"), None, "°C", 2),
    ]
    for i, (pestana, (titulo, sub, y, esperado, unidad, dec)) in enumerate(zip(st.tabs([g[0] for g in graficas_mon]),
                                                                               graficas_mon)):
        with pestana:
            items = [("line", titulo)] + ([("dash", "Esperado sin anomalías")] if esperado is not None else [])
            caja = tarjeta(f"mon-{i}", titulo + (f" ({unidad})" if unidad else ""), sub,
                           c.leyenda(*items, *LEYENDA_ALERTAS))
            grafica(caja, graficas.serie(y.index, y.values, titulo, unidad, dec, eventos=ev,
                                         comparar=esperado.values if esperado is not None else None))

    caja = tarjeta("tabla-alertas", "Alertas", f"{len(ev)} eventos con el filtro actual")
    caja.html(c.tabla(["Severidad", "Inicio", "Tipo", "Variable principal", "Duración", "Escenario simulado"],
                      filas_eventos(ev), numericas=(4,)))


# ------------------------------------------------------------ ciberseguridad

def ciberseguridad(d: Datos) -> None:
    titulo_seccion("Ciberseguridad OT", "Ataques y fallas simulados sobre la telemetría. Ninguno toca un sistema real.")
    det = d.deteccion
    ataques = det[det["tipo"] == "ataque"]
    detectados = det[det["detectado"]]
    r = d.resumen_deteccion
    st.html(c.fila_metricas([
        c.metrica("Escenarios detectados", str(r["escenarios_detectados"]), f'de {r["escenarios_totales"]}',
                  f'{len(ataques)} ataques y {len(det) - len(ataques)} fallas'),
        c.metrica("Ataques detectados", str(int(ataques["detectado"].sum())), f"de {len(ataques)}",
                  "la denegación de vista la atrapa una regla"),
        c.metrica("Tiempo medio a la alerta", c.numero(detectados["minutos_hasta_alerta"].mean()), "min",
                  "desde que empieza el escenario"),
        c.metrica("Falsas alarmas", c.numero(r["falsas_alarmas_por_dia"], 2), contexto="por día en horas normales"),
    ]))

    caja = tarjeta("deteccion", "Detección por escenario",
                   'Salida de <span class="mono">src/ataques/evaluar.py</span>: la evidencia para el criterio de ciberseguridad')
    filas = [[
        ESCENARIOS.get(x["escenario"], x["escenario"]),
        c.chip(x["tipo"]),
        f'<span class="mono">{x["tecnica"].replace(";", " + ") or "—"}</span>',
        c.chip("si" if x["detectado"] else "no"),
        c.numero(x["minutos_hasta_alerta"]) if x["detectado"] else "—",
        c.progreso(x["cobertura_pct"]),
    ] for _, x in det.iterrows()]
    caja.html(c.tabla(["Escenario", "Tipo", "Técnica", "Detectado", "Minutos a la alerta", "Ventana marcada"],
                      filas, numericas=(4,)))

    caja = tarjeta("tecnicas", "Técnicas de MITRE ATT&CK for ICS que cubre DripSafe",
                   "Cada ataque deja una huella física que no cuadra")
    caja.html('<div class="grid3">' + "".join(
        f'<div class="tech"><span class="tech-id">{i}</span><span class="tech-n">{nom}</span>'
        f'<span class="tech-d">{que}</span><span class="tech-h">{como}</span></div>'
        for i, nom, que, como in TECNICAS) + "</div>")

    izq, der = st.columns(2, gap="medium")
    with izq:
        caja = tarjeta("falla-ataque", "¿Falla o ataque?", "Cómo el detector sugiere el tipo de alerta")
        caja.html(
            '<div class="cmp">'
            f'<div class="cmp-c">{c.chip("ineficiencia")}<ul class="clean"><li>Cambia la física de forma '
            '<b>gradual y coherente</b></li><li>Afecta a varias variables a la vez</li>'
            '<li>Ejemplo: el intercambiador se ensucia</li></ul></div>'
            f'<div class="cmp-c">{c.chip("posible_ataque")}<ul class="clean"><li>Lecturas que '
            '<b>no cuadran con la física</b></li><li>Cambios bruscos o fuera de horario</li>'
            '<li>Ejemplo: caudal normal con la bomba casi apagada</li></ul></div></div>'
        )
    with der:
        caja = tarjeta("instalacion", "Cómo se instala sin abrir una puerta nueva", "Basado en ISA/IEC 62443")
        caja.html(
            '<ul class="clean">'
            '<li><b>Solo lee:</b> recibe una copia del tráfico (puerto espejo o diodo de datos) y nunca manda órdenes.</li>'
            '<li><b>Alerta a una persona:</b> no actúa solo sobre la planta.</li>'
            '<li><b>Vive en su propia zona</b> de red, sin salida a internet.</li>'
            '<li><b>Se entrena con periodos verificados como limpios</b> y cada versión queda registrada.</li></ul>'
        )


# ------------------------------------------------------------ balance neto

def _posicion_log(valor: float) -> float:
    """Posición (0 a 100 %) en una escala logarítmica de 0.1 a 100 000."""
    return max(0.0, min(100.0, (math.log10(valor) + 1) / 6 * 100))


def balance(d: Datos) -> None:
    n = d.numeros
    titulo_seccion("Balance neto", "Requisito obligatorio: la energía y el CO₂ del modelo deben ser menores que lo que ahorra")
    gasto, ahorro = cifra(n, "kwh_modelo_anual", 0), cifra(n, "kwh_ahorrados_anual", 0)
    st.html(c.fila_metricas([
        c.metrica("El modelo gasta", c.numero(gasto, 2), "kWh/año", "entrenamiento + inferencia (CodeCarbon)"),
        c.metrica("DripSafe ahorra", c.numero(ahorro), "kWh/año", "enfriamiento que se deja de desperdiciar"),
        c.metrica("Balance neto", f'+{c.numero(cifra(n, "balance_neto_kwh"))}', "kWh/año",
                  extra=f'<span class="delta good">{c.numero(cifra(n, "balance_neto_veces"))}× lo que consume</span>'),
        c.metrica("CO₂ del modelo", c.numero(cifra(n, "kg_co2e_modelo"), 4), "kg CO₂e", "por entrenamiento"),
    ]))

    caja = tarjeta("barras", "Lo que gasta contra lo que ahorra",
                   "Escala logarítmica: la diferencia es de varios órdenes de magnitud")
    if gasto and ahorro:
        pg, pa = _posicion_log(gasto), _posicion_log(ahorro)
        marcas = "".join(f'<span style="left: {_posicion_log(x):.1f}%">{"0.1" if x < 1 else c.numero(x)}</span>'
                         for x in (0.1, 1, 10, 100, 1000, 10000, 100000))
        caja.html(
            '<div class="bars">'
            f'<div class="bar-r"><span class="bar-l">Lo que gasta el modelo</span><div class="bar-t">'
            f'<div class="bar-b model" style="width: {pg:.1f}%"></div>'
            f'<span class="bar-v" style="left: {pg:.1f}%">{c.numero(gasto, 2)} kWh/año</span></div></div>'
            f'<div class="bar-r"><span class="bar-l">Lo que ahorra</span><div class="bar-t">'
            f'<div class="bar-b save" style="width: {pa:.1f}%"></div>'
            f'<span class="bar-v" style="left: {min(pa, 62):.1f}%">{c.numero(ahorro)} kWh/año</span></div></div>'
            f'</div><div class="logax">{marcas}</div>'
        )

    izq, der = st.columns(2, gap="medium")
    with izq:
        caja = tarjeta("formulas", "Cómo se calcula", 'Fórmulas de <span class="mono">docs/05-solucion-tecnica.md</span>')
        caja.html(
            '<div class="formula"><span>ahorro = Σ (enfriamiento real − esperado) durante las alertas</span>'
            '<span>ahorro_anual = ahorro × 365 / días evaluados</span>'
            '<span>balance = ahorro_anual − kWh del modelo</span>'
            '<span>agua = kWh evitados × L por kWh de calor + reposición evitada</span></div>'
            '<p class="muted">Si el operador corrige en cuanto llega la alerta, ese desperdicio se evita.</p>'
        )
    with der:
        caja = tarjeta("origen", "De dónde sale cada número",
                       'Todo sale de <span class="mono">resultados/numeros_oficiales.json</span>')
        simulado = d.fuentes.get("numeros") == "simulado"
        filas = [[f'<span class="mono">{k}</span>', c.numero(v["valor"], 3 if isinstance(v["valor"], float) and v["valor"] < 10 else 0),
                  RESPONSABLES.get(k, v.get("responsable", "—")), c.etiqueta_simulado(simulado)]
                 for k, v in n.items() if isinstance(v, dict) and isinstance(v.get("valor"), (int, float))]
        caja.html(c.tabla(["Cifra", "Valor", "Responsable", "Estado"], filas, numericas=(1,)))


# ------------------------------------------------------------ agua y acuífero

def agua(d: Datos, v: Vista) -> None:
    titulo_seccion("Agua y acuífero de Yucatán",
                   "Requisito obligatorio: impacto en el acuífero · Bono: cero agua dulce potable")
    agua_h = calculos.por_hora(v.tabla, "agua_reposicion_l", "sum")
    st.html(c.fila_metricas([
        c.metrica("Agua ahorrada", c.numero(cifra(d.numeros, "litros_ahorrados_anual")), "L/año",
                  "reposición que deja de salir del acuífero"),
        c.metrica("Reposición promedio", c.numero(agua_h.mean()), "L/h", "torre de enfriamiento"),
        c.metrica("WUE actual", "[WUE]", "L/kWh", "pendiente: sale del kit (Nico, #15)"),
        c.metrica("Agua potable con el bono", "0", "L", "meta del enfriamiento híbrido"),
    ]))

    caja = tarjeta("agua", "Reposición de agua por hora", "La fuga simulada se ve como agua extra sin calor extra que disipar",
                   c.leyenda(("line", "Agua de reposición"), *LEYENDA_ALERTAS))
    grafica(caja, graficas.serie(agua_h.index, agua_h.values, "Reposición", "L/h", 0, eventos=v.eventos, alto=240))

    caja = tarjeta("acuifero", "Por qué el acuífero de Yucatán es especial", "Fuentes por citar antes del pitch (Nico, #13)")
    caja.html('<div class="grid3">' + "".join(
        f'<div class="fact"><span class="fact-t">{t}</span><span class="fact-d">{x}</span></div>'
        for t, x in HECHOS_ACUIFERO) + "</div>")

    caja = tarjeta("impacto", "Impacto de DripSafe en el acuífero", "Cinco aspectos del análisis obligatorio")
    caja.html(c.tabla(["Aspecto", "Pregunta", "Cómo ayuda DripSafe"], [[f"<b>{a}</b>", p, x] for a, p, x in IMPACTO_ACUIFERO]))

    caja = tarjeta("bono", "Bono · Cero agua dulce: enfriamiento híbrido",
                   "Circuito cerrado como base y agua residual tratada solo en picos de calor")
    caja.html(c.tabla(["Opción", "Ventaja", "Desventaja en Yucatán"], [[f"<b>{o}</b>", ve, de] for o, ve, de, _ in BONO],
                      resaltar=tuple(i for i, b in enumerate(BONO) if b[3])))
    caja.html(c.aviso("La IA <b>recomienda</b> cuándo activar el respaldo con agua tratada y el operador <b>confirma</b>. "
                      "Así nadie que engañe al modelo controla el enfriamiento."))
