# 11 · Cómo trabajamos en paralelo

> Documento para **todos**. Explica cómo avanzamos los cinco al mismo tiempo sin esperarnos ni pisarnos, y cómo queda **trazado** todo lo que hacemos. Complementa a [CONTRIBUTING.md](../CONTRIBUTING.md), que explica el flujo de Git.

## La idea en tres reglas

1. **Cada quien es dueño de una carpeta.** Solo el dueño la cambia libremente; si alguien más la toca, el dueño revisa el PR.
2. **Las piezas se comunican solo por archivos con formato fijo** (los «contratos»). Si mi pieza produce un archivo con las columnas acordadas, a los demás no les importa cómo lo hice por dentro.
3. **Nadie espera al kit.** `src/sinteticos.py` genera datos falsos con el mismo formato que tendrá el kit ya limpio. Cada quien desarrolla con ellos desde hoy, y cuando Misa entregue el kit limpio solo se cambia la ruta del archivo.

## El flujo de datos

```text
data/kit/  (crudo, confidencial, nunca sale de tu laptop)
   │  Misa · src/datos/   (usa config/columnas.json)
   ▼
data/procesado/telemetria.csv ................................. CONTRATO 1
   │  Misa · src/metricas/pue.py → PUE inicial + energías y periodo → Nico
   │  Guille · src/ataques/inyectar.py
   ▼
data/escenarios/telemetria_escenarios.csv + manifiesto ........ CONTRATO 2
   │  Gadiel · src/modelo/
   ▼
data/resultados/alertas.csv + consumo_modelo.json ............. CONTRATO 3
   │  Guille · src/ataques/evaluar.py  → deteccion_por_escenario.csv
   │  Nico · src/metricas/ (impacto, usando la referencia inicial de Misa)
   │  Misa + Nico · src/metricas/balance_neto.py (balance neto final)
   ▼
resultados/numeros_oficiales.json ............................. CONTRATO 4
   │  Leo · app/  (y las diapositivas)
   ▼
Dashboard y pitch
```

Mientras no exista el CONTRATO 1 real, cualquiera lo reemplaza con:

```bash
python -m src.sinteticos --dias 14 --salida data/sinteticos/telemetria.csv
```

## Los contratos

### Contrato 1 · Telemetría limpia (Misa)

`data/procesado/telemetria.csv`. Columnas definidas en [src/contrato.py](../src/contrato.py):

| Columna | Unidad | ¿Obligatoria? |
|---|---|---|
| `timestamp` | fecha y hora, intervalo fijo | Sí |
| `kw_ti` | kW de los servidores (o kWh/intervalo si es horario) | Sí |
| `kw_total` | kW de toda la instalación (o kWh/intervalo) | Sí |
| `kw_chiller`, `kw_bombas`, `kw_torre` | kW | Si el kit las trae |
| `t_exterior`, `t_suministro`, `t_retorno`, `setpoint_suministro` | °C | Si el kit las trae |
| `flujo_m3h` | m³/h | Si el kit las trae |
| `agua_reposicion_l` | litros por intervalo | Si el kit las trae |
| `bomba_encendida` | 0 o 1 | Si el kit las trae |
| `site_id` | SIM-A/B/C en el kit | Si hay varios sitios |
| `cooling_type` | aire / evaporativa / liquida | Si el kit las trae |
| `load_pct`, `inlet_temp_c`, `ot_event` | % / °C / texto | Si el kit las trae |

Misa traduce los nombres del kit a estos en `config/columnas.json` y los carga con `python -m src.datos.cargar --kit <csv>`. Para revisar que un archivo cumple el contrato: `contrato.validar(df)` regresa una lista vacía. Si existe `site_id`, el orden del `timestamp` se valida **por sitio**.

**Entrega a Nico:** además de la telemetría limpia, Misa entrega el PUE inicial calculado en `src/metricas/pue.py` y las energías total y de TI en kWh, indicando unidades, intervalo y periodo. Esos datos sustentan la referencia inicial; el cociente PUE por sí solo no permite calcular kWh ahorrados. Este acuerdo de responsabilidades no añade columnas ni archivos al contrato.

### Contrato 2 · Telemetría con escenarios (Guille)

`data/escenarios/telemetria_escenarios.csv`: las mismas columnas del contrato 1, con ataques y fallas simulados dentro de ventanas de tiempo, más cuatro columnas de respuesta correcta:

| Columna | Valores |
|---|---|
| `etiqueta_escenario` | nombre del escenario, vacío si es normal |
| `etiqueta_tipo` | `normal`, `falla` o `ataque` |
| `etiqueta_tecnica` | ID de MITRE ATT&CK for ICS, vacío si no aplica |
| `etiqueta_particion` | `entrenamiento` (sin escenarios) o `evaluacion` |

