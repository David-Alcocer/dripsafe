# 02 · Decisiones tomadas y por qué

> Registro de las decisiones del equipo. D20 recoge la decisión vigente sobre el detector; las propuestas anteriores se conservan solo como historial.

## D1 · Sub-reto 3: detección de anomalías con IA ✅

**Decisión:** sub-reto 3, con **PUE** como métrica principal.

**Por qué:**
- Somos 5 estudiantes de Ingeniería de Software: construir un modelo y una demo es nuestro fuerte.
- Un mismo detector de anomalías cubre **los dos lados del reto**:
  - **Agua y energía:** detecta ineficiencias en el enfriamiento → baja el PUE.
  - **Ciberseguridad:** detecta lecturas o comandos que no cuadran con la física del sistema → posible manipulación.
- Así sumamos en "Eficiencia Green AI" **y** en "Impacto en ciberseguridad" sin hacer dos proyectos.

**Pendiente:** confirmarla al leer el kit el 19. Si los datos del sub-reto 3 vinieran muy incompletos, lo platicamos.

## D2 · Modelo ligero, hecho por nosotros (histórico; sustituido por D20)

La propuesta inicial contemplaba un modelo de bosque de anomalías. El equipo lo descartó el 20 de octubre. La arquitectura vigente y el alcance de N2 están en D20.

## D3 · Demo en Streamlit, no Grafana ✅

**Decisión:** dashboard en **Streamlit**.

**Por qué:**
- Es Python, así que se conecta directo con el modelo.
- Se arma en horas.
- Grafana se ve muy "industrial", pero requiere una base de datos de series de tiempo (InfluxDB o Prometheus) o plugins, y duplicaría el trabajo de la demo.
- **Grafana no da puntos extra.** Los jueces califican qué hace la solución y sus números.

**Grafana queda como extra opcional** solo si a Guille le sobra tiempo el 21.

## D4 · Ir por el bono de cero agua dulce ✅

**Decisión:** proponer un **enfriamiento híbrido**:
- **Base:** enfriamiento líquido en circuito cerrado. El refrigerante recircula y casi no se repone agua.
- **Respaldo en picos de calor:** agua residual tratada, no potable.
- **Conexión con nuestra IA:** el modelo **recomienda** cuándo activar el respaldo y el operador lo confirma. La IA nunca manda órdenes al enfriamiento: si pudiera, quien engañe al modelo controlaría la planta (ver «Cómo se instala DripSafe sin abrir una puerta nueva» en [06-ciberseguridad-ot.md](06-ciberseguridad-ot.md)). *Ajuste aprobado por Guille el 19 oct.*

**Por qué:** el bono suma de 5% a 15% a la calificación final y puede definir el primer lugar. El enfriamiento por aire solo, en el clima cálido y húmedo de Yucatán, sube el consumo de energía y por lo tanto el PUE.

## D5 · Cubrir ciberseguridad con lo justo ✅

**Contexto:** nadie del equipo tiene experiencia fuerte en ciberseguridad. Guille es quien más sabe (Linux, SSH keys, ufw, Fail2ban).

**Decisión:** no prometer una solución completa de seguridad. Presentar el modelo como **primera capa de detección** y mapear de 3 a 4 técnicas de ataque de MITRE ATT&CK for ICS que detectaría.

**Por qué:** el criterio "Impacto en ciberseguridad" lo califican a todos. Con esto evitamos sacar cero en él, sin desviarnos del sub-reto. El 22 hay mentores en sitio para validar.

## D6 · Flujo de Git: trunk-based ✅

**Decisión:** **trunk-based development** con ramas cortas (de horas) y PR rápidos a `main`. `git worktree` es **opcional**, recomendado para quien trabaje con Claude o la terminal (Misa y Guille). Ver [CONTRIBUTING.md](../CONTRIBUTING.md).

**Por qué no git flow:** en 3 días las ramas largas solo generan conflictos.

## D7 · Nombre del proyecto ✅

**DripSafe**: juega con "goteo" (agua) y "seguro" (ciberseguridad).

## D8 · Piezas conectadas por contratos de datos (propuesta de Guille, por aprobar)

