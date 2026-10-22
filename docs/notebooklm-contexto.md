# DripSafe · Contexto completo para investigación (NotebookLM)

Este documento resume TODO el contexto de nuestro proyecto para el Hackatón CIFOX · AguaSegura AI. Sirve como fuente base para buscar y analizar artículos. Al final hay preguntas de investigación, palabras clave y una plantilla de apuntes.

---

## 1. El hackatón

- **Nombre:** Hackatón CIFOX · AguaSegura AI. Ciberseguridad y sostenibilidad hídrica para la infraestructura de IA.
- **Organiza:** CIFOX, con Va por la Tierra A.C. y la Universidad Politécnica de Yucatán (UPY).
- **Sede:** Sala de Usos Múltiples de la UPY, Yucatán, México.
- **Fechas:** el 19 de octubre de 2026 se entrega el kit de datos y empieza el trabajo remoto. El 22 de octubre de 2026 es la jornada presencial: 6 horas de desarrollo, mentoría, pitch ante el jurado y premiación.
- **Kit de datos:** datasets de consumo hídrico y energético, especificaciones técnicas de sistemas OT/ICS de enfriamiento, documentación de contexto y criterios de evaluación. Es confidencial.
- **Convocatoria oficial:** https://vaporlatierra.com/2026/convocatoria-hackaton-cifox-aguasegura-ai/

### Pregunta detonadora
¿Cómo podemos hacer que la infraestructura que hace posible la inteligencia artificial sea, al mismo tiempo, más segura, más eficiente y más responsable con el agua?

### Problema de fondo
1. Los centros de datos de IA consumen enormes cantidades de energía y agua para enfriarse, lo que presiona recursos hídricos escasos.
2. Los sistemas OT/ICS que controlan el enfriamiento y la gestión del agua son infraestructura crítica vulnerable a ciberataques.

### Los 4 sub-retos (se elige uno)
1. Optimización del consumo de agua en enfriamiento de centros de datos. Métrica: WUE.
2. Ciberseguridad de sistemas OT/ICS de gestión hídrica y enfriamiento. Métrica: reducción de superficie de ataque y riesgo.
3. **Detección de anomalías con IA en sistemas de enfriamiento y gestión hídrica. Métrica: PUE. ← NUESTRA ELECCIÓN**
4. Green AI, gobernanza y métricas. Métrica: CUE.

### Métricas
- **WUE** (Water Usage Effectiveness) = litros de agua consumidos ÷ kWh de energía de TI.
- **PUE** (Power Usage Effectiveness) = energía total de la instalación ÷ energía de TI. El ideal es 1.0.
- **CUE** (Carbon Usage Effectiveness) = kg CO₂e ÷ kWh de energía de TI = factor de emisión de la red × PUE.

### Requisitos obligatorios para todos los equipos
1. **Balance neto positivo:** el consumo computacional del modelo de IA (energía y carbono) no debe superar el ahorro hídrico y energético que genera. Debe justificarse con cifras.
2. **Impacto en el acuífero o la cuenca local:** extracción, presión sobre el acuífero, riesgo de contaminación y gobernanza del recurso.

Sin estos dos elementos, la propuesta no se evalúa completa.

### Criterios de evaluación (7, sin pesos publicados)
Innovación · Viabilidad técnica · Impacto en ciberseguridad · Eficiencia Green AI (WUE, PUE, CUE) · Balance neto y gobernanza hídrica · Escalabilidad y modelo de negocio · Presentación y claridad.

### Bono de puntos extra (único)
**Zero Freshwater Footprint: +5% a +15%.** Se otorga por una alternativa de enfriamiento técnicamente viable que reduzca a cero el uso de agua dulce potable: agua reciclada o no potable, aire de alta eficiencia, enfriamiento líquido en circuito cerrado u otra arquitectura equivalente.

