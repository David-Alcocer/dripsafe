# N1 · Protocolo reproducible de evaluación

Este módulo implementa el criterio D17 sin guardar filas del kit en el repositorio.
Se ejecuta **por sitio** y únicamente sobre horas de `evaluacion`; las horas
de `entrenamiento` no cuentan para TP, FP ni exposición limpia. La rejilla de
evaluación debe estar completa en cada sitio.

## Definiciones

- **Episodio verdadero:** intervalo inclusivo `[inicio, fin]` de un sitio.
  Los episodios originales pueden derivarse de tramos contiguos con
  `etiqueta_escenario`; las inyecciones llegan con su manifiesto. Ventanas que
  se solapan en el mismo sitio se fusionan. Si una inyección se solapa con una
  anomalía original, el episodio fusionado se atribuye a la inyección.
- **TP:** episodio con al menos una alerta dentro de su ventana. Por muchas
  horas que dure, cuenta una sola vez. **Latencia:** horas desde `inicio` hasta
  la primera alerta dentro de la ventana.
- **FN:** episodio sin ninguna alerta dentro de la ventana.
- **Hora limpia:** hora de evaluación fuera de todas las ventanas verdaderas.
  **FP:** tramo continuo de horas limpias alertadas en un sitio. Dos horas
  consecutivas con alerta forman un FP, no dos. Un hueco temporal o una hora
  sin alerta abre otro tramo.
- **Precisión:** `TP / (TP + FP)`. **Recall:** `TP / (TP + FN)`.
  Si el denominador es cero, se devuelve `None`.
- **Falsas alarmas por día y sitio:** `FP / (horas limpias acumuladas / 24)`.
  El intervalo de confianza del 95 % es Poisson exacto para ese recuento;
  presupone falsas alarmas independientes y debe leerse con cautela en siete
  días de datos autocorrelacionados.

## Comparación justa

`reglas_fijas()` implementa las cuatro señales didácticas de `common/cifox.py`
del kit: `PUE > 1.6`, `WUE in situ > 1.5 L/kWh TI`, temperatura de entrada
`> 29 °C` y evento OT distinto de `normal`. OT está activo por defecto.
`incluir_ot=False` es una comparación física separada. Comparar solo métodos
que recibieron **la misma tabla de entrada y acceso equivalente al registro
OT**. El kit fue construido para que estas reglas vean sus anomalías; una
coincidencia perfecta en él no demuestra eficacia externa.

`evaluar_episodios()` recibe cualquier tabla de alertas que tenga
`site_id`, `timestamp` y `anomalia`. Por eso se puede evaluar con el mismo
código las reglas fijas del kit y el detector de Gadiel. Se congelan sus
parámetros antes de abrir la evaluación.
Las múltiples corridas corresponden a semillas o inyecciones diferentes; no
se vuelven a ajustar umbrales usando los resultados de evaluación.

### Fijación técnica para N2

Antes de la comparación, `congelar_n2` contrasta el CSV con el `MANIFEST.json`
entregado por CIFOX y registra en `resultados/n2_congelamiento.json` los hashes
del kit y del código, el commit de corte, las ventanas y los parámetros
aprendidos por sitio. El JSON contiene solo metadatos y agregados; no incluye
filas del kit ni rutas de la laptop. Para reproducir la fijación actual:

```bash
KIT_CSV=/ruta/local/al/kit/data/operaciones_simuladas.csv
.venv/bin/python -m src.evaluacion.congelar_n2 --kit "$KIT_CSV" --revision ac24bf8
git diff --exit-code -- resultados/n2_congelamiento.json
```

El comando rechaza un CSV que no coincida con el inventario y un código fuente
distinto del commit indicado. Verifica además que cambiar las etiquetas de
resultado no altere las predicciones y que cambiar la evaluación no altere los
parámetros aprendidos. `etiqueta_particion` solo selecciona las 48 h de ajuste
y las 24 h de calibración por sitio; las 96 h posteriores son evaluación.
`ot_event` es una entrada legítima para clasificar, pero no ajusta la línea
base numérica. El estado del manifiesto es **fijación local pendiente de
confirmación de Gadiel**; no contiene ni sustituye su medición de CodeCarbon.
El detector fijado en este commit usa mínimos cuadrados, umbrales y EWMA.
Según D20, esa es la arquitectura acordada para N2. Cualquier cambio posterior
requiere un nuevo commit de corte y repetir la evaluación con esa versión.

## Métricas de impacto

