"""Textos del dashboard en un solo lugar, para que cualquiera los corrija sin tocar la lógica.

Guille: revisa CLASES, DEMO y TECNICAS (ciberseguridad) y HECHOS_ACUIFERO e IMPACTO_ACUIFERO (acuífero, D13).
Misa: revisa BONO y EPOCAS (bono, D13).
Nico: revisa LIMITES y TIPOS_CIFRA (qué es medido, estimado o proyectado).
"""

SITIOS = {"SIM-A": "SIM-A · aire", "SIM-B": "SIM-B · evaporativa", "SIM-C": "SIM-C · líquida"}

# Nombre y unidad de cada variable del kit (y de las derivadas que calcula la app).
NOMBRES = {
    "pue": "PUE",
    "wue": "Agua por energía IT (L/kWh)",
    "energy_total_kwh": "Energía total (kWh)",
    "energy_it_kwh": "Energía IT (kWh)",
    "energia_no_ti_kwh": "Energía no TI (kWh)",
    "water_l": "Agua captada (L)",
    "inlet_temp_c": "Temperatura de entrada (°C)",
    "outdoor_temp_c": "Temperatura exterior (°C)",
    "load_pct": "Carga (%)",
    "ot_codigo": "Eventos OT",
}
UNIDADES = {
    "pue": ("", 3), "wue": ("L/kWh", 2), "energy_total_kwh": ("kWh", 0), "energy_it_kwh": ("kWh", 0),
    "energia_no_ti_kwh": ("kWh", 1), "water_l": ("L", 0), "inlet_temp_c": ("°C", 1),
    "outdoor_temp_c": ("°C", 1), "load_pct": ("%", 0), "ot_codigo": ("", 0),
}

# Variables que vigila la línea base: (columna real, columna esperada, residuo, unidad del residuo).
VIGILADAS = {
    "energia": ("energia_no_ti_kwh", "esperado_energia_no_ti_kwh", "residuo_energia_pct", "%"),
    "agua": ("water_l", "esperado_agua_l", "residuo_agua_pct", "%"),
    "entrada": ("inlet_temp_c", "esperado_entrada_c", "residuo_entrada_c", "°C"),
}
NOMBRE_VIGILADA = {"energia": "Energía no TI", "agua": "Agua captada", "entrada": "Temperatura de entrada"}

EVENTOS_OT = {"normal": 0, "login_fallido": 1, "cambio_config_no_autorizado": 2}
EVENTOS_OT_TEXTO = {"login_fallido": "Login fallido", "cambio_config_no_autorizado": "Cambio de configuración no autorizado"}

ESCENARIOS = {
    "evento_ot": "Evento OT",
    "fuga_agua": "Fuga de agua",
    "ineficiencia": "Ineficiencia energética",
}

# Las cuatro clases de alerta del MVP (plan de ejecución y propuesta, §3.3), en orden de prioridad.
# (nombre, severidad, color, qué significa, acción sugerida). La propuesta la valida Guille (U1).
CLASES = {
    "incidente_ot": (
        "Incidente OT con efecto", "Crítica", "rojo",
        "Evento OT y, desde su inicio hasta 24 h después de su fin, un exceso físico que empieza después del evento.",
        "Restaurar la configuración aprobada y pasar a modo seguro manual. Confirmar en sitio.",
    ),
    "cambio_no_autorizado": (
        "Cambio no autorizado", "Alta", "rojo",
        "Cambio de configuración no autorizado, con o sin efecto físico por ahora.",
        "Comparar contra la configuración aprobada y vigilar 24 h: puede notarse en el siguiente pico de calor.",
    ),
    "escalon_sin_registro": (
        "Escalón sin registro", "Alta", "naranja",
        "Exceso físico sin evento OT: falla brusca o cambio no registrado. Con datos de proceso no se distinguen.",
        "Primero comparar los setpoints contra la versión aprobada (minutos). Si el exceso es de agua, "
        "inspección física en paralelo (posible fuga). Después, mantenimiento.",
    ),
    "intento_acceso": (
        "Intento de acceso", "Media", "amarillo",
        "Logins fallidos sin cambio de configuración ni efecto físico.",
        "Revisar accesos y cuentas. Un login fallido no prueba una intrusión.",
    ),
}
ORDEN_CLASES = list(CLASES)

