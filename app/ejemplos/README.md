# Archivos de cifras del dashboard

`resultados/numeros_oficiales.json` es el único archivo de cifras. La app obtiene la vista plana para sus paneles con `src.metricas.generar_numeros.plano()` en memoria. Esa vista lleva `_ejemplo: false`, procedencia, periodo, unidad, tipo y estados pendientes.

Si falta el kit, solo la telemetría y las métricas calculadas desde ella son
**Ejemplo**. Las cifras consolidadas siguen siendo las del kit fijado en el
JSON oficial; la app avisa que no deben compararse con las gráficas de ejemplo.
Si el CSV local tiene otro hash, tampoco se usan las alertas calculadas para
el kit fijado.

Las claves planas principales son `pue_referencia`, `pue_antes`, `pue_sin_exceso`, `wue_referencia`, `wue_antes`, `wue_sin_exceso`, `punto_ciego_pct`, `exceso_energia_kwh`, `exceso_agua_l`, `detector_cpu_ms`, `detector_kwh_anual`, `detector_gco2e_anual`, `equilibrio_horas`, `comparacion`, `comparacion_por_sitio`, `curva_sensibilidad`, `rejilla_completa`, `rejilla_por_sitio`, `robustez`, `ruido_por_escenario`, `falsas_alarmas_ruido`, `bono_horas_respaldo` y `escenario_anual`. `comparacion` cuenta episodios; `comparacion_por_sitio` separa episodios y horas. La curva muestra recall por episodio; el efecto físico visto y el exceso no visto conservan sus propios campos. `rejilla_por_sitio` incluye planeadas, ejecutadas y omitidas. Las falsas alarmas del ruido se miden sobre bases limpias, sin asignarlas a cada inyección. Los pendientes conservan `valor: null` y `motivo_pendiente`.

La salida del detector que consume la app está en `data/resultados/alertas.csv`, una fila por sitio y hora. Su contrato vive en `src/modelo/detector.py` y `app/linea_base.COLUMNAS`; incluye línea base esperada, residuos, banderas físicas y clase OT. Las clases son `normal`, `incidente_ot`, `cambio_no_autorizado`, `escalon_sin_registro` e `intento_acceso`.
