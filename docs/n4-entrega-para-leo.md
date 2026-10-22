# N4 · Contenido técnico para dos láminas

Entrega para Leo. Las afirmaciones de diseño son **propuesta**, los datos del kit son **simulados** y toda cifra que aparezca en las láminas debe cotejarse con `resultados/numeros_oficiales.json` al integrarlas. La actualización de este documento no modifica el JSON ni su firma.

## Lámina 1 · El riesgo hídrico local

**Titular:** «En Yucatán importa cuánto se capta y adónde termina cada descarga».

**Visual sugerido:** acuífero bajo suelo calizo con un pozo, cenote y una ruta de descarga que se comprueba, sin dibujar una conexión específica no medida.

**Texto visible:**

- CONAGUA describe drenaje principalmente subterráneo, cavernas y cenotes en el acuífero 3105.
- La disponibilidad oficial es regional; no prueba calidad, permiso ni abasto para un predio.
- DripSafe señala captación en exceso. El origen del agua y el destino de la purga requieren datos del operador.

**Nota para exponer:** la profundidad del agua varía por zona. Si Leo incluye la disponibilidad numérica o litros proyectados, debe tomarlos del JSON oficial, con año, unidad y etiqueta de estimación; si el campo sigue pendiente, se omite la cifra. Nunca convertir automáticamente `water_l` del kit en extracción del acuífero ni en purga evitada.

**Fuente al pie:** [CONAGUA, *Actualización de la disponibilidad del acuífero Península de Yucatán (3105)*, 2024](https://sigagis.conagua.gob.mx/gas1/Edos_Acuiferos_18/yucatan/DR_3105.pdf), §§3.1, 3.3, 5.4–5.5 y 8.4. Para purga, [DOE, *Cooling Towers*](https://www.energy.gov/sites/default/files/2013/10/f3/waterfs_coolingtowers.pdf), ecuaciones 1–7.

## Lámina 2 · El intercambio agua–energía

**Titular:** «Cero agua potable de enfriamiento es una meta de diseño con costo energético por cuantificar».

**Visual sugerido:** servidores W40 → circuito cerrado → enfriador seco; una derivación al chiller condensado por aire en horas cálidas. Abajo, dos medidores distintos: agua potable de reposición y electricidad del enfriamiento.

**Texto visible:**

- El llenado y toda reposición deben proceder de una fuente no potable verificada. El enfriador seco y el chiller por aire no evaporan agua.
- ERA5 de Mérida ofrece horas por encima de umbrales exteriores; son un **proxy climático**, no horas observadas del chiller.
- El PUE anual del bono queda pendiente de carga y curvas de enfriador, chiller y bombas. Los tres sitios simulados ilustran el intercambio, pero no prueban el PUE de esta arquitectura.

**Nota para exponer:** tomar cualquier conteo de horas exclusivamente del campo `bono_zero_freshwater.horas_respaldo_mérida_al_año` del JSON oficial y llamarlo «horas sobre umbral». No sustituir horas por la fracción de energía de TI. El respaldo con agua tratada es una opción futura, condicionada a disponibilidad, tratamiento y descarga autorizada. El detector solo recomienda en la arquitectura propuesta; no opera el chiller en la demo.

**Fuentes al pie:** [ASHRAE, clases de enfriamiento líquido](https://www.ashrae.org/file%20library/technical%20resources/bookstore/emergence-and-expansion-of-liquid-cooling-in-mainstream-data-centers_wp.pdf); [Microsoft, diseño de cero evaporación y efecto en PUE (2024)](https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/); [Open-Meteo, API histórica ERA5](https://open-meteo.com/en/docs/historical-weather-api).

## Integración pendiente

1. Nico incorpora al JSON oficial, mediante el flujo de firma del equipo, fuente, fecha y disponibilidad del acuífero 3105 tras confirmar el valor que se publicará. Este archivo no sirve como sustituto del JSON.
2. Misa aporta especificaciones y despacho horario del enfriador seco, chiller y bombas para calcular el PUE anual del bono; sin ellas se conserva `pendiente`.
3. Leo incorpora las dos láminas al PDF del pitch, alinea el guion y comprueba cada cifra visible contra el JSON final. Misa revisa el bono y Nico el acuífero; Leo revisa los cambios de `app/`.
