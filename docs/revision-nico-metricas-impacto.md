# Revisión de Nico · Métricas de impacto

**Fecha:** 19 de octubre de 2026
**Base revisada:** kit local en `/home/nicolas/dataset` y `main` de GitHub en `49b0651`
**Estado:** revisión metodológica; ninguna cifra de exceso o ahorro es resultado oficial.

> Esta revisión describe el borrador anterior a la implementación de N1. El
> estado actualizado y las pruebas están en [reporte-n1.md](reporte-n1.md).

## Qué confirma el kit

El CSV `operaciones_simuladas.csv` contiene **datos totalmente simulados**: 504 filas de tres sitios ficticios, con 168 intervalos horarios por sitio. Cada sitio tiene 72 horas de `referencia` y 96 de `evaluacion`. Hay 21 horas etiquetadas como anómalas. En la revisión no aparecieron valores ausentes ni duplicados por sitio y hora.

Según `docs/DATA_DICTIONARY.md` del kit, `energy_it_kwh` y `energy_total_kwh` son **kWh por intervalo de una hora**. `water_l` son litros de captación operativa *in situ* por intervalo; no son consumo neto, agua potable ni huella hídrica total.

| Periodo, tres sitios | Filas | Energía TI | Energía total | Agua *in situ* | PUE | WUE ilustrativo |
|---|---:|---:|---:|---:|---:|---:|
| Referencia | 216 | 35 509.846 kWh | 45 010.955 kWh | 13 013.015 L | 1.26756 | 0.36646 L/kWh TI |
| Evaluación | 288 | 47 146.578 kWh | 60 245.050 kWh | 18 580.130 L | 1.27782 | 0.39409 L/kWh TI |

Estas cifras son **cocientes de sumas**. La diferencia entre periodos no demuestra ahorro ni un efecto del detector: también cambian las condiciones simuladas.

## 1. PUE y WUE: conservar el cálculo y fijar el perímetro

[`src/metricas/impacto.py`](../src/metricas/impacto.py) suma primero la energía y el agua por sitio, y después divide. Ese criterio coincide con `common/cifox.py` y `docs/METRICS.md` del kit. Con `horas_por_intervalo=1`, la función reproduce los agregados por sitio del CSV.

**Mejora prioritaria:** cada resultado debe identificar sitio, partición, inicio, fin, cantidad de intervalos y unidad de entrada. La función actual suma cualquier fila que reciba; si se mezclan referencia y evaluación, la cifra resultante no representa ninguno de los dos periodos.

También debe conservarse el detalle por sitio. En evaluación, el WUE aproximado es **0.032 L/kWh** en SIM-A, **0.937** en SIM-B y **0.213** en SIM-C. El valor global se calcula dividiendo las sumas globales, nunca promediando los tres WUE.

### Comparación del PUE proyectado

