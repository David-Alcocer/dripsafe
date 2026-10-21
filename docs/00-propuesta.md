# DripSafe · Propuesta v7

**Hackatón CIFOX · AguaSegura AI · Sub-reto 3 (detección de anomalías en enfriamiento y gestión hídrica) · Métrica principal: PUE**

> DATOS SIMULADOS. Todo lo que sale del kit CIFOX (3 sitios ficticios, 7 días) se usa para **demostrar el método**, no como evidencia de que una tecnología sea mejor que otra (el `DATA_DICTIONARY` del kit lo prohíbe). Lo medido, lo estimado y lo proyectado se marcan por separado.

## 1. El problema

1. **Agua.** En Yucatán el acuífero kárstico Península de Yucatán (clave CONAGUA 3105) es prácticamente la única fuente de agua: nivel freático somero, cenotes conectados y sin ríos. Un centro de datos con enfriamiento evaporativo extrae y evapora agua de ahí, y su purga con sales concentradas se puede infiltrar.
2. **Energía.** Cada kWh que el enfriamiento desperdicia sube el PUE, las emisiones y el agua usada para generar electricidad.
3. **Ciberseguridad OT.** El enfriamiento lo controlan PLCs y un BMS. Un cambio de configuración no autorizado puede disparar el consumo o dañar equipos sin que nadie lo note.
4. **El hueco que atacamos: los umbrales fijos.** Las reglas del kit (y muchos BMS) usan un umbral igual para todos: PUE > 1.6, agua > 1.5 L/kWh de TI, entrada > 29 °C. En el kit, el sitio de enfriamiento líquido opera con un PUE cercano a 1.2. Puede subir su energía de enfriamiento **+140 %** (hasta un PUE de unos 1.57) en cualquier hora, incluso la más calurosa, sin disparar ninguna regla. El umbral fijo protege al sitio menos eficiente y deja ciegos a los eficientes.

## 2. La idea en una línea

**DripSafe aprende cómo debería comportarse cada sitio según su carga y su clima, avisa cuando la física no cuadra, distingue un intento OT de un incidente con efecto real y ordena las alertas por los litros del acuífero en juego.**

Esto responde al reto 2 del kit: proponer un criterio nuevo, justificar su costo y separar ajuste, validación y prueba.

**Qué es conocido y qué es nuestro:**
- **Conocido:** comparar el consumo real con una línea base que depende de la carga y el clima es la práctica estándar de medición y verificación de ahorros (ASHRAE Guideline 14, IPMVP). La usamos a propósito, porque es auditable.
- **Nuestro:**
  1. Aplicar la línea base de M&V a la **detección por sitio** y **medir su sensibilidad** frente al umbral fijo. La curva de sensibilidad es la evidencia; detectar con una línea base, por sí solo, ya lo hacen el M&V continuo y el FDD.
  2. La **fusión evento–efecto**, que cruza el registro OT con la física para separar el intento del incidente.
  3. Priorizar por **litros del acuífero** y decidir entre gastar litros o kWh en el bono.

## 3. Cómo funciona

```
CSV del kit (6 medidores + registro OT)
   │
   ├─▶ 1. Línea base física por sitio (aprendida en 48 h de la referencia)
   ├─▶ 2. Residuos = real − esperado (%)
   │       ├─ Umbral por residuo + media móvil de 4 h  → excesos de una variable y sostenidos
   │       └─ Isolation Forest por sitio               → combinaciones raras entre residuos
   ├─▶ 3. Registro OT  →  reglas
   ├─▶ 4. Fusión evento–efecto  →  4 clases (MVP) + 2 extra
   └─▶ 5. Cola de alertas en el dashboard: kWh y litros en riesgo por hora
```

### 3.1 Línea base física por sitio
Para cada sitio, una regresión lineal con dos variables físicas:
- **Calor a disipar:** `energy_it_kwh`.
- **Pérdida de enfriamiento gratuito:** `energy_it_kwh × max(0, outdoor_temp_c − 20)`. Por encima de unos 20 °C, el aire exterior ya no ayuda y cada grado extra cuesta energía o agua.

