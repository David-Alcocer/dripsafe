# 07 · Agua, acuífero y bono de cero agua dulce

> Documento para **Nico**. Aquí van los dos requisitos obligatorios que dependen de la investigación (**balance neto** e **impacto en el acuífero**) y el **bono** de +5% a +15%.

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

## 4. Balance neto (obligatorio, junto con Gadiel)

**El consumo del modelo de IA debe ser menor que el ahorro que genera.** Las fórmulas están en [05-solucion-tecnica.md](05-solucion-tecnica.md#balance-neto-obligatorio).

**A Nico le toca conseguir y citar:**
- [ ] Factor de emisión del Sistema Eléctrico Nacional de México, en su valor oficial más reciente.
- [ ] Intensidad hídrica de la generación eléctrica (L/kWh), o un valor de referencia citado.
- [ ] WUE típico de un centro de datos con torres de enfriamiento, como referencia si el kit no lo trae.

**Gadiel aporta:** la energía del modelo, medida con CodeCarbon.

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
- 1 diapositiva: el acuífero de Yucatán y por qué importa.
- 1 diapositiva: balance neto con cifras.
- 1 diapositiva: propuesta de enfriamiento híbrido para el bono.
- Lista de fuentes citadas.

## Para leer más
Ver las secciones "Agua y centros de datos" y "Acuífero de Yucatán" en [09-recursos.md](09-recursos.md).
