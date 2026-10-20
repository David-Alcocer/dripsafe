# Reporte de implementación y pruebas de N1

**Fecha:** 19 de octubre de 2026
**Rama local:** `nico`
**Datos:** todo el kit CIFOX es **SIMULADO** y permanece fuera de Git.
**Publicación:** no se hizo commit ni push; `main` no se modificó.

## Entorno

La rama `nico` y `origin/main` coincidían en `49b0651`; no hizo falta hacer pull.
El entorno virtual de Leo no se comparte por Git y no estaba en esta copia. Se
creó `.venv/` local, excluido por `.gitignore`, con Python 3.12.3 y `uv 0.12.0`.
Se instalaron las dependencias de `requirements.txt` y
`requirements-dev.txt`; SciPy quedó declarada explícitamente porque N1 la
importa directamente. Versiones relevantes: pandas 3.0.6, NumPy 2.5.4,
SciPy 1.18.1, pytest 9.1.1, Ruff 0.17.1 y Streamlit 1.66.0.

## Entrega de N1

- PUE y WUE calculan cocientes de sumas por sitio y partición; devuelven
  inicio, fin, cantidad de intervalos y unidad de energía de entrada.
- La unidad de energía se declara como `kwh_intervalo` o `kw_promedio` para
  evitar multiplicar dos veces por la duración. El agua es captación operativa
  *in situ* en litros, no agua potable.
- Los residuos de energía no TI y agua se calculan en todas las horas de
  evaluación. El exceso positivo se separa según coincida o no con una alerta;
  ninguna coincidencia se convierte por sí sola en ahorro atribuible.
- Las reglas reproducen los cuatro criterios didácticos del kit, incluido OT
  por defecto. La evaluación usa un TP por episodio, FP por tramo alertado en
  horas limpias, latencia de primera alerta e intervalo de confianza de FP/día.
  Rechaza huecos en la rejilla de evaluación.
- Se documentó el formato de tabla y curva de N2 sin generar puntos ni cifras
  oficiales.

## Pruebas ejecutadas después de implementar

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python -m pytest tests/test_n1.py -q` | **29 aprobadas**: partición, unidades, agua ausente, valores inválidos, residuos con/sin alerta, reglas, episodios, falsas alarmas y huecos. |
| `.venv/bin/python -m ruff check .` | **Aprobado**. |
| Comparación local de solo lectura con `reference_metrics.json` y `common/cifox.py` | **Aprobada**: 216 filas de referencia reproducen PUE/WUE; las 504 banderas coinciden fila por fila. Ninguna fila se copió al repo. |
| `.venv/bin/python -m pytest -q --tb=short` | **95 aprobadas** tras corregir localmente el dashboard. |

La primera ejecución de la suite tuvo 86 aprobadas y nueve fallidas, todas en
`tests/test_dashboard.py`, ajenas a N1. Para poder abrir la demo se corrigieron
localmente dos causas: el JSON de resultados marcado como borrador se trata
como ejemplo y usa las cifras ficticias etiquetadas de `app/ejemplos/`; además,
no se llama `st.html("")` cuando no hay aviso. El dashboard pasó después sus
13 pruebas y la suite completa quedó en 95 aprobadas. La app se abrió con el
kit local y mostró Resumen y Evaluación sin error. Leo debe revisar estos
cambios de su módulo antes de integrarlos; no se hizo push.

## Siguiente integración

Antes de N2, Misael debe confirmar la unidad canónica que entrega la
telemetría procesada y Gadiel debe confirmar los nombres y unidades de energía
no TI y agua esperadas. La salida de N1 usa nombres de columna recibidos como
parámetros y no cambia el contrato compartido. El modelo oficial, las
inyecciones de Guillermo, las cifras de ahorro y `numeros_oficiales.json`
siguen pendientes de esas entradas.