Con eso predice la energía de enfriamiento (`energy_total − energy_it`) y el agua. La **temperatura de entrada** depende del clima y no del tamaño de la carga, así que su línea base usa solo `max(0, outdoor_temp_c − 20)` y una constante. El setpoint y la configuración **no** entran como variables: si alguien los altera, el consumo real se separa de lo esperado y se ve.

**Transparencia:** esta forma coincide con la del generador del kit. Lo declaramos: la elegimos porque representa la física del enfriamiento, y para no depender de esa coincidencia la validación (§4) prueba también una forma mal especificada (solo TI y temperatura) y datos con ruido extra.

Cada alerta se explica en una frase: *"SIM-A gasta 31 % más energía de enfriamiento de lo esperado para su carga y clima."*

### 3.2 Detectores sobre los residuos (MVP: 1 y 2)
1. **Umbral por residuo** (energía, agua, entrada): alerta si el residuo supera el máximo observado en las 24 h de calibración más un **margen del 50 %**, fijado antes de ver la evaluación. Con 24 puntos no se puede estimar un percentil 99 y no lo fingimos.
2. **Media móvil de 4 h** de cada residuo, con su propio umbral calibrado igual. Atrapa excesos pequeños pero sostenidos. Son unas 5 líneas con pandas.
3. **Isolation Forest (scikit-learn) por sitio** sobre el vector de residuos, para **combinaciones** que ningún umbral individual ve. Ejemplo: la temperatura de entrada sube 0.4 °C mientras la energía de enfriamiento **baja** 5 %. Cada residuo, por separado, está dentro de su ruido normal, pero juntos dicen que el enfriamiento trabaja menos justo cuando hace falta más, por una falla de control o una lectura falsa.
   - **Por qué IF y no un z-score:** el z-score mira una variable a la vez, y el IF ve la combinación.
   - **Lo comprobamos, no lo suponemos:** la tabla de resultados se reporta con y sin IF (ablación).
   - **Es opcional y va fuera del MVP.** El MVP son la línea base y los umbrales.
   - **Lo que esperamos, dicho antes de medir:** en el kit el IF **no puede lucirse**. Los ruidos del generador son independientes y acotados, así que una combinación "rara" en datos sin correlación no es rara, y los umbrales la atrapan antes. Diseñar una prueba para que el IF gane sería hacer trampa.
   - **Por eso el núcleo de la detección son la línea base y los umbrales.** El IF se mantiene (decisión D2) como capa para datos reales, donde las variables sí están correlacionadas, y en el kit solo se reporta su ablación sin venderla.
   - **Decisión para el equipo:** esto ajusta D2. Con el kit, la detección central no necesita IF; se presenta como capa para datos reales.

*Extra si sobra tiempo:* CUSUM para derivas de días. Los residuos horarios están autocorrelacionados, así que sus falsas alarmas se reportan por separado.

**Límite mínimo detectable (estimación analítica, que se verifica en la prueba b):**
- El ruido del kit sobre la energía total es de ±1.5 % de la energía de TI. En el sitio líquido eso equivale a una desviación de unos 4.4 % de la energía de enfriamiento por hora.
- **Detector 1, en una sola hora:** se detecta un exceso de aproximadamente +15 %.
- **Detector 2, sostenido durante 4 h:** se detecta uno de +10 %.
- Las reglas del kit no ven ninguno de los dos.

### 3.3 Fusión evento–efecto

**Dos reglas de oro:**
1. **Ningún exceso sin explicar va directo a mantenimiento.** Un ataque que cambia un setpoint sin dejar registro (T1692.001, antes T0855, o T0836 sin log) se ve igual que una falla brusca, así que todo escalón sin registro se trata como posible cambio no autorizado hasta comprobar la configuración.
2. **Ningún cambio de configuración no autorizado es "sin urgencia"**, aunque todavía no tenga efecto físico. Puede notarse hasta el siguiente pico de calor, o ser un cambio de límites de alarma que nunca mueve la física y aun así es grave.

