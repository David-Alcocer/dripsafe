# 01 · La convocatoria: qué nos piden

> Resumen de las bases oficiales del **Hackatón CIFOX · AguaSegura AI**.
> Fuente: <https://vaporlatierra.com/2026/convocatoria-hackaton-cifox-aguasegura-ai/>
> Ante cualquier duda, manda la convocatoria original.

## El reto

**Pregunta detonadora:** ¿Cómo podemos hacer que la infraestructura que hace posible la inteligencia artificial sea, al mismo tiempo, más segura, más eficiente y más responsable con el agua?

Hay dos problemas de fondo:

1. **Agua:** los centros de datos de IA consumen muchísima energía y agua para enfriarse, y eso presiona recursos hídricos que ya son escasos.
2. **Ciberseguridad:** los sistemas OT/ICS que controlan el enfriamiento y el agua son infraestructura crítica, vulnerable a ciberataques.

**Objetivo general:** diseñar soluciones integradas de IA y ciberseguridad que optimicen la eficiencia hídrica.

## Formato y fechas

| Fecha | Qué pasa |
|---|---|
| 14 oct | CIFOX confirma los equipos seleccionados (por correo al representante) |
| **19 oct** | **Fase 1:** entrega digital del **kit de datos** y arranque del trabajo remoto |
| **22 oct** | **Fase 2:** jornada presencial, pitch y premiación |

**Sede:** Sala de Usos Múltiples de la Universidad Politécnica de Yucatán (UPY).

**El kit de datos incluye:** datasets de consumo hídrico y energético, especificaciones técnicas de sistemas OT/ICS de enfriamiento, documentación de contexto y criterios de evaluación.

### Agenda del 22 de octubre

| Hora | Actividad |
|---|---|
| 08:00–08:30 | Registro y acreditación |
| 08:30–09:00 | Apertura y contexto del reto |
| 09:00–09:30 | Confirmación de equipos, asignación de mentores y **validación del avance remoto** |
| 09:30–15:30 | **Bloque de trabajo de 6 horas**, con rondas de mentoría |
| 15:30–16:00 | Cierre de desarrollo y preparación del pitch |
| 16:00–17:30 | **Presentaciones ante el jurado** |
| 17:30–18:00 | Deliberación y networking |
| 18:00–18:30 | Premiación y cierre |

## Equipos

- De 4 a 6 integrantes. Nosotros somos **5**.
- Un representante es el punto de contacto con CIFOX.
- Perfiles sugeridos: ciberseguridad, IA y datos, desarrollo, agua y ambiente, negocio e innovación.

## Los 4 sub-retos (se elige UNO)

| # | Sub-reto | Métrica que piden |
|---|---|---|
| 1 | Optimización del consumo de agua en enfriamiento | Mejora estimada en **WUE** |
| 2 | Ciberseguridad de sistemas OT/ICS de gestión hídrica y enfriamiento | Reducción de superficie de ataque y riesgo operativo |
| **3** | **Detección de anomalías con IA en enfriamiento y gestión hídrica** | **Impacto energético en PUE** ← **el nuestro** |
| 4 | Green AI, gobernanza y métricas | **CUE** del modelo frente a su beneficio |

### Las métricas

- **WUE (Water Usage Effectiveness):** litros de agua ÷ kWh de energía de TI.
- **PUE (Power Usage Effectiveness):** energía total de la instalación ÷ energía de TI. El ideal es 1.0.
- **CUE (Carbon Usage Effectiveness):** kg de CO₂e ÷ kWh de energía de TI.

Se reporta la métrica aplicable al sub-reto (dicen "WUE, PUE **y/o** CUE") o una variación justificada. **No es obligatorio reportar las tres.**

## ⚠️ Requisito obligatorio (sección 11)

Todos los equipos deben incluir dos cosas, sin importar el sub-reto. **Si falta alguna, la propuesta no se evalúa completa.**

1. **Balance neto positivo:** la energía y el carbono que consume nuestro modelo de IA **no deben superar** el ahorro que genera. Debe estimarse y justificarse **con cifras**.
2. **Impacto en el acuífero o la cuenca local:** extracción, presión sobre el acuífero, riesgo de contaminación y gobernanza del recurso.

## Entregables del 22 de octubre

1. Propuesta de solución (diseño, modelo, arquitectura o demo) hecha sobre el kit de datos y alineada a un sub-reto.
2. Reporte de los indicadores WUE, PUE y/o CUE aplicables.
3. Estimación del balance neto y análisis del impacto en el acuífero o cuenca.
4. Pitch ante el jurado. CIFOX comunica la duración y el formato a los equipos confirmados.

## Criterios de evaluación

Son los mismos 7 para todos los equipos. **La convocatoria no publica cuánto pesa cada uno.**

1. **Innovación:** originalidad de la solución.
2. **Viabilidad técnica:** qué tan realista y funcional es.
3. **Impacto en ciberseguridad:** protección que aporta a la infraestructura OT/ICS.
4. **Eficiencia Green AI:** mejora medible en WUE, PUE y/o CUE.
5. **Balance neto y gobernanza hídrica.**
6. **Escalabilidad y modelo de negocio.**
7. **Presentación y claridad.**

## ⭐ Puntos extra: Zero Freshwater Footprint

**Bono de +5% a +15% sobre la calificación final.** Se otorga a quien proponga una alternativa de enfriamiento **técnicamente viable** que reduzca a cero el uso de agua dulce potable. Por ejemplo:

- Enfriamiento con agua no potable o reciclada.
- Enfriamiento por aire de alta eficiencia.
- Enfriamiento líquido en circuito cerrado.
- Otras arquitecturas equivalentes.

**Es el único bono que existe.** Las herramientas que usemos (Grafana, Streamlit, etc.) no dan puntos extra.

## Premios

- 1.º, 2.º y 3.er lugar.
- Reconocimientos especiales: **Mejor solución de Green AI**, **Mejor impacto hídrico** y **Mejor propuesta de ciberseguridad OT**.

## Reglas clave

- **Propiedad intelectual:** el equipo conserva la titularidad de su solución.
- **Kit de datos confidencial:** solo puede usarse para el hackatón. **Prohibido divulgarlo.**
- **Prohibido hacer pruebas o ataques sobre sistemas reales, ajenos o en producción.** Solo se trabaja sobre el kit y en entornos simulados. Romper esta regla puede descalificar al equipo.
- La decisión del jurado es inapelable.

## Contacto

- gloria.vlencia@cifox.org
- mariana.gomez@cifox.org
