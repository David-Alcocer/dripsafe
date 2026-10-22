# 14 · Guille en el pitch: ciberseguridad, cumplimiento y negocio

> Preparación del 22 de octubre de 2026 sobre el **pitch de 4 minutos** (`Final/DripSafe_FINAL_Pitch.pdf`, 13 láminas). Guille presenta las láminas **7** (ciberseguridad), **11** (modelo de negocio) y **12** (escalabilidad), y contesta las preguntas de esos temas y de cumplimiento. No cambia código ni cifras. Todas las cifras salen de `numeros_oficiales.json` o de fuentes citadas en `docs/06`, `docs/13` y las referencias del PDF.

## 1. Qué decir, lámina por lámina

Con 13 láminas en 4 minutos tocan unos 18 segundos por lámina. Cada guion cabe en unos 20 segundos; lo demás va a las preguntas (§3).

**Lámina 7 · Ciberseguridad (unos 25 s)**
> «Un cambio en el control del enfriamiento puede pasar como una orden legítima. DripSafe cruza el registro de cambios con la física y separa cuatro casos: un intento de acceso, un cambio no autorizado, un exceso sin registro y un incidente que ya tuvo efecto, cada uno con qué revisar primero. Y solo lee: nunca da órdenes a los equipos, y vive en su propia zona de red, sin internet, como recomienda la norma industrial IEC 62443.»

*Ojo:* la lámina dice «Ataque con efecto». Al hablar, di **«incidente con efecto»** o **«ataque con efecto, que se confirma en sitio»**. DripSafe nunca afirma que un exceso pruebe un ataque.

**Lámina 11 · Modelo de negocio (unos 20 s)**
> «Cobramos con un pago inicial, por instalar y auditar la línea base del centro, y una suscripción de 40 pesos por kilovatio de servidores al año, con el reentrenamiento por temporada incluido. Un centro de 1 megavatio paga 40 mil pesos al año y los recupera evitando 16 mil kilovatios hora: menos del medio por ciento de lo que gasta en enfriamiento y otros sistemas.»

**Lámina 12 · Escalabilidad (unos 20 s)**
> «Empezamos con pilotos en Mérida, con los centros de datos que ya operan aquí. El primer cliente de pago está en Querétaro, el estado con más centros de datos del país, que va a publicar su consumo de agua desde 2027. Y cuando llegue la nueva energía a Yucatán, los centros nuevos pueden llegar medidos desde el primer día. Usa seis medidores que ya existen y corre en local, así que sirve en cualquier región con agua bajo presión.»

**Cumplimiento, en una frase** (si sobra tiempo en la lámina 10 o 12, o en preguntas):
> «Y ayuda a cumplir: en México, quien saca agua de un pozo ya está obligado a medirla y a respetar su volumen concesionado. DripSafe usa ese medidor y deja el registro para compararlo con el permiso.»

## 2. Lo que nunca hay que decir

| No digas | Di |
|---|---|
| «Detectamos ataques» | «Detectamos efectos físicos y los cruzamos con el registro» |
| «Cumplimos» o «estamos certificados en IEC 62443» | «Seguimos sus principios: zona propia, un solo sentido, sin internet» |
| «Generamos el reporte para CONAGUA» | «Dejamos el registro para compararlo con el permiso» |
| «KIO es nuestro cliente» | «Operadores con presencia en Mérida, por validar» |
| «Ahorramos 10,768 kWh» | «El escenario proyectado evita…» |
| «Protegemos los cenotes» | «Evitamos que un usuario grande sume carga sin medirla» |
| Un precio de instalación | «Se cotiza por sitio; lo definimos en el piloto» |
| Que DripSafe habría detectado FrostyGoop | «Es el ejemplo de por qué vigilar la física» |

## 3. Refutaciones probables y respuesta

### Ciberseguridad