| Clase (MVP) | Condición | Acción sugerida | ¿Está en el kit? |
|---|---|---|---|
| **Incidente OT con efecto** | Evento OT **y** un residuo físico que aparece desde el inicio del evento hasta **24 h** después de su fin, lo que cubre el siguiente pico de calor | Máxima: restaurar la configuración aprobada; modo seguro manual | No: se inyecta (§4) |
| **Cambio no autorizado** | `cambio_config_no_autorizado`, con o sin efecto por ahora | Alta: comparar contra la configuración aprobada; vigilar residuos 24 h; si aparece efecto, sube a incidente | Sí (SIM-C, precedido de logins fallidos) |
| **Escalón sin registro** | Un residuo supera el umbral de golpe (en 1 h o menos), sin evento OT | Alta: comparar setpoints contra la versión aprobada (minutos); **si el escalón es de agua, inspección física en paralelo** (posible fuga) | Sí (SIM-A energía, SIM-B agua) |
| **Intento de acceso** | Solo `login_fallido`, residuos normales | Media: revisar accesos y cuentas | Sí (SIM-C) |

*Extra, si sobra tiempo:* **incoherencia física** (sube la entrada y baja la energía de enfriamiento: sensor descompuesto o manipulado) y **deriva gradual** (la media móvil sube sin escalón: degradación).

Las clases son reglas simples sobre los residuos y el registro OT. Comparar contra la "configuración aprobada" es gestión de cambios estándar en OT (IEC 62443). DripSafe solo dice cuándo y por qué hacerlo.

**Ventana de 24 h:**
- **Por qué:** en el kit el cambio de configuración ocurre de madrugada (04:00–05:00 UTC), con carga y temperatura bajando. Un setpoint alterado puede notarse hasta la tarde.
- **Causalidad:** un residuo que ya existía **antes** del evento se marca *"coincidente, no causal"*, salvo que dé un escalón dentro de la ventana.
- **Coincidencias al azar:** se reporta cuántas habría en la evaluación limpia, combinando eventos OT al azar con los residuos.

## 4. Validación honesta

**Particiones (solo con el kit, por sitio):**
- **Ajuste:** las primeras 48 h de `referencia`.
- **Calibración de umbrales:** las 24 h siguientes de `referencia`.
- **Prueba:** `evaluacion`, una sola vez.

**Rejilla de inyecciones, fijada por escrito antes de correr nada** (este documento es el registro). Se inyecta sobre copias de `evaluacion` con `src/ataques/` adaptado:
- Enfriamiento +10, +20, +40 y +80 %, durante 4 h.
- Agua +25 y +50 %.
- Un cambio sin registro: escalón de +20 % sin evento OT. Debe caer en "escalón sin registro", **no** en mantenimiento.
- Un cambio de configuración con efecto: +20 % de enfriamiento que empieza 8 h después del evento.

**Pruebas, todas comparadas con las reglas del kit en la misma tabla** (TP, FP, FN, precisión, recall, falsas alarmas por día con intervalo y horas hasta detectar):
- **(a) Las 21 anomalías originales del kit.** Lo esperado es un **empate**, y se reporta tal cual.
- **(b) La rejilla de inyecciones.** El resultado es una **curva**: horas hasta detectar y kWh/litros no vistos **en función de la magnitud**, para DripSafe y para las reglas.
- **(c) Robustez, solo en el MVP con una condición:** ruido gaussiano del doble sobre energía y ±4 % sobre agua (el agua del kit no tiene ruido), con la magnitud de +20 %. La forma mal especificada y las demás condiciones son extra.

**Así se presenta:** como *curva de sensibilidad* ("con el ruido del kit, DripSafe detecta desde +X %; las reglas, desde +140 % en el sitio líquido"), no como "DripSafe es mejor". Si en (c) el método se cae, se reporta.

## 5. Métricas y balance neto

- **PUE y WUE** con cocientes de sumas, nunca promedios de cocientes horarios.
- **Número central: el umbral de equilibrio.**
  - El costo anual del detector se **mide** en la laptop: 10 repeticiones con CodeCarbon y tiempo de CPU, reportando media y dispersión.
  - El uso real es inferencia cada hora (8 760 veces al año) más un reentrenamiento por temporada.
  - Se compara con el exceso de energía de **una sola hora** de ineficiencia típica. Si el costo anual son unos pocos Wh y una hora de ineficiencia son decenas de kWh, **el balance es positivo con una sola detección al año**.
  - Este número no depende de que el ahorro proyectado sea exacto.
