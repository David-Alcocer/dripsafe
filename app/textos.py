"""Textos del dashboard en un solo lugar, para que cualquiera los corrija sin tocar la lógica.

Guille: revisa las acciones recomendadas de los ataques (DEMO[...]["accion"]).
"""

NOMBRES = {
    "kw_ti": "Carga de TI (kW)",
    "kw_total": "Potencia total (kW)",
    "kw_chiller": "Chiller (kW)",
    "kw_bombas": "Bombas (kW)",
    "kw_torre": "Torre de enfriamiento (kW)",
    "kw_enfriamiento": "Enfriamiento total (kW)",
    "kw_esperado_enfriamiento": "Enfriamiento esperado (kW)",
    "t_exterior": "Temperatura exterior (°C)",
    "t_suministro": "Agua helada que sale (°C)",
    "t_retorno": "Agua que regresa (°C)",
    "setpoint_suministro": "Setpoint del agua helada (°C)",
    "flujo_m3h": "Caudal de agua helada (m³/h)",
    "agua_reposicion_l": "Agua de reposición (L por intervalo)",
    "bomba_encendida": "Bomba encendida (0/1)",
    "calor_agua_kw": "Calor que saca el agua (kW)",
    "pue": "PUE por hora",
}

TIPOS = {"normal": "Normal", "ineficiencia": "Ineficiencia", "posible_ataque": "Posible ataque"}
TIPOS_REALES = {"normal": "Normal", "falla": "Falla", "ataque": "Ataque"}

# Para cada escenario: qué ve el operador en su pantalla, qué variable delata el problema,
# con qué se compara (misma unidad, misma gráfica) y qué hacer.
DEMO = {
    "vista_repetida": {
        "operador": "flujo_m3h",
        "evidencia": "kw_bombas",
        "comparar": None,
        "accion": "No confiar en la pantalla: verificar el caudal y la bomba en sitio, revisar quién "
                  "tiene acceso al HMI/SCADA y aislar el segmento de red OT afectado.",
    },
    "setpoint_alterado": {
        "operador": "setpoint_suministro",
        "evidencia": "kw_enfriamiento",
        "comparar": "kw_esperado_enfriamiento",
        "accion": "Regresar el setpoint a su valor y revisar en la bitácora del PLC quién lo cambió. "
                  "Si no fue un operador, cambiar credenciales y restringir la escritura de parámetros.",
    },
    "sensor_falsificado": {
        "operador": "t_retorno",
        "evidencia": "calor_agua_kw",
        "comparar": "kw_ti",
        "accion": "Comparar contra un sensor de respaldo o una medición manual y revisar la "
                  "comunicación del sensor (Modbus no autentica los mensajes).",
    },
    "comandos_no_autorizados": {
        "operador": "bomba_encendida",
        "evidencia": "kw_bombas",
        "comparar": None,
        "accion": "Bloquear las órdenes remotas a la bomba, identificar el origen de los comandos y "
                  "limitar qué equipos pueden escribir en el PLC.",
    },
    "denegacion_de_vista": {
        "operador": "t_retorno",
        "evidencia": "kw_total",
        "comparar": None,
        "accion": "Pasar a monitoreo local y revisar la red OT: los medidores de energía siguen "
                  "reportando, así que el corte es solo de la telemetría de proceso.",
    },
    "ensuciamiento": {
        "operador": "t_suministro",
        "evidencia": "kw_enfriamiento",
        "comparar": "kw_esperado_enfriamiento",
        "accion": "Programar la limpieza del intercambiador. El consumo extra desaparece al limpiarlo.",
    },
    "sensor_atorado": {
        "operador": "t_retorno",
        "evidencia": "calor_agua_kw",
        "comparar": "kw_ti",
        "accion": "Mantenimiento: revisar o cambiar el sensor de retorno.",
    },
    "fuga_reposicion": {
        "operador": "flujo_m3h",
        "evidencia": "agua_reposicion_l",
        "comparar": None,
        "accion": "Revisar la válvula de reposición y el nivel de la torre: cada hora de fuga es agua "
                  "que sale del acuífero.",
    },
}

PASOS_DEMO = [
    ("Lo que ve el operador", "En la pantalla del SCADA todo parece normal."),
    ("Lo que dice la física", "Otra medición, de un sistema distinto, cuenta otra historia."),
    ("DripSafe lo marca", "El detector nota que las variables ya no cuadran entre sí."),
    ("Qué hacer", "La alerta llega con su técnica de ataque y una acción concreta para el operador."),
]

