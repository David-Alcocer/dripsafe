# 13 · Yucatán: a quién le vendemos, los cenotes y cómo crecemos

> Revisión del 22 de octubre de 2026 (Guille), hecha durante la jornada presencial. Contrasta lo que ya dicen la propuesta y el guion con fuentes públicas sobre Yucatán. **No cambia código ni cifras oficiales.** Las frases propuestas para el guion (§5) las decide Leo. Las cifras de aquí son **externas y citadas** (§7); ninguna sale del kit ni de `numeros_oficiales.json`.

## 1. El problema que resolvemos, en corto

El enfriamiento de un centro de datos lo controlan PLCs y un BMS. Cuando algo se descompone o alguien cambia un setpoint, el sitio desperdicia energía y agua **sin que nadie lo note**, por dos razones:

1. **Se vigila con umbrales iguales para todos** (PUE > 1.6). Un sitio eficiente puede subir 158 % su energía no TI sin cruzar esa línea.
2. **Las alarmas no separan** un intento de acceso de un incidente con efecto físico.

En Yucatán, además, toda el agua sale de un solo acuífero kárstico. Detalle en `docs/00-propuesta.md` §1.

## 2. Lo que ya está cubierto

| Ángulo | Dónde | Qué dice |
|---|---|---|
| Cliente y precio | `docs/00` §9 | Centros de datos y colocation de 0.5 MW o más en la Península; salas universitarias como piloto gratuito; $40 MXN por kW de TI al año |
| Competencia | `docs/00` §9 | FDD (Schneider, Siemens, SkySpark) y monitoreo OT (Nozomi, Claroty, Dragos); DripSafe los complementa |
| Expansión | `docs/00` §9 | Querétaro y otros acuíferos sobreexplotados |
| Acuífero | `docs/07` §2–3 | Acuífero 3105, cenotes, calidad como riesgo principal, purga y gobernanza |
| Balance y bono | `docs/07` §4–5 | 4.8 t de CO₂ evitadas (proyectado) y cero agua potable con PUE 1.284 (escenario) |

**Lo que falta:**
- El guion hablado dice muy poco de **quién compra**.
- No conecta a DripSafe con lo que hoy le pasa a los cenotes.
- Al revisar las fuentes salió un hueco en el primer segmento de clientes (§3).

## 3. Hallazgo: casi no hay centros de datos grandes en Yucatán

- **Los que existen son chicos y se enfrían con aire.** KIO opera dos centros de datos en Mérida, MER1 y MER2. La ficha técnica de MER1 dice:
  - inicio de operaciones en 2017;
  - características Tier I;
  - piso técnico de 21 m² en contenedor;
  - UPS modular de 60 kW y acometida de 150 kVA;
  - 3 CRAC en N+1, es decir, aire acondicionado de precisión, sin torres de agua;
  - BMS y **PUE promedio de 2**.

  No encontramos una fuente confiable de la capacidad de MER2. El Ayuntamiento de Mérida también licitó en 2025 equipo para un centro de datos municipal.
- **Los grandes esperan energía.** Según una columna de *El Economista* (17 sep 2026), a Yucatán le faltan gas y centrales de ciclo combinado. Las nuevas centrales de CFE, Mérida IV y Valladolid, suman 1 519 MW. Todavía no operan a plena capacidad y se espera que todo funcione a finales de 2027.
- **Consecuencia para el pitch.** El primer segmento de pago de `docs/00` §9 («0.5 MW o más en la Península») casi no existe hoy en Yucatán. Un jurado local puede saberlo. Con sitios de decenas de kW, la propia propuesta dice que DripSafe es **piloto, no cliente de pago**.

**Encuadre propuesto: en Yucatán, pilotos hoy; el cliente de pago, en Querétaro; y los centros de datos que lleguen a Yucatán, medidos desde el primer día.**

1. **Pilotos en Yucatán (hoy).**
   - Salas de cómputo universitarias, como la de la UPY.
   - Centros de datos chicos en Mérida, enfriados por aire.

   Con un PUE de 2, un sitio así es justo el caso de **ineficiencia crónica**: la auditoría de línea base al instalar (`docs/00` §9) la saca a la luz el primer día. El ahorro es de energía, y con él de CO₂ y del agua que gastan las centrales eléctricas. Con enfriamiento por aire casi no hay agua en el sitio.
2. **Primer cliente de pago: Querétaro.**
   - Es el estado con más centros de datos del país: 12 en operación y 18 en construcción, unos 250 MW, según la Sedesu citada por DCD.
   - Siete de sus 11 acuíferos están sobreexplotados.
   - Su gobierno anunció que **publicará el consumo de agua de los centros de datos desde 2027**, con un piloto en 2026, porque hoy no tienen las mismas obligaciones de reporte que la manufactura (DCD; una sola fuente).

   Un operador que pronto tendrá que reportar su agua necesita medirla y explicarla.