### Premios
1.º, 2.º y 3.er lugar. Reconocimientos especiales: Mejor solución de Green AI, Mejor impacto hídrico y Mejor propuesta de ciberseguridad OT. No se publicó si hay premio económico.

### Reglas
Prohibido atacar sistemas reales: solo se trabaja con el kit o con simulaciones. El kit es confidencial. Cada equipo conserva la propiedad intelectual de su solución.

---

## 2. Nuestro equipo

Somos 5 estudiantes de segundo año de Ingeniería de Software. Todos venimos de C++ y estamos aprendiendo Python para este proyecto.

Reparto vigente (D13, 19 oct; el acuífero pasó a Nico el 21 oct):
- **Leo** (líder): demo en Streamlit, guion y diapositivas del pitch.
- **Misa** (co-líder): datos, PUE inicial, GitHub e integración; comparación de refrigeración y bono; balance neto con Nico.
- **Gadiel**: construye el detector por sitio y mide su consumo con CodeCarbon.
- **Nico**: evalúa el detector (calidad frente a costo, Green AI), ahorro y PUE final proyectados, balance neto con Misa, análisis del acuífero y gobernanza. Participó en IRAP (programa de investigación de Texas A&M en Yucatán).
- **Guille**: ciberseguridad OT. Maneja Linux y seguridad básica.

Sobre el kit (19 oct): datos totalmente simulados, 3 sitios ficticios (enfriamiento por aire, evaporativo y líquido) × 168 h, con energía, agua, carga, temperaturas y eventos OT resumidos. Las reglas simples del kit detectan sus anomalías de ejemplo; comparamos nuestro detector con ellas por episodio y con inyecciones adicionales.

---

## 3. Nuestra solución: DripSafe

**Concepto:** un detector de anomalías ligero, basado en IA, para los sistemas de enfriamiento de centros de datos. Con un solo modelo logramos dos beneficios:
1. **Eficiencia:** detecta consumo anormal de energía y agua en el enfriamiento, lo que permite corregirlo y bajar el PUE (y el WUE).
2. **Ciberseguridad OT:** detecta lecturas o comandos que no cuadran con la física del sistema, una señal de manipulación de sensores o PLCs.

**Cómo funciona:**
- Entrada: datos de sensores del enfriamiento (torres, bombas, chillers, flujo, temperatura y energía), que viajan por protocolos como Modbus o BACnet.
- Modelo: **línea base física por sitio** que predice energía no TI, agua y temperatura; umbrales y media móvil detectan residuos anómalos, y reglas OT clasifican las alertas.
- Clasificación: ineficiencia (consumo coherente pero excesivo) o posible ataque (lecturas incoherentes entre sensores, cambios bruscos o actividad fuera de horario).
- Salida: dashboard en Streamlit con alertas, PUE antes y después, y balance neto.

**Por qué un modelo ligero y no un LLM:** entrena en minutos en una laptop, consume casi nada de energía (balance neto muy positivo), es explicable y los LLM son malos con miles de lecturas numéricas.

**Balance neto (método):**
- Costo = energía del modelo (entrenamiento + inferencia anual, medida con CodeCarbon) → CO₂ (× factor de emisión de la red) y agua (× WUE del sitio + intensidad hídrica de la electricidad).
- Ahorro = (PUE antes − PUE después) × energía de TI anual → CO₂ y agua evitados.
- Balance = ahorro − costo > 0.

**Propuesta para el bono:** enfriamiento híbrido, con circuito cerrado líquido como base y agua residual tratada (no potable) solo en picos de calor. La IA decide cuándo activar el respaldo.

**Ciberseguridad (MITRE ATT&CK for ICS v20):** con el kit se observan Valid Accounts (T0859, en los logins fallidos) y Modify Parameter (T0836, en el cambio de configuración), y se inyecta Manipulation of Control (T0831). Con sensores de agua helada se verían también Unauthorized Message: Reporting Message (T1692.002, antes T0856) y Manipulation of View (T0832). DripSafe no afirma que un exceso pruebe un ataque: cruza el registro OT con el efecto físico en cuatro clases. Lo presentamos como "primera capa de detección", alineada con ISA/IEC 62443. Detalle en docs/06.

