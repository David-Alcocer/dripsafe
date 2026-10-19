# 05 · Solución técnica

> Documento para **Gadiel** (modelo), **Misa** (datos) y **Leo** (demo). Es una propuesta inicial: se ajusta cuando veamos el kit el 19.

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
| PUE base | Misa | pandas |
| Features y modelo | Gadiel | scikit-learn |
| Consumo del modelo | Gadiel | CodeCarbon |
| Clasificar anomalías (falla o ataque) | Gadiel + Guille | reglas + modelo |
| PUE después y balance neto | Misa + Nico | pandas |
| Dashboard | Leo | Streamlit |

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
- Entrena en segundos o minutos en una laptop, así que el balance neto queda positivo.
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

**PUE antes y después:**
- **Antes:** PUE calculado con los datos del kit tal como vienen.
- **Después:** se resta el exceso de energía de los periodos con anomalías de ineficiencia, como si se hubieran corregido:

```text
PUE_después = (E_total − E_exceso_evitado) / E_TI
```

El exceso se estima comparando cada periodo anómalo contra el comportamiento normal en condiciones similares (misma carga de TI y hora).

## Balance neto (obligatorio)

**Hay que demostrar con números que el modelo ahorra más de lo que gasta.**

```text
Costo del modelo:
  E_modelo   = energía de entrenamiento + inferencia durante un año (kWh)  ← CodeCarbon
  CO2_modelo = E_modelo × factor de emisión de la red (kg CO2e/kWh)
  Agua_modelo = E_modelo × (WUE_sitio + intensidad hídrica de la electricidad)  (L)

Ahorro:
  E_ahorrada  = (PUE_antes − PUE_después) × E_TI anual (kWh)
  CO2_ahorrado = E_ahorrada × factor de emisión
  Agua_ahorrada = ΔWUE × E_TI + E_ahorrada × intensidad hídrica de la electricidad  (L)

Balance neto = Ahorro − Costo   → debe ser > 0
Razón        = Ahorro / Costo    → "ahorra N veces lo que consume"
```

**Datos a buscar** (Nico y Misa):
- Factor de emisión del Sistema Eléctrico Nacional de México, en su valor oficial más reciente.
- Intensidad hídrica de la generación eléctrica (litros por kWh). El artículo *Making AI Less "Thirsty"* explica cómo se calcula el agua "fuera del sitio".

> Con un Isolation Forest, la energía del modelo se mide en milésimas o centésimas de kWh, mientras que un centro de datos consume miles de kWh al día. Esa diferencia de órdenes de magnitud es nuestro mejor argumento.

## Demo (Streamlit)

Pantallas sugeridas:
1. **Resumen:** PUE antes y después, agua ahorrada y balance neto en tarjetas grandes.
2. **Serie de tiempo:** consumo con las anomalías marcadas en rojo o naranja.
3. **Detalle de alerta:** qué variable falló, si es ineficiencia o posible ataque, y qué hacer.
4. **Balance neto:** costo del modelo frente al ahorro, en una gráfica de barras.

```bash
streamlit run app/main.py
```

**Importante:** grabar un video de la demo el 21 como respaldo.
