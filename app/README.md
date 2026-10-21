# Dashboard de DripSafe

**DATOS SIMULADOS.** Demo local sobre el kit CIFOX. Compara cada hora de cada sitio con lo que
**debería** gastar según su carga y su clima (línea base), cruza los excesos con el registro OT y
los clasifica en cuatro clases de alerta. Solo lee un CSV; no controla equipos ni se conecta a redes OT.

## De dónde sale cada cosa

La barra lateral lo dice siempre:

| Fuente | Oficial (cuando exista) | Mientras tanto |
|---|---|---|
| Telemetría | CSV del kit, fuera del repo | Datos de ejemplo inventados (aviso naranja arriba) |
| Detector | `data/resultados/alertas.csv` (Gadiel + Guille), columnas de `app/linea_base.COLUMNAS` | **Vista previa** de `app/linea_base.py` |
| Cifras | `resultados/numeros_oficiales.json` (Nico) | `app/ejemplos/numeros_ejemplo.json`, **valores ficticios** marcados «Ejemplo» |

Si `numeros_oficiales.json` existe pero su `_meta` lo identifica como borrador
con valores de ejemplo, la app sigue usando el archivo de ejemplo y no lo
presenta como oficial.

El JSON oficial tiene secciones anidadas (`resultados/README.md`); `cargar.adaptar_oficial()` las
pasa a las claves que lee la app (curva de la rejilla, robustez, horas del bono). Lo que sigue en
`null` se muestra como **Pendiente**. Las claves de primer nivel con `valor`, como
`punto_ciego_pct` o `equilibrio_horas`, pasan tal cual.

Cada cifra lleva una etiqueta: **Observado**, **Medido**, **Estimado**, **Proyectado**, **Vista previa** o
**Ejemplo**. La propuesta de forma del JSON está en `app/ejemplos/README.md`.

## Requisitos

- Python **3.12** (el mismo que pide el kit).
- Internet **solo para instalar** paquetes. Después funciona sin conexión: fuentes, íconos y datos son locales.
- No necesita GPU, cuentas, claves de API ni hardware extra. Corre en el CPU de la laptop.

## Instalar (una vez por laptop)

Desde la raíz del repo:

