# 03 · Equipo y roles

> Somos 5 estudiantes de segundo año de Ingeniería de Software. Todos venimos de **C++**, así que la primera tarea común es **instalar Python 3.12 y aprender lo básico de pandas y numpy**. A programadores competitivos esto les toma una tarde.
>
> **Reparto vigente: D13 (19 oct), con el ajuste de #13 a Nico en `678b5ff` (21 oct).** Ver [02-decisiones.md](02-decisiones.md).

## Perfiles

| Integrante | Fortalezas |
|---|---|
| **Leo** (líder) | C++, programación competitiva, POO media, **muy bueno en diseño front**, no deja nada a medias |
| **Misa** (co-líder) | Orden, **GitHub** (trunk-based, git flow), investigación, **trabaja muy bien con Claude y la terminal**, POO media |
| **Gadiel** | C++, **programación competitiva**, muy dedicado a esa área, POO |
| **Nico** | C++, programación competitiva, **algoritmos**, POO, **participó en IRAP** (investigación de campo en Yucatán y propuestas ante evaluadores) |
| **Guille** | C++, **Linux** (administra un server de Minecraft), **ciberseguridad básica** (Fail2ban, SSH keys, ufw), estricto con GitHub, trabaja bien con Claude y la terminal, **inglés alto** |

## Roles

### Leo · Demo, diapositivas y guion
- Dashboard en **Streamlit** (el Stack A del kit sirve de referencia): alertas, PUE inicial y final proyectado, y las cifras consolidadas por Nico. El aviso **"DATOS SIMULADOS"** debe estar siempre visible.
- **Guion del pitch** (#16) y diseño de las diapositivas, con las mismas cifras que el dashboard. Nico aporta los números y su explicación.
- Video de respaldo de la demo.
- **Por qué él:** es fuerte en diseño front y termina lo que empieza.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md) y [08-pitch.md](08-pitch.md).

### Misa · Datos, integración y bono
- Cargar el kit, adaptarlo al contrato (**D14, contrato v2**) y entregar la telemetría limpia (#1).
- **PUE inicial** por sitio y periodo en `src/metricas/pue.py`, con energías total y de TI, unidades e intervalo (#2).
- Comando único que corre todo el flujo (#4), repo, tablero e integración.
- **Balance neto final junto con Nico** (#14).
- **Comparación de refrigeración y bono** (#15): comparar aire, evaporativa y líquida en el mismo periodo (reto 3 del kit) y proponer el enfriamiento híbrido con cero agua potable. Recomendaciones condicionadas a sus supuestos, nunca "ahorro observado".
- **Por qué ella:** orden, GitHub y saber usar Claude para procesar datos rápido. El kit es pequeño, así que le queda tiempo para el bono.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md), [07-agua-y-acuifero.md](07-agua-y-acuifero.md) (sección del bono) y [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

### Gadiel · Construye el detector
- **Detector por sitio** (#6): línea base, umbrales de residuos y media móvil, ajustado **solo con la partición de referencia**; el registro OT clasifica las alertas.
- **Consumo esperado** de energía auxiliar y agua por sitio, según carga, temperatura y tipo de enfriamiento (#5). Con eso se mide el exceso.
- Explicar cada alerta con un motivo legible (#8).
- Medir su consumo con **CodeCarbon** (#7).
- **Por qué él:** su fuerte en algoritmos le ayuda a construir y ajustar el modelo.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md).

### Nico · Pone a prueba el detector y calcula el impacto
- **Evaluación justa y Green AI** (issue nuevo): comparar el detector con las reglas del kit usando **las mismas entradas**, ajuste y evaluación separados y **varias corridas** con dispersión. Reportar calidad (precisión y recall) junto al costo (tiempo, memoria y energía estimada).
- **Ahorro y PUE final proyectado** (#3), con el PUE inicial de Misa y el consumo esperado de Gadiel.
- **Balance neto final junto con Misa** (#14), con análisis de sensibilidad a los supuestos (watts y gCO₂e/kWh).
- Consolidar `resultados/numeros_oficiales.json`.
- **Análisis del acuífero de Yucatán y gobernanza** (#13, obligatorio), incluida la fuente y el año del dato del acuífero 3105 (ajuste `678b5ff`).
- **Por qué él:** fuerte en algoritmos, y el balance neto depende directamente del modelo.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md) y [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

### Guille · Ciberseguridad OT
- Interpretar los **eventos OT del kit** (login fallido, cambio de configuración no autorizado) y mapearlos a ATT&CK for ICS, sin exagerar: un login fallido **no prueba** un ataque (#11).
- Escenarios simulados (#9) y evaluación por escenario (#10). Sobre el kit, solo los escenarios cuyas columnas existan (ver D14).
- Cómo se instalaría el detector sin abrir una puerta nueva (#12).
- **Por qué él:** base en Linux y seguridad, y la parte OT del kit resultó más ligera de lo esperado.
- **Lee:** [06-ciberseguridad-ot.md](06-ciberseguridad-ot.md) y [07-agua-y-acuifero.md](07-agua-y-acuifero.md).

## Qué trae el kit y qué le toca a cada quien hoy (lunes 19)

| Quién | Qué hacer con el kit |
|---|---|
| **Todos** | Instalar Python 3.12 y correr el **Stack A** siguiendo la guía del kit |
| **Misa** | Proponer el contrato v2 (D14) y cargar el CSV; calcular el PUE inicial por sitio |
| **Gadiel** | Fijar el detector por sitio y sus parámetros sobre referencia; medir su consumo |
| **Nico** | Leer `docs/METRICS.md` del kit y diseñar el protocolo de comparación justa |
| **Guille** | Revisar cómo vienen los eventos OT y empezar a buscar fuentes del acuífero |
| **Leo** | Revisar la app del Stack A y qué debe mostrar la demo de 3 minutos que sugiere el kit |

Al final: **30 minutos juntos** para confirmar D12 y D14.

## Pitch

Por definir quién presenta. Candidatos: **Nico** (presentó en IRAP) y **Leo** (líder).
