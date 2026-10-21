# 06 · Ciberseguridad OT: guía rápida

> Documento para **Guille**. No tienes que ser experto: solo saber explicar con claridad **qué amenazas existen, cuáles detecta nuestro modelo y qué recomendaríamos**. El 22 hay mentores de ciberseguridad para validar.

## 1. ¿Qué es OT/ICS?

- **IT** (tecnología de la información): computadoras, servidores, correo, datos.
- **OT** (tecnología operacional): sistemas que controlan **equipos físicos** como bombas, válvulas, chillers y torres de enfriamiento.
- **ICS** (Industrial Control Systems): los sistemas de control industrial. Incluyen:
  - **Sensores:** miden temperatura, flujo, presión y energía.
  - **PLCs** (controladores lógicos programables): reciben lecturas y mandan órdenes a los equipos.
  - **SCADA / HMI:** las pantallas desde donde el operador ve y controla todo.

En un centro de datos, el sistema de enfriamiento es OT: si falla o lo atacan, los servidores se sobrecalientan o se desperdicia agua y energía.

### Modelo Purdue (en una línea)
Es la forma clásica de dividir una red industrial en niveles: sensores y actuadores (0), PLCs (1), SCADA/HMI (2), operaciones (3) y red corporativa (4–5). **La regla de oro es que los niveles bajos no deberían estar expuestos a internet.**

## 2. ¿Por qué son vulnerables?

- **Protocolos antiguos sin seguridad.** **Modbus** (de 1979) y muchas configuraciones de **BACnet** **no autentican ni cifran**: cualquiera que llegue a la red puede leer valores o mandar órdenes.
- **Equipos que duran 15 a 20 años** y casi nunca se actualizan.
- **Redes IT y OT mal separadas.**
- **Accesos remotos** de mantenimiento mal protegidos.

## 3. Técnicas de ataque que detectaría nuestro modelo

