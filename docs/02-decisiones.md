# 02 · Decisiones tomadas y por qué

> Registro de las decisiones del equipo. Si alguien quiere cambiar una, que la discuta con todos **antes del 19 en la noche**. Después ya no hay tiempo para cambiar de rumbo.

## D1 · Sub-reto 3: detección de anomalías con IA ✅

**Decisión:** sub-reto 3, con **PUE** como métrica principal.

**Por qué:**
- Somos 5 estudiantes de Ingeniería de Software: construir un modelo y una demo es nuestro fuerte.
- Un mismo detector de anomalías cubre **los dos lados del reto**:
  - **Agua y energía:** detecta ineficiencias en el enfriamiento → baja el PUE.
  - **Ciberseguridad:** detecta lecturas o comandos que no cuadran con la física del sistema → posible manipulación.
- Así sumamos en "Eficiencia Green AI" **y** en "Impacto en ciberseguridad" sin hacer dos proyectos.

**Pendiente:** confirmarla al leer el kit el 19. Si los datos del sub-reto 3 vinieran muy incompletos, lo platicamos.

## D2 · Modelo ligero, hecho por nosotros ✅

**Decisión:** **Isolation Forest** de scikit-learn, entrenado con los datos del kit. No usaremos un LLM para analizar los datos.

**Por qué:**
- Se entrena en minutos en una laptop y buscamos un consumo bajo → el **balance neto positivo** obligatorio se verificará con las mediciones de Gadiel y los cálculos conjuntos de Misa + Nico (D11).
- Es explicable: podemos decir por qué marcó una alerta.
- Los LLM son malos analizando miles de lecturas numéricas, cuestan energía y los jueces quieren ver nuestro trabajo, no el de una API.
- "Hecho por nosotros" no es "desde cero": scikit-learn trae el algoritmo listo. Son unas 20 líneas.

**Uso permitido de LLM:**
- Como asistente para programar, investigar y entender el kit (Claude, etc.).
- *Opcional:* en la demo, para explicar una alerta en lenguaje natural. Si se hace, su consumo **se suma al balance neto**.

**Alternativas si el Isolation Forest no basta:** One-Class SVM, un autoencoder pequeño o umbrales estadísticos (z-score) como línea base.

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

## Decisiones pendientes

- [ ] ¿Quién presenta el pitch? Candidatos: Nico (presentó propuestas en IRAP) y Leo (líder).
- [ ] Duración del pitch: preguntarle a CIFOX.
- [ ] Confirmar las variables exactas del modelo al ver el kit.
- [ ] ¿Quién es el representante oficial ante CIFOX?
