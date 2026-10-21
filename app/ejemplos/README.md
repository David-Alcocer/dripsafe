# Archivos de cifras del dashboard

`numeros_ejemplo.json` conserva el nombre que usa Leo, pero ahora es la **vista oficial plana** de `resultados/numeros_oficiales.json`, generada por `python -m src.metricas.generar_numeros`. Lleva `_ejemplo: false`, procedencia, periodo, unidad, tipo y estados pendientes. No se edita a mano.

`numeros_demo.json` contiene los antiguos valores ficticios. Se carga si falta
el kit o si el CSV local tiene un hash distinto al del kit fijado en
`resultados/n2_congelamiento.json`: la app avisa y evita asociar las alertas o
las cifras de N2 a otra telemetría. Esos valores se etiquetan **Ejemplo** y
nunca pasan al JSON oficial ni al pitch.

Las claves planas principales son `pue_referencia`, `pue_antes`, `pue_sin_exceso`, `wue_referencia`, `wue_antes`, `wue_sin_exceso`, `punto_ciego_pct`, `exceso_energia_kwh`, `exceso_agua_l`, `detector_cpu_ms`, `detector_kwh_anual`, `detector_gco2e_anual`, `equilibrio_horas`, `comparacion`, `comparacion_por_sitio`, `curva_sensibilidad`, `rejilla_completa`, `rejilla_por_sitio`, `robustez`, `ruido_por_escenario`, `falsas_alarmas_ruido`, `bono_horas_respaldo` y `escenario_anual`. `comparacion` cuenta episodios; `comparacion_por_sitio` separa episodios y horas. La curva muestra recall por episodio; el efecto físico visto y el exceso no visto conservan sus propios campos. `rejilla_por_sitio` incluye planeadas, ejecutadas y omitidas. Las falsas alarmas del ruido se miden sobre bases limpias, sin asignarlas a cada inyección. Los pendientes conservan `valor: null` y `motivo_pendiente`.

La salida del detector que consume la app está en `data/resultados/alertas.csv`, una fila por sitio y hora. Su contrato vive en `src/modelo/detector.py` y `app/linea_base.COLUMNAS`; incluye línea base esperada, residuos, banderas físicas y clase OT. Las clases son `normal`, `incidente_ot`, `cambio_no_autorizado`, `escalon_sin_registro` e `intento_acceso`.