Del catálogo **MITRE ATT&CK for ICS** (<https://attack.mitre.org/matrices/ics/>). Verifica los IDs y descripciones en la matriz antes del pitch.

| Técnica | ID | Qué es | Cómo la detecta DripSafe |
|---|---|---|---|
| Manipulation of View | T0832 | El operador ve datos falsos en su pantalla | Las lecturas no cuadran con la física (por ejemplo, la temperatura "baja" sin que el chiller consuma más) |
| Spoof Reporting Message | T0856 | Un sensor reporta valores inventados | Un sensor se separa del comportamiento correlacionado de los demás |
| Modify Parameter | T0836 | Alguien cambia valores de configuración (setpoints) | Cambio brusco de un parámetro fuera del patrón normal u horario |
| Unauthorized Command Message | T0855 | Llegan órdenes no autorizadas a bombas o válvulas | Arranques y paros que no corresponden con la carga ni el horario |
| Manipulation of Control | T0831 | El atacante altera el control físico del proceso | Consumo de energía o agua anómalo sin causa operativa |
| Denial of View | T0815 | El operador deja de recibir la telemetría | Huecos en los sensores mientras los medidores de energía siguen reportando. **Se atrapa con una regla, no con el modelo** (ver 3b) |

Por dónde entraría un atacante (para el modelo de amenazas): **Internet Accessible Device** (T0883), un BMS o HMI expuesto a internet, y **Remote Services** (T0886), el acceso remoto de un proveedor de mantenimiento.

## 3b. Escenarios simulados (`src/ataques/`)

Para demostrar con números qué detecta DripSafe, metemos ataques y fallas **simulados** en la telemetría: solo cambian números en un CSV. Cada escenario vive en su propia ventana de tiempo y la respuesta correcta queda en las columnas `etiqueta_*`, que el modelo nunca ve.

```bash
python -m src.ataques.inyectar --entrada data/procesado/telemetria.csv    # o data/sinteticos/...
python -m src.ataques.evaluar                                              # cuando existan las alertas de Gadiel
```

| Escenario | Tipo | Técnica | Qué se simula | Huella física que lo delata |
|---|---|---|---|---|
| `setpoint_alterado` | Ataque | T0836 | Bajan 3 °C la temperatura objetivo, poco a poco | El chiller gasta ~9 % más con la misma carga de TI |
| `sensor_falsificado` | Ataque | T0856 | El sensor de retorno reporta 0.8 °C menos | Caudal × ΔT ya no alcanza para el calor de los servidores |
| `vista_repetida` | Ataque | T0832 + T0831 | Bajan la bomba al 65 % y repiten en pantalla las lecturas de ayer | La bomba gasta ~70 % menos pero el caudal «es normal»: rompe la ley de afinidad (potencia ∝ caudal³) |
| `comandos_no_autorizados` | Ataque | T0855 | Apagan y prenden la bomba cada 10 min a las 3 a. m. | Arranques y paros sin relación con la carga ni el horario |
| `denegacion_de_vista` | Ataque | T0815 | Se corta la telemetría de temperatura y caudal | Sensores vacíos mientras la energía sigue llegando |
| `ensuciamiento` | Falla | — | El intercambiador se ensucia en 2 días | Consumo que sube gradual y coherente |
| `sensor_atorado` | Falla | — | El sensor repite siempre el mismo valor | Varianza cero |
| `fuga_reposicion` | Falla | — | Entra 35 % más agua a la torre | Más agua sin más calor (sube el WUE) |

**Falla contra ataque, en una frase:** una falla cambia la física de forma gradual y coherente; un ataque deja lecturas que **no cuadran con la física** o cambios bruscos sin causa operativa. Un sensor congelado es falla; un sensor que se mueve «normal» pero rompe el balance de calor es ataque.

### Primer experimento (datos sintéticos, 19 oct)

Un Isolation Forest rápido, entrenado con los 7 días limpios y evaluado en los 7 días con escenarios:

| Variables del modelo | Escenarios detectados | Falsas alarmas |
|---|---|---|
| Solo las columnas crudas | 6 de 8 | 0.5 por día |
| Crudas + variables físicas (balance de calor, afinidad de la bomba, chiller por kW de TI, agua por calor, varianza del sensor) | **7 de 8** | 1 por día |

Lo que aprendimos (insumo para Gadiel):
- **Las variables físicas son las que atrapan los ataques disfrazados.** `vista_repetida` solo se detecta con ellas, y `sensor_falsificado` pasa de 1 % a 11 % de la ventana marcada.
- **La telemetría cortada (T0815) no la ve el modelo**, porque nunca vio huecos al entrenar. Se resuelve con una regla directa: «si faltan lecturas de sensores y la energía sigue llegando → alerta».
- Un Isolation Forest diluye una anomalía que aparece en una sola variable cuando hay muchas. Conviene combinarlo con reglas simples sobre las variables físicas (z-score), la línea base que ya propone [05-solucion-tecnica.md](05-solucion-tecnica.md).

Son datos sintéticos: los números finales salen del kit.

**Mensaje clave para el pitch:**
> "DripSafe funciona como **primera capa de detección**: no reemplaza un firewall ni un SOC, pero detecta cuando los datos físicos del enfriamiento no tienen sentido, que es justo lo que pasa cuando alguien manipula sensores o controladores."

## 3c. Rejilla de inyecciones sobre el kit (U1 · U2)

Las 21 anomalías del kit están hechas para que las reglas fijas las vean, así que ahí lo esperado es un empate. Para medir **desde qué tamaño** ve cada método un problema, metemos excesos controlados en copias de la evaluación. La rejilla quedó fijada aquí y en [`src/ataques/rejilla.py`](../src/ataques/rejilla.py) **antes de correrla sobre el kit**, y una prueba (`test_la_rejilla_es_la_que_fijo_la_propuesta`) impide cambiarla sin que se note.

| Inyección | Qué se cambia | Duración | Evento OT | Clase esperada |
|---|---|---|---|---|
| `energia_+10` … `energia_+80` | Energía no TI +10, +20, +40 y +80 % | 4 h | No | Escalón sin registro |
| `agua_+25`, `agua_+50` | Agua +25 y +50 % | 4 h | No | Escalón sin registro |
| `cambio_sin_registro` | Energía no TI +20 % (setpoint cambiado sin dejar registro, T0836) | 12 h | No | Escalón sin registro, **nunca** mantenimiento directo |
| `cambio_con_efecto` | `cambio_config_no_autorizado` y, **8 h después**, energía no TI +20 % | 12 h | Sí | Incidente OT con efecto |

**Dónde se pone cada una:**
- Una inyección por copia, en cada sitio, a 6, 18, 30, 42, 54 y 66 h del inicio de la evaluación (noche, mañana y tarde).
- Si ahí estorba una anomalía original del kit (con 2 h de margen) o hay un evento OT del kit en las 24 h previas, se recorre hora por hora hasta un lugar limpio. Se anota cuánto se recorrió y no se repite un lugar.
- Solo se toca la evaluación. Ajuste y calibración quedan idénticos, así que el detector aprende exactamente lo mismo en todas las copias: la corrida lo verifica en cada copia y se detiene si no es así.
- Las respuestas correctas van en `etiqueta_*`, que el detector nunca lee (prueba `test_el_detector_no_ve_las_etiquetas_de_la_inyeccion`).

**Robustez (prueba c):** se repite toda la rejilla con sensores peores en **todas** las horas: el ruido de la energía se duplica (gaussiano de 1.5 % de la energía TI encima del ±1.5 % uniforme del kit) y el agua lleva ±4 %. Se corre con 5 semillas para ver la dispersión.

**Qué mide la corrida** ([`src/ataques/correr_rejilla.py`](../src/ataques/correr_rejilla.py)), para DripSafe y para las reglas del kit en la misma tabla:

| Columna | Qué responde |
|---|---|
| `detectado`, `horas_hasta_detectar` | ¿Hubo alguna alerta en el episodio? Se cuenta por episodio (D17) con la función de Nico |
| `efecto_visto`, `horas_hasta_ver_efecto` | ¿Se vio el exceso físico, no solo el evento OT? |
| `inyectado_kwh`, `no_visto_kwh` (o `_l`) | Exceso exacto que metimos y la parte que pasó antes de verlo |
| `clase_obtenida`, `clase_correcta_pct` | ¿La clase OT fue la esperada? (solo DripSafe) |

La corrida también da las falsas alarmas por día de la evaluación **sin** inyecciones y las coincidencias al azar de la §4b.

```bash
python -m src.ataques.correr_rejilla --kit RUTA/operaciones_simuladas.csv   # o --entrada data/procesado/telemetria.csv
python -m src.ataques.correr_rejilla --ejemplo                              # sin el kit: datos inventados
```

Salidas, todas fuera de Git: `data/escenarios/rejilla.manifiesto.json` (cada inyección con su ventana y sus etiquetas) y `data/resultados/rejilla_por_inyeccion.csv`, `rejilla_resumen.csv` (la curva por magnitud), `rejilla_base_limpia.csv` y `coincidencias_al_azar.csv`. Nico (N2) toma de ahí la tabla y la curva oficiales; solo los agregados van a `numeros_oficiales.json`.

**Lo que ya se ve con datos inventados** (`--ejemplo`, solo para probar el flujo): las reglas no ven ningún exceso de energía de +10 o +20 % y solo un tercio de los de +80 %, mientras que DripSafe ve todos desde +40 %. En los 15 cambios con efecto, las reglas disparan por el evento OT pero no ven ninguno de los excesos que llegan 8 h después; DripSafe los ve todos y los clasifica como incidente. Las cifras del pitch salen del kit.

## 4. Las 4 clases de alerta: tabla de decisión (D16 · U1)

DripSafe no adivina si algo es «falla» o «ataque»: con datos de proceso esas dos cosas a veces se ven igual. Lo que sí puede hacer es **cruzar el registro OT con los excesos físicos** y ordenar la respuesta. Las reglas viven en un solo lugar, [`src/ot/clases.py`](../src/ot/clases.py); el detector las llama y el dashboard muestra lo que sale de ahí. Cada fila de las tablas de abajo tiene una prueba en [`tests/test_clases.py`](../tests/test_clases.py).

**Palabras que usamos (todo es por sitio):**
- **Exceso:** una hora en la que el detector marca energía no TI, agua o temperatura de entrada por encima de lo esperado (por umbral o por la media de 4 h).
- **Tramo:** horas seguidas con exceso. Un hueco en los datos corta el tramo.
- **Evento OT:** horas seguidas con `ot_event` distinto de `normal` (`login_fallido` o `cambio_config_no_autorizado`).
- **Ventana de efecto:** desde la primera hora del evento hasta 24 h después de su última hora. Si el evento ocupa la hora de las 04:00, cuentan los excesos que **empiecen** entre las 04:00 y las 04:00 del día siguiente.
- **Causal:** el tramo **empieza** dentro de la ventana. **Coincidente, no causal:** el tramo ya venía de antes y el evento cae a la mitad.

| Clase | Cuándo | Prioridad | Acción sugerida |
|---|---|---|---|
| **Incidente OT con efecto** | Un tramo empieza dentro de la ventana de un evento OT. También sube a esta clase la hora del cambio que lo causó | Máxima | Restaurar la configuración aprobada y pasar a modo seguro manual; confirmar en sitio |
| **Cambio no autorizado** | Hora con `cambio_config_no_autorizado` sin efecto atribuido (todavía) | Alta | Comparar contra la configuración aprobada y vigilar 24 h |
| **Escalón sin registro** | Exceso sin ningún evento OT que lo cause | Alta | Comparar los setpoints contra la versión aprobada **antes** de mandar a mantenimiento. Si el exceso es de agua, inspección física en paralelo (posible fuga) |
| **Intento de acceso** | Hora con `login_fallido` y sin exceso | Media | Revisar accesos y cuentas. Un login fallido no prueba una intrusión |

**Precedencia:** incidente > cambio no autorizado > escalón sin registro > intento de acceso > normal. Ninguna regla baja la clase que ya tiene una hora.

**Dos reglas de oro:**
1. **Ningún exceso sin explicar va directo a mantenimiento.** Un cambio de setpoint sin registro (T0836 sin log) se ve igual que una falla brusca, así que primero se revisa la configuración.
2. **Ningún cambio no autorizado es «sin urgencia»**, aunque todavía no tenga efecto: puede notarse en el siguiente pico de calor.

### Casos ambiguos y su respuesta

| # | Situación | Respuesta | Por qué |
|---|---|---|---|
| 1 | Cambio a las 04:00 y exceso desde las 12:00 | Incidente (el exceso y la hora del cambio) | La ventana de 24 h cubre el siguiente pico de calor |
| 2 | El exceso empieza 25 h después del cambio | Escalón; el cambio sigue como cambio no autorizado | Fuera de la ventana: se revisa, pero no se atribuye |
| 3 | El exceso ya venía 4 h antes del cambio | Escalón, marcado **coincidente, no causal**; el cambio no baja de prioridad | Un cambio no puede causar algo que ya pasaba |
| 4 | Ese exceso coincidente termina y empieza otro dentro de la ventana | El nuevo es incidente | Es un efecto nuevo después del evento |
| 5 | Un segundo cambio cae a la mitad de un incidente | Sigue siendo incidente | Precedencia. La versión anterior del detector bajaba esa hora |
| 6 | Login fallido y, 6 h después, un exceso | Incidente; el login sigue como intento | Un acceso que sí funcionó no deja evento en el kit: el login pudo ser el paso previo |
| 7 | Tres logins y luego dos horas de cambio (patrón de SIM-C) sin efecto | Intento en los logins y cambio no autorizado en el cambio | Cada hora conserva lo que registró |
| 8 | Login y luego cambio, ambos antes del mismo exceso | Se atribuye al cambio | Es la causa más directa |
| 9 | Login en una hora que ya tenía exceso | Escalón, con una nota del login en el motivo | El exceso es más grave que el intento |
| 10 | Exceso pequeño y sostenido, visto solo por la media de 4 h | Escalón, con forma «gradual» | Mientras «deriva gradual» sea un extra, se trata como posible cambio sin registro |
| 11 | Exceso de agua sin evento | Escalón + inspección física | Posible fuga |
| 12 | Falta una hora de datos a la mitad de un exceso | El tramo se corta en dos | No se inventan horas |

**Límites que declaramos:**
- Un exceso que ya venía de antes y **empeora** después del evento, sin cortarse, se queda como coincidente. Distinguir ese «escalón dentro del escalón» necesita el umbral de cada variable; por ahora lo resuelve una persona.
- Con una ventana de 24 h, un exceso que no tiene nada que ver puede caer dentro **por casualidad**. Por eso lo medimos (siguiente sección) en lugar de suponerlo.

### 4b. ¿Cuántas atribuciones serían pura coincidencia?

La propuesta (§3.3) pide reportar cuántas coincidencias al azar habría. `clases.coincidencias_al_azar()` lo calcula así: sobre la evaluación **sin inyecciones**, pone un evento OT ficticio de 1 h en cada hora posible y revisa si algún tramo de exceso empieza dentro de su ventana. El porcentaje de aciertos es la probabilidad de llamar «incidente OT con efecto» a algo que el evento no causó.

Se reporta para ventanas de 1, 4, 8, 12 y 24 h, porque es un intercambio: una ventana corta casi no se equivoca por casualidad, pero se pierde el caso del cambio que se nota 8 h después. Las cifras salen de la corrida de la rejilla sobre el kit (U2, #32) y van al JSON oficial.

### Mensaje honesto para el pitch

> *"DripSafe no afirma que un residuo pruebe un ciberataque. Distingue un intento (login fallido), un cambio (sin efecto confirmado), un escalón sin registro (falla o cambio no registrado: primero se revisa la configuración) y un incidente con efecto (evento OT seguido de un exceso físico medible). Y dice qué tan seguido esa atribución podría ser casualidad."*

## 5. Recomendaciones de defensa (para la propuesta)

Basadas en **ISA/IEC 62443**, el estándar de seguridad industrial:
- **Zonas y conductos:** separar la red OT del enfriamiento de la red IT y controlar qué tráfico pasa entre ellas.
- **Lista blanca de comandos:** solo ciertos equipos pueden mandar órdenes a los PLCs.
- **Monitoreo continuo:** aquí entra DripSafe.
- **Acceso remoto seguro:** VPN, llaves SSH y autenticación multifactor. Lo que ya sabes del server aplica.
- **Respaldo manual:** si se detecta un ataque, el sistema pasa a un modo seguro.

### Cómo se instala DripSafe sin abrir una puerta nueva

Un detector conectado a la planta también puede ser atacado. Por eso:
- **Solo lee.** Recibe una copia del tráfico (puerto espejo o diodo de datos, que deja pasar información en un solo sentido) y **nunca manda órdenes** a PLCs ni bombas.
- **Alerta a una persona; no actúa solo.** Si DripSafe pudiera cambiar el enfriamiento, quien engañe al modelo controlaría la planta. Esto aplica también al bono: la IA **recomienda** cuándo activar el respaldo con agua tratada y el operador confirma.
- **Vive en su propia zona** de la red (IEC 62443): separado de la red de oficina y sin salida a internet.
- **Se entrena solo con periodos verificados como limpios** y cada versión del modelo queda registrada. Así nadie le «enseña» a ver un ataque como normal (envenenamiento del modelo).
- **Si el atacante conoce el modelo:** puede imitar la estadística de un sensor, pero tendría que falsificar a la vez temperatura, caudal y energía de forma físicamente coherente, y los medidores de energía suelen ser otro sistema.

## 6. Lo que trae el kit sobre OT (19 oct)

- **No trae** equipos, protocolos ni diagrama de red. El kit es solo de lectura local: sin PLC, sin red OT, sin actuadores y sin respuesta automatizada.
- **Sí trae** una columna `ot_event` con eventos ficticios resumidos: `login_fallido` y `cambio_config_no_autorizado`, sin IPs ni credenciales.
- El kit advierte que **un login fallido no prueba un ataque**. Proponemos tratarlo como `evento_ot` que requiere revisión humana, no como "ataque" confirmado (ver D14).
- Mapeo tentativo para la tabla final: `cambio_config_no_autorizado` → **Modify Parameter (T0836)**. Para `login_fallido`, documentar que es un indicio de acceso, no una técnica confirmada; verificar en la matriz si conviene citar alguna técnica de acceso inicial.
- Los escenarios de `src/ataques/` que necesitan columnas que el kit no trae (temperaturas del agua, chiller, caudal) **siguen sirviendo con los sintéticos** para mostrar la idea de "no cuadra físicamente". Sobre el kit, solo se usan los que tengan sus columnas.
- **Acuífero y gobernanza (#13) también son de Guille desde D13.** Ver [07-agua-y-acuifero.md](07-agua-y-acuifero.md).

## 7. Entregable de Guille

- 1 o 2 diapositivas: amenazas → cómo las detectamos → recomendaciones.
- Tabla final de técnicas de ATT&CK aplicadas al caso del kit.
- Escenarios simulados sobre el kit (contrato 2) y `deteccion_por_escenario.csv` con el modelo final de Gadiel: qué detecta, en cuánto tiempo y con cuántas falsas alarmas.
- Diagrama del modelo de amenazas (niveles Purdue y puntos de entrada).

## Regla del hackatón
**Prohibido hacer pruebas o ataques sobre sistemas reales.** Todo se hace sobre el kit de datos o en simulaciones. Los "ataques" se simulan modificando datos en un CSV, nunca contra equipos reales.

## Para leer más
Ver la sección "Ciberseguridad OT" en [09-recursos.md](09-recursos.md).
