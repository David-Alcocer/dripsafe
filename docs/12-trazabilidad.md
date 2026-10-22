# 12 · Matriz de trazabilidad

> Liga cada requisito de la convocatoria ([01-convocatoria.md](01-convocatoria.md)) con quién lo cubre, en qué issue y con qué evidencia. **Un requisito está cumplido solo cuando su evidencia existe en `main`.** La actualiza Misa al cerrar cada issue.

Estado: ⬜ pendiente · 🟨 en curso · ✅ con evidencia en `main`

**Reparto aprobado en D10, ajustado en D11 y D13 (19 oct), con #13 reasignado a Nico en `678b5ff` (21 oct):** Nico lleva el acuífero (#13) y la evaluación justa del detector (#22), Misa el bono (#15) y Leo el guion (#16). Misa entrega el PUE inicial (#2); Nico calcula el PUE final proyectado y consolida resultados (#3); Misa + Nico validaron el balance neto energético (#14) en el PR #55. Gadiel proporciona las alertas, el consumo esperado y las mediciones del modelo. Esta matriz registra el reparto acordado; los responsables y descripciones de los issues deben reflejarlo también en GitHub.

## Requisitos de la convocatoria

| § | Requisito | Responsable | Issue | Evidencia esperada | Estado |
|---|---|---|---|---|---|
| 10 | Sub-reto 3: reportar el impacto en **PUE** | Misa: inicial; Nico: final proyectado | #2, #3 | `numeros_oficiales.json` → `pue_antes`, `pue_despues` (proyectado) | ✅ PUE 1.278 → 1.268 (proyectado), lámina 13 |
| 11 | **Balance neto positivo**, con cifras | Misa + Nico: cálculo y validación; Gadiel: medición del modelo | #7, #14 | `consumo_modelo.json` v2 (kit, código, equipo, método y kWh por repetición) + `numeros_oficiales.json` → `balance_neto_*`, FESEN 0.444 kgCO₂e/kWh y agua indirecta 2.0632 L/kWh (estimación NREL/CNE), con frecuencia y sin doble conteo | ✅ balance firmado; CO₂ y agua indirecta son proyecciones con fuente |
| 11 | **Impacto en el acuífero** de Yucatán | Nico (ajuste `678b5ff`) | #13 | [`docs/07` §§2–3](07-agua-y-acuifero.md#3-análisis-de-impacto-obligatorio): extracción, presión local, descargas, contaminación, gobernanza y límites; disponibilidad 3105 y exceso simulado en `resultados/numeros_oficiales.json`; contenido de lámina en `docs/n4-entrega-para-leo.md` | ✅ integrado en `main` con el PR #68; láminas 10 y 15 |
| 12 | Propuesta de solución sobre el kit | Todos | #4 | `main` corre de punta a punta con el kit | ✅ `numeros_oficiales.json` firmado; código en `Final/DripSafe_FINAL_Codigo.zip` |
| 12 | Pitch final | Leo (guion y diapositivas) + Nico (cifras) | #16, #19 | Diapositivas en PDF + guion | 🟨 `Final/DripSafe_FINAL_Presentacion.pdf` (19 láminas) y guion en `docs/08`; falta el ensayo con cronómetro (#16) |
| 14 | Bono de cero agua dulce | Misa (D13) | #15 | [`docs/07` §5](07-agua-y-acuifero.md#5-bono-zero-freshwater-footprint-5-a-15) (circuito cerrado, respaldo por aire y PUE proyectado con COP y proxy ERA5) + `src/metricas/refrigeracion.py` | 🟨 escenario calculado en N4; faltan curvas y agua no potable verificadas en sitio |
| 17 | Kit confidencial | Todos | pruebas automáticas | Pruebas automáticas: ningún archivo de datos en el repo | ✅ |
| 18 | Nada de ataques a sistemas reales | Guille | #9 | Los ataques solo existen como cambios en CSV (`src/ataques/`) | ✅ |

## Criterios de evaluación (§ 13)

| Criterio | Responsable | Issues | Evidencia que lo demuestra | Estado |
|---|---|---|---|---|
| Innovación | Gadiel + Nico | #6, #8, #22 | Detector con línea base física por sitio y comparación por episodio frente a las reglas del kit | ✅ bloque `deteccion` del JSON oficial; láminas 3, 4 y 11 |
| Viabilidad técnica | Misa | #1, #4 | Un solo comando reproduce todos los números (`python -m src.pipeline`) | 🟨 balance firmado; factores externos integrados y pendientes de revisión de Misa |
| Impacto en ciberseguridad | Guille | #9–#12, #30, #32 | Tabla de decisión de las 4 clases (`src/ot/clases.py`), rejilla corrida sobre el kit (`src/ataques/correr_rejilla.py`, cifras en `numeros_oficiales.json`), pruebas exploratorias de piso, rampa y calor (`src/ataques/exploratorias.py`) y modelo de amenazas con tabla ATT&CK v20 (`docs/06`) | ✅ integrado (#38–#40). Falta la revisión con un mentor el 22 (#11) |
| Eficiencia Green AI | Nico: impacto y costo del detector; Misa: PUE inicial; Gadiel: consumo esperado | #2, #3, #5, #22 | PUE inicial y final proyectado + tabla calidad frente a costo | ✅ JSON oficial y `g3_consumo_modelo.json`; láminas 12 a 14 |
| Balance neto y gobernanza hídrica | Misa + Nico: balance; Nico: acuífero | #13, #14 | Balance en kWh y litros + [`docs/07` §§2–3](07-agua-y-acuifero.md#3-análisis-de-impacto-obligatorio) + disponibilidad regional del JSON oficial | ✅ balance firmado y análisis hídrico integrado (#68); normas de agua en `docs/13` §7 |
| Escalabilidad y negocio | Leo + Nico | #16 | Diapositiva de modelo de negocio | ✅ láminas 6, 14 y 16; mercado y fuentes en `docs/13` |
| Presentación | Leo + Nico | #17 a #21 | Dos ensayos con cronómetro + video de respaldo | 🟨 video de respaldo listo (#20); falta el ensayo con cronómetro |

