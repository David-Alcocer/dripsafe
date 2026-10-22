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
> "Yucatán tiene un acuífero kárstico con poco drenaje superficial y numerosos cenotes. CONAGUA reporta disponibilidad regional positiva, pero eso no garantiza calidad ni agua disponible para un predio. Cuando un centro usa agua subterránea, importan tanto la captación como el destino de sus descargas.
> Y el enfriamiento lo controlan PLCs: si alguien cambia un setpoint, el consumo se dispara sin que nadie lo note.
> Hoy se vigila con umbrales fijos: alertar si el PUE pasa de 1.6. Pero un sitio eficiente, con PUE de 1.2, puede subir su energía no TI hasta **158 %** sin cruzar esa línea. El umbral fijo deja ciegos justo a los sitios eficientes."

### 2 · La solución (50 s)
> "DripSafe aprende, con 72 horas limpias de referencia (48 para ajustar y 24 para calibrar), cuánto **debería** gastar cada sitio según su carga y la temperatura exterior. Cada hora compara lo real contra lo esperado. Es la misma línea base que se usa para verificar ahorros de energía (ASHRAE Guideline 14), pero aplicada a detectar en tiempo real.
> Y cruza esos excesos con el registro OT. Así separa cuatro casos: un **incidente con efecto físico**, un **cambio no autorizado** que todavía no mueve la física, un **exceso sin registro** y un simple **intento de acceso**.
> Dos reglas de oro: ningún exceso sin explicar va directo a mantenimiento, y ningún cambio no autorizado es «sin urgencia»."

### 3 · Demo (90 s) · dashboard en modo presentación
1. **Resumen** (15 s): "Esto es el kit oficial, datos simulados. La línea punteada es lo esperado; el área naranja es el exceso."
2. **Demo de ataque · Evento OT · SIM-C** (45 s), los 4 pasos: "El operador ve todo normal. La energía también va en lo esperado. Pero el registro OT muestra tres logins fallidos de madrugada y luego un cambio de configuración. DripSafe lo marca como **cambio no autorizado**: no hay efecto físico todavía, pero se compara contra la configuración aprobada y se vigila 24 horas."
3. **Demo · Ineficiencia · SIM-A** (30 s): "Aquí no hay evento OT, pero la energía no TI sube hasta **107 %** sobre lo esperado. Es un **escalón sin registro**: puede ser una falla o un cambio que no dejó huella. Primero se revisa la configuración, después mantenimiento. DripSafe solo avisa; decide una persona."

> Si la demo falla: pasar al video de respaldo sin comentarlo (#20).

### 4 · Los números (60 s)
> "En los 3 episodios anómalos del kit, 21 horas en total, DripSafe y las reglas empatan: el kit los diseñó para que las reglas los vean, y lo decimos así.
> El aporte está en las fallas más pequeñas. Inyectamos excesos de 10 a 80 % con una rejilla fija, escrita antes de medir. DripSafe detecta las 18 fallas de cada tamaño desde **+10 %**, en la misma hora; las reglas fijas no ven ninguna hasta **+80 %**, y ahí solo 6 de 18. Solo en las fallas de +20 %, las reglas dejan pasar **625 kWh**.
> ¿Y lo que gasta DripSafe? Medimos [detector_cpu_ms] ms por corrida en una laptop. Eso es [detector_kwh_anual] kWh al año, estimado. Basta con detectar a tiempo **[equilibrio] de exceso al año** para pagar su propia energía. Ese es el balance neto: no depende de prometer ahorros."

### 5 · Impacto y escala (60 s)
> "En agua, el ahorro depende del tipo de enfriamiento: es grande en el evaporativo y casi nulo en el de aire. Lo decimos en lugar de prometer agua en todos lados.
> Para el bono proponemos llegar a **cero agua potable de enfriamiento** en obra nueva: circuito cerrado W40, enfriador seco y chiller condensado por aire. La serie ERA5 de Mérida cuenta horas por encima de varios umbrales, pero todavía no mide las horas del chiller. Microsoft describió en 2024 un diseño sin evaporación y reconoció su costo energético. Nuestro PUE del bono sigue pendiente de las curvas del equipo. El agua tratada para un respaldo adiabático sería una alternativa futura condicionada a suministro y descarga verificados.
> DripSafe corre en local, sin nube y sin GPU, con seis medidores que casi cualquier centro de datos ya tiene. Cuesta por kW, y con nuestro precio supuesto la cuota se paga sola con menos del 0.5 % del consumo auxiliar de un sitio de 1 MW.
> Nuestros límites: datos simulados, una sola semana de clima y sin sensores de agua helada. La siguiente validación es con datos reales de una sala de cómputo en Yucatán.
> DripSafe: que cada litro y cada kWh que sobra se note a tiempo."

## Checklist: los 7 criterios deben escucharse

- [ ] **Innovación:** línea base física por sitio aplicada a detectar + fusión evento–efecto + prioridad por litros (diapositivas 3 y 4).
- [ ] **Viabilidad técnica:** demo funcionando sobre el kit real, en una laptop, sin internet.
- [ ] **Impacto en ciberseguridad:** cuatro clases, T0859 y T0836 observables, T0831 inyectada y el cambio sin registro (T0836 sin log o T1692.001, antes T0855); solo lectura (diapositiva 4). Cifras y frases en `docs/06` §6 y §10.
- [ ] **Eficiencia Green AI:** PUE con sumas, exceso medido sobre la línea base y curva de sensibilidad (diapositiva 6).
- [ ] **Balance neto y gobernanza:** umbral de equilibrio, acuífero y reporte para CONAGUA (diapositivas 7 y 8).
- [ ] **Escalabilidad y negocio:** seis medidores, autocalibración y precio por kW (diapositiva 9).
- [ ] **Presentación:** una idea por diapositiva y la demo en modo presentación.
- [ ] **Bono:** meta condicionada de cero agua potable con respaldo seco; declarar PUE pendiente (contenido para Leo en `docs/n4-entrega-para-leo.md`).

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Cómo saben que es un ataque y no una falla? | No lo adivinamos. Si hay evento OT y luego un exceso, es incidente. Si hay exceso sin registro, no se puede saber con datos de proceso: por eso primero se revisa la configuración. |
| ¿Por qué no un modelo más complejo? | El método más ligero que funciona es el argumento Green AI. La línea base explica cada alerta en una frase y pesa milisegundos. |
| ¿Qué aporta si las reglas detectan los 3 episodios? | En el kit empatan, y lo decimos. El aporte se ve con fallas pequeñas: la curva de sensibilidad. |
| ¿Cuánta energía consume? | [detector_cpu_ms] ms medidos por corrida; la energía se estima con supuestos editables. El umbral de equilibrio es [equilibrio]. |
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
