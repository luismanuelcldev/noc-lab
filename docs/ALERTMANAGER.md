# Alertmanager: decisiones del diseño

Este documento recoge el razonamiento completo detrás de `alertmanager.yml`.
El fichero de configuración lleva solo un resumen y apunta aquí, para que
caben en 100 líneas sin perder el "por qué".

## Qué hace Alertmanager aquí

Cinco tareas, en orden de importancia real:

1. **Deduplicar** → una alerta de N réplicas de Prometheus se notifica una vez.
2. **Agrupar** → N alertas relacionadas salen como una sola notificación.
3. **Inhibir** → una causa raíz firing silencia sus consecuencias. Es lo que
   evita la tormenta de 300 alertas.
4. **Enrutar** → cada grupo va al equipo que lo es dueño.
5. **Silenciar** → supresión temporal durante mantenimiento.

## Por qué no hay variables de entorno en la configuración

Alertmanager **no** expande `${VAR}` en su fichero de configuración. Escribir
`${BRIDGE_TOKEN}` ahí no produce un token: produce esa cadena literal, que
después acaba en una cabecera `Authorization` inválida y en un 401 difícil de
diagnosticar porque el error parece de red y no de configuración.

Las credenciales del webhook las inyecta `docker/alertmanager-entrypoint.sh`
sobre una copia en tmpfs del fichero, solo para los webhooks que apuntan al
bridge. Así el token se genera en el momento del despliegue y nunca vive en el
repositorio. Si `BRIDGE_TOKEN` está vacío el script no inyecta nada y el bridge
acepta llamadas sin autenticar, lo cual es aceptable en este laboratorio
autoalojado porque el bridge no publica puerto de host y solo es alcanzable
desde la red `mesh`. Fuera de aquí, eso necesita TLS y autenticación en el
propio ntfy. Ver `docs/SECURITY.md`.

## Por qué no hay plantillas propias

Decisión medida contra un Alertmanager 0.34.1 real, no asumida:

1. Las plantillas se aplican **solo** a receivers de email y a la propia UI de
   Alertmanager. Un webhook nunca las renderiza.
2. `payload` (desde 0.32) sí renderiza, pero **reemplaza** el cuerpo entero en
   lugar de añadir a él. En una prueba real el POST llegó con una única clave
   `summary_text`: sin `alerts`, sin `status`, sin `groupLabels`, sin
   `commonLabels`.

Por eso Alertmanager envía su cuerpo por defecto, que es el contrato
documentado y estable, y el bridge formatea el texto. La ventaja es que el
formato vive en Python, donde un test puede comprobarlo, en lugar de dentro de
una cadena de plantilla Go que solo se revela como incorrecta cuando llega una
alerta.

## Enrutado: el orden es el diseño

Las rutas se evalúan de arriba abajo y se detiene en la **primera** coincidencia,
así que el orden importa de verdad:

1. `severity="info"` → `registro-interno`. Va primero a propósito:
   `LatidoDeMonitorizacion` es `severity="info"`, así que si la regla de
   monitorización se evaluara antes caería aquí y despertaría a una persona cada
   hora, justo lo contrario de lo que hace una alerta diseñada para no notificar.
   Un receiver sin webhook la deja en la UI y en los dashboards y no cuesta
   atención.
2. `service="monitoring"` → `equipo-monitoreo`. Si la monitorización está caída,
   ese incidente es del equipo de monitorización, no del negocio de guardia.
3. `severity="critical"` → `guardia` con `group_wait: 10s`: una crítica no
   espera 30s a agruparse. Lleva `continue: true` para que también aplique la
   regla 4 y una crítica sostenida llegue al equipo de negocio.
4. `severity="warning"` → `equipo-backend` con `repeat_interval: 12h`: un aviso
   se lee mañana por la mañana, así que 12h no es una alerta perdida.

`group_by: ["alertname", "service"]` es deliberado: dos críticas en servicios
distintos son problemas distintos, normalmente con dueños distintos, y no deben
colapsar en una sola notificación.

## Inhibición: la diferencia entre un config de principiante y uno de monitorización

Sin `inhibit_rules`, un host que cae dispara decenas de alertas a la vez (host
caído, CPU a cero, sockets cerrados, disco ilegible) y el equipo solo procesa
ruido. Con ellas, las consecuencias quedan registradas pero no notificadas.

### 1. Host caído silencia las alertas de infraestructura de ese host

**`equal` es `["job"]`, NO `["instance"]`, y no es cosmético.** La regla origen
es `absent_over_time(node_uname_info{job="node"}[5m])`, y `absent()` devuelve
una serie que lleva **solo** las etiquetas del selector de igualdad, aquí
`{job="node"}`. No hay etiqueta `instance` porque no queda un host concreto al
que apuntar.

Con `equal: ["instance"]` esta regla no podría coincidir nunca: `""` contra
`""` primero, y nunca contra el host real. Una regla de inhibición que no
inhibe nada es peor que no tenerla, porque aparenta estar previendo tormentas
mientras no previene ninguna. Esa es también la razón por la que el resumen de
alertas ya no imprime `$labels.instance`.

### 2. Canal caído silencia alertas de entrega

Si no, el fallo se alimenta solo: alertas sobre el canal que no puede entregar.

### 3. Una crítica abierta silencia avisos del mismo servicio e instancia

Si un servicio está caído, que además te digan que va lento es redundante.

### 4. Un servicio caído silencia sus propias sondas

Las sondas HTTP y TCP fallan juntas por definición cuando el servicio muere:
dos alertas, una causa.
