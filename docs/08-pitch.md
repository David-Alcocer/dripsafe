# 08 · El pitch

> Documento para **Leo** (guion y diseño, D13) y **Nico** (cifras y su explicación). Sigue la propuesta v9 y el plan de ejecución (19 oct). **Pendiente:** preguntar a CIFOX la duración y el formato exactos. El guion está pensado para **5 minutos**; si son menos, se recorta como dice la última sección.

## ¿Qué es el pitch?

Es una **presentación corta ante el jurado** en la que explicamos qué hicimos y por qué es buena solución. **No es para venderle el producto a una empresa ese día.** Los jueces son especialistas en ciberseguridad, IA, agua y academia.

Sí tenemos que demostrar que la solución **podría** usarse en el mundo real, porque uno de los 7 criterios es "Escalabilidad y modelo de negocio".

## La idea en una línea

**DripSafe aprende cómo debería comportarse cada sitio según su carga y su clima, avisa cuando la física no cuadra, distingue un intento OT de un incidente con efecto real y ordena las alertas por los litros del acuífero en juego.**

## Estructura

| # | Parte | Tiempo | Diapositivas (11) |
|---|---|---|---|
| 1 | El problema | 0:00 – 0:40 | 1 · Portada, 2 · El problema |
| 2 | La solución | 0:40 – 1:30 | 3 · Real contra esperado, 4 · Cuatro clases |
| 3 | Demo en vivo | 1:30 – 3:00 | 5 · Demo (pasar al dashboard en modo presentación; video de respaldo listo) |
| 4 | Los números | 3:00 – 4:00 | 6 · Evaluación honesta, 7 · Balance neto |
| 5 | Impacto y escala | 4:00 – 5:00 | 8 · Acuífero y bono, 9 · Escala y negocio, 10 · Límites, 11 · Cierre |

**Cifras del pitch.** Todo número entre corchetes sale de `resultados/numeros_oficiales.json` (Nico) o, si es un
supuesto de negocio, se dice como supuesto. Los valores dentro de los corchetes son los esperados según la
propuesta y se confirman con el JSON antes de congelar.

## Guion

Las cifras entre corchetes salen **solo** de `resultados/numeros_oficiales.json` (Nico). Si una cifra no está ahí, no se dice.

### 1 · El problema (40 s)
> "En Yucatán no hay ríos. Casi toda el agua sale de un solo acuífero, con el agua a pocos metros de la superficie y conectado por cenotes. Cada centro de datos que enfría con torres evaporativas saca agua de ahí.
> Y el enfriamiento lo controlan PLCs: si alguien cambia un setpoint, el consumo se dispara sin que nadie lo note.
> Hoy se vigila con umbrales fijos: alertar si el PUE pasa de 1.6. Pero un sitio eficiente, con PUE de 1.2, puede subir su energía no TI hasta **158 %** sin cruzar esa línea. El umbral fijo deja ciegos justo a los sitios eficientes."

### 2 · La solución (50 s)
> "DripSafe aprende, con 72 horas limpias de referencia (48 para ajustar y 24 para calibrar), cuánto **debería** gastar cada sitio según su carga y la temperatura exterior. Cada hora compara lo real contra lo esperado. Es la línea base de ASHRAE Guideline 14, usada para detectar en tiempo real.
> Y cruza esos excesos con el registro OT. Así separa cuatro casos: un **incidente con efecto físico**, un **cambio no autorizado** que todavía no mueve la física, un **exceso sin registro** y un simple **intento de acceso**.
> Dos reglas de oro: ningún exceso sin explicar va directo a mantenimiento, y ningún cambio no autorizado es «sin urgencia».
> El kit nos dio los datos simulados y unas reglas de ejemplo. Lo nuestro es la línea base por sitio, las cuatro clases OT y la prueba con fallas pequeñas."

### 3 · Demo (90 s) · dashboard en modo presentación
1. **Resumen** (15 s): "Esto es el kit oficial, datos simulados. La línea punteada es lo esperado; el área naranja es el exceso."
2. **Demo de ataque · Evento OT · SIM-C** (45 s), los 4 pasos: "El operador ve todo normal. La energía también va en lo esperado. Pero el registro OT muestra tres logins fallidos de madrugada y luego un cambio de configuración. DripSafe lo marca como **cambio no autorizado**: no hay efecto físico todavía, pero se compara contra la configuración aprobada y se vigila 24 horas."
3. **Demo · Ineficiencia · SIM-A** (30 s): "Aquí no hay evento OT, pero la energía no TI sube hasta **107 %** sobre lo esperado. Es un **escalón sin registro**: puede ser una falla o un cambio que no dejó huella. Primero se revisa la configuración, después mantenimiento. DripSafe solo avisa; decide una persona."