Además se genera un `.manifiesto.json` con las ventanas exactas de cada escenario.

**Regla de oro:** el modelo **nunca** usa columnas `etiqueta_*` para entrenar ni para predecir; usa `contrato.columnas_del_modelo(df)`. Entrena solo con las filas `entrenamiento`.

### Contrato 3 · Alertas y consumo del modelo (Gadiel)

`data/resultados/alertas.csv`, una fila por cada fila de la telemetría:

| Columna | Significado |
|---|---|
| `timestamp` | igual que en la entrada |
| `score` | salida de `decision_function`: más bajo = más raro |
| `anomalia` | `True` o `False` |
| `tipo_sugerido` | `normal`, `ineficiencia` o `posible_ataque` |
| `variable_principal` | la variable que más pesó en la alerta (opcional) |
| `kw_esperado_enfriamiento` | lo que el enfriamiento debería gastar en condiciones normales (para medir el exceso) |

`data/resultados/consumo_modelo.json`, medido con CodeCarbon:

```json
{"kwh_entrenamiento": 0.0, "kwh_inferencia_anual": 0.0, "kg_co2e_entrenamiento": 0.0, "fecha": "2026-10-20"}
```

### Contrato 4 · Números oficiales (Nico; PUE inicial de Misa)

`resultados/numeros_oficiales.json` es **la única fuente** de las cifras que aparecen en el dashboard, las diapositivas y el pitch. Cada número dice de dónde salió:

**Nico consolida** el JSON canónico y genera `app/ejemplos/numeros_ejemplo.json`, la vista plana que consume Leo. Misa aporta y revisa el PUE; Gadiel entrega tiempo y energía medidos del detector; Guille confirma el dato del acuífero. Misa y Nico validan el balance neto cuando Gadiel entregue CodeCarbon.

Cada cifra lleva `valor`, `unidad`, `tipo`, `origen`, `responsable`, `estado` y, si queda en `null`, `motivo_pendiente`. `tipo` distingue `observado` (kit simulado), `medido` (hardware con repeticiones), `estimado` (modelo) y `proyectado` (escenario). `_meta.periodos` fija referencia (216 horas-sitio) y evaluación (288 horas-sitio), con fechas inclusivas, sitios e intervalo de una hora. Las energías de entrada son kWh por intervalo, el agua es captación in situ en L; PUE es ratio y WUE L/kWh IT.

`pue.referencia` conserva la línea base histórica. `pue.antes` es el PUE observado de **evaluación** y `pue.despues_proyectado` resta de esa misma evaluación solo el exceso estimado que coincide con alertas físicas. Es un contrafactual, no ahorro observado. Se hace lo mismo con WUE. `periodos_y_sitios` deja auditables los totales de referencia y evaluación, el exceso por sitio y las unidades. La comparación original de detección cuenta **3 episodios**; las 21 horas anómalas se reportan aparte. Los nombres de clases coinciden con `src/ot/clases.py`.

Este archivo **sí** se sube al repo, porque solo contiene totales que de todos modos se van a mostrar en el pitch, nunca filas del kit. Así Git guarda el historial de cada cifra. Si un número aparece en una diapositiva y no está aquí, es un error.

El generador `python -m src.metricas.generar_numeros` usa telemetría, alertas y resultados de la rejilla bajo `data/` (ignorado por Git), más la serie ERA5 de Mérida cuando está disponible. Versiona solo agregados; `src/contrato.py::validar_numeros_oficiales` comprueba metadatos, tipos y `null` justificados. La demo sin kit usa `app/ejemplos/numeros_demo.json`, rotulada **Ejemplo**. El costo del detector, el balance que depende de él, el PUE con bono y el acuífero siguen pendientes hasta recibir evidencia.

### Cambiar un contrato

Un contrato solo cambia con un PR que actualice **este documento y `src/contrato.py` a la vez**, y con el visto bueno de todos los que leen o escriben ese archivo.

## Dueños de cada carpeta

| Carpeta | Dueño | Revisa |
|---|---|---|
| `src/contrato.py`, `config/`, `src/datos/` | Misa | Gadiel |
| `src/metricas/pue.py` (PUE inicial) | Misa | Gadiel |
| `src/metricas/balance_neto.py` (balance neto final) | Misa + Nico | Ambos validan el resultado |
| Resto de `src/metricas/` (ahorro, PUE final proyectado e impacto) | Nico | Misa |
| `src/modelo/` | Gadiel (construye) | Nico (evalúa) |
| `src/evaluacion/` (comparación justa y costo del detector) | Nico | Gadiel |
| `src/ataques/`, `docs/06-ciberseguridad-ot.md` | Guille | Gadiel |
| `app/` | Leo | Misa |
| `docs/07-*` (acuífero: Guille · bono: Misa) | Guille + Misa | Nico |
| `docs/08-*` | Leo | Nico |
| `.github/`, `CONTRIBUTING.md`, este documento | Misa | Guille |
| `resultados/numeros_oficiales.json` | Nico | Misa |

