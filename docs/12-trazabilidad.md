# 12 · Matriz de trazabilidad

> Liga cada requisito de la convocatoria ([01-convocatoria.md](01-convocatoria.md)) con quién lo cubre, en qué issue y con qué evidencia. **Un requisito está cumplido solo cuando su evidencia existe en `main`.** La actualiza Misa al cerrar cada issue.

Estado: ⬜ pendiente · 🟨 en curso · ✅ con evidencia en `main`

**Reparto aprobado en D10, ajustado en D11 y D13 (19 oct), con #13 reasignado a Nico en `678b5ff` (21 oct):** Nico lleva el acuífero (#13) y la evaluación justa del detector (#22), Misa el bono (#15) y Leo el guion (#16). Misa entrega el PUE inicial (#2); Nico calcula el PUE final proyectado y consolida resultados (#3); Misa + Nico validaron el balance neto energético (#14) en el PR #55. Gadiel proporciona las alertas, el consumo esperado y las mediciones del modelo. Esta matriz registra el reparto acordado; los responsables y descripciones de los issues deben reflejarlo también en GitHub.

## Requisitos de la convocatoria

| § | Requisito | Responsable | Issue | Evidencia esperada | Estado |
|---|---|---|---|---|---|
| 10 | Sub-reto 3: reportar el impacto en **PUE** | Misa: inicial; Nico: final proyectado | #2, #3 | `numeros_oficiales.json` → `pue_antes`, `pue_despues` (proyectado) | ⬜ |
| 11 | **Balance neto positivo**, con cifras | Misa + Nico: cálculo y validación; Gadiel: medición del modelo | #7, #14 | `consumo_modelo.json` v2 (kit, código, equipo, método y kWh por repetición) + `numeros_oficiales.json` → `balance_neto_*` con frecuencia y sin doble conteo | ⬜ |
| 11 | **Impacto en el acuífero** de Yucatán | Nico (ajuste `678b5ff`) | #13 | Sección en `docs/07` con fuentes citadas | ⬜ |
| 12 | Propuesta de solución sobre el kit | Todos | #4 | `main` corre de punta a punta con el kit | ⬜ |
| 12 | Pitch final | Leo (guion y diapositivas) + Nico (cifras) | #16, #19 | Diapositivas en PDF + guion | ⬜ |
| 14 | Bono de cero agua dulce | Misa (D13) | #15 | [`docs/07` §5](07-agua-y-acuifero.md#5-bono-zero-freshwater-footprint-5-a-15) (circuito cerrado, respaldo por aire y PUE proyectado con COP y proxy ERA5) + `src/metricas/refrigeracion.py` | 🟨 escenario calculado en N4; faltan curvas y agua no potable verificadas en sitio |
| 17 | Kit confidencial | Todos | pruebas automáticas | Pruebas automáticas: ningún archivo de datos en el repo | ✅ |
| 18 | Nada de ataques a sistemas reales | Guille | #9 | Los ataques solo existen como cambios en CSV (`src/ataques/`) | ✅ |

## Criterios de evaluación (§ 13)

