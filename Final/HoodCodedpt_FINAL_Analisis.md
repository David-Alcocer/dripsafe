# DripSafe · Análisis final

> DATOS SIMULADOS · Hackatón CIFOX · AguaSegura AI · 22 de octubre de 2026 · commit 1ccb655


---

# DripSafe · Propuesta v7

**Hackatón CIFOX · AguaSegura AI · Sub-reto 3 (detección de anomalías en enfriamiento y gestión hídrica) · Métrica principal: PUE**

> DATOS SIMULADOS. Todo lo que sale del kit CIFOX (3 sitios ficticios, 7 días) se usa para **demostrar el método**, no como evidencia de que una tecnología sea mejor que otra (el `DATA_DICTIONARY` del kit lo prohíbe). Lo medido, lo estimado y lo proyectado se marcan por separado.

> **Alcance actualizado por D20 (20 oct):** el detector se limita a línea base por sitio, umbrales, media móvil y clasificación OT.

## 1. El problema

1. **Agua.** En Yucatán predomina el drenaje subterráneo en el acuífero kárstico Península de Yucatán (clave CONAGUA 3105), con cenotes y nivel freático que varía por zona. Si un centro de datos usa agua de ese acuífero para enfriamiento evaporativo, importan tanto la captación como la ruta autorizada de su purga; el kit no identifica el origen del agua ni el destino de la descarga.
2. **Energía.** Cada kWh que el enfriamiento desperdicia sube el PUE, las emisiones y el agua usada para generar electricidad.
3. **Ciberseguridad OT.** El enfriamiento lo controlan PLCs y un BMS. Un cambio de configuración no autorizado puede disparar el consumo o dañar equipos sin que nadie lo note.
4. **El hueco que atacamos: los umbrales fijos.** Las reglas del kit (y muchos BMS) usan un umbral igual para todos: PUE > 1.6, agua > 1.5 L/kWh de TI, entrada > 29 °C. En el kit, el sitio de enfriamiento líquido opera con un PUE cercano a 1.2. Puede subir su energía de enfriamiento **+140 %** (hasta un PUE de unos 1.57) en cualquier hora, incluso la más calurosa, sin disparar ninguna regla. El umbral fijo protege al sitio menos eficiente y deja ciegos a los eficientes.

## 2. La idea en una línea

**DripSafe aprende cómo debería comportarse cada sitio según su carga y su clima, avisa cuando la física no cuadra, distingue un intento OT de un incidente con efecto real y muestra la captación de agua en exceso para investigarla.**

Esto responde al reto 2 del kit: proponer un criterio nuevo, justificar su costo y separar ajuste, validación y prueba.

**Qué es conocido y qué es nuestro:**
- **Conocido:** comparar el consumo real con una línea base que depende de la carga y el clima es la práctica estándar de medición y verificación de ahorros (ASHRAE Guideline 14, IPMVP). La usamos a propósito, porque es auditable.
- **Nuestro:**
  1. Aplicar la línea base de M&V a la **detección por sitio** y **medir su sensibilidad** frente al umbral fijo. La curva de sensibilidad es la evidencia; detectar con una línea base, por sí solo, ya lo hacen el M&V continuo y el FDD.
  2. La **fusión evento–efecto**, que cruza el registro OT con la física para separar el intento del incidente.
  3. Cuantificar la **captación in situ en exceso**; el bono compara agua y energía como escenario de diseño. La prioridad operativa vigente depende de la clase OT.

## 3. Cómo funciona

```
CSV del kit (6 medidores + registro OT)
   │
   ├─▶ 1. Línea base física por sitio (aprendida en 48 h de la referencia)
   ├─▶ 2. Residuos = real − esperado (%)
   │       ├─ Umbral por residuo + media móvil de 4 h  → excesos de una variable y sostenidos
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

La decisión D20 fija esta arquitectura como detector completo para N2; no se añade un tercer método.

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
- **Por qué:** en el kit el cambio de configuración ocurre de madrugada (04:00–05:00 UTC), con carga y temperatura todavía cerca de su mínimo del día (ya empiezan a subir). Un setpoint alterado puede notarse hasta el pico de calor de la tarde.
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
- **CUE:** energía × **0.444 kgCO₂e/kWh**, el FESEN 2024 que SEMARNAT indica usar en la COA 2026. Es un factor oficial, no una medición local.
- **Agua de la red eléctrica:** **2.0632 L/kWh**, estimada con los factores de Macknick et al. (NREL, 2012) ponderados por la mezcla neta del SEN 2024 de la CNE. Son factores de tecnologías de EE. UU. aplicados a la mezcla mexicana: supuesto citado y editable, no un factor oficial mexicano.

## 6. Impacto en el acuífero de Yucatán

- **Disponibilidad:** la actualización técnica de CONAGUA de 2024 calcula **2059.634923 hm³/año** para todo el acuífero 3105; la cifra y su procedencia están en `resultados/numeros_oficiales.json`. La disponibilidad regional no resuelve los riesgos de calidad, presión local ni autorizaciones: el terreno es kárstico y la profundidad del agua varía por zona.
- **Purga cuantificada como escenario:** en una torre estable, sin pérdidas adicionales y a ciclos constantes, `purga = evaporación ÷ (ciclos de concentración − 1)`. Con 4 ciclos supuestos, 3 L evaporados generan 1 L de purga y requieren 4 L de reposición. Si se evita 1 L de reposición **por menor evaporación**, se evita ¼ L de purga; una fuga evitada no implica esa reducción. La descarga necesita una ruta autorizada: el kit no registra su destino.
- **El beneficio hídrico depende del tipo de enfriamiento** (el kit lo ilustra, no lo prueba):
  - **Evaporativo:** es grande.
  - **Aire:** es casi nulo; solo cuenta el agua de la red eléctrica.
  - DripSafe lo dice en lugar de prometer agua en todos los sitios.
- **Gobernanza:** los agregados de captación simulada y excesos estimados ilustran la información que podría contrastarse con la autorización de un sitio real. El producto actual no genera ni envía un reporte para CONAGUA; la purga exige medidor o balance físico aparte.
- **Justicia ambiental:** investigar excesos de captación podría beneficiar a otros usuarios solo si se conoce la fuente de suministro y se verifica una reducción real.

## 7. Bono Zero Freshwater Footprint: transición guiada por datos

**Propuesta:** enfriamiento líquido de agua tibia en circuito cerrado, rechazando el calor con enfriadores secos sin evaporación. El respaldo principal es un chiller condensado por aire; el adiabático con agua tratada es una opción futura. La meta de cero agua potable depende de verificar la fuente de llenado y reposición. DripSafe podría recomendar el modo al operador cuando tenga los datos de equipo necesarios; la demo actual no lo hace.

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
   - **El cálculo:** Nico cuenta las horas por encima de 27, 30, 33 y 35 °C como sensibilidad. Convertirlas en kWh del respaldo requiere carga y curva del chiller; no se hace una conversión directa de horas a litros o energía.
     - **Datos:** serie horaria ERA5 2025 vía Open-Meteo; fuente y límites en `docs/07` §5.4.
3. **Los dos respaldos, ninguno con agua potable:**
   - **A. Adiabático con agua residual tratada** (JAPAY). Gasta poca energía, pero evapora agua no potable. **Damos por hecho que JAPAY no confirmará a tiempo:** el pitch presenta el respaldo B como el plan y el A como mejora futura sujeta a convenio.
   - **B. Chiller mecánico condensado por aire.** No evapora agua y consume más electricidad, como el diseño de Microsoft. No depende de suministro de agua para disipar calor, aunque sí requiere verificar energía y rendimiento.
   - **Agua pluvial y condensado:** complemento parcial, no plan B. Abril y mayo son los meses más calientes y caen antes de las lluvias (junio a octubre), así que se necesitaría guardar agua de la temporada anterior. Lo declaramos parcial.
4. **Purga del respaldo A:** si se construye, debe contar con una ruta de descarga autorizada y verificable; no se presupone retorno a una planta de tratamiento.
5. **Legionella:** tratamiento y monitoreo del circuito de agua no potable, como en cualquier torre.
6. **El papel de DripSafe:**
   - **Propuesta futura:** con parámetros reales del equipo, comparar la energía de cada modo y recomendar cuál activar.
   - **Propuesta futura:** un medidor dedicado verifica la fuente y el volumen de agua potable del enfriamiento.
   - El operador confirma; la IA nunca manda órdenes.

**Meta por verificar:** WUE potable de enfriamiento = 0 L/kWh durante operación si llenado y reposición usan fuente no potable; se necesitará un medidor dedicado. El kit no separa potable de no potable. Con un COP de referencia aportado por Misa y horas ERA5 por encima de 30 °C, el **PUE proyectado del escenario es aproximadamente 1.284**, bajo los supuestos de `docs/07` §5.4. No es el PUE físico de esta arquitectura: faltan curvas locales y energía de bombas. El respaldo A sigue siendo una alternativa futura condicionada a suministro y descarga.

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
- **Expansión:** Querétaro, el polo nacional de centros de datos, también con estrés hídrico, y otros acuíferos sobreexplotados. El método no depende de Yucatán; el impacto hídrico local se evalúa según la fuente de suministro y el destino de las descargas.
- **Competencia:**
  - **Diagnóstico automático de fallas (FDD) y analítica de BMS:** Schneider EcoStruxure, Siemens Desigo, SkyFoundry SkySpark. Detectan fallas de equipos y se enfocan en energía.
  - **Monitoreo OT:** Nozomi, Claroty, Dragos. Ven el tráfico de red y también variables de proceso leídas de los protocolos industriales. No modelan la línea base de energía y agua por carga y clima, ni priorizan por litros.
  - **Lo que DripSafe hace distinto:**
    1. Una **línea base de energía y agua** por sitio, ajustada por carga y clima.
    2. Hace visible la **captación de agua en exceso**; la meta de cero agua potable del bono requiere un medidor y una fuente no potable verificada.
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
| Extra | Incoherencia física, deriva, CUSUM, robustez (c) completa, cola por litros | Gadiel / Guille / Leo | Si sobra tiempo |

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
- Pendientes de obtener (Nico): normales y datos horarios oficiales del SMN de Mérida y disponibilidad vigente del acuífero 3105. El factor de emisión del SEN ya está integrado (0.444 kgCO₂e/kWh) y la intensidad hídrica se publica como estimación NREL/CNE (2.0632 L/kWh).

---

# 05 · Solución técnica

> Documento para **Gadiel** (modelo), **Misa** (datos y PUE inicial), **Nico** (evaluación del detector y cálculo de impacto), **Misa + Nico** (balance neto final) y **Leo** (demo). **Actualizado tras el kit (19 oct):** ver la sección siguiente.

## Lo que trae el kit (19 oct)

> Resumen del kit oficial. **El kit no se sube al repo.** Aquí solo se describe su estructura. Decisiones derivadas: D12, D13 y D14 en [02-decisiones.md](02-decisiones.md).

**Datos:** un CSV **totalmente simulado** con 3 sitios ficticios × 168 horas (una semana), intervalo de 1 hora.

| Columna del kit | Unidad | Uso |
|---|---|---|
| `timestamp`, `site_id` | UTC · SIM-A/B/C | Clave: una fila por sitio y hora |
| `cooling_type` | aire / evaporativa / liquida | Un tipo por sitio |
| `energy_it_kwh`, `energy_total_kwh` | kWh por intervalo | PUE = suma(total) / suma(IT), **nunca** el promedio de PUE horarios |
| `water_l` | L por intervalo | Captación in situ simulada; "WUE pedagógica" = suma(agua) / suma(IT) |
| `load_pct`, `outdoor_temp_c`, `inlet_temp_c` | %, °C, °C | Variables de contexto |
| `ot_event` | normal / login_fallido / cambio_config_no_autorizado | Evento OT resumido; un login fallido no prueba un ataque |
| `split` | referencia (72 h) / evaluacion (96 h) | Ajustar con referencia, evaluar con evaluacion |
| `scenario`, `simulated_anomaly` | etiquetas | **Prohibido** usarlas como entrada; solo para evaluar |

**Qué cambia respecto al plan original:**
- **No hay sensores por equipo** (chiller, bombas, torre, temperaturas del agua, caudal). La "coherencia física" se hace a nivel agregado por sitio: energía auxiliar (total − IT) y agua esperadas según carga, temperatura exterior y tipo de enfriamiento.
- **Las reglas del kit ya detectan todo en su ejemplo.** Por eso:
  - **Gadiel** construye una línea base por sitio con umbrales de residuo y media móvil, ajustada solo con referencia; las reglas OT clasifican cada alerta.
  - **Nico** compara ese detector con las reglas del kit por episodio, con ajuste y evaluación separados, varias corridas y calidad reportada junto al costo. Si las reglas bastan, se dice. *El método más ligero que funciona es el argumento Green AI.*
- **Stack:** el Stack A (Streamlit) del kit es la referencia y se usa **Python 3.12**. Las herramientas del kit (`common/cifox.py` y `tools/compare_detectors.py`) se pueden reutilizar citando que vienen del kit (licencia MIT).
- **Reglas de presentación del kit:** "DATOS SIMULADOS" siempre visible. Energía y emisiones como **estimación con supuestos** (watts y gCO₂e/kWh editables, con análisis de sensibilidad). Nada de litros por consulta. Los ahorros son **proyecciones**, no observaciones. Hay que explicar **qué venía en el kit y qué aportamos**.

**Entregable que sugiere el kit:** demo local de 3 minutos, README reproducible, cambios y tests, ficha de datos y supuestos, resultados con incertidumbre, tres límites y la siguiente validación necesaria.

## Concepto: línea base + fusión evento–efecto

> **Alcance vigente (D20):** línea base física por sitio + umbral por residuo + media móvil de 4 h y clasificación OT.

```text
CSV del kit (6 medidores + registro OT)
   │
   ├─▶ 1. Línea base física por sitio (aprendida en 48 h de la referencia)
   ├─▶ 2. Residuos = real − esperado (%)
   │       ├─ Umbral por residuo + media móvil de 4 h   → excesos sostenidos
   ├─▶ 3. Registro OT  →  reglas
   ├─▶ 4. Fusión evento–efecto  →  4 clases (D16)
   └─▶ 5. Cola de alertas en el dashboard: kWh y L en riesgo por hora