| Te dicen | Respondes |
|---|---|
| «Esto es eficiencia energética, no ciberseguridad.» | «Es las dos cosas, y esa es la idea. Un monitor de red ve el tráfico. Si el atacante usa órdenes válidas, como en FrostyGoop, el tráfico se ve normal, pero el gasto cambia. Complementamos al monitor de red; no lo reemplazamos.» |
| «¿Cómo saben que es un ataque y no una falla?» | «No lo adivinamos. Si hay un cambio no autorizado registrado y después un exceso, es un incidente y se confirma en sitio. Si hay un exceso sin registro, no se puede saber, y por eso se revisa la configuración antes de mandar a mantenimiento.» |
| «El atacante borra el registro.» | «Entonces el exceso aparece como "exceso sin registro" y la regla es revisar la configuración primero. Para ver el efecto no dependemos del registro.» |
| «Falsifica los medidores.» | «Tendría que falsificar a la vez el registro del sistema de control y los medidores de energía, que suelen ser otro sistema, y de forma coherente con la carga y el clima. Con el kit no lo podemos probar y lo decimos: haría falta medir caudal y temperaturas del agua.» |
| «DripSafe es otra puerta de entrada.» | «Solo lee: recibe una copia de los datos en un solo sentido, vive en su propia zona y no tiene internet. No puede mandar órdenes.» |
| «¿Cuántas falsas alarmas?» | «En el kit, cero por día y sitio. Con el doble de ruido, 0.07 por día y sitio: más o menos una cada dos semanas.» |
| «¿Y si es un técnico que cambió algo sin registrarlo?» | «Sale como exceso sin registro y lleva a revisar la configuración. Eso destapa el cambio no documentado, que también es una falla de proceso que vale la pena corregir.» |
| «¿Qué tan pequeño se les escapa?» | «Un exceso sostenido menor a 4 % en el sitio de aire o a 7.5 % en el líquido. Por debajo de eso no lo vemos, y lo decimos.» |
| «¿Punto débil?» | «Una ola de calor que no conoce: un +10 % pasó sin verse en 8 de 11 tardes. Se cierra con una línea base por época del año.» |
| «¿Dónde está la IA? Es una regresión.» | «Sí, a propósito. Es aprendizaje automático sencillo: aprende de los datos de cada centro. Se explica en una frase, se audita con el estándar de medición de ahorros ASHRAE 14 y gasta 0.000013 kWh al año. Un modelo más complejo costaría más energía y sería más difícil de explicar; con este ya vemos las fallas desde +10 % en el kit.» |
| «Son datos simulados.» | «Sí, y lo decimos en cada lámina. Demuestran el método, no la eficacia en un centro real. La prueba con fallas pequeñas la fijamos antes de medir, y el siguiente paso es validar con datos reales de una sala de cómputo en Yucatán.» |
| «¿Qué pasaría sin DripSafe?» | Respuesta en lenguaje llano en `docs/06` §10b. |

### Cumplimiento

| Te dicen | Respondes |
|---|---|
| «¿Cumplen IEC 62443?» | «Seguimos sus principios: zona propia, conducto de un solo sentido, sin internet y mínimo privilegio. No estamos certificados; certificar sería parte del producto real.» |
| «¿Qué ley de ciberseguridad aplica en México?» | «Que sepamos, no hay una ley general de ciberseguridad aprobada: en enero se anunció que se prepararía una. En mayo, un estudio del Observatorio Legislativo de la Cámara de Diputados concluyó que la protección de la infraestructura crítica está dispersa en varias leyes, sin una norma única. Por eso nos apoyamos en estándares internacionales: IEC 62443 y MITRE ATT&CK para sistemas industriales.» |
| «¿Qué norma de agua cumple un centro de datos?» | «No hay límite legal de eficiencia en agua ni en energía. Si usa pozo: concesión de CONAGUA, pago de derechos y medidor obligatorio. Si descarga o infiltra agua residual, como la purga de una torre: permiso de descarga y la NOM-001. La Ley General de Aguas de diciembre de 2025 pone primero el consumo humano. DripSafe ayuda a cumplir; no sustituye el cumplimiento.» (`docs/13` §7) |
| «¿Generan el reporte para CONAGUA?» | «No. Dejamos el registro de captación y de excesos para compararlo con el permiso; el formato oficial sería parte del servicio.» |
| «¿Y los datos? ¿Van a la nube?» | «No. Corre en local, sin nube. Lee telemetría de equipos; si el registro trae el usuario que hizo un cambio, ese dato se queda en el sitio.» |
| «¿Respetaron las reglas del hackatón?» | «El kit no está en el repositorio, y una prueba automática lo impide. Los ataques solo existen como cambios en copias de los datos; nunca tocamos un sistema real. La propiedad intelectual es del equipo, con derechos reservados (`LICENSE.md`).» |
| «¿Y las emisiones?» | «Usamos el factor oficial de SEMARNAT para la red eléctrica, 0.444 kg de CO₂ por kWh, el que se usa en la Cédula de Operación Anual. Sirve para los reportes de carbono del cliente.» |

### Modelo de negocio