# Qué tan firme es cada cifra (lo pide la guía del kit). Clave = valor de "tipo" en numeros_oficiales.json.
TIPOS_CIFRA = {
    "observado": ("Observado", "Sale directo de los datos del kit (simulados)."),
    "medido": ("Medido", "Medido en la laptop del equipo, con repeticiones."),
    "estimado": ("Estimado", "Calculado con un modelo o con supuestos declarados."),
    "proyectado": ("Proyectado", "Escenario a futuro con parámetros editables: no es un ahorro observado."),
    "ejemplo": ("Ejemplo", "Valor ficticio para probar la interfaz. No va al pitch."),
    "vista_previa": ("Vista previa", "Calculado por la app mientras llega la cifra oficial."),
}

# Para cada escenario del kit: qué ve el operador, qué variable delata el problema y qué se aprende.
DEMO = {
    "evento_ot": {
        "operador": "inlet_temp_c", "evidencia": "ot_codigo", "vigilada": "energia",
        "tecnica": "T0859 + T0836", "nombre_tecnica": "Valid Accounts + Modify Parameter (propuesta)",
        "huella": "Tres logins fallidos de madrugada y luego un cambio de configuración. La energía no TI sigue "
                  "dentro de lo esperado: por ahora el cambio no tiene efecto físico.",
    },
    "fuga_agua": {
        "operador": "load_pct", "evidencia": "water_l", "vigilada": "agua",
        "tecnica": "", "nombre_tecnica": "Sin evento OT: falla o cambio no registrado",
        "huella": "Entra mucha más agua de la esperada para esa carga y ese clima, sin ningún evento OT.",
    },
    "ineficiencia": {
        "operador": "load_pct", "evidencia": "energia_no_ti_kwh", "vigilada": "energia",
        "tecnica": "", "nombre_tecnica": "Sin evento OT: falla o cambio no registrado",
        "huella": "La energía no TI sube muy por encima de lo esperado para esa carga y ese clima, "
                  "y la temperatura de entrada también.",
    },
}

PASOS_DEMO = [
    ("Lo que ve el operador", "En la pantalla todo parece normal: la carga y las temperaturas no cambian."),
    ("Real contra esperado", "DripSafe compara cada hora con lo que el sitio debería gastar según su carga y su clima."),
    ("DripSafe lo clasifica", "La alerta llega con su clase, su motivo legible y qué tan grande es el exceso."),
    ("Qué hacer", "Cada clase propone una revisión humana concreta. DripSafe nunca actúa solo."),
]

# (ID, nombre, qué es, cómo se ve en DripSafe, estado: 'kit' observable, 'inyectada' o 'fuera' de alcance)
TECNICAS = [
    ("T0859", "Valid Accounts", "Alguien intenta entrar con cuentas válidas o adivinadas.",
     "Logins fallidos fuera de horario (login_fallido en SIM-C): clase «intento de acceso».", "kit"),
    ("T0836", "Modify Parameter", "Alguien cambia un parámetro de configuración sin autorización.",
     "Cambio de configuración no autorizado (SIM-C): clase «cambio no autorizado».", "kit"),
    ("T0831", "Manipulation of Control", "El atacante altera el control físico del proceso.",
     "Exceso de energía después de un evento OT: clase «incidente OT con efecto» (se inyecta).", "inyectada"),
    ("T0855", "Unauthorized Command Message", "Llegan órdenes no autorizadas a bombas o válvulas.",
     "Escalón sin evento OT: «escalón sin registro», se revisa la configuración antes de mantenimiento.", "inyectada"),
    ("T0856", "Spoof Reporting Message", "Un sensor reporta valores inventados pero creíbles.",
     "Requiere caudal y temperaturas del agua, que el kit no trae.", "fuera"),
    ("T0832", "Manipulation of View", "El operador ve datos falsos en su pantalla.",
     "Requiere un balance de calor con sensores que el kit no trae.", "fuera"),
]
ESTADO_TECNICA = {"kit": ("Observable en el kit", "ok"), "inyectada": ("Se inyecta", "est"),
                  "fuera": ("Fuera de alcance del kit", "sim")}

# Fuente: docs/07-agua-y-acuifero.md (Guille cita las fuentes en #13; ver ~/hackathon/Papers).
HECHOS_ACUIFERO = [
    ("Suelo kárstico", "Roca caliza porosa y fracturada: el agua se infiltra rápido y corre por conductos y cenotes conectados."),
    ("Nivel freático somero", "El agua subterránea está a pocos metros de la superficie, sobre todo en el norte del estado."),
    ("Sin ríos superficiales", "El acuífero Península de Yucatán (CONAGUA 3105) es prácticamente la única fuente de agua."),
    ("Muy vulnerable", "Lo que se vierte en la superficie llega rápido al agua subterránea: el riesgo principal es la calidad."),
    ("Intrusión salina", "Cerca de la costa, extraer de más permite que entre agua de mar."),
    ("Anillo de Cenotes", "Reserva geohidrológica clave para el abasto de agua de Mérida."),
]