- **Mejora medible, dicha con precisión:** con datos simulados ningún equipo puede medir un ahorro real, y no lo fingimos. Lo que sí se mide:
  - **Sobre las 21 anomalías del kit:** PUE y WUE de la evaluación **observados**, más el exceso que DripSafe identifica en kWh y litros con su línea base. Es la misma información que dan las reglas, pero **cuantificada**.
  - **Sobre la rejilla fijada de antemano:** kWh y litros de exceso que **no vio** cada método, como curva por magnitud. Muestra desde qué tamaño de falla cada método deja de perder energía y agua. No es una cifra única elegida por nosotros.
  - **PUE "si se corta el exceso en cada alerta":** se presenta como lo que es, una cota calculada sobre los datos, no un ahorro.
- **Ahorro anual como escenario paramétrico, no como promesa:** *"si ocurren N horas al año de un exceso de X % y se corrigen en T horas, el ahorro es…"*. N, X y T son editables en el dashboard. Las anomalías del kit sirven de ejemplo, no se anualizan como cifra del pitch.
- **CUE:** energía × factor de emisión del Sistema Eléctrico Nacional (fuente: el aviso vigente de CRE/SEMARNAT; editable).
- **Agua de la red eléctrica:** intensidad hídrica por tecnología de generación (fuente: Macknick et al., NREL, 2012), ponderada por la mezcla del SEN. Son factores de tecnologías de EE. UU. aplicados a la mezcla mexicana: supuesto citado y editable.

## 6. Impacto en el acuífero de Yucatán

- **Disponibilidad:** el acuífero 3105 tiene disponibilidad oficial positiva. Se cita una sola cifra: la del acuerdo de disponibilidad vigente publicado en el DOF (Nico la obtiene; el DOF de 2013 reporta la de 2009). El riesgo principal no es agotarlo en total, sino la **calidad**: suelo kárstico, freático somero, intrusión salina en la costa y baja cobertura de saneamiento.
- **Purga cuantificada:** en una torre, `purga = evaporación ÷ (ciclos de concentración − 1)`. Con 4 ciclos (supuesto típico), cada 3 L evaporados generan 1 L de purga con sales concentradas. El agua captada es evaporación más purga, así que **por cada litro captado que se evita por exceso de evaporación, se evita ¼ de litro de descarga** hacia el subsuelo. Evitar una fuga ahorra agua, pero no reduce la purga.
- **El beneficio hídrico depende del tipo de enfriamiento** (el kit lo ilustra, no lo prueba):
  - **Evaporativo:** es grande.
  - **Aire:** es casi nulo; solo cuenta el agua de la red eléctrica.
  - DripSafe lo dice en lugar de prometer agua en todos los sitios.
- **Gobernanza:** un reporte mensual verificable de consumo, litros evitados y purga, útil para el título de concesión de CONAGUA, las normas de descarga y los reportes ESG.
- **Justicia ambiental:** la cola prioriza litros, y lo evitado queda para las comunidades del mismo acuífero.

## 7. Bono Zero Freshwater Footprint: transición guiada por datos

**Propuesta:** enfriamiento líquido de agua tibia en circuito cerrado, rechazando el calor con enfriadores secos sin evaporación. En los picos de calor hay dos respaldos, y **ninguno usa agua potable**. DripSafe verifica que el agua potable sea cero y recomienda qué respaldo usar.

1. **Que es viable lo respaldan fuentes externas, no el kit:**
   - **Circuito cerrado sin evaporación:** Microsoft anunció en 2024 un diseño con enfriamiento líquido a nivel de chip que, una vez lleno, no consume agua para enfriar. Estima evitar más de 125 millones de litros al año por sitio, a cambio de un aumento "nominal" del PUE. Son cifras de la empresa; los pilotos arrancan en 2026.
   - **Agua residual tratada:** Google enfría su centro de datos de Douglas County (Georgia) con agua residual tratada desde 2012. Financió una planta lateral en la planta municipal y devuelve el agua no evaporada tratada al río.
   - **Clases de agua de ASHRAE:**
     - Aire a la entrada del servidor: 18–27 °C recomendado.
     - Clases de agua para enfriamiento líquido: W32, W40 y W45, con suministro de hasta 32, 40 y 45 °C.
     - Con agua más tibia, el enfriador seco funciona más horas sin ayuda.