| Criterio | Responsable | Issues | Evidencia que lo demuestra | Estado |
|---|---|---|---|---|
| Innovación | Gadiel + Nico | #6, #8, #22 | Detector con línea base física por sitio y comparación por episodio frente a las reglas del kit | ⬜ |
| Viabilidad técnica | Misa | #1, #4 | Un solo comando reproduce todos los números (`python -m src.pipeline`) | 🟨 balance y supuestos preparados para revisión; falta firma conjunta (#14) |
| Impacto en ciberseguridad | Guille | #9–#12, #30, #32 | Tabla de decisión de las 4 clases (`src/ot/clases.py`), rejilla corrida sobre el kit (`src/ataques/correr_rejilla.py`, cifras en `numeros_oficiales.json`), pruebas exploratorias de piso, rampa y calor (`src/ataques/exploratorias.py`) y modelo de amenazas con tabla ATT&CK v20 (`docs/06`) | ✅ integrado (#38–#40). Falta la revisión con un mentor el 22 (#11) |
| Eficiencia Green AI | Nico: impacto y costo del detector; Misa: PUE inicial; Gadiel: consumo esperado | #2, #3, #5, #22 | PUE inicial y final proyectado + tabla calidad frente a costo | ⬜ |
| Balance neto y gobernanza hídrica | Misa + Nico: balance; Nico: acuífero | #13, #14 | Balance en kWh y litros + análisis del acuífero | ⬜ |
| Escalabilidad y negocio | Leo + Nico | #16 | Diapositiva de modelo de negocio | ⬜ |
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
| #6 | Gadiel | Detector por sitio: línea base, umbrales y media móvil (alcance D20) | Contrato 3 (`alertas.csv`) |
| #7 | Gadiel | Medición con CodeCarbon | `consumo_modelo.json` |
| #8 | Gadiel | Explicar cada alerta | `variable_principal` + `tipo_sugerido` en `alertas.csv` (`src/modelo/explicar.py`, reglas en [`docs/05`](05-solucion-tecnica.md#cómo-se-explica-cada-alerta-8)); `clasificacion_correcta_pct` en `src/ataques/evaluar.py` y en la rejilla (`rejilla_por_inyeccion.csv`) |
| #9 | Guille | Escenarios simulados de ataque y falla | Contrato 2 |
| #10 | Guille | Evaluación de detección por escenario | `rejilla_por_inyeccion.csv` + bloque `deteccion` (lo cubren #30 y #32) |
| #11 | Guille | Modelo de amenazas y tabla ATT&CK final | `docs/06` §2–§3 + `docs/img/modelo-amenazas-purdue.svg` |
| #12 | Guille | Cómo se instala el detector sin abrir una puerta nueva | `docs/06` |
| #13 | Nico | Análisis del acuífero | `docs/07` |
| #14 | Misa + Nico | Balance neto final energético y, con datos suficientes, hídrico y de emisiones | `balance_neto_*` + fuentes, periodo y supuestos |
| #15 | Misa | Comparación de refrigeración y propuesta del bono | `docs/07` |
| #16 | Leo | Guion del pitch (cifras de Nico) | `docs/08` |
| #17 | Leo | Dashboard v1 con datos sintéticos | `app/` |
| #18 | Leo | Dashboard con datos reales y demo de ataque | `app/` |
| #19 | Leo | Diapositivas | PDF |
| #20 | Leo | Video de respaldo | Video sin conexión |
| #21 | Todos | Congelamiento y ensayo del miércoles | Etiqueta `congelado-21` |
| #30 | Guille | U1 · Tabla de decisión de las 4 clases OT + inyector de la rejilla | `src/ot/clases.py`, `src/ataques/rejilla.py`, `docs/06` §4–§5 |
| #32 | Guille | U2 · Correr la rejilla contra el detector congelado | `src/ataques/correr_rejilla.py` → `deteccion_para_numeros_oficiales.json` (insumo de N2) |

### Issues nuevos propuestos tras el kit (crear en GitHub)

| # | Dueño | Issue | Produce |
|---|---|---|---|
| #22 | Nico | Evaluación justa y Green AI: detector vigente frente a reglas del kit, por episodio y con varias corridas | Tabla calidad frente a costo + `numeros_oficiales.json` |
| #23 | Misa | Contrato v2 adaptado al kit (D14) | PR que cambia doc 11, `src/contrato.py` y `config/columnas.json` |
| — | Guille | Mapear las etiquetas del kit a `etiqueta_*` y separar escenarios del kit de los nuestros | Cubierto: `src/datos/cargar.py` (#1) mapea las etiquetas y la rejilla (#30) marca cada episodio como `origen=kit` u `origen=inyeccion` |

Los números #22–#24 son tentativos: usar los que asigne GitHub y actualizar esta tabla.
