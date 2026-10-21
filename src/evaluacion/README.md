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

### Paso 2 · Auditoría de la rejilla

Después de correr U2 con el mismo CSV del kit, la auditoría comprueba que la
fuente coincide con el hash fijado en el paso 1 y que el código del detector
conserva sus hashes. Verifica todas las combinaciones de sitio, inyección e
inicio, que cada inyección ejecutada tenga exactamente un resultado por método,
que cada omisión tenga motivo y que las posiciones y omisiones sean las mismas
en la base y en las cinco semillas de ruido. U2 verifica además que cada copia
conserve los parámetros aprendidos de su condición.

```bash
KIT_CSV=/ruta/local/al/kit/data/operaciones_simuladas.csv
python -m src.ataques.correr_rejilla --kit "$KIT_CSV"
python -m src.evaluacion.auditar_rejilla
```

La corrida de U2 evalúa cientos de copias y puede tardar varios minutos;
informa el avance cada 24 posiciones. Si ya existe `rejilla_por_inyeccion.csv`
y solo se quieren revisar los denominadores, basta ejecutar el segundo
comando, que no vuelve a correr el detector.

En el kit fijado hubo **144 posiciones planeadas por condición** (3 sitios ×
8 inyecciones × 6 inicios), **141 ejecutadas y 3 omitidas**. SIM-C no tuvo
ventana limpia para `cambio_sin_registro` a las 66 h ni para
`cambio_con_efecto` a las 54 y 66 h. Por tanto, los denominadores por
inyección son 18, excepto esos cambios: 17 y 16, respectivamente. Los mismos
lugares y omisiones se conservaron en las cinco semillas; entre seis corridas
hay 846 inyecciones y 1692 filas de resultados para dos métodos.

`data/resultados/n2_auditoria_rejilla.csv` incluye **las 864 posiciones
planeadas**, ejecutadas u omitidas, con el motivo y desplazamiento.
`data/resultados/n2_auditoria_denominadores.csv` separa planeadas, ejecutadas
y omitidas por condición, semilla, sitio e inyección. Ambas tablas, el
manifiesto de U2 y los resultados por método permanecen bajo `data/`, fuera de
Git. Los porcentajes de detección usan solo inyecciones ejecutadas como
denominador; nunca convierten una omisión en fallo del detector.

### Paso 3 · Comparación del kit original

Desde la raíz del repositorio, con el CSV local del kit disponible:

```bash
.venv/bin/python -m src.evaluacion.comparar_originales --kit "$KIT_CSV"
```

Si `.venv` está en otro checkout, se puede usar su Python con la ruta completa.
El comando comprueba el hash del CSV y su `MANIFEST.json`, los archivos del
detector y las ventanas de evaluación contra `resultados/n2_congelamiento.json`.
Usa la misma telemetría y el mismo registro OT para DripSafe y las cuatro
reglas. Las etiquetas solo se consultan para puntuar, nunca para predecir.

`data/resultados/n2_originales_comparacion.csv` contiene una fila por método y
sitio, además de `TOTAL`. `data/resultados/n2_originales_episodios.csv` registra
la detección y latencia de cada episodio por método. Ambos quedan fuera
de Git. Las 96 horas de evaluación de cada sitio son **horas-sitio**; el total
son 288 horas-sitio, no 96 horas de reloj. Hay 267 horas-sitio limpias.

| Método | Sitio | Episodios TP/FP/FN | Horas TP/FP/FN | Precisión/recall (episodios y horas) | Latencia media |
|---|---|---:|---:|---:|---:|
| DripSafe | SIM-A | 1/0/0 | 8/0/0 | 100 % / 100 % | 0 h |
| DripSafe | SIM-B | 1/0/0 | 8/0/0 | 100 % / 100 % | 0 h |
| DripSafe | SIM-C | 1/0/0 | 5/0/0 | 100 % / 100 % | 0 h |
| DripSafe | TOTAL | 3/0/0 | 21/0/0 | 100 % / 100 % | 0 h |
| Reglas del kit | SIM-A | 1/0/0 | 8/0/0 | 100 % / 100 % | 0 h |
| Reglas del kit | SIM-B | 1/0/0 | 8/0/0 | 100 % / 100 % | 0 h |
| Reglas del kit | SIM-C | 1/0/0 | 5/0/0 | 100 % / 100 % | 0 h |
| Reglas del kit | TOTAL | 3/0/0 | 21/0/0 | 100 % / 100 % | 0 h |

