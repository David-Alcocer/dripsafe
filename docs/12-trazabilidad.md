# 12 · Matriz de trazabilidad

> Liga cada requisito de la convocatoria ([01-convocatoria.md](01-convocatoria.md)) con quién lo cubre, en qué issue y con qué evidencia. **Un requisito está cumplido solo cuando su evidencia existe en `main`.** La actualiza Misa al cerrar cada issue.

Estado: ⬜ pendiente · 🟨 en curso · ✅ con evidencia en `main`

**Reparto aprobado en D10:** Misa entrega el PUE inicial (#2); Nico calcula el PUE final proyectado y consolida resultados (#3), además del balance neto (#14). Gadiel proporciona las alertas, el consumo esperado y las mediciones del modelo. Los cálculos siguen pendientes de implementación. Esta matriz registra el reparto acordado; los responsables y descripciones de los issues deben reflejarlo también en GitHub.

## Requisitos de la convocatoria

| § | Requisito | Responsable | Issue | Evidencia esperada | Estado |
|---|---|---|---|---|---|
| 10 | Sub-reto 3: reportar el impacto en **PUE** | Misa: inicial; Nico: final proyectado | #2, #3 | `numeros_oficiales.json` → `pue_antes`, `pue_despues` (proyectado) | ⬜ |
| 11 | **Balance neto positivo**, con cifras | Nico: cálculo; Gadiel: medición del modelo | #7, #14 | `consumo_modelo.json` + `numeros_oficiales.json` → `balance_neto_*`, con fuentes y supuestos | ⬜ |
| 11 | **Impacto en el acuífero** de Yucatán | Nico | #13 | Sección en `docs/07` con fuentes citadas | ⬜ |
| 12 | Propuesta de solución sobre el kit | Todos | #4 | `main` corre de punta a punta con el kit | ⬜ |
| 12 | Pitch final | Nico + Leo | #16, #19 | Diapositivas en PDF + guion | ⬜ |
| 14 | Bono de cero agua dulce | Nico | #15 | Sección del bono en `docs/07` con WUE estimado | ⬜ |
| 17 | Kit confidencial | Todos | pruebas automáticas | Pruebas automáticas: ningún archivo de datos en el repo | ✅ |
| 18 | Nada de ataques a sistemas reales | Guille | #9 | Los ataques solo existen como cambios en CSV (`src/ataques/`) | ✅ |

## Criterios de evaluación (§ 13)

| Criterio | Responsable | Issues | Evidencia que lo demuestra | Estado |
|---|---|---|---|---|
| Innovación | Gadiel + Guille | #6, #8 | Detección por coherencia física: ataques que se ven normales pero «no cuadran» | ⬜ |
| Viabilidad técnica | Misa | #1, #4 | Un solo comando reproduce todos los números | ⬜ |
| Impacto en ciberseguridad | Guille | #9, #10, #11, #12 | `deteccion_por_escenario.csv` + tabla ATT&CK final en `docs/06` | ⬜ |
| Eficiencia Green AI | Nico: impacto; Misa: PUE inicial; Gadiel: consumo esperado | #2, #3, #5 | PUE inicial y final proyectado en `numeros_oficiales.json` | ⬜ |
| Balance neto y gobernanza hídrica | Nico | #13, #14 | Balance en kWh y litros + análisis del acuífero | ⬜ |
| Escalabilidad y negocio | Nico + Leo | #16 | Diapositiva de modelo de negocio | ⬜ |
| Presentación | Leo + Nico | #17 a #21 | Dos ensayos con cronómetro + video de respaldo | ⬜ |

## Issues iniciales

Creados en GitHub el 19 de octubre, cada uno con su etiqueta `rol:*` y sus etiquetas `criterio:*`.

| # | Dueño | Issue | Produce |
|---|---|---|---|
| #1 | Misa | Cargar y limpiar el kit; llenar `config/columnas.json` | Contrato 1 |
| #2 | Misa | PUE inicial y entrega de datos, energías, unidades y periodo a Nico | `pue_antes` y referencia de cálculo |
| #3 | Nico | Ahorro energético, PUE final proyectado y consolidación de `numeros_oficiales.json` | Contrato 4 + ejemplo reproducible |
| #4 | Misa | Un solo comando que corre todo el flujo | `python -m src.pipeline` |
| #5 | Gadiel | Modelo de consumo esperado del enfriamiento | `kw_esperado_enfriamiento` |
| #6 | Gadiel | Isolation Forest v1 | Contrato 3 (`alertas.csv`) |
| #7 | Gadiel | Medición con CodeCarbon | `consumo_modelo.json` |
| #8 | Gadiel | Explicar cada alerta | `variable_principal` |
| #9 | Guille | Escenarios simulados de ataque y falla | Contrato 2 |
| #10 | Guille | Evaluación de detección por escenario | `deteccion_por_escenario.csv` |
| #11 | Guille | Modelo de amenazas y tabla ATT&CK final | `docs/06` |
| #12 | Guille | Cómo se instala el detector sin abrir una puerta nueva | `docs/06` |
| #13 | Nico | Análisis del acuífero | `docs/07` |
| #14 | Nico | Balance neto energético y, con datos suficientes, hídrico y de emisiones | `balance_neto_*` + fuentes, periodo y supuestos |
| #15 | Nico | Propuesta del bono | `docs/07` |
| #16 | Nico | Guion del pitch | `docs/08` |
| #17 | Leo | Dashboard v1 con datos sintéticos | `app/` |
| #18 | Leo | Dashboard con datos reales y demo de ataque | `app/` |
| #19 | Leo | Diapositivas | PDF |
| #20 | Leo | Video de respaldo | Video sin conexión |
| #21 | Todos | Congelamiento y ensayo del miércoles | Etiqueta `congelado-21` |
