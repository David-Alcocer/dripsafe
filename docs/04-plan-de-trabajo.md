# 04 · Plan de trabajo: del 18 al 22 de octubre

> **Regla de oro:** el día 22 solo se pule y se presenta. **El trabajo pesado va del 19 al 21.** El miércoles 21 en la noche la demo ya debe funcionar.

## Domingo 18: preparar (1–2 h cada uno)

- [ ] **Todos:** instalar Python 3, `pandas`, `scikit-learn`, `jupyter` y `streamlit`.
- [ ] **Misa:** crear la estructura del repo y el tablero de tareas. Subirlo a GitHub como **privado**.
- [ ] **Leo:** revisar el correo de confirmación de CIFOX y **preguntar la duración del pitch**. Hacer un "hola mundo" en Streamlit.
- [ ] **Gadiel:** correr un ejemplo de Isolation Forest con datos de prueba.
- [ ] **Nico:** juntar de 3 a 5 fuentes sobre el acuífero de Yucatán (CONAGUA, UADY, CICY).
- [ ] **Nico:** preparar las fórmulas, entradas y supuestos del cálculo de impacto y un ejemplo con datos sintéticos, según [05-solucion-tecnica.md](05-solucion-tecnica.md).
- [ ] **Guille:** leer la introducción de MITRE ATT&CK for ICS y qué es Modbus.

## Lunes 19: entender el kit

- [ ] Leer el kit cada quien desde su rol (ver [03-equipo-y-roles.md](03-equipo-y-roles.md)).
- [ ] **Misa:** cargar y limpiar los datos; entregar a Nico el **PUE inicial**, las energías total y de TI, unidades, intervalo y periodo.
- [ ] **Nico:** revisar esos insumos, identificar qué cálculos de agua y emisiones permite el kit y ajustar los supuestos del ejemplo.
- [ ] **Todos, en la noche:** 30 min de reunión para confirmar el sub-reto, las variables del modelo y el plan.

## Martes 20: construir

- [ ] **Gadiel:** modelo v1 entrenado; entregar alertas y consumo esperado del enfriamiento a Nico.
- [ ] **Gadiel:** medir el consumo del modelo con CodeCarbon.
- [ ] **Guille:** 3 o 4 técnicas de ataque mapeadas y cómo las detecta el modelo.
- [ ] **Nico:** implementar ahorro energético y PUE final proyectado; estimar agua y emisiones si hay datos suficientes y consolidar los resultados para Leo.
- [ ] **Misa + Nico:** implementar juntos el balance neto final, usando el ahorro estimado por Nico y el consumo del modelo de Gadiel.
- [ ] **Nico:** preparar el borrador del análisis del acuífero y documentar fuentes y supuestos de los cálculos.
- [ ] **Leo:** dashboard leyendo los datos reales.
- [ ] **Misa:** integrar datos, modelo y métricas de Nico con la demo.
- [ ] **Todos, en la noche:** llamada corta de avance.

## Miércoles 21: cerrar

- [ ] Demo funcionando de punta a punta.
- [ ] **Video de respaldo** de la demo grabado.
- [ ] Análisis del acuífero y propuesta del bono terminados.
- [ ] **Misa + Nico:** verificar juntos el balance neto final, sus unidades, periodo y supuestos.
- [ ] **Nico:** entregar programa y ejemplo reproducible con el balance conjunto y las cifras consolidadas, distinguiendo mediciones de proyecciones.
- [ ] **Nico:** cerrar el contenido y guion del pitch; **Leo:** diseñar las diapositivas con las mismas cifras que el dashboard.
- [ ] **Todos:** primer ensayo con cronómetro.
- [ ] **Regla:** a partir de hoy en la noche no entra nada nuevo.

## Jueves 22: UPY

| Hora | Qué hacemos |
|---|---|
| 08:00 | Llegar con la demo probada en la laptop que se va a usar |
| 09:00–09:30 | Validación del avance: mostrar sub-reto, datos explorados y prototipo corriendo |
| 09:30–15:30 | Pulir la demo, ajustar cifras y validar con mentores (sobre todo la parte de ciberseguridad) |
| 15:30–16:00 | Ensayar el pitch dos veces |
| 16:00–17:30 | Pitch, demo en vivo y video como respaldo |
| 17:30–18:30 | Platicar con jueces y aliados, y premiación |

**Checklist para llevar:**
- [ ] Laptop con la demo, cargador y extensión eléctrica.
- [ ] Video de respaldo guardado sin depender de internet.
- [ ] Diapositivas en PDF, también sin conexión.
- [ ] Repo clonado y actualizado.
