# N3 · Entrega de Nico para revisión con Misa

Estado: **preparado para revisión; balance neto sin firma conjunta**. Trabajar
solo con los agregados versionados. El kit y las tablas intermedias no forman
parte de esta entrega.

## Cuenta anual auditada

- `periodos_y_sitios.referencia.energia_no_ti_kwh` = **9501.1089 kWh** para
  **los tres sitios juntos** durante 72 horas comunes. Las 216 horas-sitio
  suman 72 horas de cada sitio; no se multiplica la energía otra vez por tres.
- Escenario editable: 6 fallas por sitio y año, 72 h sin alerta, 4 h hasta
  corregir y 20 % de exceso no TI. La cuenta usa la energía agregada sin
  redondear a la tasa horaria mostrada:

  `9501.1089 kWh / 72 h × 6/año × (72 − 4) h × 0.20 = 10767.92342 kWh/año`

- Se publica **10767.9234 kWh/año** como ahorro **proyectado**. No es ahorro
  observado. El resultado depende de que esas fallas y ese tiempo de
  corrección representen el escenario futuro.

## G3 incorporado para revisión

En `resultados/numeros_oficiales.json` y su vista plana para Leo:

| Concepto | Valor publicado | Tipo |
| --- | ---: | --- |
| Entrenamiento anual | 2.04099e-07 kWh/año | estimado |
| Inferencia anual | 1.2712085e-05 kWh/año | estimado |
| Costo anual total | 1.2916184e-05 kWh/año | estimado |
| Tiempo del detector | 33.641 ms | medido |
| Razón ahorro/costo | 833676835.2 veces | proyectado |

La anualización usa fases separadas: 168 h por lote, 8760 h/año,
1 lote/h y 4 reentrenamientos/año. Entrenamiento + inferencia = costo total;
la corrida completa no se suma. La energía de G3 proviene de una estimación
CodeCarbon basada en TDP, no de un sensor de pared. La razón se calcula con
el **costo publicado redondeado**; por ello difiere del valor enviado antes
por Gadiel, que dividía entre un costo con más decimales.

La procedencia versionada incluye los hashes del kit y manifiesto, el commit
de código de la medición, el equipo, el método y diez repeticiones. Ninguno
de los JSON de esta entrega incluye filas del kit.

## Pendientes para Misa + Nico

1. Revisar juntos que 1 lote/h, 4 reentrenamientos/año y el escenario de
   6 fallas, 20 %, 72 h y 4 h sean supuestos que quieren presentar. Comprobar
   que la etiqueta `proyectado` y sus límites sean visibles en el pitch.
2. Resolver el **umbral de equilibrio** con una procedencia verificable de la
   mediana de exceso no TI por hora con alerta física. Ese denominador no
   aparece en los agregados versionados; el umbral sigue en `null`. No adoptar
   como validado el número enviado por Gadiel sin reproducirlo.
3. Acordar la atribución y anualización de CO₂ antes de publicar emisiones.
   El campo anual de emisiones sigue en `null`.
4. `balance_neto.balance_energia_kwh_anual` ya está en el JSON oficial y en
   la vista de Leo como `null` con motivo. Tras la revisión conjunta,
   calcularlo como ahorro proyectado menos costo anual, en `kWh/año`, tipo
   `proyectado`, con fuentes y supuestos.
5. Solo después de que ambos aprueben explícitamente el resultado, ejecutar
   la firma conjunta; `balance_neto.validado_por` sigue en `null`.

## Verificación de esta entrega

- `tests/test_numeros_oficiales.py` y `tests/test_pipeline.py`: 48 pruebas
  aprobadas, incluidas entradas positivas, cero, negativas, no finitas y
  booleanas para `balance_energia_anual()`.
- `python -m src.procedencia --validar-oficial resultados/numeros_oficiales.json`
  y el validador del contrato:
  sin problemas. La vista de Leo coincide con `plano(numeros_oficiales)`.

La revisión de Misa debe centrarse en el bloque `balance_neto`, la
procedencia G3 y estos supuestos. No se ha firmado ni cerrado N3.
