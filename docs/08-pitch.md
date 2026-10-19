# 08 · El pitch

> Documento para **Nico** (estructura y contenido) y **Leo** (diseño visual). **Pendiente:** preguntar a CIFOX la duración y el formato exactos.

## ¿Qué es el pitch?

Es una **presentación corta ante el jurado** en la que explicamos qué hicimos y por qué es buena solución. **No es para venderle el producto a una empresa ese día.** Los jueces son especialistas en ciberseguridad, IA, agua y academia.

Sí tenemos que demostrar que la solución **podría** usarse en el mundo real, porque uno de los 7 criterios es "Escalabilidad y modelo de negocio".

## Estructura sugerida

| # | Parte | Tiempo aprox. | Contenido |
|---|---|---|---|
| 1 | **El problema** | ~15% | La IA consume agua; en Yucatán el acuífero es la única fuente; el enfriamiento es infraestructura crítica atacable |
| 2 | **La solución** | ~15% | DripSafe: un vigilante, dos beneficios |
| 3 | **Demo en vivo** | ~25% | Mostrar una alerta de ineficiencia y una de posible ataque. Tener el video de respaldo listo |
| 4 | **Los números** | ~25% | PUE inicial y final proyectado, ahorro estimado y balance neto; agua y emisiones solo si hay datos suficientes |
| 5 | **Impacto y escala** | ~20% | Acuífero, bono de cero agua dulce, quién lo usaría y cierre |

**Preparación:** Nico calcula el ahorro y el PUE final proyectado, usando el PUE inicial de Misa y los insumos de Gadiel. **Misa + Nico calculan y validan juntos el balance neto final**; Nico consolida las cifras en `resultados/numeros_oficiales.json` y escribe el contenido. Leo diseña las diapositivas y muestra las mismas cifras en el dashboard. El PUE final y los ahorros se presentan como proyecciones hasta contar con evidencia medida; las métricas pendientes no se presentan como resultados.

## Checklist: los 7 criterios deben escucharse en el pitch

- [ ] **Innovación:** un solo modelo para eficiencia y ciberseguridad.
- [ ] **Viabilidad técnica:** demo funcionando sobre el kit real.
- [ ] **Impacto en ciberseguridad:** técnicas de MITRE ATT&CK for ICS que detectamos.
- [ ] **Eficiencia Green AI:** comparación del PUE inicial con el final proyectado, con sus supuestos.
- [ ] **Balance neto y gobernanza:** comparar el costo medido o extrapolado del modelo con el ahorro estimado para el mismo horizonte, más el análisis del acuífero.
- [ ] **Escalabilidad y negocio:** ver abajo.
- [ ] **Presentación:** historia clara y diapositivas limpias.
- [ ] **Bono:** propuesta de enfriamiento híbrido con cero agua potable.

## Modelo de negocio (basta con 2 o 3 ideas)

- **Quién lo usaría:** operadores de centros de datos, plantas de tratamiento de agua y cualquier instalación con enfriamiento industrial (hospitales, industria, edificios grandes).
- **Por qué les conviene:** ahorran energía y agua, o sea dinero, y detectan ataques antes de que causen daños.
- **Cómo escala:** el mismo modelo se reentrena con los datos de otra instalación sin rehacer todo.
- *Opcional:* cómo se ofrecería, por ejemplo como software por suscripción por instalación.

## Consejos

- **Simple gana.** Un modelo sencillo que funciona y números claros le ganan a algo complejo que nadie entiende.
- **Sean honestos.** "Primera capa de detección" funciona mejor que "solución completa de ciberseguridad".
- **Una idea por diapositiva.** Números grandes, poco texto.
- **Ensayen dos veces con cronómetro** el 21 y otra vez el 22 a las 15:30.
- **Preparen respuestas** a preguntas probables:
  - ¿Cómo saben que es un ataque y no una falla?
  - ¿Cuánta energía consume su modelo?
  - ¿Qué pasa si el atacante conoce el modelo?
  - ¿Funcionaría en otra instalación?
  - ¿De dónde salen sus cifras del acuífero?

## ¿Quién presenta?

Por definir. Candidatos: **Nico** (presentó propuestas en IRAP) y **Leo** (líder). Puede ser uno o repartirse las partes.
