# DripSafe 

> Proyecto del equipo para el **Hackatón CIFOX · AguaSegura AI** (Universidad Politécnica de Yucatán, 22 de octubre de 2026).

**DripSafe** es un detector de anomalías ligero, basado en IA, para los sistemas de enfriamiento de centros de datos. Con **un solo modelo** buscamos dos cosas:

1. **Eficiencia:** detectar consumo anormal de energía y agua en el enfriamiento para bajar el **PUE** (y, de paso, el WUE).
2. **Ciberseguridad OT:** detectar lecturas o comandos que no cuadran con el comportamiento físico normal, una señal de manipulación de sensores o PLCs.

---

## Resumen 

| Tema | Decisión |
|---|---|
| Sub-reto | **3 · Detección de anomalías con IA** en enfriamiento y gestión hídrica |
| Métrica principal | **PUE** (Power Usage Effectiveness) |
| Modelo | **Isolation Forest** (scikit-learn): ligero y explicable; balance neto por verificar |
| Demo | **Streamlit** (Python) |
| Bono extra | Ir por el **Zero Freshwater Footprint** (+5% a +15%) con enfriamiento híbrido |
| Flujo de Git | **Trunk-based**, con ramas cortas; `git worktree` es opcional |
| Fechas clave | 19 oct: llega el kit · 22 oct: jornada presencial y pitch |

---

## Documentación

Cada documento es independiente. Léanlo completo o pásenselo a su IA de confianza para hacerle preguntas.

| # | Documento | Para quién | De qué trata |
|---|---|---|---|
| 01 | [Convocatoria](docs/01-convocatoria.md) | Todos | Reglas, sub-retos, entregables, criterios y bono |
| 02 | [Decisiones](docs/02-decisiones.md) | Todos | Qué decidimos y por qué |
| 03 | [Equipo y roles](docs/03-equipo-y-roles.md) | Todos | Quién hace qué |
| 04 | [Plan de trabajo](docs/04-plan-de-trabajo.md) | Todos | Día por día, del 18 al 22 |
| 05 | [Solución técnica](docs/05-solucion-tecnica.md) | Gadiel, Misa, Nico, Leo | Arquitectura, modelo, métricas y balance neto |
| 06 | [Ciberseguridad OT](docs/06-ciberseguridad-ot.md) | Guille | Guía rápida de OT/ICS y MITRE ATT&CK for ICS |
| 07 | [Agua y acuífero](docs/07-agua-y-acuifero.md) | Nico | Acuífero de Yucatán, balance neto y bono |
| 08 | [Pitch](docs/08-pitch.md) | Nico, Leo | Estructura del pitch y modelo de negocio |
| 09 | [Recursos](docs/09-recursos.md) | Todos | Enlaces en español e inglés por tema |
| 10 | [Preguntas frecuentes](docs/10-faq.md) | Todos | Dudas que ya resolvimos |
| 11 | [Trabajo en paralelo](docs/11-trabajo-en-paralelo.md) | Todos | Contratos entre piezas, dueños de carpetas y trazabilidad |
| 12 | [Trazabilidad](docs/12-trazabilidad.md) | Todos | Requisito → responsable → issue → evidencia |
| — | [CONTRIBUTING](CONTRIBUTING.md) | Todos | Cómo trabajamos con Git |
| — | [AGENTS](AGENTS.md) | Su IA | Contexto del proyecto para asistentes de IA |

---

## 👥 Equipo

| Integrante | Rol |
|---|---|
| **Leo** (líder) | Demo en Streamlit y diseño visual del pitch |
| **Misa** (co-líder) | Datos limpios, PUE inicial y energías de referencia, repositorio e integración |
| **Gadiel** | Modelo de IA (Isolation Forest) y medición de consumo con CodeCarbon |
| **Nico** | Ahorro y PUE final proyectados, balance neto, resultados de impacto, acuífero, bono y contenido del pitch |
| **Guille** | Ciberseguridad OT: amenazas y mapeo con MITRE ATT&CK for ICS |

Detalle en [docs/03-equipo-y-roles.md](docs/03-equipo-y-roles.md).

**Reparto aprobado:** Misa entrega a Nico el PUE inicial y los datos que lo sustentan; Nico calcula el impacto posterior y consolida las cifras para Leo, usando las alertas, el consumo esperado y las mediciones del modelo que aporta Gadiel. Los cálculos están pendientes de implementación; los ahorros y el PUE final serán proyecciones hasta contar con evidencia medida.

---

## Cómo usar esta documentación con tu IA

Copia el documento de tu rol, más `01-convocatoria.md` y `02-decisiones.md`, y pégalos en tu IA con un prompt como este:

```text
Soy estudiante de segundo año de Ingeniería de Software. Participo en un hackatón
de IA, ciberseguridad y agua. Mi rol en el equipo es: [TU ROL].
Te paso el contexto del proyecto. Explícame mi parte paso a paso, en lenguaje
sencillo, y dime qué debo tener listo antes del 22 de octubre.

[PEGA AQUÍ LOS DOCUMENTOS]
```

Si usan Claude Code u otro agente en la terminal, este repo trae [AGENTS.md](AGENTS.md) con el contexto resumido.

---

## Reglas importantes

- **El kit de datos es confidencial.** La convocatoria prohíbe divulgarlo. **No lo suban a GitHub.** La carpeta `data/` está en `.gitignore`. Si el repo va a GitHub, que sea **privado** hasta después del hackatón.
- **Prohibido atacar sistemas reales.** Todo se prueba sobre el kit de datos o en entornos simulados.
- **El 22 no se construye nada nuevo.** La demo debe funcionar desde el miércoles 21 en la noche.

---

## Estructura propuesta del repo

```text
dripsafe/
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── docs/          # Documentación del proyecto
├── config/        # Traducción de nombres del kit al contrato (columnas.json)
├── data/          # Kit de datos y todo lo derivado de él (NO se sube; está en .gitignore)
├── notebooks/     # Exploración y experimentos (Jupyter)
├── src/           # Código: contrato, datos, ataques, modelo y métricas
├── resultados/    # numeros_oficiales.json: solo totales, la única fuente de cifras del pitch
├── tests/         # Pruebas automáticas (solo datos sintéticos)
├── .github/       # Plantillas de PR e issues, dueños y pruebas automáticas
└── app/           # Demo en Streamlit
```

Para empezar sin esperar el kit:

```bash
pip install -r requirements.txt
python -m src.sinteticos --dias 14 --salida data/sinteticos/telemetria.csv
pytest
```

Cómo se conectan las piezas: [docs/11-trabajo-en-paralelo.md](docs/11-trabajo-en-paralelo.md).

---

## Contacto CIFOX

- gloria.vlencia@cifox.org
- mariana.gomez@cifox.org
- Convocatoria oficial: <https://vaporlatierra.com/2026/convocatoria-hackaton-cifox-aguasegura-ai/>
