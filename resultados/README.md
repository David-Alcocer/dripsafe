# Contrato 4 · números de DripSafe

`numeros_oficiales.json` es el único archivo versionado de cifras. `python -m src.metricas.generar_numeros` lo genera; la app deriva la vista plana con `plano()` en memoria. También se muestran estas cifras en la demo sin kit local, con su procedencia y un aviso que las separa de la telemetría inventada.

Las entradas por fila permanecen bajo `data/`, ignorado por Git: `data/procesado/telemetria.csv`, `data/resultados/alertas.csv`, `data/resultados/deteccion_para_numeros_oficiales.json` y `data/clima/merida_era5_2025.json`. El kit crudo se lee fuera del repo. El JSON versionado contiene exclusivamente agregados y rutas relativas de código, sin filas ni rutas locales de la laptop.

Para regenerar, desde la raíz del repo, con el kit disponible:

```bash
.venv/bin/python -m src.datos.cargar --kit "$KIT_CSV" --salida data/procesado/telemetria.csv
.venv/bin/python -m src.modelo.detector --entrada data/procesado/telemetria.csv --salida data/resultados/alertas.csv --sin-medir
.venv/bin/python -m src.ataques.correr_rejilla --kit "$KIT_CSV"
.venv/bin/python -m src.evaluacion.comparar_originales --kit "$KIT_CSV"
.venv/bin/python -m src.evaluacion.cerrar_n2 --kit "$KIT_CSV"
.venv/bin/python -m src.metricas.generar_numeros --descargar-clima
```

`--sin-medir` evita atribuir una medición de esta laptop a Gadiel. Sin la salida verificada de CodeCarbon de Gadiel, el costo del detector y el balance neto son `null` con `estado: pendiente`, responsable y motivo. Lo mismo ocurre con el PUE del bono sin rendimiento de chiller de Misa y el acuífero sin fuente confirmada por Guille.

La medición G3 usa el formato 2 de `consumo_modelo.json`: sella hashes del kit y del código, equipo y método, y guarda el kWh de **cada** repetición en tres fases (`entrenamiento`, `inferencia`, `corrida_completa`). El balance anualiza `(inferencia / lote.horas) × horas × lotes + entrenamiento × reentrenamientos`; la corrida completa no se suma porque ya incluye el ajuste. Un archivo v1 se acepta como cota superior y no se le suma reentrenamiento. La frecuencia (8 760 h y 4 reentrenamientos) es un supuesto editable, no una medición; `--validacion-conjunta` deja constancia de que Misa y Nico revisaron el balance.
`--descargar-clima` guarda las 8760 horas de ERA5 2025 bajo `data/` para reproducir los agregados climáticos; sin red también puede pasarse un archivo ya descargado con `--clima`.
Si ya existen las salidas auditadas de U2 y la serie climática, se pueden
omitir la corrida de `correr_rejilla` y `--descargar-clima`. El cierre de N2
requiere la base y las cinco semillas de ruido, y genera
`data/resultados/n2_cierre.json`; el generador oficial exige ese archivo.
`python -m src.pipeline --sin-medir --sin-rejilla` también verifica y agrega
N2 automáticamente al reutilizar las salidas de U2.

Cada métrica tiene `valor`, `unidad`, `tipo` (`observado`, `medido`, `estimado`, `proyectado`), `origen`, `responsable` y `estado`. Las métricas pendientes llevan `motivo_pendiente`. `_meta.periodos` separa 216 horas-sitio de referencia de 288 de evaluación. `pue.antes` y `pue.despues_proyectado` se refieren a **la misma evaluación**; `pue.referencia` se conserva aparte. El exceso es residuo estimado en horas con alerta física, no ahorro observado. `periodos_y_sitios` incluye PUE/WUE y exceso por sitio y unidad.

La comparación original cuenta 3 episodios que cubren 21 horas anómalas. La rejilla de inyecciones cuenta inyecciones, no esas horas. Las clases OT cuentan horas, con claves iguales a `src/ot/clases.py`. Las horas de respaldo de Mérida usan temperatura horaria ERA5 de 2025 ([API histórica Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api)); son un proxy climático y no miden operación real del chiller. Los factores de emisión e intensidad hídrica siguen pendientes hasta verificar y documentar la fuente y periodo aplicables.

`deteccion.comparacion_contra_reglas_kit.cierre_n2` conserva solo agregados
auditados: comparación original por método y sitio, tabla base por inyección y
sitio, curva por magnitud, resultados de cinco semillas y falsas alarmas sobre
las bases limpias. La vista plana de Leo expone esos grupos como
`comparacion_por_sitio`, `rejilla_por_sitio`, `ruido_por_escenario` y
`falsas_alarmas_ruido`. En `cambio_con_efecto`, una alerta OT puede contar como
episodio detectado aun si el exceso físico posterior no se vio; ambos conteos
se conservan por separado. Una inyección omitida no entra al denominador.

El sello `DATOS SIMULADOS` es obligatorio. Los números del kit prueban el método en simulación; no describen una instalación real.
El escenario inicial usa **6 fallas por sitio y año**, 20 % de exceso no TI, 72 h de duración sin alerta y 4 h hasta corrección con alerta; suma las tasas horarias de los tres sitios para energía y solo SIM-B para agua. Estos son supuestos editables, no frecuencias observadas.