`.github/CODEOWNERS` no repite esta tabla: pone a Misa y a Leo como revisores de cualquier PR, y GitHub les pide la revisión automáticamente si el plan de la cuenta lo permite.

**D13 (19 oct):** Nico se suma al modelo como evaluador; el acuífero pasa a Guille, el bono a Misa y el guion a Leo.

El reparto de métricas fue aprobado en **D10 y ajustado en D11**: #2 sigue con Misa, #3 pasa a Nico y #14 queda compartida entre Misa + Nico. `src/metricas/balance_neto.py` es el módulo previsto para el trabajo conjunto; las rutas de métricas y resultados señalan el destino de los entregables pendientes, sin cambiar los formatos de intercambio. Asignar un dueño no significa que ya estén implementados.

## Reglas de entrega entre personas (plan-ejecucion)

- Cada tarea se entrega con **ejemplo de entrada**, **salida**, **unidades** y **forma de ejecutarla**; el receptor confirma que la pudo consumir.
- Misael registra cualquier cambio de columnas o rutas en el contrato y avisa a los cuatro **antes** de integrarlo.
- Gadiel entrega resultados **por sitio y hora**; Guillermo añade la **clase y acción**; Nico agrega resultados **por episodio y periodo**; Leo solo los presenta.
- Las etiquetas del kit (`etiqueta_*`) sirven para separar ajuste/calibración/prueba y evaluar; **nunca como predictores**. `src/contrato.py:columnas_del_modelo()` las excluye.
- El kit y sus filas derivadas permanecen fuera de Git. Solo código, pruebas sintéticas y agregados autorizados.
- Si dos piezas discrepan en una cifra, se corrige el cálculo o el contrato **antes** de modificar el pitch.

## Criterio de evaluación por episodio (D17)

Se cuenta **una alerta verdadera por episodio**, no una por hora alertada. Un episodio tiene su ventana en el manifiesto de inyecciones (U2).

**Métricas oficiales:** TP, FP, FN, precisión, recall, **falsas alarmas por día con intervalo de confianza** y **horas hasta detectar**.

**Reglas:**
- Ventanas superpuestas se fusionan en un solo episodio.
- Inyecciones sobre anomalías originales del kit: episodios distintos solo si no se solapan; si se solapan, cuenta la inyección.
- Horas limpias = toda hora fuera de un episodio del manifiesto; sobre ellas se calcula la tasa de falsas alarmas.

## Cómo queda trazado todo

Cada pieza de trabajo deja este rastro:

```text
Requisito de la convocatoria → issue → rama → PR (con «Cierra #N») → commit en main → evidencia
```

1. **Issues:** cada entregable es un issue con su dueño y dos etiquetas: `rol:<nombre>` y `criterio:<criterio que ataca>`. La lista inicial está en [12-trazabilidad.md](12-trazabilidad.md).
2. **Ramas:** `tipo/descripcion-corta`, por ejemplo `feat/escenarios-ataque`. Una rama, un issue.
3. **PR:** usa la plantilla, menciona `Cierra #N`, pasa las pruebas automáticas y tiene una revisión del dueño de la carpeta. Se integra con *squash merge*: un commit por tarea en `main`.
4. **Decisiones:** toda decisión que cambie el plan se registra en [02-decisiones.md](02-decisiones.md) con el siguiente número `D`.
5. **Matriz:** [12-trazabilidad.md](12-trazabilidad.md) liga cada requisito de la convocatoria con su issue y su evidencia. Misa la actualiza al cerrar cada issue.

## Pruebas automáticas

Cada PR corre `pytest` en GitHub Actions **solo con datos sintéticos**. También revisa que no se haya subido ningún archivo de datos (`.csv`, `.xlsx`, `.parquet`), por si alguien se brinca el `.gitignore`. Para correrlas en tu laptop:

```bash
pip install -r requirements.txt
pytest
```

## Ritmo

| Cuándo | Qué |
|---|---|
| Todos los días, hora fija | 15 min: qué hice, qué sigue, en qué estoy atorado (dirige Leo) |
| Martes 20 en la noche | Primera prueba de punta a punta con datos reales |
| Miércoles 21, 20:00 | **Congelamiento:** `main` queda fija y se etiqueta `congelado-21`. Se congela también `numeros_oficiales.json` |
| Jueves 22 | Solo ramas `fix/`. Cada quien tiene `main` congelada en un worktree aparte (`git worktree add ../dripsafe-estable congelado-21`) |