ESCENARIOS = {
    "comandos_no_autorizados": "Comandos no autorizados",
    "denegacion_de_vista": "Denegación de vista",
    "vista_repetida": "Vista repetida",
    "fuga_reposicion": "Fuga en la reposición",
    "sensor_atorado": "Sensor atorado",
    "sensor_falsificado": "Sensor falsificado",
    "ensuciamiento": "Ensuciamiento del intercambiador",
    "setpoint_alterado": "Setpoint alterado",
}

# (ID, nombre, qué es, cómo lo detecta DripSafe). Fuente: docs/06-ciberseguridad-ot.md
TECNICAS = [
    ("T0832", "Manipulation of View", "El operador ve datos falsos en su pantalla.",
     "Las lecturas no cuadran con la física de los demás equipos."),
    ("T0856", "Spoof Reporting Message", "Un sensor reporta valores inventados pero creíbles.",
     "El balance de calor (caudal × ΔT) ya no alcanza para la carga de TI."),
    ("T0836", "Modify Parameter", "Alguien cambia un setpoint sin razón operativa.",
     "El chiller gasta más con la misma carga de TI."),
    ("T0855", "Unauthorized Command Message", "Llegan órdenes no autorizadas a bombas o válvulas.",
     "Arranques y paros sin relación con la carga ni el horario."),
    ("T0831", "Manipulation of Control", "El atacante altera el control físico del proceso.",
     "Consumo de energía o agua anómalo sin causa operativa."),
    ("T0815", "Denial of View", "El operador deja de recibir la telemetría.",
     "Lo atrapa una regla: faltan sensores mientras la energía sigue llegando."),
]

# Fuente: docs/07-agua-y-acuifero.md (Nico cita las fuentes en #13).
HECHOS_ACUIFERO = [
    ("Suelo kárstico", "Roca caliza porosa y fracturada: el agua se infiltra rápido y corre por conductos y cenotes conectados."),
    ("Nivel freático somero", "El agua subterránea está a pocos metros de la superficie, sobre todo en el norte del estado."),
    ("Sin ríos superficiales", "El acuífero es prácticamente la única fuente de agua de la población."),
    ("Muy vulnerable", "Lo que se vierte en la superficie llega rápido al agua subterránea."),
    ("Intrusión salina", "Cerca de la costa, extraer de más permite que entre agua de mar."),
    ("Anillo de Cenotes", "Reserva geohidrológica clave para el abasto de agua de Mérida."),
]

IMPACTO_ACUIFERO = [
    ("Extracción", "¿Cuánta agua deja de extraerse?", "Menos energía desperdiciada y menos reposición en la torre."),
    ("Descargas", "¿Qué pasa con el agua de purga?", "Detectar operación anómala reduce purgas innecesarias."),
    ("Contaminación", "¿Puede llegar a cenotes o al freático?", "El circuito cerrado del bono casi elimina las descargas."),
    ("Gobernanza", "¿Quién regula y qué permisos aplican?", "Concesiones de CONAGUA, normas de descarga y zonas protegidas."),
    ("Justicia ambiental", "¿A quién le quita agua el centro de datos?",
     "Cada litro ahorrado queda para las comunidades del mismo acuífero."),
]

# (opción, ventaja, desventaja en Yucatán, ¿recomendada?)
BONO = [
    ("Circuito cerrado líquido", "El refrigerante recircula y casi no se repone agua.", "Mayor inversión inicial.", False),
    ("Agua residual tratada", "No compite con el agua de consumo humano.", "Depende de una planta de tratamiento cercana.", False),
    ("Aire de alta eficiencia", "Cero agua.", "En clima cálido y húmedo gasta mucha energía y sube el PUE.", False),
    ("Híbrido (recomendado)", "Circuito cerrado como base y agua tratada solo en picos de calor.",
     "Más complejo de operar; la IA recomienda y el operador confirma.", True),
]

# Quién responde por cada cifra del contrato 4 (docs/11-trabajo-en-paralelo.md).
RESPONSABLES = {
    "pue_antes": "Misa", "pue_despues": "Misa", "kwh_ahorrados_anual": "Misa + Nico",
    "litros_ahorrados_anual": "Nico", "kwh_modelo_anual": "Gadiel", "kg_co2e_modelo": "Gadiel",
    "balance_neto_kwh": "Nico + Gadiel", "balance_neto_veces": "Nico + Gadiel",
    "escenarios_detectados": "Guille", "escenarios_totales": "Guille", "falsas_alarmas_por_dia": "Guille",
}