2. **Horas de respaldo en Mérida (método y estimación preliminar):**
   - **El dato:** la máxima media de abril y mayo ronda los 37 °C (normales 1991–2020 citadas por fuentes secundarias; por confirmar con el SMN).
   - **Saltos de temperatura:** entre el aire exterior y el agua del servidor hay dos.
     - El enfriador seco: 5–8 K (supuesto; 5 es optimista).
     - El intercambiador CDU entre el circuito de la planta y el de los servidores: 2–5 K.
   - **Con clase W32:** 32 − (7 a 13) da un umbral de respaldo de **19–25 °C**. Haría falta respaldo casi todas las tardes del año, así que **no sirve**.
   - **Con clase W40:** 40 − (5 a 8) − (2 a 5) da un umbral de respaldo de **27–33 °C** según los supuestos, sobre todo en las tardes de abril a agosto. Si con el supuesto pesimista (27 °C) las horas son demasiadas, lo decimos y la recomendación pasa a W45.
   - **El cálculo:** Nico cuenta las horas por encima de 27, 30, 33 y 35 °C, como sensibilidad, y las convierte en litros (respaldo A) o kWh (respaldo B).
     - **Datos:** horarios del SMN. Si no están disponibles a tiempo, se usa el reanálisis ERA5 vía Open-Meteo o Meteostat, citado.
3. **Los dos respaldos, ninguno con agua potable:**
   - **A. Adiabático con agua residual tratada** (JAPAY). Gasta poca energía, pero evapora agua no potable. **Damos por hecho que JAPAY no confirmará a tiempo:** el pitch presenta el respaldo B como el plan y el A como mejora futura sujeta a convenio.
   - **B. Chiller mecánico de apoyo.** Usa **cero agua** a cambio de más energía, como el diseño de Microsoft. Es el respaldo garantizado: no depende de la lluvia ni de JAPAY.
   - **Agua pluvial y condensado:** complemento parcial, no plan B. Abril y mayo son los meses más calientes y caen antes de las lluvias (junio a octubre), así que se necesitaría guardar agua de la temporada anterior. Lo declaramos parcial.
4. **Purga del respaldo A:** nunca se infiltra en el suelo kárstico. Regresa por drenaje a la planta de tratamiento.
5. **Legionella:** tratamiento y monitoreo del circuito de agua no potable, como en cualquier torre.
6. **El papel de DripSafe:**
   - Con su línea base estima las horas de respaldo y compara, hora por hora, los **litros de A contra los kWh de B**. Así recomienda cuál usar según la disponibilidad de agua tratada y el precio de la energía.
   - Una regla verifica que el medidor de agua potable del enfriamiento marque cero.
   - El operador confirma; la IA nunca manda órdenes.

**Meta verificable:** WUE potable = 0 L/kWh, comprobado con un medidor dedicado (el kit no separa el agua potable de la no potable, así que con el kit no se puede demostrar). El PUE con el respaldo B y el WUE no potable con el respaldo A se reportan como estimaciones con supuestos citados. **El costo del bono es explícito:** el respaldo B sube el PUE (la métrica principal del sub-reto) durante las horas de respaldo; se reporta el PUE anual con y sin bono, para que el jurado vea el intercambio de agua por energía.

## 8. Arquitectura segura

- **Solo lectura:** copia del tráfico o diodo de datos; nunca escribe en PLCs.
- **Persona en el ciclo:** solo recomienda.
- **Zona propia de red** (IEC 62443), sin internet.
- **Entrenamiento solo con periodos verificados como limpios**, con modelos versionados (contra el envenenamiento).
- **Corre en CPU,** sin GPU ni nube y sin LLM.

## 9. Escalabilidad y modelo de negocio

