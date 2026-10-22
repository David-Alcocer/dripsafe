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

**Purga, solo como escenario físico simplificado.** En una torre estable, sin arrastre, fugas ni rebose, reposición = evaporación + purga y ciclos = reposición / purga. Por tanto, `purga = evaporación / (ciclos − 1)`. Con **4 ciclos supuestos**, 3 L evaporados requieren 1 L de purga y 4 L de reposición. Si se evita 1 L de *reposición causada por evaporación* y los ciclos no cambian, se evita 0.25 L de purga. **Una fuga evitada no implica esa reducción.** La relación procede del [balance del Departamento de Energía de EE. UU., ecuaciones 1–7](https://www.energy.gov/sites/default/files/2013/10/f3/waterfs_coolingtowers.pdf) y se reproduce con `src.metricas.purga.balance_torre`; no se calcula a partir de `water_l` del kit.

## 4. Balance neto (obligatorio, cálculo conjunto de Misa + Nico)

**El consumo del modelo de IA debe ser menor que el ahorro que genera.** Las fórmulas están en [05-solucion-tecnica.md](05-solucion-tecnica.md#balance-neto-obligatorio).

**Misa entrega:** PUE inicial, datos limpios y energías total y de TI, con unidades, intervalo y periodo.

**Nico calcula:** ahorro energético y PUE final proyectado; estima agua y emisiones cuando haya datos suficientes. Identifica proyecciones, fuentes y supuestos, y consolida los resultados para Leo.

**Misa + Nico calculan y validan juntos:** el balance neto final, descontando el consumo del modelo del ahorro estimado con unidades y periodos compatibles. La firma y las cifras vigentes están en `resultados/numeros_oficiales.json`; este análisis hídrico no modifica ese archivo.

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

Para estimar el PUE anual de la propuesta hacen falta energía anual de TI, energía no TI de la base, potencia o curva de rendimiento del enfriador seco, chiller y bombas, y su despacho horario. El cálculo sería `PUE = (E_IT + E_otros + E_enfriador_seco + E_chiller + E_bombas) / E_IT`, con todas las energías en el mismo periodo. **El PUE del bono permanece pendiente** hasta que Misa aporte esos parámetros. Las cifras de PUE y WUE de los sitios simulados en §5.1 no se transfieren a este equipo.

### 5.5 Evidencia técnica y alcance

- [ASHRAE](https://www.ashrae.org/file%20library/technical%20resources/bookstore/emergence-and-expansion-of-liquid-cooling-in-mainstream-data-centers_wp.pdf) documenta la clase W40. La clase se aplica al suministro líquido de equipos compatibles; no fija por sí sola las horas de respaldo en Mérida.
- [Microsoft (2024)](https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/) describe circuito cerrado sin evaporación para enfriamiento y reconoce el aumento energético del enfriamiento mecánico. Sus cifras corporativas no se usan como medición del proyecto.
- La serie [ERA5 de Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) permite explorar umbrales climáticos. No sustituye un diseño térmico ni datos del sitio.

### 5.6 Validaciones necesarias antes de afirmar viabilidad local

1. Confirmar compatibilidad W40 de los servidores, carga térmica, curvas de enfriador/chiller, energía de bombas y PUE anual resultante; comparar energía directa e impacto indirecto del SEN si existe un factor verificable.
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
