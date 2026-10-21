# DripSafe · Plan de ejecución por dependencias

**Base:** `propuesta-dripsafe.md` (v7). **Ventana:** 19 de octubre → 21 de octubre de 2026, 20:00. **Objetivo:** llegar al 22 con una demostración reproducible, cifras trazables y un pitch ensayado.

Este es un reparto propuesto para el equipo. El kit es confidencial y los datos simulados solo demuestran el método. Ninguna cifra estimada se presenta como ahorro real.

## Qué se entrega en el MVP

1. Carga y validación de telemetría y registro OT, sin que las etiquetas lleguen al modelo.
2. Línea base aprendida por sitio para energía no TI, agua y temperatura de entrada; residuos, umbrales y media móvil de 4 horas.
3. Cuatro clases de alerta: incidente OT con efecto, cambio no autorizado, escalón sin registro e intento de acceso.
4. Comparación contra las reglas fijas del kit: casos originales, rejilla de inyecciones y una prueba básica de ruido.
5. PUE/WUE, exceso estimado de kWh y litros, costo energético del detector, balance neto y análisis del acuífero, con procedencia y supuestos.
6. Dashboard y pitch alimentados por las cifras consolidadas, con una ruta de demostración que funcione sin el kit.

CUSUM, las clases extra y la optimización detallada del bono son ampliaciones. No bloquean el MVP. El detector acordado se limita a la línea base, los umbrales, la media móvil y la clasificación OT (D20).

## Dependencia principal

```text
Contrato de datos + JSON de ejemplo (Misael)
    ├── Modelo y residuos (Gadiel) ──┐
    ├── Eventos, reglas e inyecciones (Guillermo) ──┤
    ├── Métricas y evaluación (Nico) ────────────────┤→ Integración (Misael) → cifras oficiales → dashboard (Leo) → pitch
    └── Dashboard con datos de ejemplo (Leo) ───────┘
```

Para no esperar el contrato definitivo, cada quien puede desarrollar la lógica con ejemplos sintéticos aislados, pero **Misael publica el contrato definitivo antes de integrar**. El mapeo de columnas ocurre una sola vez al cargar los datos, no en cada módulo.

## Fase 0 · Hoy, 19 de octubre: trabajo independiente

| ID | Dueño | Trabajo que puede empezar ya | Entregable verificable | Prioridad |
|---|---|---|---|---|
| M1 | **Misael** | Si ya llegó el kit, comparar sus columnas con `src/contrato.py`; acordar unidades, zona horaria, granularidad, sitio, ausentes y formato del registro OT. Renombrar `scenario`, `simulated_anomaly` y `split` a `etiqueta_*` al cargar. Si aún no llegó, publicar el esquema provisional de la propuesta y cerrar el mapeo al recibirlo. | Contrato actualizado, adaptador de carga y prueba que impida la entrada de etiquetas al modelo. | **Bloqueante** |
| M2 | **Misael** | Definir con Nico y Leo la forma de `resultados/numeros_oficiales.json` y un ejemplo con valores ficticios marcados como tales. Planear el orden de integración y las revisiones. | JSON de ejemplo validado y lista corta de interfaces aceptadas por los cinco. | **Bloqueante** |
| G1 | **Gadiel** | Implementar funciones puras por sitio: partición 48 h/24 h, ajuste de regresión, predicción, residuos, umbral individual y media móvil de 4 h. Usar un ejemplo sintético y conectarlo después al adaptador único de Misael. | Tabla de resultados por sitio y hora con esperado, real, residuo y bandera por detector; ejemplo ejecutable en CPU. | **MVP** |
| U1 | **Guillermo** | Escribir la tabla de decisión de las cuatro clases OT, precedencia, ventana de 24 h y casos ambiguos. Adaptar el inyector existente a la rejilla fijada en la propuesta, solo sobre copias de datos simulados. | Casos inyectados reproducibles con semilla y resultado esperado; reglas unitarias que Nico pueda revisar. | **MVP** |
| N1 | **Nico** | Crear funciones de métricas que operen sobre tablas recibidas: PUE/WUE como cocientes de sumas, exceso estimado, reglas fijas comparables, TP/FP/FN por episodio y horas hasta detectar. Preparar el formato de tabla y curva, sin resultados inventados. | Cálculos reproducibles sobre datos sintéticos; definición clara de qué cuenta como episodio y falsa alarma. | **MVP** |
| L1 | **Leo** | Guardar el dashboard actual si existe fuera de esta copia; diseñar la pantalla con el JSON de ejemplo: real frente a esperado, alertas, curva de sensibilidad y escenario anual editable. Marcar medido/estimado/proyectado. | Demo visual navegable con datos de ejemplo y estados vacíos. | **MVP** |

