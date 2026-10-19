# 10 · Preguntas frecuentes

> Dudas que ya resolvimos durante la preparación.

### ¿Tenemos que cubrir ciberseguridad Y enfriamiento a la vez?
No es obligatorio: se elige **un solo sub-reto**. Pero los **7 criterios de evaluación son iguales para todos**, e incluyen "Impacto en ciberseguridad" y "Eficiencia Green AI". Si ignoramos uno de los dos temas, ese criterio sale bajo. Por eso elegimos el sub-reto 3: con un solo modelo cubrimos ambos.

### ¿Hay que reportar WUE, PUE y CUE?
**No.** La convocatoria dice "WUE, PUE **y/o** CUE", es decir, la que aplique. Para el sub-reto 3, basta con **PUE**. Otra métrica es un extra opcional.

### Entonces, ¿qué es lo "obligatorio para todos"?
Dos cosas de la sección 11, sin importar el sub-reto:
1. **Balance neto positivo** con cifras: el modelo gasta menos de lo que ahorra.
2. **Análisis del impacto en el acuífero o la cuenca local.**

Si falta alguna, no nos evalúan completo.

### ¿Nos juega en contra no saber de ciberseguridad?
No mucho. El sub-reto 3 es sobre todo de IA y datos, y detectar anomalías ya es una técnica reconocida de seguridad OT. Basta con que Guille aprenda lo básico (ver [06-ciberseguridad-ot.md](06-ciberseguridad-ot.md)), que lo presentemos como **primera capa de detección** y que lo validemos con los mentores el 22.

### ¿Qué hacemos el día 22?
Pulir y presentar, **no construir desde cero**. Son 6 horas de trabajo con mentorías, luego el pitch y la premiación. El trabajo pesado va del 19 al 21.

### ¿Hacemos nuestro propio modelo o usamos un LLM barato?
**Nuestro propio modelo** (Isolation Forest con scikit-learn). Los LLM son malos con datos numéricos masivos, arruinan el balance neto y los jueces quieren ver nuestro trabajo. Un LLM solo se usaría, opcionalmente, para explicar alertas en lenguaje natural, sumando su consumo al balance. Usar Claude para programar e investigar sí está bien.

### ¿Usamos Grafana?
No para el plan principal: usamos **Streamlit**, que se conecta directo con el modelo en Python. Grafana requiere más configuración y **no da puntos extra**. Queda como opcional si sobra tiempo.

### ¿Qué da puntos extra?
Solo el **bono Zero Freshwater Footprint** (+5% a +15%): una alternativa de enfriamiento técnicamente viable con cero agua dulce potable. Además hay **premios especiales** (Green AI, impacto hídrico y ciberseguridad OT), que no suman puntos pero son reconocimientos aparte.

### ¿El pitch es para venderle la solución a empresas?
No. Es una presentación ante el jurado. Pero hay que mostrar en 2 o 3 frases que **podría** usarse en el mundo real (quién la usaría, por qué le conviene y cómo escala), porque "Escalabilidad y modelo de negocio" es un criterio.

### ¿Usamos git worktree?
Sí, como herramienta **opcional y personal**, sobre todo para quien trabaje con Claude o la terminal. La metodología del equipo es **trunk-based**. Ver [CONTRIBUTING.md](../CONTRIBUTING.md).

### ¿Podemos subir el kit de datos a GitHub?
**No.** La convocatoria prohíbe divulgarlo. La carpeta `data/` está en `.gitignore` y el repo debe ser **privado**.

### ¿Podemos probar ataques?
Solo sobre el kit de datos o en simulaciones, por ejemplo modificando un CSV. **Nunca** sobre sistemas reales: es motivo de descalificación.
