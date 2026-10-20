# Ejemplos para el dashboard

`numeros_ejemplo.json` tiene **valores ficticios**. El dashboard lo usa solo mientras no exista
`resultados/numeros_oficiales.json`, y en ese caso marca cada cifra como **Ejemplo** y muestra un aviso.
Nunca va al pitch.

## Propuesta de forma para el contrato 4 (para M2: Misael con Nico y Leo)

Cada cifra es un objeto con la misma forma que ya pide `docs/11-trabajo-en-paralelo.md`
(`valor`, `unidad`, `origen`, `responsable`), más un campo nuevo, **`tipo`**, que el dashboard
y las diapositivas usan para decir qué tan firme es la cifra:

| `tipo` | Significa |
|---|---|
| `observado` | Sale directo de los datos del kit (simulados) |
| `medido` | Medido en la laptop del equipo, con repeticiones |
| `estimado` | Calculado con un modelo o con supuestos declarados (`supuestos`) |
| `proyectado` | Escenario a futuro con parámetros editables; no es un ahorro observado |

Campos opcionales: `nota`, `supuestos`, `dispersion`, `repeticiones`. Las tablas
(`comparacion`, `curva_sensibilidad`, `robustez`, `bono_horas_respaldo`) llevan `filas`.

| Clave | Tipo | Responsable | Dónde la muestra el dashboard |
|---|---|---|---|
| `pue_antes`, `wue_antes` | observado | Misael | Resumen, Balance |
| `punto_ciego_pct` | observado | Nico | Evaluación (y diapositiva 2) |
| `exceso_energia_kwh`, `exceso_agua_l`, `pue_sin_exceso` | estimado | Nico | Resumen, Balance |
| `detector_cpu_ms` | medido | Gadiel | Balance |
| `detector_kwh_anual`, `detector_gco2e_anual` | estimado | Gadiel | Balance |
| `equilibrio_horas` | estimado | Misael + Nico | Resumen, Balance |
| `comparacion` | observado | Nico | Evaluación |
| `curva_sensibilidad`, `robustez` | observado | Nico | Evaluación, Resumen |
| `bono_horas_respaldo` | estimado | Misael | Agua y acuífero |
| `escenario_anual.parametros` | proyectado | Nico | Balance (valores iniciales del escenario editable) |

Si el contrato final usa otras claves, solo cambia `app/paginas.py` (las lecturas usan `cifra()`).

## Propuesta de contrato 3 v2: salida del detector (para Misael, Gadiel y Guillermo)

El contrato 3 actual (`docs/11`) tiene `score`, `anomalia`, `tipo_sugerido` y `kw_esperado_enfriamiento`, sin
`site_id`. La propuesta y el plan nuevos piden resultados **por sitio y hora** con esperado, residuo, banderas y
clase. Propuesta de columnas (las que lee el dashboard, `app/linea_base.COLUMNAS`):

| Columna | Quién la escribe | Significa |
|---|---|---|
| `timestamp`, `site_id` | Gadiel | Clave: una fila por sitio y hora |
| `esperado_energia_no_ti_kwh`, `esperado_agua_l`, `esperado_entrada_c` | Gadiel | Línea base |
| `residuo_energia_pct`, `residuo_agua_pct`, `residuo_entrada_c` | Gadiel | Real − esperado |
| `alerta_umbral`, `alerta_media_4h`, `clima_no_visto` | Gadiel | Banderas de cada detector |
| `clase` | Guillermo | `normal`, `incidente_ot`, `cambio_no_autorizado`, `escalon_sin_registro`, `intento_acceso` |
| `motivo` | Gadiel + Guillermo | Texto legible (opcional) |

El cambio de contrato lo hace Misael con un PR que actualice `docs/11` y `src/contrato.py` (regla del repo).
Mientras tanto la app usa su **vista previa** (`app/linea_base.py`), marcada así en la barra lateral y en cada cifra.
Si `alertas.csv` existe pero no trae estas columnas, la app lo dice con un aviso naranja: nunca lo ignora en silencio.
Cuando exista `data/resultados/consumo_modelo.json` (CodeCarbon), la sección Balance usa esa energía.