| Te dicen | Respondes |
|---|---|
| «En Yucatán no hay clientes.» | «Por eso Mérida es piloto, no ingreso. El primer cliente de pago está en Querétaro: 12 centros operando y 18 en construcción. Yucatán entra cuando llegue la energía.» |
| «¿Por qué 2027 en Yucatán?» | «Es cuando se espera que las nuevas centrales de CFE, en Mérida y Valladolid, funcionen a plena capacidad. Sin energía no llegan centros grandes.» |
| «40 pesos por kW es muy poco. ¿Es negocio?» | «Es un precio supuesto, pensado para que se pague solo con menos del 0.5 % del consumo auxiliar. En México hay unos 280 MW de centros de datos y la meta es 1,500 MW para 2030. A ese precio, cada 100 MW son 4 millones de pesos al año, más las instalaciones. Es un servicio de nicho, barato para entrar, y el precio se valida en el piloto.» |
| «¿Cuánto vale para el cliente?» | «Supuesto: en un centro de 1 MW, evitar del 1 al 5 % del consumo auxiliar son entre 87 mil y 437 mil pesos al año, contra 40 mil de suscripción. Es conservador: las herramientas de diagnóstico automático en edificios logran una mediana de 9 % de ahorro, según el laboratorio Berkeley (LBNL).» |
| «¿Cuánto cuesta instalar?» | «No lo tenemos cotizado. Depende de cómo se conecte en modo de solo lectura (con un puerto espejo del switch existente o con un diodo de datos, que es más caro), de un equipo de cómputo y de la integración con los medidores. Lo definimos en el piloto.» |
| «¿Por qué no lo hace ya Schneider o Siemens?» | «Sus plataformas diagnostican fallas de equipos y energía. Los monitores de red, como Nozomi, Claroty o Dragos, miran el tráfico. Que sepamos, ninguno cruza el registro de cambios con una línea base de energía y agua por centro. Un fabricante grande podría agregarlo; nosotros vamos a centros medianos, con precio por kW, local y encima de los datos que ya tienen.» |
| «¿Quién compra?» | «El operador del centro de datos: el área de instalaciones por la energía y el agua, y el área de seguridad por la alerta OT. Las dos ganan con lo mismo.» |
| «¿Cómo llegan a Querétaro?» | «La Asociación Mexicana de Data Centers trabaja con el gobierno de Querétaro en el sistema para medir el agua. Ese es el canal natural; todavía no tenemos contacto.» |
| «Si ya tienen alarmas, ¿para qué pagar?» | «Porque la alarma fija no ve a los centros eficientes: uno puede gastar 158 % más en enfriamiento sin que suene. En la prueba, las alarmas fijas vieron 0 de 18 fallas de +10 %; DripSafe, 18 de 18.» |
| «¿Y si el cliente no tiene medidor de agua?» | «Funciona con energía y temperatura; sin medidor de agua no hay alertas de agua. Si el centro saca agua de un pozo, la ley ya lo obliga a tener medidor.» |

## 4. Datos de respaldo

| Dato | Valor | Tipo y fuente |
|---|---|---|
| Punto ciego de la alarma fija | 158 % más energía no TI sin cruzar PUE 1.6 | Estimado · `numeros_oficiales.json` |
| Fallas de +10 % vistas | DripSafe 18 de 18 · alarma fija 0 | Observado sobre inyecciones · JSON oficial |
| Falsas alarmas | 0 por día y sitio · 0.07 con el doble de ruido | Observado · `docs/06` §6 |
| Coincidencia al azar con 24 h | 1 de cada 5 | Observado · `docs/06` §4b |
| Costo del detector | 33.6 ms por corrida · 0.000013 kWh al año | Medido y estimado · `g3_consumo_modelo.json` |
| Suscripción | $40 MXN por kW de TI al año; 1 MW = $40,000; se cubre con 16 MWh | Supuesto · `docs/00` §9 |
| Valor para un centro de 1 MW | 1–5 % del consumo auxiliar = $87,000–$437,000 MXN al año | Supuesto · `docs/00` §9; LBNL: mediana de 9 % |
| Querétaro | 12 centros en operación y 18 en construcción; agua pública desde 2027 | DatacenterDynamics · `docs/13` §3 |
| México | ~280 MW hoy; meta de 1,500 MW en 2030 | Expansión (27 may 2026) |
| Energía en Yucatán | Centrales de CFE (1,519 MW) previstas a plena capacidad a fines de 2027 | *El Economista* (17 sep 2026) · `docs/13` §3 |

## 5. Fuentes nuevas de este documento

- Expansión (27 may 2026), capacidad de centros de datos en México: https://expansion.mx/tecnologia/2026/05/27/data-centers-en-queretaro-chocan-con-el-estres-hidrico
- Expansión Política (5 may 2026), Observatorio Legislativo sobre infraestructura crítica: https://politica.expansion.mx/mexico/2026/05/05/mexico-enfrenta-riesgos-por-falta-de-legislacion-en-torno-a-infraestructura-critica-dice-observatorio
- Expansión (5 ene 2026), plan y ley de ciberseguridad propuestos: https://expansion.mx/tecnologia/2026/01/05/mexico-primer-plan-de-ciberseguridad-2026

Las demás fuentes están en `docs/06` (§9b y §10b) y `docs/13` (§8).
