# 05 · Solución técnica

> Documento para **Gadiel** (modelo), **Misa** (datos y PUE inicial), **Nico** (evaluación del detector y cálculo de impacto), **Misa + Nico** (balance neto final) y **Leo** (demo). **Actualizado tras el kit (19 oct):** ver la sección siguiente.

## Lo que trae el kit (19 oct)

> Resumen del kit oficial. **El kit no se sube al repo.** Aquí solo se describe su estructura. Decisiones derivadas: D12, D13 y D14 en [02-decisiones.md](02-decisiones.md).

**Datos:** un CSV **totalmente simulado** con 3 sitios ficticios × 168 horas (una semana), intervalo de 1 hora.

| Columna del kit | Unidad | Uso |
|---|---|---|
| `timestamp`, `site_id` | UTC · SIM-A/B/C | Clave: una fila por sitio y hora |
| `cooling_type` | aire / evaporativa / liquida | Un tipo por sitio |
| `energy_it_kwh`, `energy_total_kwh` | kWh por intervalo | PUE = suma(total) / suma(IT), **nunca** el promedio de PUE horarios |
| `water_l` | L por intervalo | Captación in situ simulada; "WUE pedagógica" = suma(agua) / suma(IT) |
| `load_pct`, `outdoor_temp_c`, `inlet_temp_c` | %, °C, °C | Variables de contexto |
| `ot_event` | normal / login_fallido / cambio_config_no_autorizado | Evento OT resumido; un login fallido no prueba un ataque |
| `split` | referencia (72 h) / evaluacion (96 h) | Ajustar con referencia, evaluar con evaluacion |
| `scenario`, `simulated_anomaly` | etiquetas | **Prohibido** usarlas como entrada; solo para evaluar |

**Qué cambia respecto al plan original:**
- **No hay sensores por equipo** (chiller, bombas, torre, temperaturas del agua, caudal). La "coherencia física" se hace a nivel agregado por sitio: energía auxiliar (total − IT) y agua esperadas según carga, temperatura exterior y tipo de enfriamiento.
- **Las reglas del kit ya detectan todo en su ejemplo.** Por eso:
  - **Gadiel** construye una línea base por sitio con umbrales de residuo y media móvil, ajustada solo con referencia; las reglas OT clasifican cada alerta.
  - **Nico** compara ese detector con las reglas del kit por episodio, con ajuste y evaluación separados, varias corridas y calidad reportada junto al costo. Si las reglas bastan, se dice. *El método más ligero que funciona es el argumento Green AI.*
- **Stack:** el Stack A (Streamlit) del kit es la referencia y se usa **Python 3.12**. Las herramientas del kit (`common/cifox.py` y `tools/compare_detectors.py`) se pueden reutilizar citando que vienen del kit (licencia MIT).
- **Reglas de presentación del kit:** "DATOS SIMULADOS" siempre visible. Energía y emisiones como **estimación con supuestos** (watts y gCO₂e/kWh editables, con análisis de sensibilidad). Nada de litros por consulta. Los ahorros son **proyecciones**, no observaciones. Hay que explicar **qué venía en el kit y qué aportamos**.

**Entregable que sugiere el kit:** demo local de 3 minutos, README reproducible, cambios y tests, ficha de datos y supuestos, resultados con incertidumbre, tres límites y la siguiente validación necesaria.

## Concepto: línea base + fusión evento–efecto

> **Alcance vigente (D20):** línea base física por sitio + umbral por residuo + media móvil de 4 h y clasificación OT.

```text
CSV del kit (6 medidores + registro OT)
   │
   ├─▶ 1. Línea base física por sitio (aprendida en 48 h de la referencia)
   ├─▶ 2. Residuos = real − esperado (%)
   │       ├─ Umbral por residuo + media móvil de 4 h   → excesos sostenidos
   ├─▶ 3. Registro OT  →  reglas
   ├─▶ 4. Fusión evento–efecto  →  4 clases (D16)
   └─▶ 5. Cola de alertas en el dashboard: kWh y L en riesgo por hora
```

