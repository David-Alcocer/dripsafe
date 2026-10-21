# 07 · Agua, acuífero y bono de cero agua dulce

> **Reparto D13 (19 oct):** el **acuífero y la gobernanza** (sección 3) los lleva **Guille**; la **comparación de refrigeración y el bono** (sección 5) los lleva **Misa**; el **balance neto** sigue con **Misa + Nico**. Incluye los requisitos de **balance neto** e **impacto en el acuífero** y la propuesta del **bono** de +5% a +15%.
>
> **Del kit:** `water_l` es **captación in situ** simulada. No es consumo neto, ni agua de la generación eléctrica, ni potabilidad. Las diferencias entre los sitios del kit no son un experimento controlado: toda recomendación del bono va **condicionada a sus supuestos**.

## 1. Por qué la IA consume agua

Un centro de datos usa agua de dos formas:
- **En sitio:** las **torres de enfriamiento** evaporan agua para disipar el calor de los servidores. Además, parte del agua se **purga** (*blowdown*) para que no se acumulen sales y minerales.
- **Fuera de sitio:** las plantas que generan la electricidad que consume el centro de datos también usan agua.

El artículo *Making AI Less "Thirsty"* (ver [09-recursos.md](09-recursos.md)) es la referencia para entender esta división.

## 2. El acuífero de Yucatán: por qué es especial

Datos generales que hay que **respaldar con fuentes** antes del pitch:
- **Suelo kárstico:** roca caliza muy porosa y fracturada. El agua se infiltra rapidísimo y circula por conductos subterráneos y **cenotes conectados**.
- **Nivel freático somero:** el agua subterránea está a pocos metros de la superficie, sobre todo en el norte del estado.
- **Sin ríos superficiales:** el acuífero es prácticamente **la única fuente de agua** de la población.
- **Muy vulnerable a la contaminación:** lo que se vierte en superficie llega rápido al agua subterránea. Granjas porcícolas, fosas sépticas y crecimiento urbano ya la afectan.
- **Intrusión salina:** cerca de la costa, extraer demasiada agua dulce permite que entre agua de mar.
- **Anillo de Cenotes:** zona de reserva geohidrológica considerada clave para el abasto de agua de Mérida.

## 3. Análisis de impacto (obligatorio)

Estructura sugerida para la propuesta:

| Aspecto | Pregunta a responder | Cómo ayuda DripSafe |
|---|---|---|
| **Extracción** | ¿Cuánta agua del acuífero deja de extraerse? | Menos energía desperdiciada y menos agua de reposición en torres |
| **Descargas** | ¿Qué pasa con el agua de purga, con sales y químicos? | Detectar operación anómala reduce purgas innecesarias |
| **Contaminación** | ¿Hay riesgo de que llegue a cenotes o al freático? | El enfriamiento en circuito cerrado casi elimina las descargas |
| **Gobernanza** | ¿Quién regula y qué permisos aplican? | CONAGUA (concesiones de agua) y normas de descarga; zonas protegidas |
| **Justicia ambiental** | ¿A quién le quita agua el centro de datos? | Comunidades que dependen del mismo acuífero |

## 4. Balance neto (obligatorio, cálculo conjunto de Misa + Nico)