```

1. **La línea base** aprende cómo debería comportarse cada sitio según su **carga** (energía de TI) y su **clima** (pérdida de enfriamiento gratuito arriba de 20 °C).
2. **El residuo** (real menos esperado) delata los excesos sostenidos. El umbral se calibra con 24 h extra de referencia.
3. **Las 4 clases OT (D16)** cruzan el registro OT con los residuos: incidente con efecto, cambio no autorizado, escalón sin registro e intento de acceso.
4. **La prioridad operativa depende de la clase OT.** Los litros de captación en exceso se muestran como contexto para investigar; solo podrían atribuirse al acuífero si se confirma la fuente del suministro (ver [07-agua-y-acuifero.md](07-agua-y-acuifero.md)).

## Pipeline

```text
data/ (kit)  →  src/datos/cargar.py  →  src/modelo/ (baseline + residuos)  →  src/fusion/ (reglas + 4 clases)
                                                                          →  src/metricas/  →  resultados/numeros_oficiales.json  →  app/ (Streamlit)
```

| Paso | Responsable | Herramienta | Fase |
|---|---|---|---|
| Cargar kit y validar contrato | Misa (M1) | pandas + `src/contrato.py` | 0 |
| Partición 48/24, regresión por sitio, residuos, umbral, MM 4 h | Gadiel (G1) | pandas + numpy | 0 |
| Rejilla de inyecciones + 4 clases OT | Guille (U1) | pandas | 0 |
| PUE/WUE, exceso estimado, episodios | Nico (N1) | pandas | 0 |
| JSON ejemplo y pantallas con estados vacíos | Leo (L1) | Streamlit | 0 |
| **Integración y punto de corte** | Todos (Fase 1) | — | 1 |
| Congelar parámetros, rejilla, tabla y curva | G2+U2+N2 | — | 2 |
| CodeCarbon (10 repeticiones) y umbral de equilibrio | Gadiel (G3) + Misa | CodeCarbon | 2 |
| Balance neto compartido | Misa + Nico (M3/N3) | pandas | 2 |
| Acuífero + bono + fuentes | Nico (N4) | — | 2 |
| Integración final, ensayo cronometrado | Misa (M4) | — | 2 |
| Dashboard integrado + diapositivas | Leo (L2) | Streamlit | 2 |

**Entrega entre Misa y Nico:** Misa entrega el PUE inicial junto con la telemetría limpia y las energías total y de TI en kWh, indicando unidades, intervalo y periodo. El PUE por sí solo no basta para calcular kWh ahorrados. Nico usa esa referencia, las alertas, el consumo esperado y las mediciones de CodeCarbon de Gadiel para calcular el impacto posterior. Los formatos de intercambio siguen definidos en [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

**Estado:** este reparto está aprobado (D10, D11 y D13); los cálculos y la consolidación de resultados siguen pendientes de implementación.

## Stack

- **Python 3.11+**
- `pandas`, `numpy`: datos
- `codecarbon`: energía y CO₂ del modelo
- `streamlit`, `plotly`: demo
- `jupyter`: exploración

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy scipy codecarbon streamlit plotly jupyter
```

## El detector: línea base, umbrales y media móvil

### 1. Línea base física por sitio (MVP)

Para cada sitio, una **regresión lineal** con dos variables físicas:
- **Calor a disipar:** `energy_it_kwh`.
- **Pérdida de enfriamiento gratuito:** `energy_it_kwh × max(0, outdoor_temp_c − 20)`. Arriba de 20 °C el aire exterior ya no ayuda y cada grado cuesta energía o agua.

Con eso se predice la **energía no TI** (`energy_total − energy_it`, ver D18) y el agua. La **temperatura de entrada** depende del clima y no del tamaño de la carga, así que su línea base usa solo `max(0, outdoor_temp_c − 20)` y una constante. **El setpoint y la configuración no entran como variables:** si alguien los altera, el consumo real se separa de lo esperado y se ve.

**Transparencia:** la forma coincide con la del generador del kit. Lo declaramos: la elegimos porque representa la física, y para no depender de esa coincidencia la validación prueba **una forma mal especificada** (solo TI y temperatura) y **datos con ruido extra** (§4 de la propuesta).

Cada alerta se explica en una frase: *"SIM-A gasta 31 % más energía no TI de lo esperado para su carga y clima."*

### Cómo se explica cada alerta (#8)

`src/modelo/explicar.py` agrega dos columnas a `alertas.csv` sin volver a detectar nada (`python -m src.modelo.explicar --alertas data/resultados/alertas.csv`; por omisión reescribe el mismo archivo):

- **`variable_principal`** (`energia`, `agua`, `entrada` o vacío): entre las variables que el detector marcó (`exceso_*`), la de mayor residuo relativo. Energía y agua ya vienen en %; para comparar la entrada (°C), cada residuo se divide entre el umbral mínimo del detector (3 %, 3 % y 0.5 °C), así que **1 °C de entrada pesa lo mismo que 6 %**. En empate gana el orden energía, agua, entrada. Vacío si no hay alerta física (por ejemplo, un login fallido sin exceso).
- **`tipo_sugerido`** sale solo de la clase OT:

| Clase | `tipo_sugerido` | Por qué |
|---|---|---|
| Incidente OT, cambio no autorizado, intento de acceso | `posible_ataque` | Hay un evento OT de por medio. «Posible»: un login fallido no prueba una intrusión |
| Escalón sin registro | `ineficiencia` | Exceso físico sin evento OT. La acción no cambia: revisar la configuración **antes** de mandar a mantenimiento (regla de oro 1) |
| Normal | `normal` | Sin alerta |

**Límite declarado:** un ataque que no deja registro OT (por ejemplo, el `cambio_sin_registro` de la rejilla) sale como `ineficiencia`, porque un exceso por sí solo no distingue falla de ataque (docs/06 §7.5). La rejilla lo mide en `clasificacion_correcta_pct` en lugar de esconderlo.

### 2. Detectores sobre los residuos (MVP)

1. **Umbral por residuo** (energía, agua, entrada): alerta si el residuo supera el máximo observado en las 24 h de calibración más un **margen del 50 %**, fijado antes de ver la evaluación.
2. **Media móvil de 4 h** de cada residuo, con su propio umbral igual. Atrapa excesos pequeños pero sostenidos. Son unas 5 líneas con pandas.

*Extra si sobra tiempo:* **CUSUM** para derivas de días.

**Límite mínimo detectable** (estimación analítica que se verifica en la prueba de robustez):
- El ruido del kit sobre la energía total es de ±1.5 % de la energía de TI. En el sitio líquido eso equivale a ~4.4 % de la energía no TI por hora.
- **Detector 1, en una hora:** detecta un exceso de ~+15 %.
- **Detector 2, sostenido 4 h:** detecta uno de ~+10 %.
- Las reglas del kit **no ven ninguno de los dos**.

## Las 4 clases OT (D16)

El diagnóstico sale de cruzar el **registro OT** con los **residuos físicos**. Diseño de Guille y Gadiel, lógica revisada por Nico.

| Clase | Condición | Acción |
|---|---|---|
| **Incidente OT con efecto** | Evento OT **y** residuo físico desde el inicio del evento hasta 24 h después | Máxima: restaurar config aprobada; modo seguro manual |
| **Cambio no autorizado** | `cambio_config_no_autorizado`, con o sin efecto | Alta: comparar contra config aprobada; vigilar 24 h |
| **Escalón sin registro** | Un residuo supera el umbral de golpe sin evento OT | Alta: comparar setpoints; si es agua, inspección física |
| **Intento de acceso** | Solo `login_fallido`, residuos normales | Media: revisar accesos |

**Dos reglas de oro:**
1. Ningún exceso sin explicar va directo a mantenimiento.
2. Ningún cambio no autorizado es "sin urgencia".

**Ventana de 24 h:** en el kit el cambio de configuración ocurre de madrugada; un setpoint alterado puede notarse hasta la tarde. Un residuo que ya existía **antes** del evento se marca `coincidente, no causal`, salvo que dé un escalón dentro de la ventana. Se reporta cuántas coincidencias al azar habría combinando eventos OT con residuos en la evaluación limpia.

*Extra si sobra tiempo:* `incoherencia física` (sube entrada y baja energía no TI) y `deriva gradual`.

## Métricas

**Siempre cocientes de sumas, nunca promedios de cocientes horarios.**

```text
PUE = Σ energía total (kWh) / Σ energía de TI (kWh)
WUE = Σ agua in situ (L)    / Σ energía de TI (kWh)
CUE = Σ emisiones CO2e (kg) / Σ energía de TI (kWh)  =  factor de emisión de la red × PUE
```

