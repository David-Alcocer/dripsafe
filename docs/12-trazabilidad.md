# 12 · Matriz de trazabilidad

> Liga cada requisito de la convocatoria ([01-convocatoria.md](01-convocatoria.md)) con quién lo cubre, en qué issue y con qué evidencia. **Un requisito está cumplido solo cuando su evidencia existe en `main`.** La actualiza Misa al cerrar cada issue.

Estado: ⬜ pendiente · 🟨 en curso · ✅ con evidencia en `main`

## Requisitos de la convocatoria

| § | Requisito | Responsable | Issue | Evidencia esperada | Estado |
|---|---|---|---|---|---|
| 10 | Sub-reto 3: reportar el impacto en **PUE** | Misa | — | `numeros_oficiales.json` → `pue_antes`, `pue_despues` | ⬜ |
| 11 | **Balance neto positivo**, con cifras | Nico + Gadiel | — | `consumo_modelo.json` + `numeros_oficiales.json` → `balance_neto_*` | ⬜ |
| 11 | **Impacto en el acuífero** de Yucatán | Nico | — | Sección en `docs/07` con fuentes citadas | ⬜ |
| 12 | Propuesta de solución sobre el kit | Todos | — | `main` corre de punta a punta con el kit | ⬜ |
| 12 | Pitch final | Nico + Leo | — | Diapositivas en PDF + guion | ⬜ |
| 14 | Bono de cero agua dulce | Nico | — | Sección del bono en `docs/07` con WUE estimado | ⬜ |
| 17 | Kit confidencial | Todos | — | Pruebas automáticas: ningún archivo de datos en el repo | ✅ |
| 18 | Nada de ataques a sistemas reales | Guille | — | Los ataques solo existen como cambios en CSV (`src/ataques/`) | ⬜ |

## Criterios de evaluación (§ 13)

| Criterio | Responsable | Evidencia que lo demuestra | Estado |
|---|---|---|---|
| Innovación | Gadiel + Guille | Detección por coherencia física: ataques que se ven normales pero «no cuadran» | ⬜ |
| Viabilidad técnica | Misa | Un solo comando reproduce todos los números | ⬜ |
| Impacto en ciberseguridad | Guille | `deteccion_por_escenario.csv` + tabla ATT&CK final en `docs/06` | ⬜ |
| Eficiencia Green AI | Misa + Gadiel | PUE antes y después en `numeros_oficiales.json` | ⬜ |
| Balance neto y gobernanza hídrica | Nico | Balance en kWh y litros + análisis del acuífero | ⬜ |
| Escalabilidad y negocio | Nico + Leo | Diapositiva de modelo de negocio | ⬜ |
| Presentación | Leo + Nico | Dos ensayos con cronómetro + video de respaldo | ⬜ |

## Issues iniciales

Se crean en GitHub con la etiqueta de rol y de criterio. Al crearlos, se anota su número en las tablas de arriba.

| Dueño | Issue | Produce |
|---|---|---|
| Misa | Cargar y limpiar el kit; llenar `config/columnas.json` | Contrato 1 |
| Misa | PUE base | `pue_antes` |
| Misa | PUE después y `numeros_oficiales.json` | Contrato 4 |
| Misa | Un solo comando que corre todo el flujo | `python -m src.pipeline` |
| Gadiel | Modelo de consumo esperado del enfriamiento | `kw_esperado_enfriamiento` |
| Gadiel | Isolation Forest v1 | Contrato 3 (`alertas.csv`) |
| Gadiel | Medición con CodeCarbon | `consumo_modelo.json` |
| Gadiel | Explicar cada alerta | `variable_principal` |
| Guille | Escenarios simulados de ataque y falla | Contrato 2 |
| Guille | Evaluación de detección por escenario | `deteccion_por_escenario.csv` |
| Guille | Modelo de amenazas y tabla ATT&CK final | `docs/06` |
| Guille | Cómo se instala el detector sin abrir una puerta nueva | `docs/06` |
| Nico | Análisis del acuífero | `docs/07` |
| Nico | Balance neto en kWh y litros | `balance_neto_*` |
| Nico | Propuesta del bono | `docs/07` |
| Nico | Guion del pitch | `docs/08` |
| Leo | Dashboard v1 con datos sintéticos | `app/` |
| Leo | Dashboard con datos reales y demo de ataque | `app/` |
| Leo | Diapositivas | PDF |
| Leo | Video de respaldo | Video sin conexión |
| Todos | Congelamiento y ensayo del miércoles | Etiqueta `congelado-21` |
