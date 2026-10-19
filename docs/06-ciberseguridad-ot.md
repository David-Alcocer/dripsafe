# 06 · Ciberseguridad OT: guía rápida

> Documento para **Guille**. No tienes que ser experto: solo saber explicar con claridad **qué amenazas existen, cuáles detecta nuestro modelo y qué recomendaríamos**. El 22 hay mentores de ciberseguridad para validar.

## 1. ¿Qué es OT/ICS?

- **IT** (tecnología de la información): computadoras, servidores, correo, datos.
- **OT** (tecnología operacional): sistemas que controlan **equipos físicos** como bombas, válvulas, chillers y torres de enfriamiento.
- **ICS** (Industrial Control Systems): los sistemas de control industrial. Incluyen:
  - **Sensores:** miden temperatura, flujo, presión y energía.
  - **PLCs** (controladores lógicos programables): reciben lecturas y mandan órdenes a los equipos.
  - **SCADA / HMI:** las pantallas desde donde el operador ve y controla todo.

En un centro de datos, el sistema de enfriamiento es OT: si falla o lo atacan, los servidores se sobrecalientan o se desperdicia agua y energía.

### Modelo Purdue (en una línea)
Es la forma clásica de dividir una red industrial en niveles: sensores y actuadores (0), PLCs (1), SCADA/HMI (2), operaciones (3) y red corporativa (4–5). **La regla de oro es que los niveles bajos no deberían estar expuestos a internet.**

## 2. ¿Por qué son vulnerables?

- **Protocolos antiguos sin seguridad.** **Modbus** (de 1979) y muchas configuraciones de **BACnet** **no autentican ni cifran**: cualquiera que llegue a la red puede leer valores o mandar órdenes.
- **Equipos que duran 15 a 20 años** y casi nunca se actualizan.
- **Redes IT y OT mal separadas.**
- **Accesos remotos** de mantenimiento mal protegidos.

## 3. Técnicas de ataque que detectaría nuestro modelo

Del catálogo **MITRE ATT&CK for ICS** (<https://attack.mitre.org/matrices/ics/>). Verifica los IDs y descripciones en la matriz antes del pitch.

| Técnica | ID | Qué es | Cómo la detecta DripSafe |
|---|---|---|---|
| Manipulation of View | T0832 | El operador ve datos falsos en su pantalla | Las lecturas no cuadran con la física (por ejemplo, la temperatura "baja" sin que el chiller consuma más) |
| Spoof Reporting Message | T0856 | Un sensor reporta valores inventados | Un sensor se separa del comportamiento correlacionado de los demás |
| Modify Parameter | T0836 | Alguien cambia valores de configuración (setpoints) | Cambio brusco de un parámetro fuera del patrón normal u horario |
| Unauthorized Command Message | T0855 | Llegan órdenes no autorizadas a bombas o válvulas | Arranques y paros que no corresponden con la carga ni el horario |
| Manipulation of Control | T0831 | El atacante altera el control físico del proceso | Consumo de energía o agua anómalo sin causa operativa |

**Mensaje clave para el pitch:**
> "DripSafe funciona como **primera capa de detección**: no reemplaza un firewall ni un SOC, pero detecta cuando los datos físicos del enfriamiento no tienen sentido, que es justo lo que pasa cuando alguien manipula sensores o controladores."

## 4. Cómo distinguir falla de ataque

- **Falla o ineficiencia:** suele afectar varias variables de forma **coherente** y aparece de forma gradual (desgaste o suciedad en intercambiadores).
- **Ataque:** suele mostrar **incoherencias** (un sensor dice una cosa y el resto otra), cambios **bruscos**, o actividad **fuera de horario**.

Esto se diseña con Gadiel. Ver [05-solucion-tecnica.md](05-solucion-tecnica.md).

## 5. Recomendaciones de defensa (para la propuesta)

Basadas en **ISA/IEC 62443**, el estándar de seguridad industrial:
- **Zonas y conductos:** separar la red OT del enfriamiento de la red IT y controlar qué tráfico pasa entre ellas.
- **Lista blanca de comandos:** solo ciertos equipos pueden mandar órdenes a los PLCs.
- **Monitoreo continuo:** aquí entra DripSafe.
- **Acceso remoto seguro:** VPN, llaves SSH y autenticación multifactor. Lo que ya sabes del server aplica.
- **Respaldo manual:** si se detecta un ataque, el sistema pasa a un modo seguro.

## 6. Qué revisar en el kit (lunes 19)

- [ ] ¿Qué equipos aparecen (chillers, torres, bombas, CRAC/CRAH)?
- [ ] ¿Qué protocolos usan (Modbus TCP, BACnet/IP, OPC UA)?
- [ ] ¿Hay diagrama de red o arquitectura?
- [ ] ¿Hay eventos de ataque o falla marcados en los datos?

## 7. Entregable de Guille

- 1 o 2 diapositivas: amenazas → cómo las detectamos → recomendaciones.
- Tabla final de técnicas de ATT&CK aplicadas al caso del kit.

## Regla del hackatón
**Prohibido hacer pruebas o ataques sobre sistemas reales.** Todo se hace sobre el kit de datos o en simulaciones. Los "ataques" se simulan modificando datos en un CSV, nunca contra equipos reales.

## Para leer más
Ver la sección "Ciberseguridad OT" en [09-recursos.md](09-recursos.md).