**Decisión:** cada quien es dueño de una carpeta y las piezas se comunican solo por archivos con columnas fijas. Mientras el kit no esté limpio, todos trabajan con datos sintéticos del mismo formato. Ver [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

**Por qué:** en 3 días nadie puede esperar a nadie. Si el formato está fijo desde hoy, el modelo, los ataques simulados, las métricas y el dashboard avanzan al mismo tiempo y se unen el martes sin sorpresas.

## D9 · Una sola fuente para las cifras del pitch (propuesta de Guille, por aprobar)

**Decisión:** `resultados/numeros_oficiales.json` es la única fuente de las cifras del dashboard, las diapositivas y el pitch. Se sube al repo porque solo trae totales, nunca filas del kit.

**Por qué:** si el dashboard dice un PUE y la diapositiva otro, el jurado deja de creer todos los números. Además, Git guarda el historial de cada cifra.

## D10 · Misa entrega el PUE inicial; Nico calcula el impacto posterior ✅

**Ajuste vigente D11:** el balance neto final queda a cargo de Misa + Nico. El reparto actualizado se detalla a continuación.

**Decisión aprobada por el equipo:** Misa entrega el PUE inicial, la telemetría limpia y las energías total y de TI, con unidades y periodo. Conserva el cálculo base en `src/metricas/pue.py`, el repositorio y la integración.

Nico calcula el ahorro energético, el PUE final proyectado y el impacto en agua y emisiones cuando los datos lo permitan. Misa + Nico calculan y validan juntos el balance neto final en `src/metricas/balance_neto.py` (pendiente de implementación). Nico es responsable del resto de `src/metricas/`, salvo el PUE inicial de Misa, y de consolidar `resultados/numeros_oficiales.json`. Gadiel aporta alertas, consumo esperado y mediciones de CodeCarbon; Leo integra las cifras en la demo y diseña las diapositivas.

Nico conserva el análisis del acuífero, la propuesta del bono y el contenido y modelo de negocio del pitch. Su entregable incluye un programa en Python, un ejemplo reproducible y resultados con fuentes y supuestos.

**Tareas:** #2 sigue con Misa, #3 pasa a Nico y #14 queda compartida entre Misa + Nico (ajuste D11). Los cálculos siguen pendientes de implementación. El PUE final y los ahorros se presentan como proyecciones hasta tener evidencia medida; un balance positivo debe comprobarse.

**Por qué:** deja claro quién entrega la referencia y quién transforma esa referencia en cifras de impacto. Este acuerdo actualiza los responsables descritos en D8 y D9; esas propuestas conservan su estado pendiente de aprobación.

## D11 · Balance neto final compartido entre Misa + Nico ✅

**Decisión:** Misa + Nico calculan y validan juntos el balance neto final (#14), usando el ahorro estimado por Nico y el consumo del modelo medido por Gadiel. Comparten la responsabilidad del módulo previsto `src/metricas/balance_neto.py`.

**Por qué:** el balance final se construye entre ambos, con unidades, periodos y supuestos acordados. Misa conserva el PUE inicial; Nico conserva el ahorro, el PUE final proyectado, las estimaciones de agua y emisiones y la consolidación de resultados. Este ajuste actualiza D10.

## D12 · El kit cambia el enfoque del modelo (19 oct; actualizado por D20)

El kit contiene tres sitios simulados con 168 horas por sitio, datos de energía, agua, carga, temperaturas y eventos OT; las etiquetas solo sirven para evaluación. No hay sensores por equipo. Las reglas didácticas del kit detectan sus anomalías originales. El equipo decidió comparar el detector propio contra esas reglas por episodio y con inyecciones adicionales. La decisión final sobre el detector está en D20.

## D13 · Reparto ajustado: Nico se suma al modelo ✅ (19 oct)

**Decisión:**
- **Gadiel** construye el detector por sitio (#5, #6, #8) y mide su consumo con CodeCarbon (#7).
- **Nico** se encarga de la **evaluación justa y Green AI** (costo frente a calidad del detector), del ahorro y el PUE final proyectado (#3), de consolidar `numeros_oficiales.json` y del balance neto con Misa (#14). **Deja** el acuífero, el bono y el guion.
- **Guille** conserva ciberseguridad (#9–#12) y **toma el acuífero y la gobernanza** (#13).
- **Misa** conserva datos, PUE inicial e integración (#1, #2, #4), el balance neto con Nico (#14), y **toma la comparación de refrigeración y el bono** (#15). Es el reto 3 del kit.
- **Leo** conserva dashboard, diapositivas y video (#17–#20) y **toma el guion del pitch** (#16). Nico le aporta las cifras.

**Por qué:** Nico es fuerte en algoritmos y el balance neto depende directamente del modelo. El kit resultó pequeño (504 filas, sin sensores por equipo), así que la parte de datos de Misa y la de OT de Guille son más ligeras de lo previsto y pueden absorber el bono y el acuífero.

**Para no pisarse en el modelo:** Gadiel **construye** el detector; Nico lo **mide y lo pone a prueba**. La interfaz entre ambos es el Contrato 3 (`alertas.csv` + `consumo_modelo.json`).

## D14 · Contrato v2 adaptado al kit real ✅ (19 oct, por confirmar en PR)

**Problema:** `src/contrato.py` supone un solo sitio, potencias en kW y sensores por equipo. El kit tiene **3 sitios por cada hora**, energía en kWh por intervalo y otras columnas. Con el contrato actual, `validar()` fallaría por dos razones: el `timestamp` se repite por sitio y aparecen columnas fuera del contrato.

**Propuesta:**

| Kit | Contrato | Nota |
|---|---|---|
| `timestamp` | `timestamp` | UTC, intervalo de 1 h |
| `energy_it_kwh` | `kw_ti` | Con intervalo de 1 h, kWh por intervalo = kW promedio |
| `energy_total_kwh` | `kw_total` | Igual |
| `outdoor_temp_c` | `t_exterior` | |
| `water_l` | `agua_reposicion_l` | Es **captación in situ**, no reposición exacta de la torre: declararlo |
| `site_id`, `cooling_type`, `load_pct`, `inlet_temp_c`, `ot_event` | **nuevas** columnas opcionales | |
| `split` | `etiqueta_particion` | referencia → entrenamiento; evaluacion → evaluacion |
| `scenario` | `etiqueta_escenario` | |
| `scenario` (derivada) | `etiqueta_tipo` | base → normal; ineficiencia y fuga_agua → falla; evento_ot → `evento_ot` (el kit advierte que un login fallido **no prueba** un ataque) |
| `simulated_anomaly`, `is_simulated` | no entran | Solo para evaluar y para el aviso de simulación |

- `validar()` debe revisar el orden por **(site_id, timestamp)** y no globalmente.
- Los escenarios de `src/ataques/` que requieren columnas que el kit no trae (chiller, temperaturas del agua, caudal) **siguen funcionando con los sintéticos**. Sobre el kit solo se inyectan los que tengan sus columnas disponibles, y se distinguen los escenarios **del kit** de los **nuestros**.

**Cómo se aprueba:** un PR que cambie a la vez [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md), `src/contrato.py` y `config/columnas.json`, con el visto bueno de todos. Responsable: Misa. Revisa: Gadiel.

**Implementado en:** rama `feat/datos-kit-v2`, cierra #1. Incluye `src/datos/cargar.py` para transformar el kit al contrato v2 y pruebas en `tests/test_datos.py`.

## D15 · MVP = línea base + umbrales (19 oct; actualizado por D20)

La línea base por sitio, los umbrales de residuo y la media móvil de cuatro horas pasaron de MVP a arquitectura definitiva del detector. La ampliación del modelo propuesta inicialmente se descartó según D20.

## D16 · Cuatro clases OT (fusión evento–efecto) ✅ (19 oct)

**Decisión:** las clases oficiales de alerta son **cuatro**, basadas en el cruce entre el registro OT y los residuos físicos:

| Clase | Condición | Acción | ¿En el kit? |
|---|---|---|---|
| **Incidente OT con efecto** | Evento OT **y** residuo físico desde el inicio del evento hasta 24 h después | Máxima: restaurar config aprobada; modo seguro manual | Se inyecta |
| **Cambio no autorizado** | `cambio_config_no_autorizado`, con o sin efecto | Alta: comparar contra config aprobada; vigilar 24 h | Sí (SIM-C) |
| **Escalón sin registro** | Residuo supera umbral de golpe sin evento OT | Alta: comparar setpoints; si es agua, inspección física | Sí (SIM-A/B) |
| **Intento de acceso** | Solo `login_fallido`, residuos normales | Media: revisar accesos | Sí (SIM-C) |

**Dos reglas de oro:**
1. Ningún exceso sin explicar va directo a mantenimiento (podría ser cambio sin registro).
2. Ningún cambio no autorizado es "sin urgencia" (puede notarse en el siguiente pico de calor).

**Extra, si sobra tiempo:** `incoherencia física` y `deriva gradual`.

**Dueño:** Guille (reglas); Nico (lógica); Gadiel (residuos disponibles).

## D17 · Criterio de evaluación por episodio, no por hora ✅ (19 oct)

**Decisión:** se cuenta **una alerta verdadera por episodio**, no una por hora alertada. Un episodio tiene su ventana definida en el manifiesto de inyecciones (U2). Las métricas son TP, FP, FN, precisión, recall, falsas alarmas por día **con intervalo de confianza** y **horas hasta detectar**.

**Por qué:** contar cada hora como caso independiente infla el recall artificialmente y no refleja lo que un operador vería (una sola alarma por evento, con una duración).

**Reglas:**
- Ventanas superpuestas: se fusionan en un solo episodio.
- Inyecciones sobre anomalías originales del kit: se tratan como episodios distintos solo si no se solapan; si se solapan, cuenta la inyección.
- Horas limpias: toda hora fuera de un episodio del manifiesto. Sobre ellas se calcula la tasa de falsas alarmas.

**Dueño:** Nico.

## D18 · "Energía no TI" en vez de "energía de enfriamiento" ✅ (19 oct)

**Decisión:** `energy_total_kwh − energy_it_kwh` se llama **energía no TI** (overhead) en todo el repo, no "energía de enfriamiento". Solo se puede llamar "enfriamiento" si el kit confirma que no incluye otros consumos (UPS, iluminación, auxiliares).

**Por qué:** honestidad metodológica. El kit no desglosa el overhead; asumir enfriamiento sobreestima el valor de las alertas.

**Dueño:** Misa (contrato y nombres de variables); Nico (textos de métricas).

## D19 · Repo canónico ✅ (19 oct)

**Decisión:** el repositorio canónico es **`dripsafe/`** (este). Cualquier variante `dripsafe-reestructura/` queda archivada; no se trabaja sobre ella.

**Por qué:** evitar trabajo duplicado y confusión sobre qué rama tiene las interfaces oficiales.

## D20 · Detector definitivo para N2 ✅ (20 oct)

**Decisión del equipo:** se descarta Isolation Forest por completo. No forma parte del detector, la comparación N2, las ampliaciones ni la demo. Esta decisión sustituye las propuestas de D2, D12 y D15 que lo contemplaban.

**Alcance vigente:** regresión por sitio sobre la referencia, umbrales de residuos calibrados antes de evaluación y media móvil de 4 h; el registro OT se usa para clasificar las alertas. N2 lo compara con las reglas didácticas del kit por episodio, latencia y falsas alarmas. Gadiel mide este detector con CodeCarbon; su medición sigue pendiente.

## Decisiones pendientes

- [ ] ¿Quién presenta el pitch? Candidatos: Nico (presentó propuestas en IRAP) y Leo (líder).
- [ ] Duración del pitch: preguntarle a CIFOX.
- [x] Confirmar las variables exactas del modelo al ver el kit → ver D12.
- [x] Aprobar el contrato v2 (D14) → PR de la rama `feat/datos-kit-v2`.
- [x] Confirmar el detector definitivo → D20; descartada la ampliación propuesta inicialmente.
- [x] Repositorio canónico → D19.
- [x] MVP de detección → D15.
- [x] Clases OT finales → D16.
- [x] Criterio de evaluación → D17.
- [x] Nombre "energía no TI" → D18.
- [ ] ¿Quién es el representante oficial ante CIFOX?
- [ ] Confirmar estado del dashboard (Leo) y punto de corte el 20 a mediodía.
- [ ] Fuentes externas (Nico): SMN horario, factor SEN vigente, intensidad hídrica, disponibilidad acuífero 3105, JAPAY.