---

## 4. Contexto local: el acuífero de Yucatán

- Suelo kárstico: roca caliza porosa y fracturada, con conductos subterráneos y cenotes conectados.
- Nivel freático somero: el agua subterránea está a pocos metros de la superficie.
- No hay ríos superficiales: el acuífero es prácticamente la única fuente de agua.
- Muy vulnerable a la contaminación (granjas porcícolas, fosas sépticas, crecimiento urbano) y a la intrusión salina cerca de la costa.
- Anillo de Cenotes: zona de reserva geohidrológica clave para el abasto de Mérida.
- Regulación: CONAGUA (concesiones de agua y disponibilidad de acuíferos) y normas de descarga.

Hay que respaldar cada dato con una fuente.

---

## 5. Preguntas de investigación (prioridad)

### A. Agua y centros de datos
1. ¿Cuánta agua consume un centro de datos típico por kWh (WUE promedio con torres de enfriamiento y sin ellas)?
2. ¿Cuánta agua se usa "fuera de sitio" para generar la electricidad (intensidad hídrica, en L/kWh)? ¿Hay valores para México?
3. ¿Qué porcentaje del agua de una torre de enfriamiento se pierde por evaporación y cuánto por purga (blowdown)?
4. ¿Qué empresas ya usan enfriamiento con agua reciclada o en circuito cerrado? Casos reales con cifras.
5. ¿Cuál es el PUE promedio actual de la industria y cuál el de los centros de datos más eficientes?

### B. Detección de anomalías y Green AI
6. ¿Qué estudios usan detección de anomalías para mejorar la eficiencia energética de sistemas HVAC o de enfriamiento? ¿Cuánto ahorro reportan?
7. ¿Qué tan efectivos son los modelos de línea base y los umbrales de residuos en datos de sensores industriales?
8. ¿Cuánta energía consume entrenar un modelo clásico de machine learning frente a un LLM?
9. ¿Existen casos documentados donde la IA redujo el PUE de un centro de datos?

### C. Ciberseguridad OT/ICS
10. ¿Qué incidentes reales han afectado sistemas de agua o enfriamiento industrial?
11. ¿Por qué Modbus y BACnet son inseguros? ¿Qué ataques típicos permiten?
12. ¿Cómo se usa la detección de anomalías en datos físicos (process-based anomaly detection) para detectar ataques?
13. ¿Qué recomienda ISA/IEC 62443 para proteger sistemas de control?

### D. Acuífero de Yucatán y gobernanza
14. ¿Cuál es la disponibilidad oficial del acuífero de la Península de Yucatán según CONAGUA?
15. ¿Qué estudios del CICY, la UADY o la UNAM documentan la contaminación de cenotes y del acuífero?
16. ¿Hay centros de datos o proyectos industriales planeados en Yucatán que usen agua del acuífero?
17. ¿Qué regula la Reserva Geohidrológica del Anillo de Cenotes?
18. ¿Cuál es el factor de emisión oficial más reciente del Sistema Eléctrico Nacional de México (kg CO₂e/kWh)?

### E. Negocio y escalabilidad
19. ¿Cuánto cuesta la energía y el agua en un centro de datos? ¿Cuánto ahorraría bajar el PUE 0.1?
20. ¿Qué empresas venden soluciones de monitoreo OT o de eficiencia en enfriamiento? ¿Cómo cobran?

---

## 6. Palabras clave para buscar

**Inglés:** data center water footprint · water usage effectiveness WUE · power usage effectiveness PUE · cooling tower blowdown evaporation · closed-loop liquid cooling data center · reclaimed water data center cooling · anomaly detection HVAC energy efficiency · baseline residual threshold industrial sensor data · process-based anomaly detection ICS · false data injection attack ICS · MITRE ATT&CK for ICS · IEC 62443 · Modbus security · Green AI carbon footprint machine learning · CodeCarbon · SWaT dataset · WADI dataset.

