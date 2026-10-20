# 04 · Plan de trabajo por dependencias (19–21 oct)

> **Base:** [00-propuesta.md](00-propuesta.md) (v7) y [00-plan-ejecucion.md](00-plan-ejecucion.md). **Regla de oro:** el 22 solo se pule y se presenta. El 21 a las 20:00 la demo ya corre de punta a punta.

Este plan reemplaza el día-por-día anterior. Está organizado por **dependencias**, no por fechas, para que nadie espere a nadie y la integración ocurra en pasos verificables.

## Qué entregamos (MVP)

1. **Carga y validación** de telemetría y registro OT, sin que las etiquetas lleguen al modelo.
2. **Línea base aprendida por sitio** para energía no TI, agua y temperatura de entrada; residuos, umbrales y media móvil de 4 h.
3. **Cuatro clases de alerta OT:** incidente con efecto, cambio no autorizado, escalón sin registro e intento de acceso.
4. **Comparación contra reglas fijas del kit:** casos originales, rejilla de inyecciones y prueba básica de ruido.
5. **PUE/WUE, exceso estimado** (kWh y L), costo del detector, balance neto y análisis del acuífero, todo con procedencia y supuestos.
6. **Dashboard y pitch** alimentados por el JSON oficial, con ruta de demo que funcione sin kit.

**Ampliaciones (no bloquean el MVP):** Isolation Forest con ablación, CUSUM, incoherencia física, deriva, cola por litros, pantallas extra.

## Flujo de dependencias

```text
Contrato de datos + JSON de ejemplo (Misael)
    ├── Modelo y residuos (Gadiel) ──┐
    ├── Eventos, reglas e inyecciones (Guillermo) ──┤
    ├── Métricas y evaluación (Nico) ───────────────┤→ Integración (Misael) → cifras oficiales → dashboard (Leo) → pitch
    └── Dashboard con datos de ejemplo (Leo) ───────┘
```

Cada quien puede desarrollar con ejemplos sintéticos aislados, pero **Misael publica el contrato definitivo antes de integrar**. El mapeo de columnas ocurre una sola vez al cargar los datos, no en cada módulo.

## Fase 0 · Hoy, 19 de octubre: trabajo independiente

| ID | Dueño | Trabajo | Entregable verificable | Prioridad |
|---|---|---|---|---|
| **M1** | Misael | Comparar columnas del kit con `src/contrato.py`; acordar unidades, zona horaria, granularidad, sitio, ausentes y formato OT. Renombrar `scenario`, `simulated_anomaly` y `split` a `etiqueta_*` **al cargar**, con prueba que impida que las etiquetas entren al modelo. | Contrato actualizado, adaptador de carga, prueba de exclusión de etiquetas. | **Bloqueante** |
| **M2** | Misael | Definir con Nico y Leo la forma de `resultados/numeros_oficiales.json` + ejemplo con valores ficticios marcados como tales. Planear orden de integración. | JSON de ejemplo validado por los cinco. | **Bloqueante** |
| **G1** | Gadiel | Funciones puras por sitio: partición 48/24, regresión, predicción, residuos, umbral individual y MM 4 h. Ejemplo sintético ejecutable en CPU. | Tabla por sitio y hora con `esperado`, `real`, `residuo`, `bandera`. | **MVP** |
| **U1** | Guillermo | Tabla de decisión de las 4 clases OT, precedencia, ventana de 24 h y casos ambiguos. Adaptar el inyector a la rejilla fija de la propuesta sobre copias de datos simulados. | Casos inyectados reproducibles con semilla + reglas unitarias. | **MVP** |
| **N1** | Nico | Funciones de métricas sobre tablas: PUE/WUE como cocientes de sumas, exceso estimado, reglas fijas comparables, TP/FP/FN **por episodio**, horas hasta detectar. | Cálculos reproducibles sobre datos sintéticos; definición clara de episodio y falsa alarma. | **MVP** |
| **L1** | Leo | Guardar el dashboard actual aparte; diseñar la pantalla con el JSON de ejemplo: real vs esperado, alertas, curva de sensibilidad, escenario anual editable. Marcar `medido/estimado/proyectado`. | Demo navegable con datos de ejemplo y estados vacíos. | **MVP** |

**Cierre de Fase 0:** Misael publica un ejemplo de entrada y uno de salida. Los otros cuatro confirman que sus módulos los pueden leer. Si el kit aún no está, se mantiene la interfaz con sintéticos; no se paraliza nadie.

## Fase 1 · 20 de octubre, mañana: primera integración

| Orden | Responsable | Acción | Criterio de terminado |
|---|---|---|---|
| 1 | Misael + Gadiel | Conectar adaptador de datos al modelo. | Los 3 sitios se entrenan con referencia limpia; **ninguna columna `etiqueta_*`** entra al ajuste ni a la predicción. |
| 2 | Nico + Guillermo | Conectar residuos y eventos OT con las 4 clases. | Los 4 ejemplos del MVP tienen clase y acción; el escalón sin registro **nunca** se atribuye automáticamente a mantenimiento o ataque. |
| 3 | Misael | Ejecutar la ruta completa con sintéticos: carga → modelo → fusión → métricas → JSON. | Un solo procedimiento reproduce la misma salida sin intervención manual. |
| 4 | Leo | Sustituir el JSON ficticio por la salida integrada. | El dashboard **no calcula cifras oficiales**; muestra unidades, sitio, periodo y procedencia. |

### 🛑 Punto de corte: 20 de octubre al mediodía

**Si esta ruta no corre a mediodía, se detienen las ampliaciones.** El equipo corrige interfaces y termina evaluación, cifras y demo antes de añadir modelos o pantallas.