> Si la demo falla: pasar al video de respaldo sin comentarlo (#20).

### 4 · Los números (60 s)
> "En los 3 episodios anómalos del kit, DripSafe y las reglas empatan: el kit los diseñó para que las reglas los vean.
> El aporte está en las fallas más pequeñas. Inyectamos excesos de 10 a 80 % con una rejilla fija, escrita antes de medir. DripSafe detecta las 18 fallas de cada tamaño desde **+10 %**, en la misma hora; las reglas fijas no ven ninguna hasta **+80 %**, y ahí solo 6 de 18. Solo en las fallas de +20 %, las reglas dejan pasar **625 kWh**.
> Si cada alerta física se atiende a tiempo, el PUE de la semana evaluada pasaría de **1.278 a 1.268** y el WUE de **0.394 a 0.366 L/kWh**. Es una proyección sobre datos simulados, no un ahorro observado.
> ¿Y lo que gasta DripSafe? Medimos **34 ms** por corrida en una laptop. Con una potencia supuesta del procesador, eso equivale a unos **0.000013 kWh al año**: es una estimación, no una lectura de un medidor. En la cuenta, **menos de un milisegundo** de exceso típico al año paga su propia energía. Ese es el balance neto, validado por Misa y Nico: no depende de prometer ahorros."

### 5 · Impacto y escala (60 s)
> "En agua, el ahorro depende del tipo de enfriamiento: es grande en el evaporativo y casi nulo en el de aire.
> Para el bono proponemos llegar a **cero agua potable** en obra nueva: enfriamiento líquido en circuito cerrado con enfriadores secos, y un chiller de respaldo en las [horas] más calientes del año. Cuesta un poco de PUE y lo reportamos.
> DripSafe corre en local, sin nube y sin GPU, con seis medidores que casi cualquier centro de datos ya tiene. Cuesta por kW, y con nuestro precio supuesto la cuota se paga sola con menos del 0.5 % del consumo auxiliar de un sitio de 1 MW.
> Nuestros límites: datos simulados, una sola semana de clima y sin sensores de agua helada. La siguiente validación es con datos reales de una sala de cómputo en Yucatán.
> DripSafe: que cada litro y cada kWh que sobra se note a tiempo."

## Checklist: los 7 criterios deben escucharse

- [ ] **Innovación:** línea base física por sitio aplicada a detectar + fusión evento–efecto + prioridad por litros (diapositivas 3 y 4).
- [ ] **Viabilidad técnica:** demo funcionando sobre el kit real, en una laptop, sin internet.
- [ ] **Impacto en ciberseguridad:** cuatro clases, T0859 y T0836 observables, T0831 inyectada y el cambio sin registro (T0836 sin log o T1692.001, antes T0855); solo lectura (diapositiva 4). Cifras y frases en `docs/06` §6 y §10.
- [ ] **Eficiencia Green AI:** PUE y WUE con sumas (antes observado, después proyectado), exceso sobre la línea base y curva de sensibilidad (diapositiva 6).
- [ ] **Balance neto y gobernanza:** umbral de equilibrio, acuífero y reporte para CONAGUA (diapositivas 7 y 8).
- [ ] **Escalabilidad y negocio:** seis medidores, autocalibración y precio por kW (diapositiva 9).
- [ ] **Presentación:** una idea por diapositiva y la demo en modo presentación.
- [ ] **Bono:** cero agua potable con respaldo sin agua (diapositiva 8).

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Cómo saben que es un ataque y no una falla? | No lo adivinamos. Si hay evento OT y luego un exceso, es incidente. Si hay exceso sin registro, no se puede saber con datos de proceso: por eso primero se revisa la configuración. |
| ¿Por qué no un modelo más complejo? | El método más ligero que funciona es el argumento Green AI. La línea base explica cada alerta en una frase y pesa milisegundos. |
| ¿Qué aporta si las reglas detectan los 3 episodios? | En el kit empatan, y lo decimos. El aporte se ve con fallas pequeñas: la curva de sensibilidad. |
| ¿Cuánta energía consume? | 33.6 ms medidos por corrida (mediana de 10, desviación 0.56 ms). Los 0.000013 kWh/año salen de CodeCarbon con la potencia de diseño (TDP) del procesador como hipótesis, no de un medidor de pared. El umbral de equilibrio es 2.4×10⁻⁷ h/año (< 1 ms): es una cuenta algebraica, no una latencia demostrada, porque el kit tiene resolución de una hora. |
| ¿Qué venía en el kit y qué hicieron ustedes? | El kit trae los datos simulados, el panel de ejemplo y reglas fijas. Nosotros hicimos la línea base por sitio, la clasificación OT en cuatro clases, la curva de sensibilidad y el balance neto. |
| ¿Qué pasa en mayo, con 40 °C? | Una línea base por época, recalibrada cada semana. Fuera del clima aprendido, el margen se duplica y la alerta sale con «confianza baja», sin apagarse. |
| ¿Qué pasa si el atacante conoce el modelo? | Tendría que mover la energía de forma coherente con la carga y el clima, y los medidores de energía suelen ser otro sistema. Además DripSafe no manda órdenes. |
| ¿Funciona en otra instalación? | Necesita seis medidores comunes y 72 h limpias por época. No necesita etiquetas ni datos de ataques. |
| ¿De dónde salen las cifras del acuífero y del bono? | Fuentes citadas por Guille (acuífero) y Misael (bono); el kit no se usa como evidencia de que una tecnología sea mejor. |

## Si el tiempo es menor
- **3 minutos:** quitar la demo de SIM-A y resumir la parte 5 en dos frases (bono y límites).
- **2 minutos:** problema (30 s), solución con la diapositiva de clases (40 s), números (30 s) y cierre (20 s); la demo solo si la piden.

## Consejos

- **Simple gana.** Un modelo sencillo que funciona y números claros le ganan a algo complejo que nadie entiende.
- **Sean honestos.** "Primera capa de detección" funciona mejor que "solución completa de ciberseguridad".
- **Una idea por diapositiva.** Números grandes, poco texto.
- **Ninguna cifra sin etiqueta:** observado, medido, estimado o proyectado, igual que en el dashboard.
- **Ensayen dos veces con cronómetro** el 21 y otra vez el 22 a las 15:30.

## ¿Quién presenta?

Por definir. Candidatos: **Nico** (presentó propuestas en IRAP) y **Leo** (líder). Puede ser uno o repartirse las partes: por ejemplo, Leo el problema, la solución y la demo; Nico los números y el cierre.