**Español:** huella hídrica centros de datos · consumo de agua inteligencia artificial · eficiencia energética PUE · enfriamiento líquido circuito cerrado · agua residual tratada enfriamiento · ciberseguridad sistemas de control industrial · seguridad Modbus · acuífero Península de Yucatán · contaminación cenotes Yucatán · Anillo de Cenotes reserva geohidrológica · disponibilidad acuífero CONAGUA Yucatán · factor de emisión sistema eléctrico nacional México.

---

## 7. Fuentes iniciales (para agregar a NotebookLM)

**Base:**
- Making AI Less "Thirsty" (arXiv): https://arxiv.org/abs/2304.03271
- WUE, The Green Grid: https://thegreengrid.org/en/resources/library-and-tools/238-WP
- 2024 US Data Center Energy Usage Report (LBNL): https://eta-publications.lbl.gov/publications/2024-lbnl-data-center-energy-usage-report

**Agua y enfriamiento (español):**
- https://www.datacenterdynamics.com/es/opinion/como-la-refrigeracion-liquida-puede-resolver-la-crisis-hidrica-de-la-ia-en-los-centros-de-datos/
- https://www.datacenterdynamics.com/es/features/data-centers-verdes-como-enfriar-sin-usar-agua/
- https://blogs.iadb.org/sostenibilidad/es/podemos-sostener-la-era-digital-el-dilema-del-avance-tecnologico-y-el-consumo-de-recursos

**Ciberseguridad:**
- MITRE ATT&CK for ICS: https://attack.mitre.org/matrices/ics/
- INCIBE, IEC 62443: https://www.incibe.es/incibe-cert/blog/iec62443-evolucion-isa99
- INCIBE, Modbus seguro: https://www.incibe.es/incibe-cert/blog/evolucionando-modbus-seguro
- INCIBE, análisis de riesgos en SCI: https://www.incibe.es/incibe-cert/blog/analisis-de-riesgos-en-sci

**IA:**

**Yucatán:**
- Greenpeace, informe sobre cenotes (PDF): https://www.greenpeace.org/static/planet4-mexico-stateless/2018/11/b73d5a1c-b73d5a1c-informe-cenotes-gp_final.pdf
- DPLF, Agua amenazada (PDF): https://back.dplf.org/sites/default/files/resumen_ejecutivo_-_agua_amenzada_-_dplf_rodrigo_llanes_salazar.pdf
- DPLF, cenotes como sujeto de derechos (PDF): https://back.dplf.org/sites/default/files/cenotes_peninsula_yucatan_sujeto_derechos_dplf_2022_0.pdf

---

## 8. Plantilla para la hoja de apuntes

Para cada fuente, registrar:

```
FUENTE: [título]
AUTOR / ORGANIZACIÓN: [quién]
AÑO: [año]
ENLACE: [url]
TIPO: [paper / informe oficial / nota de prensa / blog técnico]
CONFIABILIDAD: [alta / media / baja]
TEMA: [agua · PUE · IA · ciberseguridad · acuífero · negocio]
RESPONDE A LA PREGUNTA #: [número de la sección 5]
DATO CLAVE: [cifra o hallazgo, textual si es posible]
¿SIRVE PARA EL PITCH?: [sí / no], ¿en qué parte?
CRITERIO QUE APOYA: [innovación / viabilidad / ciberseguridad / Green AI / balance neto / escalabilidad / presentación / bono]
NOTAS: [contexto, limitaciones]
```

**Reglas para el equipo:**
- Preferir fuentes primarias (papers, CONAGUA, CICY, UADY, organismos oficiales) sobre notas de prensa.
- Toda cifra que vaya al pitch necesita fuente y año.
- Marcar cuando un dato es de otro país y no de México.