```bash
python3.12 -m venv .venv                 # Windows: py -3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

No copies `.venv` entre computadoras: créalo en cada una.

## El kit de datos (no está en el repo)

El kit es **confidencial**: nunca se copia dentro de esta carpeta ni se sube a GitHub. El
dashboard lo lee de su ubicación en la laptop:

```
~/hackathon/Kit Stack Tecnológico/Para participantes/Código y recursos/
```

Si lo tienes en otra carpeta, indica la carpeta del kit (la que contiene `data/` y `docs/`):

```bash
export DRIPSAFE_KIT="/ruta/al/kit"          # Windows: $env:DRIPSAFE_KIT="C:\ruta\al\kit"
```

Si no lo encuentra, el dashboard muestra **datos de ejemplo inventados** y un aviso naranja arriba.
Nunca presentes la demo con ese aviso visible.

## Arrancar

```bash
.venv/bin/python -m streamlit run app/main.py
```

Abre **http://127.0.0.1:8501**. El servidor solo acepta conexiones de esta misma laptop
(`.streamlit/config.toml`). Para detenerlo: **Ctrl+C** en la terminal.

## Recorrido de la demo (3 minutos)

1. **Resumen.** Señala el sello DATOS SIMULADOS, la gráfica de energía no TI **real contra esperado** y las
   cuatro clases de alerta.
2. **Demo de ataque · Evento OT · SIM-C.** Avanza los 4 pasos: la temperatura se ve normal → la energía sigue
   en lo esperado y el registro OT muestra logins y un cambio de configuración → DripSafe lo clasifica como
   **cambio no autorizado** (sin efecto físico todavía) → qué hacer.
3. **Demo · Ineficiencia · SIM-A.** El exceso sin evento OT es un **escalón sin registro**: primero se revisa la
   configuración, después mantenimiento.
4. **Evaluación.** Empate con las reglas en las 21 anomalías del kit (se dice tal cual) y la **curva de
   sensibilidad**: desde qué tamaño detecta cada método.
5. **Balance neto.** El **umbral de equilibrio**: segundos de exceso al año pagan la energía del detector.
   El escenario anual es editable y está marcado como proyección.
6. **Agua y acuífero.** Agua real contra esperada, las épocas del año en Yucatán y el bono (cero agua potable).
7. **Datos y supuestos.** Etiquetas de procedencia, límites y qué venía en el kit contra lo que aporta DripSafe.

El botón de pantalla (arriba a la derecha) activa el **modo presentación** para el proyector.

## Verificar antes de presentar

```bash
.venv/bin/python -m pytest -q          # lógica y pantallas (AppTest), con datos de ejemplo
```

Luego, en la laptop de la demo y **sin internet**: arrancar, elegir un filtro, comprobar un PUE en la tabla,
explicar una alerta y detener con Ctrl+C. Guarda capturas y el video de respaldo.

Video de respaldo: con el dashboard corriendo, `python app/grabar_demo.py` (requiere `pip install playwright`
y `playwright install chromium ffmpeg`). Lo guarda en `~/hackathon/video-respaldo/`. **No graba mientras las cifras
sean de ejemplo** (para una prueba: `--borrador`). El video final se graba después del congelamiento del 21 a las 20:00.

Versiones probadas (macOS, Apple M4, Python 3.12.13):

| | Streamlit | pandas | numpy | plotly |
|---|---|---|---|---|
| Equipo | 1.66.0 | 3.0.6 | 2.x | 7.1.0 |
| Las del kit CIFOX | 1.51.0 | 2.2.3 | 2.3.5 | 7.x |

Con las versiones del kit, 3 pruebas de AppTest se saltan por un error de la herramienta de pruebas de
Streamlit 1.51 con `segmented_control`; esas pantallas se revisaron a mano en el navegador.

## Archivos

| Archivo | Qué hace |
|---|---|
| `main.py` | Barra lateral, barra superior (sitio, periodo, modo presentación) y elige la sección |
| `paginas.py` | Las ocho secciones |
| `kit.py` | Lee el CSV del kit fuera del repo, reglas fijas del kit y datos de ejemplo para pruebas |
| `linea_base.py` | **Vista previa** del detector: línea base por sitio, residuos, umbrales y las cuatro clases |
| `cargar.py` | Junta telemetría, detector (del equipo o vista previa) y cifras (oficiales o de ejemplo) |
| `calculos.py` | PUE, agua por kWh IT, eventos, evaluación, exceso, equilibrio y escenario (sin Streamlit) |
| `ejemplos/` | JSON de cifras **ficticias** y la propuesta de forma del contrato 4 |
| `grabar_demo.py` | Graba el video de respaldo (#20) recorriendo la demo en modo presentación; el video queda fuera del repo |
| `componentes.py`, `graficas.py`, `estilo.css` | Paneles estilo Grafana, gráficas y estilos |
| `textos.py` | Todos los textos: escenarios, técnicas ATT&CK, límites, acuífero y bono |

## Límites

Ver la sección «Datos y supuestos» del dashboard: datos simulados con un generador casi lineal, sin balance de
calor, falla brusca y cambio sin registro indistinguibles, una sola semana de clima, energía del detector estimada
(el tiempo sí se mide) y ahorro anual solo como escenario.

## Licencias

- Código de DripSafe: del equipo.
- Kit CIFOX (CSV, reglas didácticas, ejemplos de benchmark): MIT, © CIFOX. Se lee, no se redistribuye.
- Inter y JetBrains Mono: SIL Open Font License (`static/fuentes/OFL-*.txt`).
- Streamlit (Apache 2.0), pandas y numpy (BSD-3), plotly (MIT).