**Umbral de equilibrio (D15 + propuesta §5):** el **número central** del balance no es "el ahorro proyectado anual". Es el **costo anual del detector** (CodeCarbon × 10 repeticiones, inferencia horaria 8760 veces + reentrenamiento por temporada) comparado con **el exceso de una sola hora de ineficiencia típica**. Para no contar el ajuste dos veces, la medición separa `inferencia` (parámetros congelados) de `entrenamiento`; `corrida_completa` se conserva como referencia y no se suma. La inferencia se mide sobre un lote y se divide entre sus horas antes de multiplicar por 8 760, para no sobreestimar el costo por hora. Si el costo son unos pocos Wh y una hora de ineficiencia son decenas de kWh, **basta una detección al año** para que el balance sea positivo. Este número no depende de que el ahorro proyectado sea exacto.

**PUE inicial y final proyectado:**
- **Inicial (Misa):** PUE calculado con los datos limpios del kit, para un periodo definido.
- **Final proyectado (Nico):** se resta el exceso de energía estimado de los periodos con anomalías de ineficiencia, suponiendo que se corrigieran:

```text
PUE_final_proyectado = (E_total − E_exceso_evitado_estimado) / E_TI
```

El exceso se estima comparando cada periodo anómalo contra el comportamiento normal en condiciones similares (misma carga de TI y hora), usando el consumo esperado que entrega Gadiel. Nico documenta la corrección supuesta y mantiene el mismo periodo y energía de TI en ambos PUE. Una alerta no demuestra por sí sola un ahorro.

El campo existente `pue_despues` se presenta como **PUE final proyectado**. Los ahorros también se identifican como estimaciones hasta contar con evidencia medida tras una intervención.

## Balance neto (obligatorio)

**Hay que demostrar con números que el modelo ahorra más de lo que gasta.**

**Responsables del cálculo y validación final: Misa + Nico.** Gadiel proporciona las mediciones del modelo; Misa proporciona la referencia inicial y Nico estima el ahorro. Misa + Nico calculan juntos el balance, restando el costo del modelo con unidades y horizontes temporales compatibles. El valor puede ser positivo, cero o negativo; se reporta el resultado obtenido.

```text
Costo del modelo:
  E_modelo   = energía de entrenamiento + inferencia durante un año (kWh)  ← CodeCarbon
  CO2_modelo = E_modelo × factor de emisión de la red (kg CO2e/kWh)
  Agua_modelo = E_modelo × (WUE_sitio + intensidad hídrica de la electricidad)  (L)

Ahorro:
  E_ahorrada  = (PUE_inicial − PUE_final_proyectado) × E_TI anual (kWh)
  CO2_ahorrado = E_ahorrada × factor de emisión
  Agua_ahorrada = ΔWUE × E_TI + E_ahorrada × intensidad hídrica de la electricidad  (L)

Balance neto = Ahorro − Costo   → debe ser > 0
Razón        = Ahorro / Costo    → "ahorra N veces lo que consume"
```

Las cantidades de ahorro de este esquema son **proyecciones**. Si se extrapola a un año, Nico documenta el supuesto y utiliza ese mismo horizonte para el costo. El cálculo de agua requiere conocer el consumo o un WUE aplicable y la intensidad hídrica de la electricidad; un mejor PUE no demuestra automáticamente ahorro de agua.

**Datos a buscar y citar (Nico):**
- Factor de emisión del Sistema Eléctrico Nacional de México, en su valor oficial más reciente.
- Intensidad hídrica de la generación eléctrica (litros por kWh). El artículo *Making AI Less "Thirsty"* explica cómo se calcula el agua "fuera del sitio".

**Resultados pendientes:** si faltan datos o factores suficientes para agua o emisiones, Nico marca esas métricas como pendientes. Cualquier valor de referencia se identifica como supuesto, sin presentarlo como medición del kit.

## Demo (Streamlit)

Pantallas sugeridas:
1. **Resumen:** PUE inicial y final proyectado, ahorro estimado de agua cuando pueda calcularse y balance neto en tarjetas grandes. Leo usa las cifras consolidadas por Nico.
2. **Serie de tiempo:** consumo con las anomalías marcadas en rojo o naranja.
3. **Detalle de alerta:** qué variable falló, si es ineficiencia o posible ataque, y qué hacer.
4. **Balance neto:** costo del modelo frente al ahorro, en una gráfica de barras.

```bash
streamlit run app/main.py
```

**Importante:** grabar un video de la demo el 21 como respaldo.

---

# 06 · Ciberseguridad OT

> **Dueño:** Guille. Cubre el criterio «Impacto en ciberseguridad» (§13 de la convocatoria), la regla 18 (nada de ataques a sistemas reales) y el reto 2 del kit («documentad qué no puede inferirse de un evento sintético»). Las técnicas son de **MITRE ATT&CK for ICS v20** (13 oct 2026), verificadas contra el catálogo oficial de MITRE.

**En un minuto:**
- DripSafe **no** mira la red. Mira la **física**: cuánta energía y agua debería gastar cada sitio según su carga y su clima. Un cambio de configuración puede pasar un filtro de red con comandos válidos, pero el gasto de energía o agua lo delata.
- Cruza esos excesos con el registro OT y los clasifica en **4 clases**, con prioridad y acción, sin afirmar nunca que un exceso prueba un ataque (§4).
- En el kit, con su ruido, **DripSafe ve el 100 % de los excesos inyectados desde +10 %**. Las reglas fijas del kit no ven ninguno por debajo de +80 % ni ningún exceso de agua (§6).
- En los cambios de configuración con efecto 8 h después, las reglas ven el evento, pero **dejan pasar 1 710 kWh** de exceso; DripSafe deja pasar 5 kWh y lo clasifica como incidente (§6).
- Lo decimos también cuando no nos favorece: con el doble de ruido, a +10 % DripSafe solo ve un tercio; con la ventana de 24 h, **1 de cada 5 eventos OT al azar** encontraría un exceso que no causó; y en una ola de calor fuera de lo aprendido el umbral se duplica y un +10 % pasó sin verse en 8 de 11 tardes (§6, §6b, §7).

## 1. OT en un centro de datos, en una página

- **IT** son las computadoras, los servidores y los datos. **OT** son los sistemas que controlan equipos físicos: chillers, bombas, torres de enfriamiento, manejadoras de aire y válvulas.
- El enfriamiento de un centro de datos es OT. Lo controlan **controladores (PLC)** y un **BMS** (sistema de gestión del edificio) con sus pantallas. La energía la mide, muchas veces, **otro sistema (EPMS)**.
- **Por qué es vulnerable:**
  - **Protocolos sin seguridad.** Modbus (de 1979) y muchas instalaciones de BACnet no autentican ni cifran: quien llega a la red puede leer valores o escribir setpoints.
  - **Equipos de 15 a 20 años** que casi nunca se actualizan.
  - **Redes de oficina y de planta mal separadas.**
  - **Accesos remotos** de proveedores mal protegidos.
- **Modelo Purdue:** divide la red en niveles, desde los sensores y actuadores (nivel 0) hasta la red corporativa e internet (niveles 4–5). La regla de oro es que los niveles bajos no queden expuestos a internet.

## 2. Modelo de amenazas (niveles Purdue)

![Modelo de amenazas por niveles Purdue](img/modelo-amenazas-purdue.svg)

El diagrama ([`img/modelo-amenazas-purdue.svg`](img/modelo-amenazas-purdue.svg)) está en formato de diapositiva, listo para usarse.

**Supuesto declarado:** el kit no trae red, equipos ni protocolos. El diagrama es la arquitectura típica del enfriamiento de un centro de datos, no la de un sitio real. Sirve para ubicar dónde entraría un atacante y qué parte de su rastro le llega a DripSafe.

| # | Punto de ataque | Técnicas (ATT&CK for ICS v20) | ¿Lo ve DripSafe? |
|---|---|---|---|
| 1 | BMS o pantallas expuestos a internet | T0883 Internet Accessible Device | No: DripSafe no mira la red. Se cierra con zonas de red (M0930) |
| 2 | Acceso remoto del proveedor de mantenimiento | T0822 External Remote Services → T0886 Remote Services | No. Se cierra con MFA (M0932) y un equipo de salto con permisos mínimos |
| 3 | Contraseñas válidas robadas o de fábrica | T0859 Valid Accounts · T1694.001 Default Credentials | Solo los intentos fallidos que quedan en el registro: `login_fallido` → **intento de acceso** |
| 4 | Cambio de setpoint o de configuración | T0836 Modify Parameter. Si la orden llega directo al controlador sin pasar por el BMS: T1692.001 Unauthorized Message: Command Message | Con registro → **cambio no autorizado**. Sin registro → el exceso aparece como **escalón sin registro** |
| 5 | Efecto físico | T0831 Manipulation of Control → T0828 Loss of Productivity and Revenue (kWh y litros de más). Si llega a sobrecalentar: T0879 Damage to Property | Sí: es lo que mide la línea base. Evento + exceso en 24 h → **incidente OT con efecto** |

**Un caso real que se parece: FrostyGoop (MITRE C0041, enero de 2024).** Atacaron la calefacción urbana de una ciudad de Ucrania. El malware (S1165) escribió por **Modbus TCP** valores en controladores ENCO usando **comandos legítimos** (T0836), y dejó sin calefacción a la población; MITRE registra que la reparación tomó dos días. Es climatización como la nuestra, y la lección es la misma: los comandos eran válidos, así que un filtro de red no los distinguía, pero la física cambió.

**MITRE describe nuestra idea como estrategia de detección.** Para T0836, la analítica AN1908 propone alertar ante un cambio de parámetro sin control de cambios «**correlacionado con la deriva posterior del historiador**» y, cuando la telemetría lo permite, exigir un efecto en el proceso. Es la fusión evento–efecto de §4. Para los reportes falsos (T1692.002), AN2215 propone contrastar la telemetría contra **una medición independiente** del mismo fenómeno, que es lo que haría DripSafe con los medidores de energía si el sitio midiera caudal y temperaturas del agua (§3C).

## 3. Tabla ATT&CK final, aplicada al kit

**Aviso de versión:** MITRE **revocó T0855 y T0856** en abril de 2026. Ahora son subtécnicas de T1692 Unauthorized Message: T0855 Unauthorized Command Message pasó a **T1692.001 Command Message** y T0856 Spoof Reporting Message pasó a **T1692.002 Reporting Message**. Si el jurado o el mentor consultan la matriz, ya no van a encontrar los IDs viejos.

### A. Lo que se ve en el kit tal cual

| Técnica | Táctica | Rastro en el kit | Clase en DripSafe | Evidencia |
|---|---|---|---|---|
| T0859 Valid Accounts · T1694.001 Default Credentials (intentos) | Persistencia, movimiento lateral | `login_fallido`, 3 h en SIM-C | Intento de acceso (media) | Kit sin inyecciones: 3 h en esa clase |
| T0836 Modify Parameter | Afectar el control del proceso | `cambio_config_no_autorizado`, 2 h en SIM-C, sin efecto físico | Cambio no autorizado (alta) | Kit sin inyecciones: 2 h en esa clase |

### B. Lo que se inyecta (rejilla, §5)

| Técnica | Qué se simula | Clase esperada | Resultado en el kit |
|---|---|---|---|
| T0836 + T0831 | Cambio registrado y, 8 h después, energía no TI +20 % durante 12 h | Incidente OT con efecto | 16 de 16 vistas y bien clasificadas |
| T0836 sin registro (o T1692.001) | Energía no TI +20 % durante 12 h, sin evento | Escalón sin registro | 17 de 17 |
| T0831 → T0828 | Excesos de energía (+10 a +80 %) y de agua (+25 y +50 %) durante 4 h | Escalón sin registro | 108 de 108 |

### C. Lo que DripSafe **no** puede ver con el kit, y qué haría falta

