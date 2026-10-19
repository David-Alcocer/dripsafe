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

## 4. Cómo distinguir falla de ataque

- **Falla o ineficiencia:** suele afectar varias variables de forma **coherente** y aparece de forma gradual (desgaste o suciedad en intercambiadores).
- **Ataque:** suele mostrar **incoherencias** (un sensor dice una cosa y el resto otra), cambios **bruscos**, o actividad **fuera de horario**.

Esto se diseña con Gadiel. Ver [05-solucion-tecnica.md](05-solucion-tecnica.md).

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
