# Contexto para asistentes de IA

> Este archivo resume el proyecto para que cualquier asistente de IA (Claude, ChatGPT, Copilot, Cursor, etc.) entienda el contexto rápido. Los detalles están en `docs/`.

## Proyecto
**DripSafe**: proyecto de un equipo de 5 estudiantes de segundo año de Ingeniería de Software para el **Hackatón CIFOX · AguaSegura AI** (UPY, Mérida, Yucatán, 22 de octubre de 2026).

## Reto
Hacer que la infraestructura de IA (centros de datos) sea más segura, eficiente y responsable con el agua.

## Decisiones clave
- **Sub-reto 3:** detección de anomalías con IA en sistemas de enfriamiento y gestión hídrica. Métrica principal: **PUE**.
- **Modelo:** Isolation Forest (scikit-learn). Ligero y explicable. **Sin LLM** dentro de la solución.
- **Doble uso:** el mismo modelo detecta ineficiencias (ahorro de energía y agua) y posibles manipulaciones de sensores o PLCs (ciberseguridad OT).
- **Demo:** Streamlit.
- **Bono:** enfriamiento híbrido (circuito cerrado + agua residual tratada) para lograr cero agua dulce potable.
- **Git:** trunk-based, con ramas cortas.

## Requisitos obligatorios del hackatón
1. **Balance neto positivo:** la energía y el CO₂ del modelo deben ser menores que el ahorro, con cifras. Se mide con CodeCarbon.
2. **Impacto en el acuífero de Yucatán:** acuífero kárstico, nivel freático somero, cenotes y gobernanza.

## Stack
Python 3.11+, pandas, numpy, scikit-learn, codecarbon, streamlit, plotly y jupyter.

## Restricciones
- El kit de datos (en `data/`) es **confidencial**: nunca subirlo ni compartirlo.
- **Prohibido** atacar sistemas reales. Solo se trabaja con datos del kit o simulados.
- El equipo viene de C++ y está aprendiendo Python: explica el código con claridad y prefiere soluciones simples.

## Reglas de código
- Las piezas se comunican solo por los archivos y columnas de `src/contrato.py` y `docs/11-trabajo-en-paralelo.md`. No inventes columnas ni rutas nuevas: si hace falta una, propón el cambio del contrato.
- El modelo nunca usa columnas `etiqueta_*` (usa `contrato.columnas_del_modelo`).
- Desarrolla y prueba con `src/sinteticos.py`; nunca pongas datos del kit en pruebas, notebooks subidos ni commits.
- Toda cifra que vaya al pitch sale de `resultados/numeros_oficiales.json`.
- Respeta al dueño de cada carpeta (tabla en `docs/11-trabajo-en-paralelo.md`).

## Reparto de métricas aprobado (D10)
- Misa calcula el PUE inicial en `src/metricas/pue.py` y entrega los datos limpios, energía total y de TI, unidades y periodo; conserva la integración.
- Nico calcula ahorro, PUE final proyectado y balance neto, estima agua y emisiones cuando hay datos suficientes y consolida `resultados/numeros_oficiales.json`. El resto de `src/metricas/` es suyo.
- Gadiel entrega alertas, consumo esperado del enfriamiento y mediciones de CodeCarbon; Leo usa los resultados en el dashboard y diseña las diapositivas. Nico prepara el contenido del pitch, el acuífero y el bono.
- Los cálculos siguen pendientes de implementación. Identifica proyecciones y supuestos; el balance positivo se verifica con resultados y las métricas sin datos suficientes quedan pendientes.

## Mapa de la documentación
- `docs/01-convocatoria.md`: reglas y criterios oficiales
- `docs/02-decisiones.md`: decisiones y razones
- `docs/03-equipo-y-roles.md`: roles
- `docs/04-plan-de-trabajo.md`: cronograma
- `docs/05-solucion-tecnica.md`: arquitectura, modelo, métricas y balance neto
- `docs/06-ciberseguridad-ot.md`: OT/ICS y MITRE ATT&CK for ICS
- `docs/07-agua-y-acuifero.md`: acuífero y bono
- `docs/08-pitch.md`: pitch
- `docs/09-recursos.md`: enlaces
- `docs/10-faq.md`: preguntas frecuentes
- `docs/11-trabajo-en-paralelo.md`: contratos de datos, dueños y trazabilidad
- `docs/12-trazabilidad.md`: requisito → responsable → issue → evidencia