| Técnica | Por qué no se ve | Qué haría falta medir |
|---|---|---|
| T1692.002 Reporting Message (antes T0856) | Un sensor falso con valores creíbles necesita otro sensor con el que contrastarse | Caudal y temperaturas de suministro y retorno del agua: el balance de calor (caudal × ΔT) contra el medidor de energía, como propone AN2215 |
| T0832 Manipulation of View | Igual: sin balance de calor no hay contra qué comparar lo que ve el operador | Lo mismo, más la energía por equipo (chiller, bombas, torre) |
| T0815 Denial of View | En el kit no faltan datos | Una regla directa: sensores vacíos mientras los medidores de energía siguen reportando |
| T0838 Modify Alarm Settings | Cambiar un límite de alarma no mueve la física | Que el BMS registre esos cambios. Si los registra, DripSafe los trata como cambio no autorizado (alta) |
| T0883, T0822, T0886 | DripSafe no mira el tráfico de red | Un monitor OT de red (Nozomi, Claroty, Dragos). DripSafe lo complementa, no lo sustituye |

Los escenarios del apéndice A demuestran T1692.002, T0832 y T0815 con datos sintéticos que sí traen esos sensores. **No son evidencia del kit**: muestran por qué vale la pena instalar esa instrumentación (propuesta §9).

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

Se reporta para ventanas de 1, 4, 8, 12 y 24 h, porque es un intercambio: una ventana corta casi no se equivoca por casualidad, pero se pierde el caso del cambio que se nota 8 h después. Los resultados sobre el kit están en la §6.

### Mensaje honesto para el pitch

> *"DripSafe no afirma que un residuo pruebe un ciberataque. Distingue un intento (login fallido), un cambio (sin efecto confirmado), un escalón sin registro (falla o cambio no registrado: primero se revisa la configuración) y un incidente con efecto (evento OT seguido de un exceso físico medible). Y dice qué tan seguido esa atribución podría ser casualidad."*

## 5. Rejilla de inyecciones sobre el kit (U1 · U2)

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

Los resultados sobre el kit están en la §6.

## 6. Resultados sobre el kit (corrida del 21 de octubre)

Corrida de `python -m src.ataques.correr_rejilla --kit …` con el código del commit `cf46ead`: 141 inyecciones por condición. Son 18 de cada tipo, salvo 17 cambios sin registro y 16 cambios con efecto: en SIM-C, 3 posiciones de 12 h no tenían un lugar limpio por su evento OT y quedan como omitidas (la auditoría de Nico, `src/evaluacion/auditar_rejilla.py`, las cuenta). Son **agregados**; las filas del kit no salen de la laptop.