IMPACTO_ACUIFERO = [
    ("Extracción", "¿Cuánta agua deja de extraerse?",
     "Detecta fugas y excesos en sitios evaporativos. En sitios enfriados por aire el ahorro es de energía, no de agua."),
    ("Descargas", "¿Qué pasa con el agua de purga?",
     "Purga = evaporación ÷ (ciclos − 1). Con 4 ciclos, cada litro captado de más evitado ahorra ¼ L de purga."),
    ("Contaminación", "¿Puede llegar a cenotes o al freático?",
     "La purga del bono nunca se infiltra: regresa por drenaje a la planta de tratamiento."),
    ("Gobernanza", "¿Quién regula y qué permisos aplican?",
     "Reporte mensual verificable de consumo, litros evitados y purga, útil para la concesión de CONAGUA."),
    ("Justicia ambiental", "¿A quién le quita agua el centro de datos?",
     "La cola de alertas prioriza litros: lo evitado queda para las comunidades del mismo acuífero."),
]

# Épocas del año en Yucatán para el enfriamiento (propuesta §3.4). Rangos por confirmar con SMN o ERA5.
EPOCAS = [
    ("Secas calurosas", "marzo – mayo", "Calor extremo y aire seco; máximas medias de unos 37 °C en abril y mayo.",
     "El enfriador seco se queda corto en las tardes: más horas de respaldo y PUE más alto."),
    ("Lluvias", "junio – octubre", "Calor con humedad muy alta.",
     "Al evaporativo le afecta el bulbo húmedo: a igual temperatura rinde menos y gasta más."),
    ("Nortes", "noviembre – febrero", "Más fresco, con frentes fríos.",
     "Más horas de enfriamiento gratuito: PUE y agua más bajos."),
]

# Bono (propuesta §7): (opción, qué es, costo o riesgo, ¿es el plan?)
BONO = [
    ("Base · circuito cerrado W40", "Enfriamiento líquido de agua tibia; el calor sale por enfriadores secos, sin evaporar agua.",
     "Para obra nueva o renovación con servidores de enfriamiento líquido.", True),
    ("Respaldo B · chiller mecánico", "En picos de calor, un chiller de apoyo. Cero agua.",
     "Sube el PUE en esas horas: se reporta el PUE anual con y sin bono.", True),
    ("Respaldo A · adiabático con agua tratada", "Evapora agua residual tratada, nunca potable.",
     "Depende de un convenio con JAPAY; mejora futura, no el plan.", False),
    ("Agua pluvial y condensado", "Complemento para el llenado y la reposición del circuito.",
     "Abril y mayo llegan antes de las lluvias: es parcial.", False),
]

# Límites que la guía del kit pide declarar en la demo y en la presentación.
LIMITES = [
    ("Datos simulados", "Tres sitios ficticios durante siete días, con un generador casi lineal. "
                        "La validación demuestra el método, no su eficacia en una planta real."),
    ("Sin balance de calor", "El kit no trae caudal ni temperaturas del agua: no se detectan sensores falsificados "
                             "por balance de calor (T0856, T0832)."),
    ("Falla brusca contra cambio sin registro", "Con datos de proceso no se distinguen. DripSafe no los separa: "
                                               "manda a revisar la configuración antes de mantenimiento."),
    ("Épocas del año", "El kit cubre una semana de 15 a 31 °C. Las líneas base por época y la humedad no se "
                       "pueden probar con el kit."),
    ("Energía del detector", "El tiempo de CPU se mide; la energía y el CO₂ se estiman con supuestos editables."),
    ("Ahorro proyectado", "El ahorro anual es un escenario con parámetros editables. No es un ahorro observado."),
]

KIT_VS_EQUIPO = {
    "Del kit CIFOX": [
        "CSV simulado de 3 sitios × 168 horas y su diccionario de datos",
        "Fórmulas de PUE y WUE con sumas",
        "Reglas didácticas fijas (PUE, agua, temperatura, evento OT)",
        "Corrida de ejemplo de reglas contra Isolation Forest",
    ],
    "Aporte de DripSafe": [
        "Línea base física por sitio: lo que cada sitio debería gastar según su carga y su clima",
        "Cuatro clases de alerta que cruzan el registro OT con el efecto físico",
        "Curva de sensibilidad contra las reglas fijas y umbral de equilibrio del detector",
        "Dashboard con estructura de Grafana, procedencia de cada cifra y modo presentación",
        "Mapeo a MITRE ATT&CK for ICS, acuífero de Yucatán y bono de cero agua potable",
    ],
}
