# Contrato 4 · números de DripSafe

`numeros_oficiales.json` es la fuente canónica. `python -m src.metricas.generar_numeros` genera ese archivo y la vista plana de Leo en `app/ejemplos/numeros_ejemplo.json` en la misma corrida. El nombre del archivo de Leo se conserva por compatibilidad; ahora tiene `_ejemplo: false`. La demo ficticia se movió a `app/ejemplos/numeros_demo.json` y solo se usa sin el kit.

Las entradas por fila permanecen bajo `data/`, ignorado por Git: `data/procesado/telemetria.csv`, `data/resultados/alertas.csv`, `data/resultados/deteccion_para_numeros_oficiales.json` y `data/clima/merida_era5_2025.json`. El kit crudo se lee fuera del repo. El JSON versionado contiene exclusivamente agregados y rutas relativas de código, sin filas ni rutas locales de la laptop.

Para regenerar, desde la raíz del repo, con el kit disponible:

```bash
.venv/bin/python -m src.pipeline --kit "$KIT_CSV" --sin-medir
```

Ese comando corre el detector y la rejilla, deja sus tablas bajo `data/`, y genera **ambos** JSON mediante `src.metricas.generar_numeros`. Para reproducirlo por etapas:

```bash
.venv/bin/python -m src.datos.cargar --kit "$KIT_CSV" --salida data/procesado/telemetria.csv
.venv/bin/python -m src.modelo.detector --entrada data/procesado/telemetria.csv --salida data/resultados/alertas.csv --sin-medir
.venv/bin/python -m src.ataques.correr_rejilla --entrada data/procesado/telemetria.csv
.venv/bin/python -m src.metricas.generar_numeros --descargar-clima
```

`--sin-medir` evita atribuir una medición de esta laptop a Gadiel. Sin la salida verificada de CodeCarbon de Gadiel, el costo del detector y el balance neto son `null` con `estado: pendiente`, responsable y motivo. Lo mismo ocurre con el PUE del bono sin rendimiento de chiller de Misa y el acuífero sin fuente confirmada por Guille.
Una ejecución con `--ejemplo` usa cifras inventadas y escribe únicamente un diagnóstico bajo `data/`; nunca lee el JSON canónico como plantilla ni reemplaza los archivos versionados.
`--descargar-clima` guarda las 8760 horas de ERA5 2025 bajo `data/` para reproducir los agregados climáticos; sin red también puede pasarse un archivo ya descargado con `--clima`.

Cada métrica tiene `valor`, `unidad`, `tipo` (`observado`, `medido`, `estimado`, `proyectado`), `origen`, `responsable` y `estado`. Las métricas pendientes llevan `motivo_pendiente`. `_meta.periodos` separa 216 horas-sitio de referencia de 288 de evaluación. `pue.antes` y `pue.despues_proyectado` se refieren a **la misma evaluación**; `pue.referencia` se conserva aparte. El exceso es residuo estimado en horas con alerta física, no ahorro observado. `periodos_y_sitios` incluye PUE/WUE y exceso por sitio y unidad.

La comparación original cuenta 3 episodios que cubren 21 horas anómalas. La rejilla de inyecciones cuenta inyecciones, no esas horas. Las clases OT cuentan horas, con claves iguales a `src/ot/clases.py`. Las horas de respaldo de Mérida usan temperatura horaria ERA5 de 2025 ([API histórica Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api)); son un proxy climático y no miden operación real del chiller. Los factores de emisión e intensidad hídrica siguen pendientes hasta verificar y documentar la fuente y periodo aplicables.

El sello `DATOS SIMULADOS` es obligatorio. Los números del kit prueban el método en simulación; no describen una instalación real.
El escenario inicial usa **6 fallas por sitio y año**, 20 % de exceso no TI, 72 h de duración sin alerta y 4 h hasta corrección con alerta; suma las tasas horarias de los tres sitios para energía y solo SIM-B para agua. Estos son supuestos editables, no frecuencias observadas.