**Ya son las cifras oficiales.** Nico las integró en `resultados/numeros_oficiales.json` (N2, PR #49). El 21 de octubre se volvió a correr la rejilla con `main` (`c93194d`): los 326 valores del bloque `deteccion` salieron idénticos y la auditoría de denominadores pasó en las 6 corridas. Esa noche se repitió con `58158e0`, que ya incluye el tipo sugerido de Gadiel (#59), y el resultado fue el mismo: el #59 no mueve ninguna cifra oficial.

**Las anomalías originales del kit: empate, como se esperaba.** Los dos métodos detectan los 3 episodios (21 filas), en la primera hora y sin falsas alarmas (0 por día y sitio; IC 95 %: 0 a 0.33, sobre 267 horas limpias sumando los 3 sitios). DripSafe los clasifica así: la ineficiencia de SIM-A y la fuga de SIM-B como **escalón sin registro** (la fuga, con inspección física), los logins de SIM-C como **intento de acceso** y su cambio como **cambio no autorizado**.

**La rejilla: dónde se separan.**

| Inyección (4 h salvo los cambios, 12 h) | DripSafe ve el efecto | Con el doble de ruido (5 semillas) | Reglas del kit ven el efecto | Lo que las reglas no vieron |
|---|---|---|---|---|
| Energía no TI +10 % | 100 % | 33 % (22–50) | 0 % | 312 kWh |
| Energía no TI +20 % | 100 % | 80 % (72–89) | 0 % | 625 kWh |
| Energía no TI +40 % | 100 % | 100 % | 0 % | 1 249 kWh |
| Energía no TI +80 % | 100 % | 100 % | 33 % (solo SIM-A) | 1 382 kWh |
| Agua +25 % | 100 % | 100 % | 0 % | 1 116 L |
| Agua +50 % | 100 % | 100 % | 0 % | 2 231 L |
| Cambio sin registro (+20 %) | 100 % | 98 % (94–100) | 0 % | 1 887 kWh |
| Cambio con efecto 8 h después (+20 %) | 100 % | 98 % (94–100) | 0 % del efecto; sí ven el evento | 1 710 kWh |

- **Clase OT:** en el 100 % de las horas con efecto visto, DripSafe puso la clase esperada, con y sin ruido. Todos los cambios sin registro quedaron como escalón sin registro, que manda a revisar la configuración antes que a mantenimiento.
- **Tipo sugerido** (`tipo_sugerido`, #8, `src/modelo/explicar.py`): las fallas salen como ineficiencia en el 100 % (108 de 108) y los cambios con efecto como posible ataque en el 100 % (16 de 16); los cambios sin registro, en el 0 % (0 de 17), porque sin evento OT nada los distingue de una falla (§7, punto 5). Con ruido da lo mismo. **No es una cifra de precisión:** el tipo sale solo de la clase OT, así que da 100 % o 0 % por construcción y mide si el ataque dejó registro. Además, las fallas dan 100 % porque la rejilla las pone lejos de los eventos OT; una falla en las 24 h siguientes a un login saldría como posible ataque. No está en `numeros_oficiales.json` ni va en las diapositivas.
- **Rapidez:** DripSafe ve el efecto en la misma hora en que empieza, salvo a +10 %, que tarda en promedio 0.4 h. Lo que deja pasar: 28 kWh en los de +10 % y 5 kWh en los cambios con efecto.
- **Por qué las reglas no ven:** el sitio líquido trabaja con un PUE cercano a 1.2 y el evaporativo con un WUE cercano a 0.9 L/kWh. Les cabe mucho exceso antes de llegar a 1.6 o a 1.5 L/kWh.
- **Falsas alarmas con el doble de ruido:** suben de 0 a 0.07 por día y sitio.

**Coincidencias al azar (§4b).** Si un evento OT cayera en una hora al azar de la evaluación, ¿cuántas veces encontraría un exceso que no causó?

| Ventana | 1 h | 4 h | 8 h | 12 h | 24 h |
|---|---|---|---|---|---|
| Kit | 1.4 % | 3.6 % | 6.8 % | 10.3 % | **20.4 %** |
| Con el doble de ruido (media) | 2.0 % | 5.0 % | 9.5 % | 14.0 % | 27.0 % |

Con 24 h, uno de cada cinco «incidentes OT con efecto» podría ser casualidad. Por eso el incidente pide **confirmar en sitio** antes de actuar, y el motivo dice cuántas horas pasaron entre el evento y el exceso: a menos horas, menos probable la casualidad.

### 6b. ¿Y un atacante más cuidadoso? (pruebas exploratorias)

**Aviso:** estas pruebas **no** son parte de la rejilla fijada ni de `numeros_oficiales.json`. Se escribieron el 21 de octubre, **después** de ver la rejilla, para responder con datos tres preguntas probables del jurado. No van en las diapositivas; sirven para las preguntas. Mismas reglas que la rejilla: solo se tocan horas de evaluación de copias y el detector aprende exactamente lo mismo en cada una.

```bash
python -m src.ataques.exploratorias --kit RUTA/operaciones_simuladas.csv   # agregados → data/resultados/exploratorias.json
```

**1. ¿Qué tan pequeño tiene que ser un exceso para que no se vea?** Son los umbrales que calibró el detector congelado. Por debajo de ellos, un exceso no se ve, y lo decimos:

| Sitio | Energía no TI, una hora | Energía no TI, sostenido (media de 4 h) |
|---|---|---|
| SIM-A (aire) | 6.1 % | 4.1 % |
| SIM-B (evaporativa) | 10.1 % | 6.8 % |
| SIM-C (líquida) | 11.3 % | 7.5 % |

En agua, el piso es de 3 % en una hora y 2 % sostenido en los tres sitios, porque el agua del kit no trae ruido.

**2. ¿Y si sube la energía poco a poco?** La línea base **no se reentrena sola**, así que una subida lenta no se vuelve «normal». Rampas de 36 h que suben la energía no TI desde 0 % un poco cada hora, en las posiciones de la rejilla (13 por velocidad; 5 no caben en la evaluación):

| Velocidad | Vistas | Horas hasta verla (mediana · máx.) | Exceso al verla (mediana · máx.) | kWh antes de verla (máx.) |
|---|---|---|---|---|
| +0.25 % por hora | 13 de 13 | 19 · 24 h | 5 % · 6.25 % | 31.9 kWh |
| +0.5 % por hora | 13 de 13 | 10 · 14 h | 5.5 % · 7.5 % | 20.4 kWh |
| +1 % por hora | 13 de 13 | 7 · 10 h | 8 % · 11 % | 25.5 kWh |

Todas quedaron como escalón sin registro.

**3. ¿Y si ataca en una ola de calor?** Este es el punto débil. Fuera del clima que aprendió (15–31 °C en la referencia), el detector **duplica el umbral** para no llenar de falsas alarmas un clima que no conoce, y la alerta sale con «confianza baja». En el kit ya hay 11 horas de evaluación así. Prueba: 4 tardes por sitio (12:00–15:00) con la temperatura 1 °C por encima de lo más caliente que aprendió; el calor sube la energía, el agua y la temperatura de entrada exactamente lo que espera la línea base, y encima va un ataque de 4 h:

| Ataque | Con calor fuera de rango (11 tardes) | En la rejilla, dentro del rango |
|---|---|---|
| Solo calor, sin ataque | 0 alertas | — |
| +10 % | 3 de 11 | 100 % |
| +15 % | 7 de 11 | — |
| +20 % | 10 de 11 | 100 % |
| +30 % | 11 de 11 | — |

El calor por sí solo no genera falsas alarmas, pero un atacante que espere una ola de calor tiene más margen. Lo que lo cierra es lo que ya propone el equipo: **líneas base por época del año** (secas, lluvias y nortes), entrenadas con periodos verificados, para que una ola de calor de mayo no sea «clima no visto».

## 7. Qué **no** se puede inferir de un evento sintético (reto 2 del kit · U3)

1. **Un `login_fallido` no dice quién ni desde dónde.** El kit no trae usuario ni IP. No se distingue un ataque de alguien que se equivocó de contraseña, ni se sabe si después hubo un acceso exitoso.
2. **Un `cambio_config_no_autorizado` no dice qué cambió.** Sin el parámetro y el valor, no se sabe si podía tener efecto físico ni cuándo.
3. **El cambio del kit ocurre al final de los datos.** Va de las 04:00 a las 06:00 del 18 de octubre, y los datos terminan a medianoche: de las 24 h que siguen al evento solo se observan 18. «Sin efecto físico» vale solo para esas 18 h.
4. **Los sitios son ficticios y no tienen ubicación.** Las horas del kit están en UTC y el día simulado sigue ese reloj: la temperatura exterior es mínima hacia las 02:00 y máxima hacia las 14:00, y la carga es mínima hacia la 01:00. Por eso el evento de SIM-C (de la 01:00 a las 06:00) es **de madrugada en el día simulado**. No se debe pasar a la hora de Mérida: el kit no dice dónde están los sitios.
5. **Un exceso no distingue falla de ataque.** Por eso no existe una clase «ataque»: el escalón sin registro manda a revisar la configuración antes que a mantenimiento.
6. **El resultado base es optimista.** La línea base tiene la misma forma que el generador del kit (propuesta §3.1). La cifra honesta es la del doble de ruido.
7. **El agua del kit no trae ruido**, así que detectar sus excesos es fácil. Con ±4 % de ruido se siguen viendo todos, pero en una planta real hay que comprobarlo.
8. **Un evento sintético es solo el rastro final.** No reproduce el reconocimiento, el acceso ni el movimiento lateral de un ataque real.
9. **Nada se probó contra equipos ni redes reales** (regla 18): los ataques solo existen como cambios en copias de un CSV.

**Revisión de la narrativa (U3), 21 oct:**
- Ningún texto del repositorio, del dashboard o del pitch afirma que un exceso pruebe un ataque.
- Corregí los IDs revocados en `app/textos.py`, `docs/08`, `docs/00-propuesta.md`, `docs/notebooklm-contexto.md` y `src/ataques/escenarios.py`.
- El dashboard solo lee el kit, `alertas.csv` y el JSON oficial. No manda nada a ningún equipo ni a internet: hasta las fuentes tipográficas vienen dentro del repositorio.

## 8. Cómo se instala DripSafe sin abrir una puerta nueva

Un detector conectado a la planta también puede ser atacado. Por eso:
- **Solo lee.** Recibe una copia de los datos por un diodo de datos (información en un solo sentido) o un puerto espejo, y **nunca manda órdenes** a controladores ni bombas.
- **Alerta a una persona; no actúa solo.** Si DripSafe pudiera cambiar el enfriamiento, quien lo engañe controlaría la planta. Esto aplica también al bono: la IA **recomienda** cuándo activar el respaldo y el operador confirma (D4).
- **Vive en su propia zona** de la red (IEC 62443), sin salida a internet.
- **Se entrena solo con periodos verificados como limpios** y cada versión queda registrada. Así nadie le «enseña» a ver un ataque como normal (envenenamiento del modelo).
- **Si el atacante conoce el modelo:** tendría que falsificar a la vez el registro del BMS y los medidores de energía, que suelen ser otro sistema (EPMS), de forma coherente con la carga y el clima. Con el kit no se puede probar; es una pregunta para el mentor.

## 9. Recomendaciones de defensa

Basadas en ISA/IEC 62443 (zonas y conductos) y en las mitigaciones de MITRE para cada técnica.

| Recomendación | Contra qué | Mitigación MITRE |
|---|---|---|
| Separar la red del enfriamiento de la de oficina y sin acceso directo a internet | T0883, T0886 | M0930 Network Segmentation, M0937 Filter Network Traffic |
| Acceso remoto del proveedor solo por un equipo de salto, con MFA y en horario acordado | T0822, T0886 | M0932 Multi-factor Authentication, M0801 Access Management |
| Bloqueo tras varios intentos fallidos; cambiar todas las contraseñas de fábrica | T0859, T1694.001 | M0936 Account Use Policies, M0927 Password Policies |
| Solo ciertos usuarios cambian setpoints, y el controlador valida rangos | T0836 | M0800 Authorization Enforcement, M0818 Validate Program Inputs |
| Configuración aprobada con huella y comparación periódica. Es lo que pide la acción de DripSafe «comparar contra la configuración aprobada» | T0836, T0838 | M0947 Audit |
| Lista blanca de comandos y mensajes autenticados | T1692.001, T1692.002 | M0807 Network Allowlists, M0802 Communication Authenticity |
| Una medición independiente para validar la principal. DripSafe usa los medidores de energía como testigo | T1692.002, T0832 | M0810 Out-of-Band Communications Channel |
| Modo seguro manual y respaldo de la configuración | T0831, T0826 | M0953 Data Backup |

## 10. Para el pitch

**Diapositiva 1 · Del evento al efecto.** El diagrama de §2 y tres frases:
1. Un atacante entra por el BMS o por el acceso del proveedor y cambia un setpoint con comandos válidos, como en FrostyGoop.
2. DripSafe no mira la red: mira si la energía y el agua cuadran con la carga y el clima.
3. Cruza ese exceso con el registro OT y dice qué revisar primero. Nunca actúa solo.

**Diapositiva 2 · Lo que las reglas fijas no ven.** La tabla de §6 reducida a cuatro filas (energía +20 %, agua +25 %, cambio sin registro, cambio con efecto), con las columnas «DripSafe» y «reglas del kit», y abajo: *«Datos simulados. Con el doble de ruido, DripSafe ve el 80 % de los excesos de +20 %. Con la ventana de 24 h, 1 de cada 5 atribuciones podría ser casualidad: por eso un incidente se confirma en sitio.»*

**Frase de 20 segundos:**
> *«En el kit, un exceso de 20 % en la energía no TI no mueve ninguna regla fija: el sitio líquido parte de un PUE de 1.2. DripSafe lo ve en la primera hora. Y cuando hay un cambio de configuración no autorizado, no nos quedamos en "hubo un evento": medimos si tuvo efecto, cuánta energía y agua costó, y qué tan probable es que sea casualidad.»*

**Preguntas probables:**

| Pregunta | Respuesta corta |
|---|---|
| ¿Detectan ciberataques? | Detectamos efectos físicos y los cruzamos con el registro OT. No afirmamos que un exceso pruebe un ataque; por eso son cuatro clases y no «ataque sí o no». |
| ¿Y si el atacante también falsifica los medidores? | Tendría que falsificar a la vez el registro del BMS y los medidores de energía, que suelen ser otro sistema, de forma coherente con la carga y el clima. Con el kit no lo podemos probar y lo decimos. |
| ¿Por qué 24 h de ventana? | Un setpoint cambiado de noche puede notarse hasta el siguiente pico de calor. El costo lo medimos: 20 % de coincidencias al azar con 24 h y 7 % con 8 h. |
| ¿DripSafe no es otra puerta de entrada? | Solo lee, por diodo de datos o puerto espejo, en su propia zona y sin internet. No puede mandar órdenes. |
| ¿Qué técnicas de ATT&CK cubren? | Con el kit: T0859 y T0836 observables, T0831 inyectada. Con sensores de agua helada: T1692.002 y T0832. Usamos la versión 20 de la matriz. |
| ¿Qué tan pequeño puede ser el cambio para que no lo vean? | Depende del ruido de cada sitio: sostenido, de 4 % en el de aire a 7.5 % en el líquido. Por debajo de eso no lo vemos y lo decimos (§6b). |
| ¿Y si el atacante sube la energía poco a poco? | La línea base no se reentrena sola, así que la subida no se vuelve «normal». En el kit vimos todas las rampas lentas antes de que pasaran de 11 % (§6b; prueba exploratoria). |
| ¿Y si ataca en una ola de calor? | Es nuestro punto débil: fuera del clima aprendido el umbral se duplica y un +10 % pasó sin verse en 8 de 11 tardes. Se cierra con líneas base por época, entrenadas con periodos verificados (§6b). |

## 11. Para revisar con el mentor (22 oct)

1. ¿Una ventana de 24 h entre el evento y el efecto es razonable, o en la práctica se usan ventanas distintas según el tipo de cambio?
2. ¿Tratar un login fallido seguido de un exceso como «incidente OT con efecto» es demasiado agresivo?
3. En centros de datos reales, ¿qué tan común es que los medidores de energía (EPMS) estén separados del BMS? Nuestro argumento del testigo independiente depende de eso.
4. ¿Los BMS suelen registrar los cambios de setpoint con usuario y hora? Sin ese registro, todo cae en «escalón sin registro».
5. Para un sitio mediano, ¿diodo de datos o puerto espejo? ¿Qué cuesta cada uno?
6. ¿Cómo se lleva la «configuración aprobada» (gestión de cambios) en IEC 62443 para que la acción «comparar contra la configuración aprobada» tome minutos y no días?
7. Fuera del clima aprendido, el detector duplica el umbral para no llenar de falsas alarmas un clima que no conoce, pero eso le da margen a un atacante que espere una ola de calor (§6b). ¿Es mejor duplicar, mantener el umbral y aceptar más falsas alarmas, o pedir confirmación humana en esas horas?

## Apéndice A. Escenarios con sensores por equipo (datos sintéticos)

`src/ataques/escenarios.py` simula ataques y fallas sobre un centro de datos sintético de un solo sitio que **sí** trae chiller, bombas, caudal y temperaturas del agua (`src/sinteticos.py`). **No corren sobre el kit**, porque el kit no trae esas columnas. Sirven para mostrar qué vería DripSafe con la instrumentación que recomendamos medir (propuesta §9).

| Escenario | Técnica (v20) | Huella física que lo delata |
|---|---|---|
| `setpoint_alterado` | T0836 | El chiller gasta ~9 % más con la misma carga de TI |
| `sensor_falsificado` | T1692.002 (antes T0856) | Caudal × ΔT ya no alcanza para el calor de los servidores |
| `vista_repetida` | T0832 + T0831 | La bomba gasta ~70 % menos, pero el caudal «es normal»: rompe la ley de afinidad |
| `comandos_no_autorizados` | T1692.001 (antes T0855) | Arranques y paros de la bomba sin relación con la carga ni el horario |
| `denegacion_de_vista` | T0815 | Sensores vacíos mientras la energía sigue llegando |
| `ensuciamiento` · `sensor_atorado` · `fuga_reposicion` | Fallas | Subida gradual · varianza cero · más agua sin más calor |

```bash
python -m src.sinteticos --dias 14 --salida data/sinteticos/telemetria.csv
python -m src.ataques.inyectar --entrada data/sinteticos/telemetria.csv
```

## Regla del hackatón

**Prohibido hacer pruebas o ataques sobre sistemas reales.** Todo se hace sobre el kit o en simulaciones: los «ataques» son cambios en copias de un CSV, nunca contra equipos reales.

## Para leer más

- MITRE ATT&CK for ICS (v20): <https://attack.mitre.org/matrices/ics/>. Técnicas citadas: T0836, T0831, T0859, T1694.001, T1692, T0883, T0822, T0886, T0838, T0815, T0832, T0828, T0879, T0826.
- FrostyGoop: campaña C0041 y software S1165 en MITRE; informe de Dragos (julio de 2024).
- Ver también la sección «Ciberseguridad OT» en [09-recursos.md](09-recursos.md).

---

# 07 · Agua, acuífero y bono de cero agua dulce

> **Reparto vigente:** Nico lleva el acuífero y la gobernanza (#13), Misa la comparación de refrigeración y el bono (#15), y Misa + Nico el balance neto. Este documento cubre el análisis hídrico obligatorio y la propuesta del bono de +5 % a +15 %.
>
> **Del kit:** `water_l` es **captación in situ** simulada. No es consumo neto, ni agua de la generación eléctrica, ni potabilidad. Las diferencias entre los sitios del kit no son un experimento controlado: toda recomendación del bono va **condicionada a sus supuestos**.

## 1. Por qué la IA consume agua

Un centro de datos usa agua de dos formas:
- **En sitio:** las **torres de enfriamiento** evaporan agua para disipar el calor de los servidores. Además, parte del agua se **purga** (*blowdown*) para que no se acumulen sales y minerales.
- **Fuera de sitio:** las plantas que generan la electricidad que consume el centro de datos también usan agua.

El artículo *Making AI Less "Thirsty"* (ver [09-recursos.md](09-recursos.md)) es la referencia para entender esta división.

## 2. El acuífero de Yucatán: fuente y escala del riesgo

La [actualización de CONAGUA para el acuífero Península de Yucatán (3105), publicada en 2024](https://sigagis.conagua.gob.mx/gas1/Edos_Acuiferos_18/yucatan/DR_3105.pdf), describe calizas, drenaje principalmente subterráneo, cavernas y cenotes (§3.1, p. 8 impresa; §3.3, pp. 10–11). La infiltración y las conexiones del terreno hacen necesario controlar los vertidos: un excedente de agua captada no dice por sí solo dónde termina una descarga.

CONAGUA reporta **2 059.634923 hm³/año de disponibilidad media anual** para todo el acuífero 3105 (§8.4, p. 36 impresa). Es una cifra regional calculada con extracción registrada al **30 de diciembre de 2022**; no mide la disponibilidad en un predio ni demuestra que su agua sea potable o que una nueva extracción esté autorizada. El mismo estudio muestra profundidades al nivel estático de **2–5 m en la costa**, pero también valores mucho mayores en otras zonas (§5.4.1, p. 22). Evitamos describir toda Mérida como si tuviera un freático uniforme de pocos metros.

El estudio incluye al **Anillo de Cenotes** entre las zonas protegidas (§1.1, p. 6) y registra variación en salinidad y calidad de agua de los puntos monitoreados (§5.5, pp. 25–26). La disponibilidad volumétrica positiva no elimina riesgos de calidad, presión local ni permisos. La evaluación de un sitio concreto requiere ubicación, captación autorizada, calidad del agua y ruta de las descargas.

## 3. Análisis de impacto (obligatorio)

Efectos que DripSafe puede analizar y límites de atribución:

| Aspecto | Pregunta a responder | Cómo ayuda DripSafe |
|---|---|---|
| **Extracción** | ¿Qué fuente usa el sitio? | Detecta captación in situ por encima de la línea base; solo se atribuye al acuífero si se conoce el origen del suministro. |
| **Descargas** | ¿Cuánta purga y a dónde va? | El kit no mide purga. Se requiere caudal o balance de torre y registro del destino. |
| **Contaminación** | ¿Puede llegar al subsuelo? | El diseño debe contener y conducir la descarga por una ruta autorizada; el detector no sustituye esa infraestructura. |
| **Gobernanza** | ¿Qué autorizaciones aplican? | Revisar concesión o asignación, uso, ubicación y condiciones de descarga para el predio. CONAGUA describe zonas de veda y restricciones en §1.1, pp. 5–6. |
| **Justicia ambiental** | ¿Quién comparte la fuente? | Comparar la extracción real con otros usos locales antes de afirmar un beneficio para comunidades. |

### Conclusión del impacto de DripSafe

**DATOS SIMULADOS.** DripSafe detecta captación in situ por encima de la línea base para que un operador investigue y corrija el exceso. En la evaluación del kit, el [JSON oficial](../resultados/numeros_oficiales.json) estima **1 310.6203 L** de exceso en horas con alerta física; es un residuo calculado, no agua ahorrada. En un escenario anual editable para el sitio evaporativo ficticio SIM-B, el mismo JSON proyecta **11 461.2884 L/año de captación in situ evitada** si las fallas supuestas ocurren y se atienden a tiempo. Esa proyección no mide una reducción real de extracción ni de presión sobre el acuífero.

El beneficio para el acuífero 3105 solo podría atribuirse después de confirmar que el suministro del sitio procede de él y de medir la captación antes y después de la corrección. El kit tampoco registra purga, calidad del agua ni ruta de descarga: no permite cuantificar contaminación evitada. Por la infiltración del terreno kárstico, el operador debe verificar el destino y las condiciones autorizadas de cualquier descarga, además de comparar su captación con la autorización y con otros usos locales. La disponibilidad regional positiva de CONAGUA no resuelve por sí sola esa presión local. Los **22 216.3796 L/año** de agua de generación eléctrica evitada que proyecta el JSON son una estimación indirecta para la red eléctrica; se reportan aparte y no se atribuyen al acuífero de Yucatán.

**Purga, solo como escenario físico simplificado.** En una torre estable, sin arrastre, fugas ni rebose, reposición = evaporación + purga y ciclos = reposición / purga. Por tanto, `purga = evaporación / (ciclos − 1)`. Con **4 ciclos supuestos**, 3 L evaporados requieren 1 L de purga y 4 L de reposición. Si se evita 1 L de *reposición causada por evaporación* y los ciclos no cambian, se evita 0.25 L de purga. **Una fuga evitada no implica esa reducción.** La relación procede del [balance del Departamento de Energía de EE. UU., ecuaciones 1–7](https://www.energy.gov/sites/default/files/2013/10/f3/waterfs_coolingtowers.pdf) y se reproduce con `src.metricas.purga.balance_torre`; no se calcula a partir de `water_l` del kit.

## 4. Balance neto (obligatorio, cálculo conjunto de Misa + Nico)

**El consumo del modelo de IA debe ser menor que el ahorro que genera.** Las fórmulas están en [05-solucion-tecnica.md](05-solucion-tecnica.md#balance-neto-obligatorio).

**Misa entrega:** PUE inicial, datos limpios y energías total y de TI, con unidades, intervalo y periodo.

**Nico calcula:** ahorro energético y PUE final proyectado; estima agua y emisiones cuando haya datos suficientes. Identifica proyecciones, fuentes y supuestos, y consolida los resultados para Leo.

**Misa + Nico calculan y validan juntos:** el balance neto final, descontando el consumo del modelo del ahorro estimado con unidades y periodos compatibles. La firma y las cifras vigentes están en `resultados/numeros_oficiales.json`; este análisis hídrico no modifica ese archivo.

**A Nico le toca conseguir y citar:**
- [x] Factor de emisión del Sistema Eléctrico Nacional de México: **0.444 kgCO₂e/kWh**. Es el FESEN 2024 que el [aviso de SEMARNAT del 29 de mayo de 2026](https://www.gob.mx/cms/uploads/attachment/file/1081506/aviso_factor_de_emision_electrico_coa_2026.pdf) indica usar en la COA 2026 mientras se publica el factor 2025. El valor aparece en el [aviso FESEN 2024](https://www.gob.mx/cms/uploads/attachment/file/981194/aviso_fesen_2024.pdf).
- [x] Intensidad hídrica de la generación eléctrica: **2.0632 L/kWh**, estimada con la mezcla de generación neta del SEN 2024 del [Reporte de Confiabilidad 2024 de la CNE](https://www.cne.gob.mx/Electricidad%20CNE/Codigo%20de%20red/Anexo%20Acuerdo%20RCSEN2024%20R00.pdf) y los factores medianos de consumo de [Macknick et al. (NREL, 2012)](https://openei.org/datasets/files/969/pub/1748-9326_7_4_045802.pdf). **No es un factor oficial mexicano**: es una estimación trazable. La hidroeléctrica aporta 1.1492 L/kWh y domina el resultado; incluye evaporación de embalses, no solo agua potable.
- [x] Consumo de agua del caso: el kit entrega `water_l` como **captación in situ simulada**. El WUE in situ se calcula como `suma(water_l) / suma(energía IT)` y se publica por separado del agua indirecta. No es consumo neto, no descuenta purga y no dice si el agua es potable.

La cuenta publicada en `resultados/numeros_oficiales.json` usa el ahorro **proyectado** de 10 767.9234 kWh/año: 4 780.9580 kgCO₂e/año evitados y 22 216.3796 L/año de agua de generación evitada. Son proyecciones con factores externos, no ahorros observados. El agua in situ proyectada (11 461.2884 L/año) se mantiene separada para no sumar captaciones de distinta naturaleza.

**Gadiel aporta:** alertas, consumo esperado del enfriamiento y mediciones de energía y emisiones del modelo con CodeCarbon.

Si faltan datos suficientes, el resultado correspondiente queda pendiente. El análisis del acuífero contextualiza el impacto local; los litros de agua ahorrada requieren un cálculo sustentado.

## 5. Bono Zero Freshwater Footprint (+5% a +15%)

> **Responsable:** Misa (#15, D13). **DATOS SIMULADOS.** Las cifras del kit vienen de 3 sitios ficticios. **No son** un experimento controlado ni una clasificación de tecnologías reales: solo ilustran el intercambio entre agua y energía. Todo lo que dice **SUPUESTO** es editable y no está medido. Lo que dice **PENDIENTE** todavía no tiene sustento.

**Para que el bono cuente** hay que mostrar tres cosas:
1. Que la alternativa es **técnicamente viable**: casos reales y referencias (§5.5).
2. **Cuánto baja el consumo de agua potable**, idealmente a cero, con una estimación de WUE (§5.4).
3. Que **no dispara el PUE**. Si lo sube un poco, hay que explicar el balance (§5.4).

### 5.1 Los tres sitios del kit (agregados)

Cada cifra es un **cociente de sumas** del periodo: suma(energía total) / suma(energía de TI), y suma(agua) / suma(energía de TI). Nunca es un promedio de cocientes por hora.

| Sitio | Enfriamiento (según el kit) | PUE · referencia | L/kWh TI · referencia | PUE · evaluación | L/kWh TI · evaluación |
|---|---|---|---|---|---|
| SIM-A | aire | 1.368 | 0.032 | 1.398 | 0.032 |
| SIM-B | evaporativa | 1.237 | 0.854 | 1.237 | 0.937 |
| SIM-C | líquida | 1.198 | 0.213 | 1.198 | 0.213 |

- **Referencia:** 72 h por sitio. Es la operación normal y la que se usa para comparar diseños.
- **Evaluación:** 96 h por sitio, tal como viene, con las anomalías simuladas del kit. Por eso el PUE de SIM-A sube (escenario de ineficiencia) y el L/kWh de SIM-B sube (escenario de fuga de agua). Esas subidas son anomalías, no rasgos de la tecnología.
- **Reproducir la tabla** (el kit se queda en `data/`, fuera de Git):

  ```bash
  python -m src.metricas.refrigeracion --kit data/kit/operaciones_simuladas.csv
  python -m src.metricas.refrigeracion --ejemplo     # sin el kit, datos INVENTADOS
  ```

  El código está en `src/metricas/refrigeracion.py` (`comparar_por_enfriamiento`) y sus pruebas en `tests/test_refrigeracion.py`.

### 5.2 El intercambio agua ↔ energía

En el kit se ve el mismo patrón que describe la literatura:

- **Aire (SIM-A):** casi no usa agua en el sitio (0.032 L/kWh TI), pero tiene el **PUE más alto** (1.368). Gasta más electricidad en enfriar.
- **Evaporativa (SIM-B):** PUE intermedio (1.237), pero **la que más agua capta**: 0.854 L/kWh TI, unas 27 veces más que el aire.
- **Líquida (SIM-C):** **el PUE más bajo** (1.198) con un consumo de agua intermedio (0.213 L/kWh TI). Equilibra las dos cosas.

**Por qué importa:** bajar el agua en el sitio no siempre baja el agua total. Alston, Love y Haider (2026) modelaron un centro de 200 MW de TI. Cambiar de *chiller* enfriado por agua a *chiller* enfriado por aire redujo el agua directa un 97 %. A cambio, subió la electricidad un 32 %, y con ella un 32 % el agua que gastan las plantas que la generan (p. 6, §4.1; tabla 2, p. 7). Es decir, la huella hídrica se **mueve** del centro de datos a la red eléctrica. Su configuración híbrida tuvo la **menor demanda eléctrica** de las tres y un agua total 34 % menor que la de enfriamiento por agua (p. 6, §4.1).

**Por qué importa en Yucatán:** la elección entre enfriamiento seco y evaporativo desplaza parte del impacto del agua en sitio hacia la electricidad. El estudio de Alston et al. usa un criterio de temperatura **y humedad** para otro sistema (§3.2); no se puede trasladar su porcentaje anual a Mérida ni usarlo como umbral de una clase W40. Para nuestra propuesta seca, la serie local de temperatura de §5.4 sirve como sensibilidad; el despacho del respaldo requiere además curvas de equipo y carga.

### 5.3 Arquitectura elegida para el bono

**Propuesta para obra nueva o renovación:** servidores compatibles con clase de agua W40, circuito líquido cerrado, enfriador seco para expulsar el calor al aire y **chiller mecánico condensado por aire** como respaldo en horas cálidas. El líquido de los servidores circula dentro del circuito; «líquido» no implica una torre evaporativa. La [guía técnica de ASHRAE sobre enfriamiento líquido](https://www.ashrae.org/file%20library/technical%20resources/bookstore/emergence-and-expansion-of-liquid-cooling-in-mainstream-data-centers_wp.pdf) identifica W40 entre las clases de temperatura de suministro.

| Pieza | Función | Agua potable durante operación normal |
|---|---|---|
| Circuito cerrado W40 | Transporta calor de los servidores; requiere llenado inicial y reposición por mantenimiento o fugas. | Meta 0: el llenado y toda reposición deben usar fuente no potable compatible con el equipo. |
| Enfriador seco | Rechaza calor al aire sin evaporación. | 0 por diseño. |
| Chiller condensado por aire | Cubre la carga que no puede disipar el enfriador seco. | 0 por diseño; consume electricidad adicional. |

La meta de **WUE potable de enfriamiento = 0** es condicional: se necesita verificar la fuente de llenado y reposición mediante medidor y registros de operación. No se afirma cero agua total del centro de datos ni cero agua indirecta de la electricidad. [Microsoft anunció en 2024](https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/) una arquitectura de refrigeración líquida cerrada sin evaporación durante la operación y advirtió que sustituir enfriamiento evaporativo por mecánico aumenta el PUE. Es evidencia de factibilidad del concepto, no prueba de desempeño de DripSafe en Mérida.

**Alternativa futura:** respaldo adiabático con agua residual tratada, sujeto a disponibilidad, calidad, tratamiento y conducción autorizada de la purga. No se incluye en el diseño principal ni en su PUE. El [DOE explica](https://www.energy.gov/cmei/femp/best-management-practice-10-cooling-tower-management) que una torre pierde agua por evaporación, purga y arrastre. No suponemos que una planta de tratamiento local suministre efluente o reciba purga sin comprobar convenio e infraestructura.

DripSafe **detecta y presenta** anomalías de energía y agua con los sensores disponibles. La recomendación de modo de enfriamiento y la verificación de un medidor separado de agua potable son capacidades propuestas, no implementadas en el kit. La orden al chiller queda a cargo del operador.

### 5.4 Cuantificación pendiente del equipo real

En 2025, la serie horaria de temperatura a 2 m para Mérida, [ERA5 vía Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api), tiene 8 760 horas completas en zona `America/Mexico_City`. Conteo estricto de `temperatura > umbral`:

| Umbral ilustrativo | Horas de 2025 por encima |
|---|---:|
| 27 °C | 3 955 |
| 30 °C | 2 235 |
| 33 °C | 981 |
| 35 °C | 390 |

La consulta reproducible está en `src/metricas/generar_numeros.py` (`URL_CLIMA`); el archivo horario queda en `data/clima/`, fuera de Git. Estos conteos son **temperatura exterior estimada**, no horas medidas de chiller. El umbral efectivo depende de temperatura de suministro admitida, aproximaciones térmicas del enfriador y del intercambiador, carga, control y rendimiento del equipo. El reparto horario tampoco equivale automáticamente a la fracción de **energía de TI** servida durante el respaldo.

**Escenario proyectado de Misa:** el PUE base es **1.198**, del sitio líquido simulado SIM-C en referencia (§5.1). El respaldo usa un chiller por aire con **EER de plena carga 10.100 Btu/Wh**, valor mínimo Path A de [ASHRAE 90.1, tabla 6.8.1-3](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20errata/standards/90.1-2013-ip-erratasheet-6-15-2023-.pdf#page=7), reproducido en la [tabla oficial WAC C403.3.2(3)](https://app.leg.wa.gov/WAC/default.aspx?cite=51-11C-403323&pdf=true). `COP = EER / 3.412 ≈ 2.96`. De ERA5 se toman **2 235 / 8 760 = 0.25514** horas con temperatura `>30 °C`. Con carga de TI **constante** (para usar horas como fracción de energía) y una carga térmica igual al **100 % de la energía de TI** en esas horas, la fórmula es `PUE escenario = 1.198 + (2235 / 8760) / 2.96 = 1.2842`, aproximadamente **1.284**.

El chiller se suma a un PUE observado de otro sitio simulado; no se modela la sustitución del enfriamiento existente, bombas adicionales ni rendimiento en el calor real de Mérida. El EER tabulado corresponde a **condiciones estándar**, no a una ficha de equipo instalado. Por eso **1.2842 es un escenario, no un PUE físico verificado**. Como sensibilidad, [FEMP](https://www.energy.gov/cmei/femp/purchasing-energy-efficient-electric-chillers) recomienda EER **10.89** para un chiller por aire de menos de 150 t: COP ≈ **3.19** y el mismo cálculo daría PUE ≈ **1.278**. El JSON oficial publica solo el escenario base de Misa y conserva los supuestos y fuentes.

### 5.5 Evidencia técnica y alcance

- [ASHRAE](https://www.ashrae.org/file%20library/technical%20resources/bookstore/emergence-and-expansion-of-liquid-cooling-in-mainstream-data-centers_wp.pdf) documenta la clase W40. La clase se aplica al suministro líquido de equipos compatibles; no fija por sí sola las horas de respaldo en Mérida.
- [Microsoft (2024)](https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/) describe circuito cerrado sin evaporación para enfriamiento y reconoce el aumento energético del enfriamiento mecánico. Sus cifras corporativas no se usan como medición del proyecto.
- La serie [ERA5 de Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) permite explorar umbrales climáticos. No sustituye un diseño térmico ni datos del sitio.

### 5.6 Validaciones necesarias antes de afirmar viabilidad local

1. Confirmar compatibilidad W40 de los servidores, carga térmica, curvas de enfriador/chiller a temperaturas locales, energía de bombas y PUE anual real; comparar energía directa e impacto indirecto del SEN si existe un factor verificable.
2. Confirmar origen, calidad y volumen de agua no potable para llenado y reposición, con contingencia que no recurra inadvertidamente a agua potable. Sin esto, `WUE potable = 0` es **meta de diseño**.
3. Si se evalúa la alternativa adiabática, identificar planta, disponibilidad, tratamiento, costo y ruta autorizada de la purga; no asumir que existe conexión con JAPAY.
4. Validar con datos físicos del sitio; el kit contiene tres escenarios ficticios y solo mide captación in situ, no potabilidad, purga ni agua de generación eléctrica.

### 5.7 Qué significa el agua del kit

`water_l` es **captación in situ simulada**:
- **No** es consumo neto: no descuenta lo que se devuelve o se purga.
- **No** incluye el agua de la generación eléctrica (alcance 2 en Alston et al., 2026, §1).
- **No** dice si el agua es potable o no. El kit no separa fuentes; la meta de WUE potable del bono exige medidores y registros externos.

**Referencias de esta sección**
- Alston, G., Love, N. y Haider, R. (2026). *Data Center Cooling Choices Shift Water Impacts Across the Grid: An Integrated Water–Energy Model for Sustainable Data Center Development*. arXiv:2609.25437v1.

## 6. Entregable de Nico

**Estado de las piezas de Nico:**

- **Programa en Python** dentro de `src/metricas/`, usando el PUE inicial que entrega Misa desde `src/metricas/pue.py`. Nico calcula ahorro, PUE final proyectado y, cuando es posible, impacto en agua y emisiones; el balance neto está en `src/metricas/balance_neto.py`.
- **Ejemplo reproducible con datos sintéticos**, con instrucciones y escenarios sin ahorro, con balance positivo y con ahorro menor que el costo del modelo.
- **Resultados consolidados** en `resultados/numeros_oficiales.json`, con origen y responsable de cada cifra; documentación del periodo, unidades, fuentes y supuestos, distinguiendo mediciones de proyecciones.
- **Análisis del acuífero y propuesta del bono**, con fuentes y condiciones de viabilidad, en las secciones 2, 3 y 5. Las validaciones locales de §5.6 siguen pendientes.
- **Contenido y guion del pitch**, incluyendo el impacto local, las cifras del balance y la propuesta del bono. Leo diseña las diapositivas con esos resultados.

## Para leer más
Ver las secciones "Agua y centros de datos" y "Acuífero de Yucatán" en [09-recursos.md](09-recursos.md).

---

# 13 · Yucatán: a quién le vendemos, los cenotes y cómo crecemos

> Revisión del 22 de octubre de 2026 (Guille), hecha durante la jornada presencial. Contrasta lo que ya dicen la propuesta y el guion con fuentes públicas sobre Yucatán. **No cambia código ni cifras oficiales.** Las frases propuestas para el guion (§5) las decide Leo. Las cifras de aquí son **externas y citadas** (§7); ninguna sale del kit ni de `numeros_oficiales.json`.

## 1. El problema que resolvemos, en corto

El enfriamiento de un centro de datos lo controlan PLCs y un BMS. Cuando algo se descompone o alguien cambia un setpoint, el sitio desperdicia energía y agua **sin que nadie lo note**, por dos razones:

1. **Se vigila con umbrales iguales para todos** (PUE > 1.6). Un sitio eficiente puede subir 158 % su energía no TI sin cruzar esa línea.
2. **Las alarmas no separan** un intento de acceso de un incidente con efecto físico.

En Yucatán, además, toda el agua sale de un solo acuífero kárstico. Detalle en `docs/00-propuesta.md` §1.

## 2. Lo que ya está cubierto

| Ángulo | Dónde | Qué dice |
|---|---|---|
| Cliente y precio | `docs/00` §9 | Centros de datos y colocation de 0.5 MW o más en la Península; salas universitarias como piloto gratuito; $40 MXN por kW de TI al año |
| Competencia | `docs/00` §9 | FDD (Schneider, Siemens, SkySpark) y monitoreo OT (Nozomi, Claroty, Dragos); DripSafe los complementa |
| Expansión | `docs/00` §9 | Querétaro y otros acuíferos sobreexplotados |
| Acuífero | `docs/07` §2–3 | Acuífero 3105, cenotes, calidad como riesgo principal, purga y gobernanza |
| Balance y bono | `docs/07` §4–5 | 4.8 t de CO₂ evitadas (proyectado) y cero agua potable con PUE 1.284 (escenario) |

**Lo que falta:**
- El guion hablado dice muy poco de **quién compra**.
- No conecta a DripSafe con lo que hoy le pasa a los cenotes.
- Al revisar las fuentes salió un hueco en el primer segmento de clientes (§3).

## 3. Hallazgo: casi no hay centros de datos grandes en Yucatán

- **Los que existen son chicos y se enfrían con aire.** KIO opera dos centros de datos en Mérida, MER1 y MER2. La ficha técnica de MER1 dice:
  - inicio de operaciones en 2017;
  - características Tier I;
  - piso técnico de 21 m² en contenedor;
  - UPS modular de 60 kW y acometida de 150 kVA;
  - 3 CRAC en N+1, es decir, aire acondicionado de precisión, sin torres de agua;
  - BMS y **PUE promedio de 2**.

  No encontramos una fuente confiable de la capacidad de MER2. El Ayuntamiento de Mérida también licitó en 2025 equipo para un centro de datos municipal.
- **Los grandes esperan energía.** Según una columna de *El Economista* (17 sep 2026), a Yucatán le faltan gas y centrales de ciclo combinado. Las nuevas centrales de CFE, Mérida IV y Valladolid, suman 1 519 MW. Todavía no operan a plena capacidad y se espera que todo funcione a finales de 2027.
- **Consecuencia para el pitch.** El primer segmento de pago de `docs/00` §9 («0.5 MW o más en la Península») casi no existe hoy en Yucatán. Un jurado local puede saberlo. Con sitios de decenas de kW, la propia propuesta dice que DripSafe es **piloto, no cliente de pago**.

**Encuadre propuesto: en Yucatán, pilotos hoy; el cliente de pago, en Querétaro; y los centros de datos que lleguen a Yucatán, medidos desde el primer día.**

1. **Pilotos en Yucatán (hoy).**
   - Salas de cómputo universitarias, como la de la UPY.
   - Centros de datos chicos en Mérida, enfriados por aire.

   Con un PUE de 2, un sitio así es justo el caso de **ineficiencia crónica**: la auditoría de línea base al instalar (`docs/00` §9) la saca a la luz el primer día. El ahorro es de energía, y con él de CO₂ y del agua que gastan las centrales eléctricas. Con enfriamiento por aire casi no hay agua en el sitio.
2. **Primer cliente de pago: Querétaro.**
   - Es el estado con más centros de datos del país: 12 en operación y 18 en construcción, unos 250 MW, según la Sedesu citada por DCD.
   - Siete de sus 11 acuíferos están sobreexplotados.
   - Su gobierno anunció que **publicará el consumo de agua de los centros de datos desde 2027**, con un piloto en 2026, porque hoy no tienen las mismas obligaciones de reporte que la manufactura (DCD; una sola fuente).

   Un operador que pronto tendrá que reportar su agua necesita medirla y explicarla.
3. **Yucatán, cuando llegue la energía (2027 en adelante).** Los centros de datos nuevos llegarían a un acuífero que ya está bajo presión (§4). DripSafe propone que lleguen **medidos desde el primer día**: línea base, excesos y un reporte de captación para comparar con la concesión.

**Mercado vecino (hipótesis, no construido ni probado).** Cualquier edificio con chillers o torres de enfriamiento sigue la misma física: el enfriamiento gasta según la carga y el clima. Ejemplos: hoteles, hospitales, plazas comerciales e industria. Habría que cambiar «energía de TI» por la carga térmica del edificio. Se presenta como ruta futura, nunca como producto actual.

## 4. Hallazgo: los cenotes ya están contaminados, y no por centros de datos

- **Greenpeace México** publicó el 20 de octubre de 2026 un muestreo hecho en agosto, en 17 pozos y cenotes de siete localidades de Yucatán (Sitilpech, Kinchil, Motul, Chocholá, Molas, Celestún y San Antonio Tedzidz):
  - 16 muestras llegaron al límite superior de medición de coliformes totales;
  - 13 superaron 1 800 NMP/100 ml de coliformes fecales;
  - 2 superaron 50 mg/L de nitratos, el valor guía de la OMS.

  El propio estudio dice que **no identifica la fuente** de cada contaminante; Greenpeace lo vincula con las granjas porcícolas.
- **Mérida no tiene un drenaje sanitario para toda la ciudad** (Diario de Yucatán, 2024). Eduardo Batllori, del Cinvestav-Mérida, señala como fuentes de contaminación las aguas residuales domésticas que van a fosas sépticas, sumideros y biodigestores, además de la escorrentía urbana (Por Esto, 30 mar 2026).
- Se cita que el **83 %** de 60 cenotes monitoreados, de unos 3 100 registrados, está contaminado, sobre todo con coliformes fecales de origen animal y humano (Por Esto, 30 mar 2026; la nota no nombra el estudio original). Es una cifra de divulgación, no un estudio que cubra todo el acuífero. La misma nota dice que Profepa multó a 13 empresas porcícolas entre octubre de 2024 y junio de 2025.
- **Hay conflicto legal.** En julio de 2026, la SCJN atrajo dos casos de Homún contra la industria porcícola dentro del Anillo de Cenotes. En uno, las comunidades mayas piden que el sistema de cenotes y acuíferos tenga personalidad jurídica. Ninguno tiene todavía resolución de fondo.

**Cómo ayuda DripSafe, sin exagerar:**
- **No limpia cenotes ni ataca la causa principal.** Esa causa son las granjas y las fosas sépticas. Decir lo contrario ante un jurado de agua nos resta credibilidad.
- **Evita sumar carga.** En un sitio con enfriamiento evaporativo, detectar a tiempo una fuga o un exceso reduce la extracción del acuífero. Con los ciclos constantes, reducir la evaporación también reduce la purga, el agua con sales que se descarga (`docs/07` §3). Eso último requiere medir la purga, que el kit no trae.
- **Gobernanza:** deja un registro de cuánta agua se sacó de verdad y de cada exceso, para compararlo con la concesión de CONAGUA. Es justo lo que Querétaro empezará a pedir.
- **Lo indirecto:** cada kWh que no se desperdicia ahorra agua y CO₂ en las centrales. En el escenario proyectado son 22 216 L/año de agua de generación y 4.8 t de CO₂ (`numeros_oficiales.json`).

## 5. Frases propuestas para el guion (las decide Leo)

Las dos primeras **sustituyen** frases del guion actual, para no alargarlo. La tercera **recorta** tiempo para compensar.

**A · Parte 1, problema.** Sustituye las dos frases de CONAGUA, de «CONAGUA reporta…» a «…sus descargas»:
> "Ese acuífero ya está bajo presión: esta semana Greenpeace reportó contaminación fecal en pozos y cenotes de siete localidades de Yucatán. No la causan los centros de datos. Pero cuando lleguen, no pueden sumar otra carga sin medir."

Esta versión no trae cifras nuevas. Las cifras del estudio quedan para las preguntas (§6).

**B · Parte 5, escala.** Sustituye «DripSafe corre en local… sitio de 1 MW.»:
> "¿A quién se lo vendemos? En Yucatán empezamos con pilotos en salas de cómputo y centros de datos chicos. El primer cliente de pago está en Querétaro: es el estado con más centros de datos del país, tiene acuíferos sobreexplotados y va a publicar el consumo de agua de los centros de datos desde 2027. Y cuando la nueva energía traiga centros de datos a Yucatán, que lleguen medidos desde el primer día. Corre en local, sin nube, con seis medidores que ya existen, y se cobra por kW."

**C · Parte 4, números.** Para compensar, el párrafo del balance se reduce a:
> "¿Y lo que gasta DripSafe? 34 milisegundos por corrida, unos 0.000013 kWh al año, contra 4.8 toneladas de CO₂ evitadas en el escenario proyectado. El balance neto es positivo."

El umbral de menos de 1 ms y la explicación del TDP ya están en la tabla de preguntas de `docs/08`.

**D · Parte 4, precisión.** El guion dice que DripSafe detecta las fallas «desde +10 %, en la misma hora». A +10 %, 12 de 18 se ven en la misma hora, 4 tardan una hora y 2 tardan dos (promedio de 0.4 h, `docs/06` §6). Propuesta: «desde +10 %, casi siempre en la misma hora».

**Además (sin costo de tiempo):** decir «corre en local, solo lee, sin nube y sin GPU». Hoy el guion hablado no dice «solo lee», y es la primera duda de un jurado de ciberseguridad.

## 6. Preguntas nuevas del jurado y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Hay centros de datos en Yucatán? | Sí, chicos y enfriados por aire; uno de Mérida declara un PUE promedio de 2 en su ficha. Ahí hacemos pilotos. Los grandes esperan la energía nueva de CFE, prevista para fines de 2027. |
| ¿Cómo ayuda a los cenotes? | No los limpia: el problema principal son las granjas y las fosas sépticas. Lo que hace es evitar que los grandes usuarios de agua de enfriamiento sumen carga: detecta excesos de extracción y deja un registro para compararlo con la concesión. |
| ¿Quién paga, si el beneficio es para la comunidad? | El operador. Ahorra energía: en un sitio de 1 MW, la licencia se paga con menos del 0.5 % del overhead. Y llega preparado a los reportes de agua que vienen, como el de Querétaro en 2027. |
| ¿Sirve fuera de los centros de datos? | La física es la misma en cualquier edificio con chillers o torres, como hoteles, hospitales e industria. Es una hipótesis: no lo construimos ni lo probamos. |
| ¿Por qué ahora? | Hay tres señales: Querétaro va a publicar el agua de los centros de datos desde 2027, Yucatán espera su nueva energía para fines de 2027 y esta semana se publicó otro estudio sobre los cenotes. |
| ¿Qué dijo Greenpeace exactamente? | 17 pozos y cenotes en siete localidades: 13 con coliformes fecales por encima de 1 800 NMP/100 ml y 2 con nitratos por encima de 50 mg/L, el valor guía de la OMS. El estudio no identifica la fuente. |

## 7. Fuentes (consultadas el 22 de octubre de 2026)

- KIO, ficha técnica de MER1: https://static.datacentermap.com/company/castle-access/datacenter9833/KIO%20MER1%20Spec%20Sheet.pdf
- Ayuntamiento de Mérida, licitación de equipo para centro de datos municipal (2025): https://www.merida.gob.mx/municipio/sitiosphp/licitaciones/content/doc/proveeduria/2025/noviembre/LP-2025-ADQ-EQUIPAMIENTO-CENTRO-DATOS-01.pdf
- J. Ruiz Torre, «¿Puede llegar un centro de datos a Yucatán?», *El Economista* vía Yahoo Noticias (17 sep 2026): https://es-us.noticias.yahoo.com/llegar-centro-datos-yucat%C3%A1n-050111059.html
- DatacenterDynamics, «Querétaro publicará el consumo de agua de sus centros de datos»: https://www.datacenterdynamics.com/es/noticias/quer%C3%A9taro-publicar%C3%A1-el-consumo-de-agua-de-sus-centros-de-datos/
- Xataka México (1 sep 2025), acuíferos sobreexplotados de Querétaro: https://www.xataka.com.mx/robotica-e-ia/mexico-esta-recibiendo-centros-datos-que-nunca-hay-problema-paralelo-escasez-agua
- Expansión (27 may 2026), centros de datos en Querétaro y estrés hídrico: https://expansion.mx/tecnologia/2026/05/27/data-centers-en-queretaro-chocan-con-el-estres-hidrico
- Por Esto (20 oct 2026), muestreo de Greenpeace: https://www.poresto.com/yucatan/merida/2026/10/20/greenpeace-detecta-contaminacion-cuerpos-agua-yucatan-vinculada-megagranjas-porcicolas.html
- Por Esto (30 mar 2026), 83 % de 60 cenotes monitoreados, fuentes de contaminación (Cinvestav-Mérida) y multas de Profepa: https://www.poresto.com/yucatan/2026/3/30/en-yucatan-el-83-de-los-cenotes-monitoreados-estan-contaminados-granjas-porcicolas-boom-inmobiliario-y-turismo-amenazan-al-acuifero.html
- Diario de Yucatán (13 mar 2024), drenaje de Mérida: https://www.yucatan.com.mx/merida/2024/03/13/la-construccion-de-un-drenaje-urbano-en-merida-un-proyecto-lejos-de-concretarse.html
- Por Esto (10 jul 2026), la SCJN atrae los casos de Homún (SEFA 223/2026 y 224/2026): https://www.poresto.com/yucatan/2026/7/10/scjn-sentara-precedente-en-yucatan-definira-si-los-cenotes-y-la-abeja-melipona-pueden-tener-derechos-propios.amp.html
