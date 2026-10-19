# 07 · Agua, acuífero y bono de cero agua dulce

> Documento para **Nico**. Incluye su cálculo de impacto posterior al PUE inicial de Misa, los requisitos de **balance neto** e **impacto en el acuífero**, y la propuesta del **bono** de +5% a +15%.

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

**Propuesta: enfriamiento híbrido.**

| Opción | Ventaja | Desventaja en Yucatán |
|---|---|---|
| **Enfriamiento líquido en circuito cerrado** | El refrigerante recircula y casi no se repone agua | Mayor inversión inicial |
| **Agua residual tratada** (no potable) | No compite con el agua de consumo humano | Depende de que exista una planta de tratamiento cercana |
| **Aire de alta eficiencia** | Cero agua | En clima cálido y húmedo gasta mucha energía y sube el PUE |
| **Híbrido** (recomendado) | Circuito cerrado como base y agua tratada solo en picos de calor | Más complejo de operar, pero **nuestra IA recomienda cuándo activar el respaldo y el operador confirma** |

**Para que el bono cuente** hay que mostrar:
1. Que la alternativa es **técnicamente viable** (casos reales y referencias).
2. **Cuánto baja el consumo de agua potable**, idealmente a cero, con una estimación de WUE.
3. Que no dispara el PUE. Si lo sube un poco, explicar el balance.

## 6. Entregable de Nico

**Pendiente de implementación y elaboración:**

- **Programa en Python** dentro de `src/metricas/`, usando el PUE inicial que entrega Misa desde `src/metricas/pue.py`. Nico calcula ahorro, PUE final proyectado y, cuando sea posible, impacto en agua y emisiones; incorpora el balance neto final desarrollado junto con Misa en `src/metricas/balance_neto.py`.
- **Ejemplo reproducible con datos sintéticos**, con instrucciones y escenarios sin ahorro, con balance positivo y con ahorro menor que el costo del modelo.
- **Resultados consolidados** en `resultados/numeros_oficiales.json`, con origen y responsable de cada cifra; documentación del periodo, unidades, fuentes y supuestos, distinguiendo mediciones de proyecciones.
- **Análisis del acuífero y propuesta del bono**, con fuentes y condiciones de viabilidad.
- **Contenido y guion del pitch**, incluyendo el impacto local, las cifras del balance y la propuesta del bono. Leo diseña las diapositivas con esos resultados.

## Para leer más
Ver las secciones "Agua y centros de datos" y "Acuífero de Yucatán" en [09-recursos.md](09-recursos.md).