**Cierre de la fase 0:** Misael publica un ejemplo de entrada y uno de salida. Gadiel, Guillermo, Nico y Leo confirman que sus módulos los pueden leer. Si el kit aún no está disponible, se mantiene la misma interfaz con datos sintéticos; no se paraliza al equipo.

## Fase 1 · 20 de octubre, mañana: primera integración

| Orden | Responsable | Acción | Criterio de terminado |
|---|---|---|---|
| 1 | Misael + Gadiel | Conectar el adaptador de datos al modelo. | Se entrenan los tres sitios con referencia limpia; ninguna columna `etiqueta_*` entra al ajuste ni a la predicción. |
| 2 | Nico + Guillermo | Conectar residuos y eventos OT con las cuatro clases. | Los cuatro ejemplos del MVP tienen una clase y una acción; el escalón sin registro nunca se atribuye automáticamente a mantenimiento o ataque. |
| 3 | Misael | Ejecutar una ruta completa con datos sintéticos: carga → modelo → fusión → métricas → JSON. | Un solo procedimiento reproduce la misma salida sin intervención manual. |
| 4 | Leo | Sustituir el JSON ficticio por la salida integrada. | El dashboard no calcula cifras oficiales por su cuenta; muestra unidades, sitio, periodo y procedencia. |

**Punto de corte, 20 de octubre al mediodía:** si esta ruta no corre, se detienen las ampliaciones. El equipo corrige interfaces y termina evaluación, cifras y demo antes de añadir modelos o pantallas.

## Fase 2 · 20 de octubre, tarde y 21 de octubre: evidencia

| ID | Dueño | Trabajo | Depende de | Criterio de terminado |
|---|---|---|---|---|
| G2 | Gadiel | Congelar parámetros del detector antes de mirar la evaluación; guardar versión, sitio, periodo de ajuste y calibración. | M1 + G1 | Repetir la ejecución produce las mismas alertas. |
| U2 | Guillermo | Correr la rejilla fija: energía +10/+20/+40/+80 % por 4 h; agua +25/+50 %; escalón sin log; configuración con efecto 8 h después. | U1 + G2 | Manifiesto de inyecciones, ventanas y etiquetas aisladas de las variables del modelo. |
| N2 | Nico | Comparar DripSafe con reglas del kit en los episodios originales, la rejilla y la condición básica de ruido. Calcular curva y falsas alarmas sobre horas limpias. | G2 + U2 | Tabla y curva con TP, FP, FN, latencia y unidades; se reportan resultados desfavorables si los hay. |
| G3 | Gadiel | Medir entrenamiento e inferencia por lotes en la MacBook, diez repeticiones, con tiempo y CodeCarbon; anotar si usa lectura de hardware o estimación. | G2 | Media, dispersión y método de medición; no extrapolar desde una sola inferencia breve. |
| M3 + N3 | Misael + Nico | Calcular el balance neto con el costo aportado por Gadiel y los excesos estimados. Verificar horizontes compatibles y escenarios con balance positivo y negativo. | N2 + G3 | `numeros_oficiales.json` con fuentes, supuestos, unidades y distinción medido/estimado/proyectado. Ambos revisan. |
| N4 | Nico | Preparar acuífero, purga y bono con fuentes verificables; contar horas de respaldo según umbrales climáticos si hay datos adecuados. | Independiente; cifras finales tras N3 | Una lámina que explique el riesgo hídrico y otra el intercambio entre agua y energía, sin presentar el kit como prueba de viabilidad física. |
| U3 | Guillermo | Revisar narrativa OT y límites: intento, cambio, coincidencia e incidente con efecto; revisar que la demo sea de solo lectura. | U2 + N2 | No se afirma que un residuo por sí solo pruebe un ciberataque. |
| L2 | Leo | Integrar curva, clases y cifras oficiales; diseñar diapositivas y recorrido de demo. | N2 + N3 + N4 | Todo número visible coincide con el JSON oficial y cada pantalla indica su procedencia. |
| M4 | Misael | Integración final, revisión de privacidad del kit y ensayo cronometrado. | Todas las piezas MVP | La demo abre y se reproduce en la laptop prevista; las pruebas y el pitch cuentan la misma historia. |

