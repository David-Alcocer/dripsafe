# 05 · Solución técnica

> Documento para **Gadiel** (modelo), **Misa** (datos y PUE inicial), **Nico** (cálculo de impacto) y **Leo** (demo). Es una propuesta inicial: se ajusta cuando veamos el kit el 19.

## Concepto: un vigilante, dos beneficios

```text
 Sensores del enfriamiento            Modelo ligero                    Dos tipos de alerta
 (torres, bombas, chillers,   ──▶   de anomalías        ──▶   ① Ineficiencia → ajustar enfriamiento → baja PUE/WUE
  flujo, temperatura, energía)      (Isolation Forest)        ② Manipulación sospechosa → alerta de ciberseguridad
  vía Modbus / BACnet
```

1. El modelo **aprende el comportamiento normal** del sistema de enfriamiento a partir de los datos históricos del kit.
2. Marca como **anomalía** lo que se sale de ese patrón.
3. Clasificamos cada anomalía:
   - **Ineficiencia:** se gasta más energía o agua de lo normal para el mismo calor → oportunidad de ahorro.
   - **Posible ataque:** las lecturas o comandos **no cuadran con la física** del sistema → alerta de seguridad.

## Pipeline

```text
data/ (kit)  →  limpieza (pandas)  →  features  →  Isolation Forest  →  alertas  →  métricas (PUE, balance neto)  →  dashboard (Streamlit)
```

| Paso | Responsable | Herramienta |
|---|---|---|
| Cargar y limpiar datos | Misa | pandas |
| PUE inicial, energías total y de TI, unidades y periodo | Misa | pandas |
| Features y modelo | Gadiel | scikit-learn |
| Alertas y consumo esperado del enfriamiento | Gadiel | scikit-learn |
| Consumo del modelo | Gadiel | CodeCarbon |
| Clasificar anomalías (falla o ataque) | Gadiel + Guille | reglas + modelo |
| Ahorro energético, PUE final proyectado y balance neto | Nico | pandas |
| Impacto en agua y emisiones, cuando los datos lo permitan | Nico | pandas + fuentes citadas |
| Consolidar cifras para dashboard y pitch | Nico | `resultados/numeros_oficiales.json` |
| Integrar datos, modelo, métricas y demo | Misa | Python |
| Dashboard | Leo | Streamlit |

**Entrega entre Misa y Nico:** Misa entrega el PUE inicial junto con la telemetría limpia y las energías total y de TI en kWh, indicando unidades, intervalo y periodo. El PUE por sí solo no basta para calcular kWh ahorrados. Nico usa esa referencia, las alertas, el consumo esperado y las mediciones de CodeCarbon de Gadiel para calcular el impacto posterior. Los formatos de intercambio siguen definidos en [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

**Estado:** este reparto está aprobado (D10); los cálculos y la consolidación de resultados siguen pendientes de implementación.

## Stack

- **Python 3.11+**
- `pandas`, `numpy`: datos
- `scikit-learn`: modelo
- `codecarbon`: energía y CO₂ del modelo
- `streamlit`, `plotly`: demo
- `jupyter`: exploración

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy scikit-learn codecarbon streamlit plotly jupyter
```

## El modelo: Isolation Forest

**Idea en una línea:** construye árboles que parten los datos al azar. Los puntos raros quedan aislados con pocos cortes, y eso los delata como anomalías.

**Por qué este modelo:**
- No necesita datos etiquetados: aprende solo lo "normal".
- Entrena en segundos o minutos en una laptop; su balance neto se comprobará con las mediciones de Gadiel y los cálculos de Nico.
- Es fácil de explicar al jurado.

**Esqueleto (se adapta a las columnas reales del kit):**

```python
import pandas as pd
from sklearn.ensemble import IsolationForest
from codecarbon import EmissionsTracker

df = pd.read_csv("data/kit/enfriamiento.csv", parse_dates=["timestamp"])  # nombre de ejemplo

features = ["temp_entrada", "temp_salida", "flujo_agua", "kw_chiller", "kw_bombas", "kw_ti"]  # ejemplo
X = df[features].dropna()

tracker = EmissionsTracker(project_name="dripsafe")
tracker.start()

model = IsolationForest(n_estimators=200, contamination=0.01, random_state=42)
model.fit(X)
df.loc[X.index, "anomalia"] = model.predict(X) == -1      # True = anomalía
df.loc[X.index, "score"] = model.decision_function(X)     # más bajo = más raro

emisiones_kg = tracker.stop()   # kg CO2e; la energía (kWh) queda en emissions.csv
```

**Features útiles** (si el kit las trae):
- Diferencia de temperatura entrada-salida (ΔT).
- Energía de enfriamiento ÷ energía de TI, que es casi el PUE por instante.
- Agua consumida ÷ energía de TI, que es casi el WUE por instante.
- Hora del día y día de la semana (el patrón normal cambia).
- Promedios móviles y diferencias contra la lectura anterior.

**Línea base:** comparar contra un método simple (z-score por variable). Si el Isolation Forest no le gana, algo está mal.

## ¿Falla o ataque?

Esto lo diseñan juntos Gadiel y Guille. Algunas pistas físicas:

| Señal | Más probable |
|---|---|
| Varias variables cambian juntas y de forma coherente (sube la carga de TI, sube el consumo del chiller, sube ΔT) | Operación normal o ineficiencia |
| Un sensor reporta algo que **no cuadra** con los demás (dice que la temperatura bajó, pero el chiller no consume más) | **Posible manipulación** del sensor |
| Cambio brusco de un parámetro de control fuera de horario | **Posible comando no autorizado** |
| Consumo alto sostenido sin cambio en la carga de TI | Ineficiencia (equipo degradado o mal configurado) |

## Métricas

```text
PUE = energía total de la instalación (kWh) / energía de TI (kWh)
WUE = agua consumida en sitio (L)           / energía de TI (kWh)
CUE = emisiones CO2e (kg)                   / energía de TI (kWh)  =  factor de emisión de la red × PUE
```

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

**Responsable del cálculo: Nico.** Gadiel proporciona las mediciones del modelo; Misa proporciona la referencia inicial. Nico estima el ahorro y resta el costo del modelo con unidades y horizontes temporales compatibles. El valor puede ser positivo, cero o negativo; se reporta el resultado obtenido.

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
