# 03 · Equipo y roles

> Somos 5 estudiantes de segundo año de Ingeniería de Software. Todos venimos de **C++**, así que la primera tarea común es **instalar Python y aprender lo básico de pandas y scikit-learn**. A programadores competitivos esto les toma una tarde.

## Perfiles

| Integrante | Fortalezas
|---|---|
| **Leo** (líder) | C++, programación competitiva, POO media, **muy bueno en diseño front**, no deja nada a medias |
| **Misa** (co-líder) | Orden, **GitHub** (trunk-based, git flow), investigación, **trabaja muy bien con Claude y la terminal**, POO media | 
| **Gadiel** | C++, **programación competitiva**, muy dedicado a esa área, POO | 
| **Nico** | C++, programación competitiva, algoritmos, POO, **participó en IRAP** (investigación de campo en Yucatán y propuestas ante evaluadores) | 
| **Guille** | C++, **Linux** (administra un server de Minecraft), **ciberseguridad básica** (Fail2ban, SSH keys, ufw), estricto con GitHub, trabaja bien con Claude y la terminal |

## Roles

###  Leo · Demo y diseño visual
- Dashboard en **Streamlit**: alertas del modelo, PUE inicial y final proyectado, gráficas, usando las cifras consolidadas por Nico.
- Diseño visual de las diapositivas del pitch.
- Video de respaldo de la demo, por si algo falla en vivo.
- **Por qué él:** es fuerte en diseño front y termina lo que empieza.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md) y [08-pitch.md](08-pitch.md).

### Misa · Datos e integración
- Explorar y limpiar el kit de datos.
- Calcular el **PUE inicial o base** (antes de la solución) en `src/metricas/pue.py`.
- Entregar a Nico el PUE inicial, los datos limpios y las energías total y de TI, con unidades, intervalo de muestreo y periodo analizado.
- Calcular y validar el **balance neto final junto con Nico**, usando el ahorro estimado y las mediciones del modelo de Gadiel.
- Administrar el repo, el tablero de tareas y la integración de las partes.
- **Por qué él:** orden, GitHub y saber usar Claude para procesar datos rápido.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md) y [CONTRIBUTING.md](../CONTRIBUTING.md).

### Gadiel · Modelo de IA
- Entrenar el detector de anomalías (**Isolation Forest**).
- Entregar a Nico las alertas y el consumo esperado del enfriamiento para estimar el exceso de energía.
- Medir la energía y el carbono del modelo con **CodeCarbon**, que es el insumo del balance neto.
- Explicar por qué el modelo marca cada alerta.
- **Por qué él:** su fuerte en algoritmos le ayuda a entender y ajustar el modelo.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md).

### Nico · Cálculo de impacto, agua y contenido del pitch
- Recibir el **PUE inicial de Misa** y calcular el ahorro energético y el **PUE final proyectado**, con los insumos del modelo de Gadiel.
- Calcular y validar el **balance neto final junto con Misa** (obligatorio), descontando el consumo del modelo medido por Gadiel con CodeCarbon.
- Estimar el impacto en agua y emisiones cuando haya datos y factores suficientes; documentar unidades, periodo, fuentes y supuestos.
- Desarrollar el programa de impacto en Python y un ejemplo reproducible; consolidar `resultados/numeros_oficiales.json` para el dashboard y el pitch. Los cálculos están pendientes de implementación.
- Análisis del **impacto en el acuífero de Yucatán** (obligatorio).
- Propuesta de enfriamiento para el **bono de cero agua dulce**.
- Estructura del pitch y la parte de modelo de negocio.
- **Por qué él:** su experiencia en IRAP (investigación de campo en Yucatán y presentación de propuestas) encaja justo con esto.
- **Lee:** [05-solucion-tecnica.md](05-solucion-tecnica.md), [07-agua-y-acuifero.md](07-agua-y-acuifero.md), [08-pitch.md](08-pitch.md) y [11-trabajo-en-paralelo.md](11-trabajo-en-paralelo.md).

###  Guille · Ciberseguridad OT
- Entender OT/ICS y por qué protocolos como Modbus son inseguros.
- Mapear de 3 a 4 técnicas de **MITRE ATT&CK for ICS** que el modelo detectaría.
- Explicar cómo distinguir una **falla** de un **ataque**.
- Revisar las especificaciones OT/ICS del kit.
- Simular ataques y fallas sobre los datos (`src/ataques/`) y medir qué detecta el modelo de Gadiel.
- Definir cómo se instala el detector sin volverse una puerta de entrada.
- **Por qué él:** es el único con base en Linux y seguridad, y su inglés alto le sirve porque casi todo el material está en inglés.
- **Lee:** [06-ciberseguridad-ot.md](06-ciberseguridad-ot.md).

## Qué busca cada uno al leer el kit (lunes 19)

| Quién | Qué buscar |
|---|---|
| **Misa** | Qué datasets vienen, qué columnas traen, frecuencia de muestreo y si alcanza para calcular el PUE |
| **Gadiel** | Qué variables sirven para detectar anomalías (temperaturas, flujos, consumo de bombas y chillers) y si hay eventos etiquetados |
| **Guille** | Especificaciones OT/ICS: equipos, protocolos (Modbus, BACnet…) y arquitectura de red |
| **Nico** | Ubicación, fuente de agua y acuífero; datos disponibles para estimar ahorro, agua y emisiones, con unidades y periodo compatibles con el PUE inicial de Misa |
| **Leo** | Criterios de evaluación del kit y qué debería mostrar la demo para ganarlos |

Al final: **30 minutos juntos** para que cada quien cuente lo que encontró y confirmemos el plan.

## Pitch

Por definir. Los candidatos naturales son **Nico** (presentó en IRAP) y **Leo** (líder). Elijan a quien se sienta más cómodo hablando en público.