- **Instrumentación mínima:** 6 medidores que casi cualquier centro de datos ya tiene (energía de TI, energía total, agua, carga, temperatura exterior y temperatura de entrada).
- **Variables que habría que medir antes de recomendar cambios reales** (reto 3 del kit): caudal y temperaturas de suministro y retorno del agua helada, consumo por equipo (chiller, bombas, torre) y separación entre agua potable y no potable.
- **Autocalibración:** 72 h de operación limpia por sitio (48 h de ajuste y 24 h de calibración), sin etiquetas. Se reentrena por temporada como parte del servicio.
- **Primer segmento: centros de datos empresariales y colocation de 0.5 MW o más** en la Península de Yucatán. Las salas de cómputo universitarias (unos 50 kW) son **piloto académico gratuito** para validar con datos reales, no clientes de pago: a esa escala el ahorro no cubre una licencia.
- **Ejemplo de valor** (supuestos editables):
  - Un sitio de 1 MW de TI con PUE 1.4 gasta unos 3 500 MWh al año en **overhead** (enfriamiento, UPS, iluminación).
  - **Supuesto:** DripSafe ayuda a evitar entre el 1 % y el 5 % de ese overhead. No tiene fuente y se valida en el piloto.
  - Eso son de 35 a 175 MWh al año, unos **$87 000 a $437 000 MXN** a $2.5/kWh, más los litros de agua.
- **Precio indicativo:** $40 MXN por kW de TI al año ($40 000 para 1 MW).
  - **Umbral de equilibrio del cliente:** la licencia se paga sola si DripSafe evita 16 MWh al año, **menos del 0.5 % del overhead** de un sitio de 1 MW. Basta con detectar a tiempo unas pocas fallas al año.
  - **Referencia externa:** en edificios, las herramientas de diagnóstico automático de fallas (FDD) logran una mediana de **9 %** de ahorro anual de energía (LBNL, Smart Energy Analytics Campaign, 2019–2020). Nuestro rango ilustrativo de 1–5 % del overhead es deliberadamente más conservador, porque DripSafe no toca UPS ni iluminación y es solo una capa de detección.
- **Auditoría de línea base al instalar:** se compara el PUE de referencia del sitio con el de diseño del fabricante o con sitios del mismo tipo de enfriamiento. Así una ineficiencia crónica, que la línea base aprendería como "normal", sale a la luz desde el día uno.
- **Expansión:** Querétaro, el polo nacional de centros de datos, también con estrés hídrico, y otros acuíferos sobreexplotados. El método no depende de Yucatán; solo cambia la prioridad por litros.
- **Competencia:**
  - **Diagnóstico automático de fallas (FDD) y analítica de BMS:** Schneider EcoStruxure, Siemens Desigo, SkyFoundry SkySpark. Detectan fallas de equipos y se enfocan en energía.
  - **Monitoreo OT:** Nozomi, Claroty, Dragos. Ven el tráfico de red y también variables de proceso leídas de los protocolos industriales. No modelan la línea base de energía y agua por carga y clima, ni priorizan por litros.
  - **Lo que DripSafe hace distinto:**
    1. Una **línea base de energía y agua** por sitio, ajustada por carga y clima.
    2. Pone el **agua primero**: prioriza por litros del acuífero y verifica que el agua potable sea cero.
    3. **Clasifica cada evento OT por su efecto en esa línea base**: intento sin efecto contra incidente con efecto.
    4. Corre **local, sin nube**, en CPU, y cuesta **por kW**, al alcance de sitios medianos.
  - DripSafe **complementa** a estas herramientas; no compite con ellas.
- **Valor frente al BMS:** el BMS usa umbrales fijos. DripSafe usa la línea base de cada sitio, separa el intento OT del incidente con efecto y prioriza por agua.

## 10. Límites (declarados)

- **Los datos son simulados**, de 3 sitios y 7 días, y el generador es casi lineal. La validación demuestra el método, no su eficacia en plantas reales; la siguiente validación necesaria es con datos de una instalación real.
- **Sin balance de calor:** sin caudal ni temperaturas de agua no se detectan sensores falsificados por balance de calor (T1692.002, antes T0856, y T0832).
- **Estacionalidad:** 72 h de referencia no la cubren.
- **Ineficiencia crónica:** si la referencia ya es ineficiente, la línea base la aprende como normal. Se mitiga con la auditoría al instalar (§9). En el kit no se puede probar, porque hay un solo sitio por tipo de enfriamiento.
- **Cambio sin registro contra falla brusca:** con datos de proceso no se distinguen. DripSafe no los separa; los manda a verificar la configuración antes de mantenimiento.
- **Proyecciones y supuestos:** el ahorro es un escenario paramétrico; la energía y el CO₂ del detector se miden en una laptop; la intensidad hídrica de la red, el clima y los precios son supuestos citados.