## Mapa para la presentación (22 oct · PDF final de 19 láminas)

Qué evalúa el jurado, en qué lámina se ve, qué frase tiene que escucharse y quién contesta si preguntan. Los números de lámina son los del PDF final (`Final/DripSafe_FINAL_Presentacion.pdf`). La lista de `docs/08` usa los del borrador de 11.

**Láminas:**

| Láminas | Contenido |
|---|---|
| 1 | Portada |
| 2 | Problema |
| 3 | Solución |
| 4 | Cuatro clases OT |
| 5 | Demo |
| 6 | Operadores en Mérida |
| 7–10 | Cómo leer los números |
| 11 | Evaluación honesta |
| 12 | Balance neto |
| 13 | Métricas |
| 14 | Costos |
| 15 | Acuífero y bono |
| 16 | Escala y negocio |
| 17 | Límites |
| 18 | Entregables |
| 19 | Cierre |

| Qué evalúan | Láminas | Frase que tiene que escucharse | Contesta |
|---|---|---|---|
| **Obligatorio · balance neto con cifras** | 9, 12 | «El detector gasta 0.000013 kWh al año; el escenario evita 10,768 kWh y 4.8 t de CO₂.» | Nico (Misa) |
| **Obligatorio · impacto en el acuífero** | 2, 10, 15 | «Acuífero kárstico 3105: DripSafe señala captación en exceso; atribuir un beneficio exige conocer el origen del agua y el destino de la purga.» | Nico |
| **Métrica del sub-reto 3 · PUE** | 12, 13 | «PUE 1.278 → 1.268 si se atiende cada alerta física (proyectado).» | Nico |
| 1 · Innovación | 3, 4, 11 | «Línea base por sitio, cruce del registro OT con la física y una rejilla fijada antes de medir.» | Gadiel (detector) · Guille (clases) |
| 2 · Viabilidad técnica | 5, 18 + demo | «Corre en una laptop, sin internet, y un comando reproduce todas las cifras.» | Misa · Leo (demo) |
| 3 · Impacto en ciberseguridad | 4, 5 (SIM-C), 17 | «No afirmamos que un exceso pruebe un ataque: cuatro clases, ATT&CK for ICS v20 y solo lectura.» | Guille |
| 4 · Eficiencia Green AI | 8, 11, 12, 13 | «18 de 18 fallas de +10 % vistas; las reglas, ninguna. El detector tarda 33.6 ms.» | Nico · Gadiel |
| 5 · Balance neto y gobernanza hídrica | 9, 10, 12, 15 | «Balance positivo con menos de 1 ms de exceso al año; registro de captación para compararla con lo concesionado.» | Nico · Guille (normas, `docs/13` §7) |
| 6 · Escalabilidad y negocio | 6, 14, 16 | «Seis medidores, 72 h para aprender, sin nube; $40 MXN por kW al año.» | Leo · Nico |
| 7 · Presentación | todas | Una idea por lámina, cifras con etiqueta (observado, estimado o proyectado) y la demo en modo presentación. | Leo |
| **Bono · Zero Freshwater** (+5 a +15 %) | 13, 15 | «Cero agua potable en obra nueva: circuito cerrado W40, enfriador seco y chiller por aire; PUE proyectado 1.284.» | Misa |

**Reconocimientos especiales:**
- **Ciberseguridad OT:** láminas 4, 5 y 17. Es la carta más distintiva del equipo.
- **Green AI:** láminas 12 y 13.
- **Impacto hídrico:** láminas 10 y 15.

**Incoherencias de texto en las láminas** (se corrigen sin tocar cifras, si Leo lo decide):
1. **Lámina 16, «Qué compra»** dice «reporte para CONAGUA y ESG». `docs/08` ahora aclara que **no se genera ni envía un reporte a CONAGUA**. Propuesta: «registro de captación y excesos para auditoría y ESG».
2. **Lámina 16, «Para quién»** dice «centros de datos de 0.5 MW o más». Choca con la lámina 6, donde los centros de Mérida son chicos; el de KIO declara un UPS de 60 kW (`docs/13` §3). Propuesta: «centros de datos y colocation: pilotos en Mérida, primer cliente de pago en Querétaro».
3. **`Final/DripSafe_FINAL_Evidencias.zip`** trae una copia vieja de esta matriz, con 8 puntos en ⬜. Si la entrega se rehace, conviene regenerarla.

**Riesgo de tiempo:** son 19 láminas para un pitch pensado en unos 5 minutos. Si CIFOX da menos, aplicar los recortes de `docs/08` («Si el tiempo es menor») y dejar las láminas 7 a 10, 13 y 14 como respaldo para las preguntas.

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