**El consumo del modelo de IA debe ser menor que el ahorro que genera.** Las fórmulas están en [05-solucion-tecnica.md](05-solucion-tecnica.md#balance-neto-obligatorio).

**Misa entrega:** PUE inicial, datos limpios y energías total y de TI, con unidades, intervalo y periodo.

**Nico calcula:** ahorro energético y PUE final proyectado; estima agua y emisiones cuando haya datos suficientes. Identifica proyecciones, fuentes y supuestos, y consolida los resultados para Leo.

**Misa + Nico calculan y validan juntos:** el balance neto final, descontando el consumo del modelo del ahorro estimado con unidades y periodos compatibles. El balance positivo se verifica con cifras; los cálculos siguen pendientes de implementación.

**A Nico le toca conseguir y citar:**
- [ ] Factor de emisión del Sistema Eléctrico Nacional de México, en su valor oficial más reciente.
- [ ] Intensidad hídrica de la generación eléctrica (L/kWh), o un valor de referencia citado.
- [ ] Consumo de agua o WUE del caso; si se usa un valor de referencia, justificar su aplicación y presentarlo como escenario supuesto.

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

**Por qué importa en Yucatán:** en ese mismo estudio, el modo de enfriamiento gratuito solo se activa si el día promedio está a **≤ 27 °C y ≤ 70 % de humedad relativa** (§3.2, pp. 5–6). En un clima frío pero húmedo (Michigan, zona 5A), la humedad limitó ese modo al **25 % del año** (tabla 3 y §4.1, p. 7). El reporte de WRc (2026) también señala que, en los sistemas híbridos, el uso de agua depende de la temperatura ambiente y de los puntos de control (p. 96 impresa). **Inferencia nuestra, PENDIENTE de validar con datos climáticos:** Mérida es cálida y húmeda casi todo el año, así que el aire de enfriamiento gratuito estaría disponible todavía menos horas. Por eso descartamos el aire solo, que sube el PUE, y el evaporativo solo, que consume mucha agua del acuífero (§2).

### 5.3 Propuesta: híbrido de circuito cerrado + agua residual tratada

| Modo | Cuándo | Agua que usa |
|---|---|---|
| **Base: enfriamiento líquido en circuito cerrado** | Casi todo el año | El circuito se llena una vez y solo se repone poco, **con agua tratada** (WRc, 2026: los operadores lo describen como *single fill*, con reposición mínima, p. 60 impresa) |
| **Respaldo: enfriamiento evaporativo con agua residual tratada (no potable)** | Solo en picos de calor | Agua tratada de una planta cercana, no del acuífero potable |

**Por diseño, la propuesta usa 100 % agua no potable:** tanto la reposición del circuito cerrado como el respaldo usan agua residual tratada. El riesgo de que eso no se cumpla está en §5.6.

- **DripSafe recomienda y el operador confirma (D4).** El detector ya aprende la línea base por sitio usando la temperatura exterior. **Propuesta, no implementada:** con esa misma base, DripSafe **recomendaría** activar el respaldo cuando el calor supere lo que el circuito cerrado puede disipar, y **el operador lo confirma**. La IA nunca manda órdenes al enfriamiento; ver «Cómo se instala DripSafe sin abrir una puerta nueva» en [06-ciberseguridad-ot.md](06-ciberseguridad-ot.md).
- **Ojo con los nombres** (Alston et al., 2026, §2.1.4, p. 3): «líquido» describe cómo se saca el calor de los servidores, no cómo se expulsa del edificio. En la propuesta, el calor se expulsa con aire en la base y con evaporación de agua tratada en el respaldo.

### 5.4 WUE estimado de la propuesta (SUPUESTOS editables)

Se separan dos métricas:
- **WUE total:** todo el agua captada por kWh de TI, potable o no.
- **WUE de agua potable:** solo la parte potable. **Es lo que premia el bono y debe tender a 0.**

Fórmula (en `src/metricas/refrigeracion.py`, función `estimar_hibrido`), donde *f* es la **fracción de la energía de TI servida en modo respaldo**:

```text
WUE total   = (1 − f) · WUE_base + f · WUE_respaldo
WUE potable = (1 − f) · WUE_base · (1 − no_potable_base) + f · WUE_respaldo · (1 − no_potable_respaldo)
PUE         = (1 − f) · PUE_base + f · PUE_respaldo
```

**Valores de entrada: coeficientes didácticos del kit, NO datos de fabricante.** La base toma el sitio **líquido** del kit en referencia (WUE 0.213 L/kWh TI, PUE 1.198). El respaldo toma el sitio **evaporativo** en referencia (WUE 0.854 L/kWh TI, PUE 1.237). Son cocientes de un escenario simulado: sirven para mostrar el método, no describen ningún equipo real ni su ficha técnica. Probablemente la base es **conservadora**: un circuito cerrado *single fill* (WRc, 2026, p. 60 impresa) repone mucho menos agua que el sitio líquido simulado.

En los tres escenarios el agua es **100 % tratada en ambos modos**, por diseño (§5.3). Lo único que cambia es *f*, que es un SUPUESTO:

| Escenario | *f* (respaldo) · SUPUESTO | WUE total (L/kWh TI) | **WUE potable** (L/kWh TI) | PUE |
|---|---|---|---|---|
| Optimista | 10 % | 0.277 | **0.000** | 1.202 |
| Central | 25 % | 0.373 | **0.000** | 1.207 |
| Conservador | 50 % | 0.533 | **0.000** | 1.217 |

**Lectura:**
- **WUE potable = 0 en los tres escenarios.** Esa es la meta del bono, y se cumple porque ningún modo usa agua de la red.
- El **WUE total** sí crece con *f*: más horas de respaldo evaporativo significan más agua tratada. Aun en el escenario conservador (0.533) queda por debajo del sitio evaporativo del kit (0.854). Esa agua no sale del acuífero potable, pero sigue siendo agua consumida, y el agua tratada es un recurso limitado (§5.6).
- **El PUE no se dispara:** queda entre 1.202 y 1.217, por debajo del sitio de aire (1.368) y cerca del líquido (1.198). La suma por fracción de energía de TI es exacta si *f* se mide en energía de TI, no en horas.
- **PENDIENTE:** el valor real de *f* para Mérida (horas de respaldo por umbral de temperatura) depende de N4 (normales del SMN o ERA5) y entra en `numeros_oficiales.json → bono_zero_freshwater`. Mientras tanto, los tres valores de *f* son solo para ver la sensibilidad.
- Reproducir: `python -m src.metricas.refrigeracion --kit data/kit/operaciones_simuladas.csv` imprime la tabla de §5.1, estos tres escenarios y el caso de riesgo de §5.6.

### 5.5 Viabilidad técnica: referencias reales

1. **Uso de agua reciclada para enfriar ya existe.** AWS reportó que 24 de sus centros de datos usaban agua reciclada para enfriamiento. El centro de CoreSite en Santa Clara usó unos 159 000 m³ de agua reciclada en 2021. Microsoft, en cambio, reporta que la disponibilidad limitada lo dificulta (WRc, 2026, §3.1.4, p. 40 impresa). Cambiar a agua residual no reduce el consumo total, pero **deja de tomarlo del ambiente**, y requiere tratamiento adicional (Pan et al., 2018, citado en WRc, 2026, p. 40 impresa).
2. **La simbiosis centro de datos ↔ planta de tratamiento es escalable.** Wang et al. (2026) cruzaron más de 4 775 centros de datos con 57 547 plantas de tratamiento municipales en 98 países. Estiman que usar el efluente tratado para enfriar ahorraría unos **1 300 millones de m³ de agua dulce al año** a escala global (resumen, p. 1). El 87.8 % de las conexiones por tubería quedan a **menos de 40 km** de la planta, y recomiendan buscar oportunidades dentro de ese radio (p. 7).
3. **El enfriamiento líquido ahorra agua y sirve para cargas de IA.** WRc (2026, §3.1.3, p. 39 impresa) reporta que el enfriamiento líquido puede usar **entre 31 % y 52 % menos agua**. Además, el circuito cerrado se considera *single fill*: por ejemplo, unos 24 m³ para un sitio de 1 MW, según un operador entrevistado (§4.2.1, p. 60 impresa).

### 5.6 Límites y siguiente validación

1. **Datos simulados.** Los 3 sitios del kit son escenarios ficticios. Las diferencias entre ellos **no** prueban qué tecnología es mejor en una planta real, y la base y el respaldo de §5.4 heredan esa limitación.
2. **Sin costos.** No se estima la inversión (tubería, tratamiento terciario, intercambiadores) ni la operación (químicos, mantenimiento, bombeo). Por eso no hay costo por m³ evitado.
3. **Depende de tener agua tratada cerca.** Si no hay una planta con efluente suficiente a una distancia razonable (Wang et al. 2026 sugieren menos de 40 km), el respaldo o la reposición caen a la red potable y el WUE potable deja de ser 0. Además, la calidad del agua importa: sin tratamiento se forman biopelículas e incrustaciones que corroen el equipo (WRc, 2026, §3.1.4, p. 39 impresa).

**Riesgo: reposición del circuito cerrado con agua de la red.** Si la reposición de la base se hace con agua potable y no con agua tratada, el WUE potable ya no es 0. Por ejemplo, con *f* = 25 % y respaldo 100 % tratado queda en 0.75 × 0.213 ≈ **0.160 L/kWh TI**. El WUE total sigue en 0.373 y el PUE en 1.207, porque solo cambia la fuente del agua. Se calcula con `riesgo_reposicion_con_red` en `src/metricas/refrigeracion.py`.
- **Condición de mitigación:** conectar la reposición al mismo suministro de agua tratada que el respaldo, con su tratamiento en sitio y un depósito que cubra la reposición mientras el suministro tratado no esté disponible. Mientras eso no esté garantizado por contrato, el bono se presenta como meta de diseño y no como resultado.

**Siguiente validación necesaria:**
- Calcular *f* con las horas reales de calor en Mérida (N4).
- Identificar las plantas de tratamiento con efluente disponible cerca del sitio y su calidad, y confirmar la gobernanza de ese efluente con CONAGUA (§3).
- Repetir §5.4 con el WUE de reposición de un circuito cerrado real en lugar del sitio líquido simulado.
- Medir el agua indirecta de la electricidad con un factor del SEN (pendiente en §4), porque más PUE significa más agua en la generación (Alston et al., 2026).

### 5.7 Qué significa el agua del kit

`water_l` es **captación in situ simulada**:
- **No** es consumo neto: no descuenta lo que se devuelve o se purga.
- **No** incluye el agua de la generación eléctrica (alcance 2 en Alston et al., 2026, §1).
- **No** dice si el agua es potable o no. El kit no separa fuentes, así que el «WUE potable» de §5.4 sale **solo de los supuestos**, no del kit.

**Referencias de esta sección**
- Alston, G., Love, N. y Haider, R. (2026). *Data Center Cooling Choices Shift Water Impacts Across the Grid: An Integrated Water–Energy Model for Sustainable Data Center Development*. arXiv:2609.25437v1.
- WRc (Dingle, H., Fairhurst, R., Cahill, J., Prin, L.) para MOSL (2026). *Water Efficient Data Centres*. Reporte final UC19447.03, febrero de 2026. Las páginas citadas son las impresas del documento.
- Wang, A., Zhang, C., Xu, T., Savic, D., Jiang, J., Xiao, P., He, C., Tao, Y., Daigger, G. y Ren, N. (2026). *Global data–water symbiosis reduces AI infrastructure's carbon and water footprint*. doi:10.1016/j.ese.2026.100702.

## 6. Entregable de Nico

**Pendiente de implementación y elaboración:**

- **Programa en Python** dentro de `src/metricas/`, usando el PUE inicial que entrega Misa desde `src/metricas/pue.py`. Nico calcula ahorro, PUE final proyectado y, cuando sea posible, impacto en agua y emisiones; incorpora el balance neto final desarrollado junto con Misa en `src/metricas/balance_neto.py`.
- **Ejemplo reproducible con datos sintéticos**, con instrucciones y escenarios sin ahorro, con balance positivo y con ahorro menor que el costo del modelo.
- **Resultados consolidados** en `resultados/numeros_oficiales.json`, con origen y responsable de cada cifra; documentación del periodo, unidades, fuentes y supuestos, distinguiendo mediciones de proyecciones.
- **Análisis del acuífero y propuesta del bono**, con fuentes y condiciones de viabilidad.
- **Contenido y guion del pitch**, incluyendo el impacto local, las cifras del balance y la propuesta del bono. Leo diseña las diapositivas con esos resultados.

## Para leer más
Ver las secciones "Agua y centros de datos" y "Acuífero de Yucatán" en [09-recursos.md](09-recursos.md).
