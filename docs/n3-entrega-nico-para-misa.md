# N3 · Entrega de Nico para revisión con Misa

Estado: **balance energético firmado por Misa y Nico; factores externos
integrados**. La firma cubre los cálculos, supuestos y límites del balance
energético. CO₂ y agua indirecta se publican como proyecciones con factores
externos: el FESEN es oficial y la intensidad hídrica es una estimación
trazable NREL/CNE, no un factor oficial mexicano. El kit y las tablas
intermedias permanecen fuera de Git.

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
| Saldo energético anual | 10767.923387083816 kWh/año | proyectado |
| Umbral de equilibrio | 2.38926e-07 h/año | proyectado |
| Emisiones del detector | 0.00573479 gCO₂e/año | estimado |
| CO₂ evitado | 4780.9580 kgCO₂e/año | proyectado |
| Agua indirecta evitada | 22216.3796 L/año | proyectado |
| Factor de emisión SEN | 0.444 kgCO₂e/kWh | oficial |
| Intensidad hídrica SEN | 2.0632 L/kWh | estimado |

La anualización usa fases separadas: 168 h por lote, 8760 h/año,
1 lote/h y 4 reentrenamientos/año. Entrenamiento + inferencia = costo total;
la corrida completa no se suma. La energía de G3 proviene de una estimación
CodeCarbon basada en TDP, no de un sensor de pared. La razón se calcula con
el **costo publicado redondeado**; por ello difiere del valor enviado antes
por Gadiel, que dividía entre un costo con más decimales.

La procedencia versionada incluye los hashes del kit y manifiesto, el commit
de código de la medición, el equipo, el método y diez repeticiones. Ninguno
de los JSON de esta entrega incluye filas del kit.

## Saldo y umbral listos para revisar

El saldo es **ahorro publicado − costo publicado**, redondeado a 12
decimales. A cuatro decimales se ve igual que el ahorro porque el costo es
muy pequeño. Los decimales conservados permiten comprobar la resta y no
representan precisión de una medición física.

El umbral se reproduce con `balance_neto.umbral_equilibrio.supuestos`:

- Periodo: evaluación; intervalo: 1 h; tres sitios.
- Selección: `alerta_umbral OR alerta_media_4h`; se excluyen los excesos cero.
- 16 horas-sitio con alerta física, de las cuales 13 tienen exceso no TI positivo.
- Mediana publicada: **54.059454375881 kWh/h por sitio**.
- Cuenta: `round(1.2916184e-05 / 54.059454375881, 12) = 2.38926e-07 h/año`.

Se trata de horas de exceso típico en un sitio que compensarían el costo
anual del detector para los tres sitios. Es un umbral algebraico con energía
estimada por TDP, **no una latencia demostrada**: el kit tiene resolución de
una hora y no permite afirmar que se detecta o corrige una falla en ese tiempo.
Si otra corrida no aporta una mediana positiva, el umbral queda `null` con motivo.

## Decisiones propuestas para la revisión conjunta

1. Revisar juntos que 1 lote/h, 4 reentrenamientos/año y el escenario de
   6 fallas, 20 %, 72 h y 4 h sean supuestos que quieren presentar. Comprobar
   que la etiqueta `proyectado` y sus límites sean visibles en el pitch.
2. Conservar la política de operandos publicados: costo a 12 decimales,
   razón a una décima y saldo/umbral a 12 decimales. El costo incluye
   entrenamiento e inferencia pura; no se añade la corrida completa.
3. Revisar el agregado del umbral y el saldo calculado. Ambos se presentan
   como `proyectado`; la disponibilidad del cálculo no equivale a firma.
4. Publicar CO₂ y agua indirecta solo como **proyecciones**: usan el ahorro
   proyectado, no un ahorro observado. El factor de emisión es el 0.444
   kgCO₂e/kWh del FESEN 2024 aplicable a la COA 2026. La intensidad hídrica
   de 2.0632 L/kWh es una estimación NREL 2012 × mezcla CNE 2024; debe
   revisarse antes de presentarla como cifra propia del proyecto.
5. Registrar la firma conjunta solo cuando Misa y Nico hayan aprobado
   explícitamente el resultado. La firma existente cubre el balance
   energético; no acredita los nuevos factores externos.

Fuera de esta firma permanecen `pue_con_bono` (Misa, #15) y el dato oficial
del acuífero 3105 (Nico, #13, ajuste `678b5ff`). Se mantienen `null` y sus
motivos; `_meta.estado` permanece `parcial`.

## Alcance respecto de G3 en `1be2759`

G3 conserva intactos el equipo, las repeticiones, el método TDP y el commit
`1be2759` de la ejecución original. Se verificó que los hashes del kit y de
`src/modelo/detector.py`, `src/modelo/medicion.py`, `src/ot/clases.py`,
`src/datos/cargar.py`, `src/contrato.py` y `config/columnas.json` coinciden con G3.

Los cambios posteriores en `src/metricas/balance_neto.py` y `src/pipeline.py`
afectan cómo se calcula y publica el balance a partir de G3. Esta preparación
añade el agregado de la mediana en `generar_numeros.py` y comprobaciones del
JSON oficial en `procedencia.py`; no cambia las fases medidas del detector.
G3 no mide el consumo de ejecutar toda la rejilla ni de generar el informe.
`_meta.generado_con_commit` identifica el código de consolidación y
`_meta.procedencia_g3.codigo.commit` identifica el código de la medición.

La corrida completa del pipeline sobre el kit conservó PUE, WUE, evaluación
N2, ahorro proyectado, costo y razón. Los cambios numéricos son el saldo, el
umbral, las emisiones del detector, el CO₂ evitado y el agua indirecta. Estos
tres últimos son proyecciones o estimaciones con factores externos, no
mediciones locales.

## Cómo regenerar y firmar

Desde un checkout limpio que contenga esta preparación, definir `KIT_CSV`
con la ruta local al CSV confidencial y activar el entorno Python del repo.
Para revisar sin firmar:

```bash
python -m src.pipeline --kit "$KIT_CSV" --sin-medir \
  --consumo resultados/g3_consumo_modelo.json
python -m src.procedencia --validar-oficial resultados/numeros_oficiales.json
```

El validador informa explícitamente que la firma está pendiente. Guardar en
Git el código y los resultados revisados antes de la corrida final para que
el nuevo JSON cite un commit limpio. Cuando ambos hayan aprobado:

```bash
python -m src.pipeline --kit "$KIT_CSV" --sin-medir \
  --consumo resultados/g3_consumo_modelo.json --validacion-conjunta
python -m src.procedencia --validar-oficial resultados/numeros_oficiales.json --exigir-firma
```

La firma escribe `validado_por: ["Misa", "Nico"]`, `fecha_validacion` y una
nota coherente. No se edita el JSON a mano. Si se regenera sin el indicador,
la firma vuelve a estar pendiente. `--sin-rejilla` permite reutilizar la
rejilla local completa ya auditada cuando no cambian sus entradas.

## Verificación de esta entrega

```bash
python -m ruff check .
python -m pytest -q
python -m src.procedencia --validar resultados/g3_consumo_modelo.json
python -m src.procedencia --validar-oficial resultados/numeros_oficiales.json
```

Las pruebas cubren la selección de la mediana, el saldo, la razón, la
preparación sin firma, la firma explícita, la eliminación de firmas antiguas
al regenerar y el rechazo de cuentas alteradas, TDP rotulado como medido y
firmas sin fecha válida. El test del JSON oficial admite preparación o firma
coherentes: ya no exige editar tests al registrar la aprobación.