1. **La línea base** aprende cómo debería comportarse cada sitio según su **carga** (energía de TI) y su **clima** (pérdida de enfriamiento gratuito arriba de 20 °C).
2. **El residuo** (real menos esperado) delata los excesos sostenidos. El umbral se calibra con 24 h extra de referencia.
3. **Las 4 clases OT (D16)** cruzan el registro OT con los residuos: incidente con efecto, cambio no autorizado, escalón sin registro e intento de acceso.
4. **La prioridad es por litros del acuífero** (ver [07-agua-y-acuifero.md](07-agua-y-acuifero.md)).

## Pipeline

```text
data/ (kit)  →  src/datos/cargar.py  →  src/modelo/ (baseline + residuos)  →  src/fusion/ (reglas + 4 clases)
                                                                          →  src/metricas/  →  resultados/numeros_oficiales.json  →  app/ (Streamlit)
```

| Paso | Responsable | Herramienta | Fase |
|---|---|---|---|
| Cargar kit y validar contrato | Misa (M1) | pandas + `src/contrato.py` | 0 |
| Partición 48/24, regresión por sitio, residuos, umbral, MM 4 h | Gadiel (G1) | pandas + numpy | 0 |
| Rejilla de inyecciones + 4 clases OT | Guille (U1) | pandas | 0 |
| PUE/WUE, exceso estimado, episodios | Nico (N1) | pandas | 0 |
| JSON ejemplo y pantallas con estados vacíos | Leo (L1) | Streamlit | 0 |
| **Integración y punto de corte** | Todos (Fase 1) | — | 1 |
| Congelar parámetros, rejilla, tabla y curva | G2+U2+N2 | — | 2 |
| CodeCarbon (10 repeticiones) y umbral de equilibrio | Gadiel (G3) + Misa | CodeCarbon | 2 |
| Balance neto compartido | Misa + Nico (M3/N3) | pandas | 2 |
| Acuífero + bono + fuentes | Nico (N4) | — | 2 |
| Integración final, ensayo cronometrado | Misa (M4) | — | 2 |
| Dashboard integrado + diapositivas | Leo (L2) | Streamlit | 2 |