3. **Yucatán, cuando llegue la energía (2027 en adelante).** Los centros de datos nuevos llegarían a un acuífero que ya está bajo presión (§4). DripSafe propone que lleguen **medidos desde el primer día**: línea base, excesos y un reporte de captación para comparar con la concesión.

**Mercado vecino (hipótesis, no construido ni probado).** Cualquier edificio con chillers o torres de enfriamiento sigue la misma física: el enfriamiento gasta según la carga y el clima. Ejemplos: hoteles, hospitales, plazas comerciales e industria. Habría que cambiar «energía de TI» por la carga térmica del edificio. Se presenta como ruta futura, nunca como producto actual.

## 4. Hallazgo: los cenotes ya están contaminados, y no por centros de datos

- **Greenpeace México** publicó el 20 de octubre de 2026 un muestreo hecho en agosto, en 17 pozos y cenotes de siete localidades de Yucatán (Sitilpech, Kinchil, Motul, Chocholá, Molas, Celestún y San Antonio Tedzidz):
  - 16 muestras llegaron al límite superior de medición de coliformes totales;
  - 13 superaron 1 800 NMP/100 ml de coliformes fecales;
  - 2 superaron 50 mg/L de nitratos, el valor guía de la OMS.

  El propio estudio dice que **no identifica la fuente** de cada contaminante; Greenpeace lo vincula con las granjas porcícolas.
- **Mérida no tiene un drenaje sanitario para toda la ciudad** (Diario de Yucatán, 2024). Eduardo Batllori, del Cinvestav-Mérida, señala como fuentes de contaminación las aguas residuales domésticas que van a fosas sépticas, sumideros y biodigestores, además de la escorrentía urbana (Por Esto, 30 mar 2026).
- Se cita que el **83 %** de 60 cenotes monitoreados, de unos 3 100 registrados, está contaminado, sobre todo con coliformes fecales de origen animal y humano (Por Esto, 30 mar 2026; la nota no nombra el estudio original). Es una cifra de divulgación, no un estudio que cubra todo el acuífero. La misma nota dice que Profepa multó a 13 empresas porcícolas entre octubre de 2024 y junio de 2025.
- **Hay conflicto legal.** En julio de 2026, la SCJN atrajo dos casos de Homún contra la industria porcícola dentro del Anillo de Cenotes. En uno, las comunidades mayas piden que el sistema de cenotes y acuíferos tenga personalidad jurídica. Ninguno tiene todavía resolución de fondo.

**Cómo ayuda DripSafe, sin exagerar:**
- **No limpia cenotes ni ataca la causa principal.** Esa causa son las granjas y las fosas sépticas. Decir lo contrario ante un jurado de agua nos resta credibilidad.
- **Evita sumar carga.** En un sitio con enfriamiento evaporativo, detectar a tiempo una fuga o un exceso reduce la extracción del acuífero. Con los ciclos constantes, reducir la evaporación también reduce la purga, el agua con sales que se descarga (`docs/07` §3). Eso último requiere medir la purga, que el kit no trae.
- **Gobernanza:** deja un registro de cuánta agua se sacó de verdad y de cada exceso, para compararlo con la concesión de CONAGUA. Es justo lo que Querétaro empezará a pedir.
- **Lo indirecto:** cada kWh que no se desperdicia ahorra agua y CO₂ en las centrales. En el escenario proyectado son 22 216 L/año de agua de generación y 4.8 t de CO₂ (`numeros_oficiales.json`).

## 5. Frases propuestas para el guion (las decide Leo)

Las dos primeras **sustituyen** frases del guion actual, para no alargarlo. La tercera **recorta** tiempo para compensar.

**A · Parte 1, problema.** Sustituye las dos frases de CONAGUA, de «CONAGUA reporta…» a «…sus descargas»:
> "Ese acuífero ya está bajo presión: esta semana Greenpeace reportó contaminación fecal en pozos y cenotes de siete localidades de Yucatán. No la causan los centros de datos. Pero cuando lleguen, no pueden sumar otra carga sin medir."

Esta versión no trae cifras nuevas. Las cifras del estudio quedan para las preguntas (§6).

**B · Parte 5, escala.** Sustituye «DripSafe corre en local… sitio de 1 MW.»:
> "¿A quién se lo vendemos? En Yucatán empezamos con pilotos en salas de cómputo y centros de datos chicos. El primer cliente de pago está en Querétaro: es el estado con más centros de datos del país, tiene acuíferos sobreexplotados y va a publicar el consumo de agua de los centros de datos desde 2027. Y cuando la nueva energía traiga centros de datos a Yucatán, que lleguen medidos desde el primer día. Corre en local, sin nube, con seis medidores que ya existen, y se cobra por kW."