**Corregido (#4 y contrato 4):** [`resultados/numeros_oficiales.json`](../resultados/numeros_oficiales.json) separa `pue.referencia` (216 filas de referencia, línea base normal) de `pue.antes` (288 filas de evaluación, tal como vienen). `src/metricas/pue.py` calcula el PUE inicial para el diagnóstico y `src/metricas/generar_numeros.py` genera las cifras canónicas y la vista de Leo. Antes se usaba como `pue.antes` el PUE de referencia. El punto de partida para proyectar el efecto sobre evaluación es su PUE **observado** y el denominador sigue siendo la energía TI del mismo periodo:

```text
PUE observado, evaluación = 60 245.050 kWh / 47 146.578 kWh
PUE proyectado, evaluación = (60 245.050 kWh − exceso evitable estimado) / 47 146.578 kWh
```

El PUE de referencia sigue siendo útil como línea base descriptiva, pero se informa por separado. La proyección no es un ahorro observado.

## 2. Unidades: resolver el significado de `kw_ti` y `kw_total`

[`config/columnas.json`](../config/columnas.json) renombra `energy_it_kwh` a `kw_ti` y `energy_total_kwh` a `kw_total`. En el kit horario multiplicar esos valores por `horas_por_intervalo=1` no cambia el resultado, pero los nombres sugieren potencia en kW cuando el CSV ya contiene energía en kWh.

Antes de usar otros intervalos, Nico y Misael deben acordar si el contrato entrega **kW promedio** o **kWh por intervalo**. Si ya entrega kWh, no se multiplica de nuevo por la duración. El consumo esperado de Gadiel debe usar la misma unidad y el mismo intervalo que el consumo real.

## 3. Exceso estimado: separar residuo, detección y proyección

La función borrador `exceso_no_ti()` calcula el exceso positivo de energía **no TI** solo en horas con `anomalia=True`. Eso sirve para una primera estimación de exceso identificado, pero asigna cero a toda hora sin alerta. Así no permite medir los kWh que un método **no detectó** en la curva de sensibilidad.

El orden propuesto es:

1. Calcular el residuo `energía no TI real − energía no TI esperada` en **todas** las horas de evaluación, por sitio y hora.
2. Conservar el exceso positivo estimado y distinguir el que coincide con una alerta física del que queda sin alerta.
3. Para inyecciones, usar el manifiesto y su magnitud conocida al evaluar exceso no detectado; no tratar cualquier residuo positivo como una falla verdadera.
4. Mantener aparte el **ahorro proyectado**, que necesita un supuesto explícito de corrección y tiempo de respuesta.

El GitHub nuevo incluye [`app/linea_base.py`](../app/linea_base.py), una **vista previa**, con `esperado_energia_no_ti_kwh` y `esperado_agua_l`. Es útil para comprobar la interfaz con el kit, pero la salida oficial debe acordarse con Gadiel. El contrato anterior todavía menciona `kw_esperado_enfriamiento`; el kit no desglosa enfriamiento, UPS y demás auxiliares, así que la diferencia `total − TI` se llama **energía no TI** (D18).

Para atribuir impacto conviene separar alertas físicas de eventos OT y, dentro de las físicas, distinguir energía de agua. [`app/cargar.py`](../app/cargar.py) utiliza una bandera física conjunta: una alerta de agua puede incluir un pequeño residuo positivo de energía por ruido. Ese residuo no debe convertirse automáticamente en ahorro energético atribuible a la fuga.

## 4. Agua y procedencia de las cifras

El borrador de `impacto.py` aún no calcula litros de exceso. La vista previa sí entrega agua esperada, pero antes de publicar una cifra se necesita su equivalente en la salida oficial del modelo y una definición de qué alerta permite atribuir el exceso. El resultado se llama **exceso estimado de captación in situ**, nunca agua potable ahorrada.

**Corregido (#4 y contrato 4):** `src/metricas/pue.py` ya existe; el diagnóstico de `src.pipeline --ejemplo` reporta `filas` (horas-sitio) y `horas_reloj`. El contrato 4 guarda ambos periodos en `_meta.periodos` y el exceso estimado se refiere a las 288 horas-sitio de evaluación. Texto original de la revisión:

El JSON actual es un **ejemplo con resultados pendientes**. Su `pue.antes` cita `src/metricas/pue.py`, archivo que todavía no existe en el repositorio; el valor proviene del `reference_metrics.json` del kit. En `_meta.periodo`, `horas: 504` significa **504 horas-sitio**, equivalentes a 168 horas de reloj en tres sitios. La nota de `exceso_estimado` debe expresar **96 horas de evaluación × 3 sitios = 288 filas**, para evitar una extrapolación triple.

## Acuerdos y pasos siguientes de Nico

1. Con Misael, cerrar unidad canónica, partición y periodo para energía y agua; conservar trazabilidad del PUE inicial.
2. Con Gadiel, cerrar nombres y unidades de energía no TI y agua esperadas, además de banderas específicas para cada variable.
3. Revisar `pue_wue_por_sitio()` para que informe periodo y cobertura, y probarlo contra agregados del kit sin guardar filas en Git.
4. Revisar `exceso_no_ti()` para conservar residuos de todas las horas y separar detectado, no detectado y proyección.
5. Solo después, llenar los campos correspondientes de `numeros_oficiales.json` con fuente, periodo, unidad y etiqueta `observado/estimado/proyectado`.

## Nota de integración del GitHub nuevo

[`app/kit.py`](../app/kit.py) busca el CSV fuera del repositorio. En esta laptop, su ruta predeterminada no apunta a `/home/nicolas/dataset`; hay que configurar `DRIPSAFE_KIT` con la carpeta del kit que contiene `data/` y `docs/`. No se debe copiar el CSV al repositorio.

La app actualmente considera “oficial” cualquier `resultados/numeros_oficiales.json` existente, aunque el archivo presente se declara **de ejemplo**. Esa distinción debe resolverse antes de usar el dashboard como evidencia final.