## Fase 2 · 20 de octubre tarde + 21 de octubre: evidencia

| ID | Dueño | Trabajo | Depende de | Criterio de terminado |
|---|---|---|---|---|
| **G2** | Gadiel | Congelar parámetros del detector antes de mirar la evaluación; guardar versión, sitio, periodo de ajuste y calibración. | M1 + G1 | Repetir la ejecución produce las mismas alertas. |
| **U2** | Guillermo | Correr la rejilla fija: energía +10/+20/+40/+80 % × 4 h; agua +25/+50 %; escalón sin log; config con efecto 8 h después. | U1 + G2 | Manifiesto de inyecciones, ventanas y etiquetas aisladas de las variables del modelo. |
| **N2** | Nico | Comparar DripSafe vs reglas del kit: episodios originales, rejilla y condición básica de ruido. Curva y falsas alarmas sobre horas limpias. | G2 + U2 | Tabla con TP, FP, FN, latencia y unidades; se reportan resultados desfavorables si los hay. |
| **G3** | Gadiel | Medir entrenamiento e inferencia en la MacBook, 10 repeticiones con tiempo y CodeCarbon. | G2 | Media, dispersión y método (hardware o estimación); no extrapolar desde una inferencia breve. |
| **M3 + N3** | Misael + Nico | Balance neto con costo de Gadiel y excesos estimados. Horizontes compatibles y escenarios positivo/negativo. | N2 + G3 | `numeros_oficiales.json` con fuentes, supuestos, unidades y `medido/estimado/proyectado`. Ambos revisan. |
| **N4** | Nico | Acuífero, purga y bono con fuentes verificables; horas de respaldo según umbrales climáticos. | Independiente; cifras finales tras N3 | Una lámina para riesgo hídrico y otra para el intercambio agua↔energía. |
| **U3** | Guillermo | Revisar narrativa OT y límites: `intento`, `cambio`, `coincidencia`, `incidente con efecto`; demo de solo lectura. | U2 + N2 | No se afirma que un residuo por sí solo pruebe un ciberataque. |
| **L2** | Leo | Integrar curva, clases y cifras oficiales; diseñar diapositivas y recorrido de demo. | N2 + N3 + N4 | Todo número visible coincide con el JSON oficial. |
| **M4** | Misael | Integración final, revisión de privacidad del kit y ensayo cronometrado. | Todas las piezas MVP | La demo abre y se reproduce en la laptop prevista; pruebas y pitch cuentan la misma historia. |

## Reparto permanente

| Persona | Decide sobre | Revisa con | Evitar que sea cuello de botella |
|---|---|---|---|
| **Misael** | Contrato, secuencia de integración, GitHub, calidad. | Nico (métricas); Gadiel (entrada del modelo). | No asumir medición en la MacBook ni producir todas las cifras. |
| **Gadiel** | Ajuste del modelo, umbrales, costo computacional. | Nico (evaluación); Misael (contrato). | No hacer dashboard ni justificar el bono. |
| **Nico** | Métricas, comparación, JSON oficial, acuífero, contenido técnico del pitch. | Misael (balance); Guillermo (clases OT). | Primero evaluación y cifras; investigación externa después. |
| **Guillermo** | Reglas OT, inyecciones, límites de ciberseguridad. | Nico (lógica); Gadiel (residuos). | 4 reglas acotadas, no un detector de tráfico de red. |
| **Leo** | Experiencia de demo y claridad del pitch. | Misael (integración); Nico (significado de cifras). | Trabajar desde el primer día con el JSON de ejemplo. |

## Reglas de entrega entre personas

- Cada tarea se entrega con **ejemplo de entrada**, **salida**, **unidades** y **forma de ejecutarla**; el receptor confirma que la pudo consumir.
- Misael registra cualquier cambio de columnas o rutas en el contrato y avisa a los cuatro antes de integrarlo.
- Gadiel entrega resultados **por sitio y hora**; Guillermo añade la **clase y acción**; Nico agrega resultados **por episodio y periodo**; Leo solo los presenta.
- Las etiquetas del kit sirven para separar ajuste/calibración/prueba y evaluar; **nunca como predictores**.
- El kit y sus filas derivadas permanecen fuera de Git. Solo código, pruebas sintéticas y agregados autorizados.
- Si dos piezas discrepan en una cifra, se corrige el cálculo o el contrato **antes** de modificar el pitch.

## Si el tiempo se reduce

Conservar en este orden:

1. Contrato y exclusión de etiquetas
2. Línea base y umbrales
3. 4 clases OT básicas
4. Comparación con reglas fijas
5. PUE y balance neto
6. Acuífero
7. Demo sencilla

Dejar fuera: cuantificación detallada del bono, Isolation Forest, CUSUM, pantallas adicionales.

---

## Jueves 22: UPY (presentación)

| Hora | Qué hacemos |
|---|---|
| 08:00 | Llegar con la demo probada en la laptop que se va a usar |
| 09:00–09:30 | Validación de avance: sub-reto, datos explorados y prototipo corriendo |
| 09:30–15:30 | Pulir demo, ajustar cifras y **validar con mentores** (sobre todo ciberseguridad) |
| 15:30–16:00 | Ensayar el pitch dos veces |
| 16:00–17:30 | Pitch, demo en vivo y video como respaldo |
| 17:30–18:30 | Jueces, aliados y premiación |

**Checklist para llevar:**
- [ ] Laptop con la demo, cargador y extensión eléctrica.
- [ ] Video de respaldo guardado sin depender de internet.
- [ ] Diapositivas en PDF, también sin conexión.
- [ ] Repo clonado y actualizado.
- [ ] `numeros_oficiales.json` impreso o en pantalla para consultar con mentores.
