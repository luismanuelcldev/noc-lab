# Manual de incidentes

Lo que hago cuando se dispara cada alerta, escrito para que se lea a las 3 de la
madrugada: el disparador, cómo lo reconozco, qué hago y cómo confirmo que se acabó.
**Si una entrada dice "nunca X" y X era mi primer impulso, paro: eso es la corrección,
no un consejo.** Los nombres se quedan en español porque son los identificadores de
`rules/`, y cada sección lleva un ancla HTML explícita porque su `runbook_url` apunta
ahí, cosa que `scripts/check.py` obliga. Los comandos se ejecutan desde la raíz del
repositorio; en Docker Desktop añade `-f docker-compose.desktop.yml`.

<a id="no-dispara-todo-al-instant"></a>

## No se dispara todo al instante

Un sistema de monitorización se juzga por las alertas que llegan cuando deben **y** por
las que se quedaron calladas, y de esas dos solo se habla de una. Toda regla lleva un
`for:`: cuánto debe aguantar la condición antes de que entre una persona. Un sistema que
avisa de cada parpadeo enseña a la gente a ignorarlo, y uno que nadie lee no detecta nada.
| `for:` | Alertas | Por qué este tiempo |
|---|---|---|
| ninguno | `LatidoDeMonitorizacion` | Debe estar siempre disparada: un interruptor de hombre muerto con `for:` se calla justo cuando la monitorización se rompe. |
| 1m | `ServicioCaido`, `PuertoTCPInaccesible`, `BridgeNotificacionInaccesible` | Un servicio caído o el camino de notificación caído. Nadie discute un minuto de caída, y quita el ruido de despliegues sin esconder una caída real. |
| 1m | `HostReiniciado` | Barato de enunciar, imposible de pasar por alto después: el contador de tiempo activo se reinició. |
| 2m-5m | objetivos, sondas, contenedores, sistema de archivos de solo lectura | Un componente que se porta mal: lo bastante largo para ser un fallo, lo bastante corto para actuar. |
| 10m-30m | discos, memoria, CPU, reloj | Tendencias y agotamiento. Aún no son incidentes, y avisar de ellas a las 3 de la madrugada es lo que acaba silenciando el sistema entero. |

## Cuando no llega ninguna notificación

