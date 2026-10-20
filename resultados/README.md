# `resultados/` · Cifras oficiales de DripSafe

Esta carpeta contiene la **única fuente de verdad** de los números que aparecen en el dashboard, las diapositivas y el pitch.

## `numeros_oficiales.json`

**Contrato 4** del equipo (ver [docs/11-trabajo-en-paralelo.md](../docs/11-trabajo-en-paralelo.md)). Es el archivo que **Nico produce** (M3+N3 del [plan-ejecucion](../docs/00-plan-ejecucion.md)) y **Leo consume** desde el dashboard. Misa + Nico lo revisan juntos.

### Regla de oro

> Si un número aparece en una diapositiva, en el dashboard o en el pitch, **tiene que venir de este JSON**. Si dos piezas discrepan en una cifra, se corrige el cálculo o el contrato **antes** de modificar el pitch.

### Formato de cada métrica

Cada campo numérico sigue este patrón:

```json
"nombre_metrica": {
  "valor": <número>,
  "unidad": "<kWh | L | kgCO2e | ratio | ...>",
  "tipo": "medido | estimado | proyectado",
  "origen": "<ruta/al/script.py o fuente externa>",
  "responsable": "<persona (#issue)>",
  "nota": "<opcional, aclaraciones>",
  "supuestos": {"<opcional, parámetros editables>": "..."}
}
```

**`tipo` es obligatorio** y Leo lo pinta visualmente en el dashboard:
- **`medido`** → el valor sale de los datos del kit o de CodeCarbon directamente. Puede defenderse con una celda del CSV.
- **`estimado`** → sale de un cálculo determinista sobre datos reales (ej: residuo = real − esperado).
- **`proyectado`** → es un escenario con supuestos editables; NO es un ahorro observado. En el pitch se dice "proyección", no "ahorro".

### Qué cubre el JSON

| Sección | Dueño | Qué contiene |
|---|---|---|
| `_meta` | Misa (M4) | commit, fecha de generación, periodo, sitios, fuente de datos |
| `pue` | Misa (antes) + Nico (después proyectado) | PUE antes/después con nota de cociente de sumas |
| `wue` | Misa + Nico | WUE con nota de "captación in situ" (no huella total) |
| `energia` | Misa | IT, total, **no TI** (D18), agua, acumulados del periodo |
| `exceso_estimado` | Nico (N3) | kWh y L sobre la evaluación |
| `balance_neto` | Misa + Nico (M3+N3) | costo del detector + ahorro + CO₂ + agua + razón + **umbral de equilibrio** |
| `deteccion` | Nico (N2) | tabla y curva vs reglas del kit, falsas alarmas, conteo por clase OT (D16), latencia por episodio |
| `bono_zero_freshwater` | Nico (N4) | WUE potable meta, horas de respaldo, PUE con/sin bono |
| `fuentes_externas` | Nico | factor SEN, intensidad hídrica, acuífero 3105, SMN |
| `limites_declarados` | Equipo | lo que la propuesta v7 §10 documenta como límite |

### Estado actual

El JSON de este commit es un **ejemplo con valores ficticios**:
- Los **valores `medido`** marcados con número real vienen del `reference_metrics.json` del kit (PUE 1.2676, WUE 0.366 L/kWh, energías del periodo de referencia).
- Los demás están en `null` esperando a ser llenados en Fase 2 por Gadiel (CodeCarbon), Nico (métricas, exceso, bono) y Misa + Nico (balance).

**Aviso:** la clave `_meta.aviso` siempre debe decir `"DATOS SIMULADOS · ..."` mientras no haya datos de una instalación real. Es un requisito del propio kit (ver [docs/00-propuesta.md §10](../docs/00-propuesta.md)).

## Cómo lo consume Leo

El dashboard **no calcula cifras oficiales por su cuenta**. Lee este JSON y lo pinta:

```python
from pathlib import Path
import json

numeros = json.loads(Path("resultados/numeros_oficiales.json").read_text(encoding="utf-8"))

pue_antes = numeros["pue"]["antes"]["valor"]
pue_tipo = numeros["pue"]["antes"]["tipo"]  # pintar el tag correspondiente
```

Para cada tarjeta, Leo pinta `valor + unidad + tag según tipo`. Si el valor es `null`, se muestra el estado vacío con un `-` o "pendiente".

## Cuándo se actualiza

- **Fase 0 (hoy):** este ejemplo queda publicado para que Leo y Nico tengan referencia.
- **Fase 2 (martes–miércoles):** Nico lo actualiza con los valores reales conforme Gadiel, Guille y él terminan sus piezas. Misa valida el balance neto.
- **Al cerrar un commit (Fase 2):** `_meta.generado_con_commit` apunta al SHA del commit que generó las cifras.

## Validación mínima (opcional pero recomendada)

Antes del pitch, un script debería verificar que:
- Todos los campos `"valor": null` tienen una justificación obvia (métrica aplazada o pendiente)
- Ninguna métrica `"tipo": "medido"` tiene un valor negativo o imposible
- `_meta.aviso` contiene `"DATOS SIMULADOS"` si no hay datos reales

Si Leo o Misa lo quieren implementar: `tests/test_numeros_oficiales.py`.