## Reparto permanente

| Persona | Decide sobre | Revisa con | Evitar que se convierta en cuello de botella |
|---|---|---|---|
| **Misael** | Contrato, secuencia de integración, GitHub y calidad de entrega. | Nico en métricas; Gadiel en entrada del modelo. | No asumir la medición en la MacBook ni producir todas las cifras. |
| **Gadiel** | Ajuste del modelo, umbrales y costo computacional. | Nico en evaluación; Misael en contrato. | No hacer dashboard ni justificar el bono. |
| **Nico** | Métricas, comparación, JSON oficial, acuífero y contenido técnico del pitch. | Misael en balance; Guillermo en clases OT. | Primero evaluación y cifras; investigación externa después o en ratos libres. |
| **Guillermo** | Reglas OT, inyecciones y límites de ciberseguridad. | Nico en lógica; Gadiel en residuos disponibles. | Implementar cuatro reglas acotadas, no un detector de tráfico de red. |
| **Leo** | Experiencia de demo y claridad del pitch. | Misael en integración; Nico en significado de cifras. | Trabajar desde el primer día con el JSON de ejemplo. |

## Reglas de entrega entre personas

- Cada tarea se entrega con un ejemplo de entrada, salida, unidades y una forma de ejecutarla; el receptor confirma que la pudo consumir.
- Misael registra cualquier cambio de columnas o rutas en el contrato y avisa a los cuatro antes de integrarlo.
- Gadiel entrega resultados por **sitio y hora**; Guillermo añade la clase y acción; Nico agrega los resultados por **episodio y periodo**; Leo solo los presenta.
- Las etiquetas del kit se usan para separar ajuste, calibración y prueba, y para evaluar; nunca como predictores.
- El kit y sus filas derivadas permanecen fuera de Git. Solo se comparten código, pruebas sintéticas y agregados autorizados.
- Si dos piezas discrepan en una cifra, se corrige el cálculo o el contrato antes de modificar el pitch.

## Decisiones que deben cerrarse antes del primer merge

1. **Repositorio canónico.** Esta copia contiene `dripsafe/` y `dripsafe-reestructura/`; elegir uno para evitar trabajo duplicado.
2. **Contrato v7.** El contrato actual todavía usa columnas de la propuesta anterior. Actualizarlo junto con `docs/11-trabajo-en-paralelo.md`, las decisiones y la propiedad de archivos antes de conectar módulos.
3. **Nombre de la energía.** `energy_total − energy_it` solo puede llamarse energía de enfriamiento si el kit confirma que no incluye otros consumos; en caso contrario, usar **energía no TI**.
4. **Criterio de evaluación.** Definir una alerta verdadera por episodio, no contar cada hora alertada como un caso independiente; fijar de antemano el tratamiento de ventanas superpuestas y de inyecciones sobre anomalías originales.
5. **Estado del dashboard.** La propuesta dice que Leo ya tiene una base, pero no aparece una carpeta `app/` en estas dos copias. Si está en otra rama o equipo, incorporarla al repositorio canónico antes del 20 por la tarde.

## Si el tiempo se reduce

Conservar, en este orden: contrato y exclusión de etiquetas → línea base y umbrales → cuatro clases OT básicas → comparación con reglas fijas → PUE y balance neto → acuífero → demo sencilla. Dejar la cuantificación detallada del bono, CUSUM y pantallas adicionales para cuando todo eso funcione.