Una resolución que nunca llega **no** es un fallo: la alerta se resolvió antes de que
transcurriera `group_wait`, así que no había nada que enviar. Cuando una alerta *disparada*
no llega, compruebo, en este orden: `ntfy_bridge_delivery_success`, el contador
`result="rejected"` por un desajuste de token, la ACL del topic y, por último, la URL del
webhook. Ver [CanalNotificacionCaido](#canal-notificacion-caido) y
[BridgeNotificacionInaccesible](#bridge-inaccesible).
**Metaservicio: la propia monitorización**
## LatidoDeMonitorizacion <a id="latido-de-monitorizacion"></a>
`info` · sin `for:` · `vector(1)`. La única alerta que debería estar siempre disparada. **Haz:** si está `resolved` o no aparece, Prometheus está vivo (`wget -qO- http://localhost:9090/-/healthy`) y el problema es la carga de reglas; si no responde, Prometheus está caído. Comprueba `prometheus_config_last_reload_successful`.
## PrometheusSinScrapear <a id="prometheus-sin-scrapear"></a>
`critical` · `for: 3m` · `up{job="prometheus"} == 0`. **Haz:** ¿vive el proceso? Vivo pero sin raspar significa casi siempre que se quedó sin disco. **Nunca** borres el TSDB para hacer sitio mientras está en marcha.
## TargetCaido <a id="target-caido"></a>
`warning` · `for: 2m` · un objetivo de raspado está `down` en <http://localhost:9090/targets>. **Haz:** `docker compose ps`, y luego los logs de ese contenedor. Un objetivo caído es un contenedor; todos ellos son Prometheus.
## BridgeNotificacionInaccesible <a id="bridge-inaccesible"></a>
`critical` · `for: 1m` · `up{job="ntfy-bridge"} == 0`. La alerta llega a Prometheus y a ningún canal. **Haz:** ¿está en pie y está rechazando por el token? Un `result="rejected"` al alza significa que el token que envía Alertmanager no es el que tiene el puente. **Nunca** pruebes el token en una URL: acaba en el historial del shell y en el log de Prometheus.
## CanalNotificacionCaido <a id="canal-notificacion-caido"></a>
`critical` · `for: 5m` · `max by (sink) (ntfy_bridge_delivery_success == bool 0) > 0`. **Haz:** lee la etiqueta `sink`, nombra el que está roto. Un receptor webhook que falla es casi siempre el token; uno externo que falla es su entorno. **Nunca** silencies esto para que dejen de llegar páginas: es la alerta que dice que las demás no van a ninguna parte.
**Disponibilidad: el servicio en sí**
## ServicioCaido <a id="servicio-caido"></a>
`critical` · `for: 1m` · `probe_success{job="blackbox-http"} == 0`. **Esta es la alerta que declara una caída.** Llega como `[CRITICAL] web-frontal`. **Haz:** confirma que `probe_success` es 0, comprueba el servicio desde dentro de la red y después su puerto. Responde desde dentro pero no desde la sonda significa que el problema es la ruta, no la aplicación. **Nunca** reinicies Prometheus para "arreglar" una sonda.
## PuertoTCPInaccesible <a id="puerto-tcp-inaccesible"></a>
`critical` · `for: 1m` · `probe_success{job="blackbox-tcp"} == 0`. **Haz:** distingue rechazado de tiempo agotado, apuntan a fallos distintos. Rechazado = no escucha nadie, así que lee los logs. Tiempo agotado = algo en medio filtra. **Nunca** tomes un tiempo agotado por un servicio muerto, o reiniciarás uno sano.
## SondaDevueltaRespuestaInvalida <a id="sonda-respuesta-invalida"></a>
`warning` · `for: 2m` · `probe_http_status_code != 200`. **Haz:** mira qué devuelve de verdad. Un HTML de error o una página de login significan que el servicio está caído *para el usuario* aunque responda, que es justo lo que una sonda simple no ve.
## TiempoDeRespuestaAlto <a id="tiempo-de-respuesta-alto"></a>
`warning` · `for: 3m` · `probe_duration_seconds > 1`. **Haz:** si la latencia sube con la CPU normal, el problema está en la aplicación. Si suben juntas, ve a [CPUHostAlta](#cpu-alta). **Nunca** subas el umbral antes de leer cuál de las dos es.
**Recursos del equipo**
## TargetHostCaido <a id="target-host-caido"></a>
`critical` · `for: 3m` · el job `node` se queda vacío y todos los paneles del equipo pierden datos. **Haz:** si el equipo está vivo, lee los flags del exportador: un `--path` mal puesto da exactamente esto y parece un equipo muerto.
## DiscoCasiLleno <a id="disco-casi-lleno"></a>
`warning` · `for: 10m` · por debajo del 15% libre. **Haz:** busca el mayor consumidor y luego libera lo que no tiene consecuencias: logs rotados, imágenes sin usar. **Nunca** borres datos del TSDB bajo `/prometheus` ni configuración para hacer sitio.
## DiscoCriticamenteLleno <a id="disco-criticamente-lleno"></a>
`critical` · `for: 5m` · por debajo del 5% libre. El TSDB deja de escribir, y con él se pierde la memoria del incidente. **Haz:** libera ya lo seguro; si eso no llega al 15%, elige entre agrandar el disco y aceptar pérdida de datos. **Nunca** reinicies nada para "liberar RAM" esperando que el disco se recupere.
## DiscoSoloLectura <a id="disco-solo-lectura"></a>
`critical` · `for: 2m` · `node_filesystem_readonly == 1`. Todo parece "vivo" y no dispara ninguna alerta de recursos, pero no se escribe nada. **Haz:** confirma qué sistema de archivos es y por qué. **Nunca** hagas `remount,rw` a ciegas: si el hardware está fallando, eso es una decisión de negocio, no una orden.
## MemoriaHostAlta <a id="memoria-alta"></a>
`warning` · `for: 10m` · por encima del 90% usado. **Haz:** ¿un contenedor o todo el equipo? Uno lleva a [ContenedorUsoMemoriaAlto](#contenedor-memoria-alto). Todo el equipo suele ser caché de página, que Linux reclama bajo demanda y no es una fuga.
## HostSinMemoria <a id="host-sin-memoria"></a>
`critical` · `for: 5m` · por debajo de 256 MiB disponibles, donde el kernel empieza a matar procesos. **Haz:** mira quién se la está comiendo. Reiniciar un contenedor es aceptable **solo** si sé cuál es.
## CPUHostAlta <a id="cpu-alta"></a>
`warning` · `for: 15m` · carga alta sostenida. **Haz:** primero por contenedor. Carga alta con CPU ociosa significa una cola de ejecución atascada en E/S, no CPU. **Nunca** añadas un límite de CPU para "arreglar" un pico antes de saber la causa.
## HostReiniciado <a id="host-reiniciado"></a>
`info` · `for: 1m` · tiempo activo por debajo de 15m. **Haz:** nada urgente, pero invalida todos los "desde" de las demás alertas, así que compruebo que estaba previsto. **Nunca** dejes que sea la única pista de que un equipo se reinició a las 3 de la madrugada.
## RelojDesincronizado <a id="reloj-desincronizado"></a>
`warning` · `for: 10m` · desfase por encima de 50ms. **Haz:** lee el desfase que usa la regla y arregla el servicio de hora del equipo. **Nunca** subestimes esta: un reloj desfasado hace que dos eventos parezcan simultáneos cuando estaban separados por minutos, y ni mil líneas de log deshacen eso.
**Contenedores y tendencias**
## ContenedorUsoCPUAlto <a id="contenedor-cpu-alto"></a>
`warning` · `for: 5m`. **Haz:** ¿es el contenedor `prometheus`? Un pico tras recargar reglas es normal y se autolimita. ¿Es la aplicación? Entonces el límite de CPU está haciendo su trabajo. **Nunca** trates un pico de recarga como un incidente.
## ContenedorUsoMemoriaAlto <a id="contenedor-memoria-alto"></a>
`warning` · `for: 5m`. **Haz:** ¿crece sin parar o se mantiene estable cerca del límite? Crecer es una fuga y el kernel lo matará por OOM. Estable cerca del límite es el límite haciendo su trabajo. Ver `Memoria frente al límite, por contenedor`.
## ContenedorReiniciado <a id="contenedor-reiniciado"></a>
`warning` · `for: 2m` · `changes(container_start_time_seconds[10m]) >= 2`. **Haz:** la causa más común es el límite de memoria, así que busca un OOM kill y luego lee el log justo antes del reinicio. Varios reiniciándose a la vez significan que el primero en caer es la causa. **Nunca** reinicies todo el stack para "limpiar" un bucle de fallos.
## CrecimientoDeDiscoExcesivo <a id="crecimiento-de-disco"></a>
`warning` · `for: 30m` · `predict_linear(node_filesystem_avail_bytes[6h], 86400) < 0`. El disco se llena en 24h al ritmo actual. **Haz:** actúa sobre la predicción, no sobre el espacio libre de hoy. **Nunca** borres histórico para acortar la ventana: una ventana más corta oculta la pendiente, que es lo único que mide esta alerta.
Las reglas que ya no existen están en [ALERTS-RETIRED.md](ALERTS-RETIRED.md) con el motivo de
cada una, porque "por qué esto desapareció" se pregunta siempre durante un incidente.