**Entrega entre Misa y Nico:** Misa entrega el PUE inicial junto con la telemetría limpia y las energías total y de TI en kWh, indicando unidades, intervalo y periodo. El PUE por sí solo no basta para calcular kWh ahorrados. Nico usa esa referencia, las alertas, el consumo esperado y las mediciones de CodeCarbon de Gadiel para calcular el impacto posterior. Los formatos de intercambio siguen definidos en [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

**Estado:** este reparto está aprobado (D10, D11 y D13); los cálculos y la consolidación de resultados siguen pendientes de implementación.

## Stack

- **Python 3.11+**
- `pandas`, `numpy`: datos
- `codecarbon`: energía y CO₂ del modelo
- `streamlit`, `plotly`: demo
- `jupyter`: exploración

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy scipy codecarbon streamlit plotly jupyter
```

## El detector: línea base, umbrales y media móvil

### 1. Línea base física por sitio (MVP)

Para cada sitio, una **regresión lineal** con dos variables físicas:
- **Calor a disipar:** `energy_it_kwh`.
- **Pérdida de enfriamiento gratuito:** `energy_it_kwh × max(0, outdoor_temp_c − 20)`. Arriba de 20 °C el aire exterior ya no ayuda y cada grado cuesta energía o agua.

Con eso se predice la **energía no TI** (`energy_total − energy_it`, ver D18) y el agua. La **temperatura de entrada** depende del clima y no del tamaño de la carga, así que su línea base usa solo `max(0, outdoor_temp_c − 20)` y una constante. **El setpoint y la configuración no entran como variables:** si alguien los altera, el consumo real se separa de lo esperado y se ve.

**Transparencia:** la forma coincide con la del generador del kit. Lo declaramos: la elegimos porque representa la física, y para no depender de esa coincidencia la validación prueba **una forma mal especificada** (solo TI y temperatura) y **datos con ruido extra** (§4 de la propuesta).

Cada alerta se explica en una frase: *"SIM-A gasta 31 % más energía no TI de lo esperado para su carga y clima."*

### 2. Detectores sobre los residuos (MVP)

1. **Umbral por residuo** (energía, agua, entrada): alerta si el residuo supera el máximo observado en las 24 h de calibración más un **margen del 50 %**, fijado antes de ver la evaluación.
2. **Media móvil de 4 h** de cada residuo, con su propio umbral igual. Atrapa excesos pequeños pero sostenidos. Son unas 5 líneas con pandas.

*Extra si sobra tiempo:* **CUSUM** para derivas de días.

**Límite mínimo detectable** (estimación analítica que se verifica en la prueba de robustez):
- El ruido del kit sobre la energía total es de ±1.5 % de la energía de TI. En el sitio líquido eso equivale a ~4.4 % de la energía no TI por hora.
- **Detector 1, en una hora:** detecta un exceso de ~+15 %.
- **Detector 2, sostenido 4 h:** detecta uno de ~+10 %.
- Las reglas del kit **no ven ninguno de los dos**.

## Las 4 clases OT (D16)

El diagnóstico sale de cruzar el **registro OT** con los **residuos físicos**. Diseño de Guille y Gadiel, lógica revisada por Nico.

| Clase | Condición | Acción |
|---|---|---|
| **Incidente OT con efecto** | Evento OT **y** residuo físico desde el inicio del evento hasta 24 h después | Máxima: restaurar config aprobada; modo seguro manual |
| **Cambio no autorizado** | `cambio_config_no_autorizado`, con o sin efecto | Alta: comparar contra config aprobada; vigilar 24 h |
| **Escalón sin registro** | Un residuo supera el umbral de golpe sin evento OT | Alta: comparar setpoints; si es agua, inspección física |
| **Intento de acceso** | Solo `login_fallido`, residuos normales | Media: revisar accesos |

**Dos reglas de oro:**
1. Ningún exceso sin explicar va directo a mantenimiento.
2. Ningún cambio no autorizado es "sin urgencia".

**Ventana de 24 h:** en el kit el cambio de configuración ocurre de madrugada; un setpoint alterado puede notarse hasta la tarde. Un residuo que ya existía **antes** del evento se marca `coincidente, no causal`, salvo que dé un escalón dentro de la ventana. Se reporta cuántas coincidencias al azar habría combinando eventos OT con residuos en la evaluación limpia.

*Extra si sobra tiempo:* `incoherencia física` (sube entrada y baja energía no TI) y `deriva gradual`.

## Métricas

**Siempre cocientes de sumas, nunca promedios de cocientes horarios.**

```text
PUE = Σ energía total (kWh) / Σ energía de TI (kWh)
WUE = Σ agua in situ (L)    / Σ energía de TI (kWh)
CUE = Σ emisiones CO2e (kg) / Σ energía de TI (kWh)  =  factor de emisión de la red × PUE
```

**Umbral de equilibrio (D15 + propuesta §5):** el **número central** del balance no es "el ahorro proyectado anual". Es el **costo anual del detector** (CodeCarbon × 10 repeticiones, inferencia horaria 8760 veces + reentrenamiento por temporada) comparado con **el exceso de una sola hora de ineficiencia típica**. Para no contar el ajuste dos veces, la medición separa `inferencia` (parámetros congelados) de `entrenamiento`; `corrida_completa` se conserva como referencia y no se suma. La inferencia se mide sobre un lote y se divide entre sus horas antes de multiplicar por 8 760, para no sobreestimar el costo por hora. Si el costo son unos pocos Wh y una hora de ineficiencia son decenas de kWh, **basta una detección al año** para que el balance sea positivo. Este número no depende de que el ahorro proyectado sea exacto.

**PUE inicial y final proyectado:**
- **Inicial (Misa):** PUE calculado con los datos limpios del kit, para un periodo definido.
- **Final proyectado (Nico):** se resta el exceso de energía estimado de los periodos con anomalías de ineficiencia, suponiendo que se corrigieran:

```text
PUE_final_proyectado = (E_total − E_exceso_evitado_estimado) / E_TI
```

El exceso se estima comparando cada periodo anómalo contra el comportamiento normal en condiciones similares (misma carga de TI y hora), usando el consumo esperado que entrega Gadiel. Nico documenta la corrección supuesta y mantiene el mismo periodo y energía de TI en ambos PUE. Una alerta no demuestra por sí sola un ahorro.

El campo existente `pue_despues` se presenta como **PUE final proyectado**. Los ahorros también se identifican como estimaciones hasta contar con evidencia medida tras una intervención.

## Balance neto (obligatorio)

**Hay que demostrar con números que el modelo ahorra más de lo que gasta.**

**Responsables del cálculo y validación final: Misa + Nico.** Gadiel proporciona las mediciones del modelo; Misa proporciona la referencia inicial y Nico estima el ahorro. Misa + Nico calculan juntos el balance, restando el costo del modelo con unidades y horizontes temporales compatibles. El valor puede ser positivo, cero o negativo; se reporta el resultado obtenido.

```text
Costo del modelo:
  E_modelo   = energía de entrenamiento + inferencia durante un año (kWh)  ← CodeCarbon
  CO2_modelo = E_modelo × factor de emisión de la red (kg CO2e/kWh)
  Agua_modelo = E_modelo × (WUE_sitio + intensidad hídrica de la electricidad)  (L)

Ahorro:
  E_ahorrada  = (PUE_inicial − PUE_final_proyectado) × E_TI anual (kWh)
  CO2_ahorrado = E_ahorrada × factor de emisión
  Agua_ahorrada = ΔWUE × E_TI + E_ahorrada × intensidad hídrica de la electricidad  (L)

Balance neto = Ahorro − Costo   → debe ser > 0
Razón        = Ahorro / Costo    → "ahorra N veces lo que consume"
```

Las cantidades de ahorro de este esquema son **proyecciones**. Si se extrapola a un año, Nico documenta el supuesto y utiliza ese mismo horizonte para el costo. El cálculo de agua requiere conocer el consumo o un WUE aplicable y la intensidad hídrica de la electricidad; un mejor PUE no demuestra automáticamente ahorro de agua.

**Datos a buscar y citar (Nico):**
- Factor de emisión del Sistema Eléctrico Nacional de México, en su valor oficial más reciente.
- Intensidad hídrica de la generación eléctrica (litros por kWh). El artículo *Making AI Less "Thirsty"* explica cómo se calcula el agua "fuera del sitio".

**Resultados pendientes:** si faltan datos o factores suficientes para agua o emisiones, Nico marca esas métricas como pendientes. Cualquier valor de referencia se identifica como supuesto, sin presentarlo como medición del kit.

## Demo (Streamlit)

Pantallas sugeridas:
1. **Resumen:** PUE inicial y final proyectado, ahorro estimado de agua cuando pueda calcularse y balance neto en tarjetas grandes. Leo usa las cifras consolidadas por Nico.
2. **Serie de tiempo:** consumo con las anomalías marcadas en rojo o naranja.
3. **Detalle de alerta:** qué variable falló, si es ineficiencia o posible ataque, y qué hacer.
4. **Balance neto:** costo del modelo frente al ahorro, en una gráfica de barras.

```bash
streamlit run app/main.py
```

**Importante:** grabar un video de la demo el 21 como respaldo.