Por episodio, TP significa al menos una alerta dentro de la ventana y FP es
un tramo continuo alertado fuera de ella. Por hora, cada hora verdadera o
falsa se cuenta individualmente. La latencia va del inicio del episodio a su
primera alerta. Ambos métodos empatan en estos tres episodios simulados del
kit; el kit fue diseñado para las reglas y este empate no demuestra rendimiento
fuera de él. Esta comparación no incluye la medición de costo de Gadiel.

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

### Paso 4 · Sensibilidad, ruido y cierre de N2

Después de los pasos 2 y 3, ejecutar:

```bash
.venv/bin/python -m src.evaluacion.cerrar_n2 --kit "$KIT_CSV"
.venv/bin/python -m src.metricas.generar_numeros
```

El primer comando verifica otra vez el kit y el detector fijados, las 144
posiciones planeadas por condición (864 entre las seis), la rejilla y los
parámetros de ruido. Recalcula las bases sin inyecciones de las cinco semillas
y exige que sus TP, FP, exposición limpia y latencias coincidan con U2. También
comprueba las unidades, atributos, banderas y latencias de cada inyección.
Deja `data/resultados/n2_tabla_final.csv` con una fila por condición, semilla,
sitio, inyección y método; y `data/resultados/n2_cierre.json` con agregados.
Ambos permanecen fuera de Git. El generador copia **solo agregados** del cierre
al Contrato 4 y a la vista plana de Leo, tras comparar los originales, la
curva y el ruido con el bloque de U2. El pipeline oficial hace esta auditoría
automáticamente; con `--ejemplo` conserva el flujo de datos ficticios.

| Condición | Método | Episodios detectados | Efectos físicos vistos |
|---|---|---:|---:|
| Base, 141 inyecciones ejecutadas | DripSafe | 141/141 | 141/141 |
| Base, 141 inyecciones ejecutadas | Reglas | 22/141 | 6/141 |
| Ruido, cinco semillas × 141 | DripSafe | 625/705 | 623/705 |
| Ruido, cinco semillas × 141 | Reglas | 110/705 | 30/705 |

En la curva de energía de 4 h y sin ruido, DripSafe detectó 18/18 episodios
en cada magnitud (+10, +20, +40 y +80 % de energía no TI). Las reglas
detectaron 0/18, 0/18, 0/18 y 6/18. Con ruido extra, el caso de +10 % bajó
a 30/90 episodios en DripSafe; +20 % alcanzó 72/90. Esos fallos se conservan
en el JSON. El ruido añade una desviación normal de 1.5 % de la energía TI a
la energía total y un factor uniforme de ±4 % al agua en ajuste, calibración
y evaluación. Las semillas fijadas son 1–5.

`cambio_con_efecto` ilustra por qué hay dos métricas: las reglas detectaron el
evento OT en 16/16 episodios de la base, pero no marcaron el exceso físico
posterior en ninguna de esas 16 copias. Con ruido, DripSafe detectó ese
episodio en 80/80 copias y vio el efecto en 78/80. La exactitud de clase OT
se calcula **solo donde hubo efecto físico visto**; no convierte los casos
sin detección en clasificaciones correctas. El exceso no visto se informa en
kWh o L de inyección, según la variable.

Las falsas alarmas se miden en las **267 horas-sitio limpias de cada condición
sin inyecciones**, no se asignan a una copia inyectada. Por eso la tabla de
inyecciones informa TP, FN y recall por episodio, mientras que precisión y FP
se informan en las bases limpias. En la base original hubo
0 para ambos métodos; con ruido, DripSafe tuvo 2 tramos falsos en la semilla
1 y 2 en la 4, y 0 en las demás. Las reglas tuvieron 0 en las cinco. La
media de DripSafe fue 0.0719 falsas alarmas por día y sitio. Son cinco
perturbaciones del mismo kit, no cinco instalaciones independientes.

El JSON permanece **parcial**: Gadiel no ha entregado su medición repetida
de tiempo, energía y CodeCarbon. El costo, el equilibrio y el balance que
dependen de ella siguen en `null`. La evaluación de calidad y robustez de N2
sí queda cerrada con la versión local del detector, sujeta a la confirmación
de Gadiel de que corresponde a su versión final.

Para ejecutar las pruebas sintéticas después de implementar: `.venv/bin/python
-m pytest tests/test_n1.py -q`. Para la suite completa:
`.venv/bin/python -m pytest -q`. El kit local solo se usa para una comprobación
de lectura; sus filas no entran en Git ni en las pruebas automáticas.