**C · Parte 4, números.** Para compensar, el párrafo del balance se reduce a:
> "¿Y lo que gasta DripSafe? 34 milisegundos por corrida, unos 0.000013 kWh al año, contra 4.8 toneladas de CO₂ evitadas en el escenario proyectado. El balance neto es positivo."

El umbral de menos de 1 ms y la explicación del TDP ya están en la tabla de preguntas de `docs/08`.

**Además (sin costo de tiempo):** decir «corre en local, solo lee, sin nube y sin GPU». Hoy el guion hablado no dice «solo lee», y es la primera duda de un jurado de ciberseguridad.

## 6. Preguntas nuevas del jurado y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Hay centros de datos en Yucatán? | Sí, chicos y enfriados por aire; uno de Mérida declara un PUE promedio de 2 en su ficha. Ahí hacemos pilotos. Los grandes esperan la energía nueva de CFE, prevista para fines de 2027. |
| ¿Cómo ayuda a los cenotes? | No los limpia: el problema principal son las granjas y las fosas sépticas. Lo que hace es evitar que los grandes usuarios de agua de enfriamiento sumen carga: detecta excesos de extracción y deja un registro para compararlo con la concesión. |
| ¿Quién paga, si el beneficio es para la comunidad? | El operador. Ahorra energía: en un sitio de 1 MW, la licencia se paga con menos del 0.5 % del overhead. Y llega preparado a los reportes de agua que vienen, como el de Querétaro en 2027. |
| ¿Sirve fuera de los centros de datos? | La física es la misma en cualquier edificio con chillers o torres, como hoteles, hospitales e industria. Es una hipótesis: no lo construimos ni lo probamos. |
| ¿Por qué ahora? | Hay tres señales: Querétaro va a publicar el agua de los centros de datos desde 2027, Yucatán espera su nueva energía para fines de 2027 y esta semana se publicó otro estudio sobre los cenotes. |
| ¿Qué dijo Greenpeace exactamente? | 17 pozos y cenotes en siete localidades: 13 con coliformes fecales por encima de 1 800 NMP/100 ml y 2 con nitratos por encima de 50 mg/L, el valor guía de la OMS. El estudio no identifica la fuente. |

## 7. Fuentes (consultadas el 22 de octubre de 2026)

- KIO, ficha técnica de MER1: https://static.datacentermap.com/company/castle-access/datacenter9833/KIO%20MER1%20Spec%20Sheet.pdf
- Ayuntamiento de Mérida, licitación de equipo para centro de datos municipal (2025): https://www.merida.gob.mx/municipio/sitiosphp/licitaciones/content/doc/proveeduria/2025/noviembre/LP-2025-ADQ-EQUIPAMIENTO-CENTRO-DATOS-01.pdf
- J. Ruiz Torre, «¿Puede llegar un centro de datos a Yucatán?», *El Economista* vía Yahoo Noticias (17 sep 2026): https://es-us.noticias.yahoo.com/llegar-centro-datos-yucat%C3%A1n-050111059.html
- DatacenterDynamics, «Querétaro publicará el consumo de agua de sus centros de datos»: https://www.datacenterdynamics.com/es/noticias/quer%C3%A9taro-publicar%C3%A1-el-consumo-de-agua-de-sus-centros-de-datos/
- Xataka México (1 sep 2025), acuíferos sobreexplotados de Querétaro: https://www.xataka.com.mx/robotica-e-ia/mexico-esta-recibiendo-centros-datos-que-nunca-hay-problema-paralelo-escasez-agua
- Expansión (27 may 2026), centros de datos en Querétaro y estrés hídrico: https://expansion.mx/tecnologia/2026/05/27/data-centers-en-queretaro-chocan-con-el-estres-hidrico
- Por Esto (20 oct 2026), muestreo de Greenpeace: https://www.poresto.com/yucatan/merida/2026/10/20/greenpeace-detecta-contaminacion-cuerpos-agua-yucatan-vinculada-megagranjas-porcicolas.html
- Por Esto (30 mar 2026), 83 % de 60 cenotes monitoreados, fuentes de contaminación (Cinvestav-Mérida) y multas de Profepa: https://www.poresto.com/yucatan/2026/3/30/en-yucatan-el-83-de-los-cenotes-monitoreados-estan-contaminados-granjas-porcicolas-boom-inmobiliario-y-turismo-amenazan-al-acuifero.html
- Diario de Yucatán (13 mar 2024), drenaje de Mérida: https://www.yucatan.com.mx/merida/2024/03/13/la-construccion-de-un-drenaje-urbano-en-merida-un-proyecto-lejos-de-concretarse.html
- Por Esto (10 jul 2026), la SCJN atrae los casos de Homún (SEFA 223/2026 y 224/2026): https://www.poresto.com/yucatan/2026/7/10/scjn-sentara-precedente-en-yucatan-definira-si-los-cenotes-y-la-abeja-melipona-pueden-tener-derechos-propios.amp.html