## 11. Alcance y plan para el 21 de octubre (20:00)

| Prioridad | Pieza | Dueño | Cuándo |
|---|---|---|---|
| **MVP** | Actualizar `src/contrato.py` a las columnas del kit. Al cargar, `scenario`, `simulated_anomaly` y `split` se renombran a `etiqueta_*` para que **nunca** entren al modelo, con una prueba que lo verifique. Fijar hoy el esquema de `numeros_oficiales.json` | Misa | **19 oct** |
| **MVP** | Conseguir fuentes externas: normales del SMN (horarias), factor del SEN, disponibilidad del acuífero 3105, confirmación de JAPAY | Nico | **19 oct** |
| **MVP** | Línea base física + residuos + umbral por residuo + media móvil, partición 48/24 | Gadiel | 20 oct (mediodía) |
| **MVP** | 4 clases (reglas sobre residuos y registro OT) + inyector con la rejilla fija | Guille | 20 oct |
| **MVP** | Medición con CodeCarbon (10 repeticiones) y umbral de equilibrio | Misa (descarga a Gadiel) | 21 oct |
| **MVP** | Tabla (a), curva (b) y robustez (c) básica → `numeros_oficiales.json` | Nico + Misa | 21 oct |
| **MVP** | Commit del dashboard actual; luego clases, residuos en %, curva de sensibilidad y escenario paramétrico, trabajando con un JSON de ejemplo desde el 20 | Leo (ya tiene la base) | 20–21 oct |
| **MVP** | Acuífero con fuentes, purga y bono (respaldo B) con las horas de respaldo | Nico | 21 oct |
| Extra | Isolation Forest con ablación, incoherencia física, deriva, CUSUM, robustez (c) completa, cola por litros | Gadiel / Guille / Leo | Si sobra tiempo |

**Punto de corte:** si el 20 a mediodía el MVP no corre de punta a punta, se congela la detección y el resto del tiempo se usa en la validación y las cifras. Ninguna cifra va al pitch sin su supuesto o su fuente.

## Fuentes
- ASHRAE Guideline 14 (medición de ahorros de energía) e IPMVP (Efficiency Valuation Organization): línea base ajustada por carga y clima.
- LBNL, Smart Energy Analytics Campaign: mediana de ahorro con FDD del 9 % (https://buildings.lbl.gov/sites/default/files/Smart%20Energy%20Analytics%20Campaign%20Year%203%20Report_LBNL_11.1.19.pdf).
- Macknick, J. et al. (2012), *Operational water consumption and withdrawal factors for electricity generating technologies*, Environmental Research Letters / NREL.
- CRE / SEMARNAT, factor de emisión del Sistema Eléctrico Nacional (aviso vigente).
- CIFOX, kit del hackatón: `DATA_DICTIONARY.md`, `METRICS.md`, `EXERCISES.md`, `tools/generate_data.py`.
- Microsoft, diseño de centro de datos sin evaporación (2024): GeekWire, https://www.geekwire.com/2024/microsoft-shares-new-data-center-design-featuring-a-closed-loop-water-system-for-cooling/
- Google Douglas County, agua residual tratada: Data Center Knowledge, https://www.datacenterknowledge.com/green-materials/google-recycling-water-for-atlanta-data-center
- ASHRAE TC 9.9, Thermal Guidelines (5.ª ed., 2021): 18–27 °C de aire recomendado; clases de agua W32/W40/W45 (The Green Grid, https://www.thegreengrid.org/resources/glossary/W).
- Normales 1991–2020 de Mérida, fuente secundaria (por confirmar con el SMN): https://www.climatsetvoyages.com/climat/mexique/merida
- DOF, acuerdo de estudios técnicos del acuífero 3105 (2013, con la disponibilidad de 2009): https://vlex.com.mx/vid/dan-ta-cnicos-nacionales-neas-acua-pena-457884386
- Pendientes de obtener (Nico): normales y datos horarios oficiales del SMN de Mérida, factor de emisión del SEN vigente, intensidad hídrica de la generación eléctrica y disponibilidad vigente del acuífero 3105.