`src/metricas/impacto.py` calcula PUE y WUE como cocientes de sumas por sitio
y partición, con periodo y cobertura explícitos. El agua del kit es
**captación in situ**, no agua potable ni consumo neto. `exceso_no_ti()`
cuantifica los residuos firmados y excesos positivos de energía no TI en
**todas** las horas de evaluación; si se proporciona agua esperada, hace lo
mismo con litros. Separa excesos coincidentes y no coincidentes con cualquier
alerta; una alerta OT o de agua no atribuye causalmente el residuo de energía.
Estos excesos son **estimaciones contrafactuales**, no ahorro observado. La
proyección de PUE y el balance neto se harán después con Misael y Gadiel.

## Entrada, salida y reproducción

Desde la raíz de `dripsafe/`, Nico puede correr N1 sobre el kit local con:

```bash
.venv/bin/python -m src.evaluacion
```

El comando busca el CSV en `DRIPSAFE_KIT/data/`, en la ruta habitual del
dashboard o, si hay una sola coincidencia, dentro de `~/dataset/`. También
acepta `--kit /ruta/al/operaciones_simuladas.csv`. Imprime PUE/WUE por sitio y
partición, además de TP/FP/FN, falsas alarmas y latencia por episodio para las
reglas fijas con OT. No crea archivos de resultados ni copia filas del kit al
repositorio.

Para incluir el detector provisional del dashboard y sus estimaciones de
exceso de energía no TI y agua:

```bash
.venv/bin/python -m src.evaluacion --vista-previa
```

Esa salida está rotulada **VISTA PREVIA**: no corresponde al modelo oficial de
Gadiel ni a ahorro medido. Los agregados de exceso positivo abarcan todas las
horas de evaluación; la cifra “coincidentes con alerta” es solo un subconjunto
de ellas, no energía o agua efectivamente ahorradas.

| Función | Entrada principal | Salida y unidad |
|---|---|---|
| `pue_wue_por_sitio` | Telemetría, partición, unidad de energía y duración | Periodo, cobertura, energía TI/total en kWh, agua in situ en L, PUE y WUE in situ en L/kWh TI |
| `exceso_no_ti` | Telemetría, alertas, columna de no TI esperado y, opcionalmente, agua esperada | Residuos firmados y excesos positivos de todas las horas de evaluación; kWh y L, con/sin alerta |
| `reglas_fijas` | Telemetría, unidad de energía y duración | `anomalia` y `motivo_regla` por sitio y hora; OT incluido por defecto |
| `evaluar_episodios` | Telemetría, alertas, ventanas y duración del intervalo | Tabla de episodios con latencia en horas; resumen TP/FP/FN y FP por día sitio |

Para el kit horario, pasar `unidad_energia="kwh_intervalo"` y
`horas_por_intervalo=1`; sus columnas mapeadas `kw_ti` y `kw_total` ya contienen
kWh. Para sintéticos con potencia media de 5 minutos, pasar
`unidad_energia="kw_promedio"` y `horas_por_intervalo=5/60`. El consumo
esperado debe tener la **misma unidad e intervalo** que el real. Los nombres de
sus columnas se indican como parámetros de la función, sin cambiar el
contrato compartido. La columna heredada `kw_esperado_enfriamiento` no debe
usarse como energía no TI sin confirmación de Gadiel: total menos TI no
desglosa enfriamiento (D18).

Ejemplo sintético, sin kit:

```python
import pandas as pd
from src.metricas.impacto import pue_wue_por_sitio

datos = pd.DataFrame({
    "site_id": ["A", "A"],
    "timestamp": pd.date_range("2026-10-01", periods=2, freq="h", tz="UTC"),
    "kw_ti": [100, 200],
    "kw_total": [150, 220],
    "agua_reposicion_l": [10, 40],
    "etiqueta_particion": ["evaluacion", "evaluacion"],
})
print(pue_wue_por_sitio(datos, particion="evaluacion",
                       unidad_energia="kwh_intervalo", horas_por_intervalo=1)[
    ["site_id", "pue", "wue_in_situ_l_kwh"]
])
# A: PUE = 370 / 300 = 1.2333; WUE = 50 / 300 = 0.1667 L/kWh TI
```

### Formato preparado para N2

La futura tabla de comparación tendrá una fila por `metodo × sitio × escenario
× magnitud × ruido × semilla`, con `tp`, `fp`, `fn`, `precision`, `recall`,
`falsas_alarmas_por_dia_sitio`, límites de su IC, latencia en horas y exceso
físico no detectado en kWh/L cuando exista manifiesto de inyección. La curva
usará la misma tabla, con magnitud de la inyección en el eje horizontal y
recall por episodio en el vertical. N1 define el formato; N2 producirá los
puntos reales al recibir G2 y U2. No se inventan resultados oficiales.

Para ejecutar las pruebas sintéticas después de implementar: `.venv/bin/python
-m pytest tests/test_n1.py -q`. Para la suite completa:
`.venv/bin/python -m pytest -q`. El kit local solo se usa para una comprobación
de lectura; sus filas no entran en Git ni en las pruebas automáticas.
