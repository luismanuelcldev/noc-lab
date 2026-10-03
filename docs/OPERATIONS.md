# Operaciones

El manual del día a día del laboratorio. Para el problema concreto de una alerta concreta
está [el manual de incidentes](RUNBOOK.md), que es a donde apunta la notificación.

<a id="los-nueve-servicios"></a>

## Los nueve servicios

Solo cuatro servicios publican un puerto, y los cuatro lo hacen en `127.0.0.1`. Los otros
cinco viven en la red `mesh` sin publicar nada al equipo: no hace falta, y no publicarlos
mantiene la superficie en "cuatro puertos atados a loopback" en vez de "nueve servicios
escuchando en la red".

| Servicio | Imagen | Puerto del equipo | Qué aporta |
|---|---|---|---|
| `prometheus` | `prom/prometheus:v3.15.0` | 127.0.0.1:9090 | métricas, reglas y estado de alertas |
| `alertmanager` | `prom/alertmanager:v0.34.1` | 127.0.0.1:9093 | agrupa, silencia y enruta alertas |
| `grafana` | `grafana/grafana:12.4.11` | 127.0.0.1:3000 | los trece cuadros de mando de observabilidad |
| `ntfy` | `binwiederhier/ntfy:v2.28.0` | 127.0.0.1:8085 | recibe y entrega notificaciones |
| `node-exporter` | `prom/node-exporter:v1.12.1` | sin publicar (9100) | métricas de la máquina |
| `cadvisor` | `gcr.io/cadvisor/cadvisor:v0.55.1` | sin publicar (8080) | métricas por contenedor |
| `blackbox-exporter` | `prom/blackbox-exporter:v0.28.0` | sin publicar | comprueba que los puertos responden |
| `ntfy-bridge` | `mi-noc/ntfy-bridge:1.0.0` | sin publicar (5000) | convierte las alertas de Alertmanager en mensajes de ntfy |
| `demo-app` | `nginx:1.31-alpine` | sin publicar (80) | objetivo de prueba que puedo romper a propósito |

El puerto entre paréntesis es en el que escucha dentro del contenedor, en la red `mesh`, donde
lo alcanzo desde cualquier otro contenedor por el nombre del servicio y nunca por `localhost`:
`docker compose exec prometheus wget -qO- http://node-exporter:9100/metrics`. El 8085 de ntfy
es deliberado y no el estándar: evita chocar con un ntfy que ya esté escuchando en el puerto
80 del equipo. Todos los puertos del equipo se atan a través de `NOC_BIND_ADDRESS`, así que
desde otra máquina no es alcanzable ninguno; mira [seguridad](SECURITY.md) para entender por
qué las redes no están marcadas como internas y por qué eso aquí no es un problema.

<a id="tres-decisiones-que-no-se-degradan"></a>

## Tres decisiones que no se degradan

Las nueve imágenes están clavadas y tres de esos pines no son arbitrarios. El riesgo de
"arreglarlos" por probar es que no se ve una caída: se ve un cuadro de mando que dice "No data" o
una alerta que se dispara sola. Eso es peor que un fallo, porque no se nota.

<a id="cadvisor-clavado"></a>

### cAdvisor está clavado en v0.55.1

Es la versión más antigua que lee contenedores con Docker 28 y posteriores. Con la anterior
(v0.52.1) cAdvisor ve los contenedores a través de la API pero no consigue asociarles métricas: el
objetivo aparece `up` y todas las series `container_*` existen, pero cada una mide solo el cgroup
raíz. El panel de contenedores se lee entero como "No data" y ningún *health check* se queja,
porque técnicamente todo está bien.

Lo comprobé sobre Docker 29.5.3: v0.52.1 da 1 serie y v0.55.1 da 9. Esa diferencia es la prueba de
que el fallo es de asociación y no de visibilidad. **No bajo el pin sin repetir esa misma
comparación con la versión que quiero probar.**

<a id="exclusiones-node-exporter"></a>

### La lista de exclusiones de node-exporter se repite entera

`--collector.filesystem.*-exclude` **sustituye** la lista por defecto de node-exporter, no la
amplía. Por eso la lista completa se repite tal cual en todos los servicios que la necesitan:
dejar una entrada fuera reintroduce en silencio una métrica que el exportador excluye por un
motivo concreto.

De esa lista, `9p`, `drvfs` y `rootfs` están porque son montajes de solo lectura de la máquina
anfitriona y aparecían siempre en las métricas de disco. La alerta de disco casi lleno se
disparaba sola, contra su propio sistema de archivos. Una alerta que suena sin motivo es peor que
no tenerla, porque enseña al equipo a ignorar esa alerta concreta. Corregirlo en el origen, en el
`exclude` y no en la alerta, además mantiene honesto el cuadro de recursos del equipo.

<a id="etiquetas-externas-prometheus"></a>

### Etiquetas externas al ejecutar Prometheus fuera de Docker

Las `external_labels` de [prometheus.yml](../prometheus.yml) son lo que mantiene separados los
entornos: sin ellas un solo Alertmanager mezclaría las notificaciones de todos. Sus dos valores
son `${NOC_MONITOR_NAME}` y `${NOC_ENVIRONMENT}`, y están así a propósito, porque Prometheus nunca
expande variables de entorno en un fichero de configuración: sin intervención, el texto
`${NOC_MONITOR_NAME}` llegaría tal cual a la etiqueta.

Con Docker no hay que hacer nada. `docker/prometheus-entrypoint.sh` valida ambas variables,
sustituye los marcadores y arranca Prometheus con `prometheus.rendered.yml`, generado en
`/etc/prometheus` y no en `/tmp` a propósito: `rule_files` y `scrape_config_files` son rutas
relativas que Prometheus resuelve contra el directorio de configuración, así que un fichero
generado en `/tmp` arrancaría sin reglas y sin ningún aviso. El script aborta si falta una
variable o si queda algún `${` sin sustituir, y con eso un fallo silencioso se vuelve visible.

Ejecutar Prometheus fuera de Docker significa hacer esa sustitución a mano. El fichero generado
tiene que quedar **junto a `prometheus.yml`**, por el mismo motivo de las rutas relativas, y desde
la raíz del repositorio:

```sh
sed -e "s|\${NOC_MONITOR_NAME}|$NOC_MONITOR_NAME|" \
    -e "s|\${NOC_ENVIRONMENT}|$NOC_ENVIRONMENT|" \
    prometheus.yml > prometheus.rendered.yml
prometheus --config.file=prometheus.rendered.yml
```

`prometheus.rendered.yml` no está en `.gitignore`, así que hay que borrarlo en cuanto se termine.
Si se apunta directamente a `prometheus.yml`, Prometheus arranca sin error y las alertas salen
con la etiqueta literal `${NOC_MONITOR_NAME}`: llegan, se leen, y no se pueden separar por
entorno.

## Comandos del día a día

Todo pasa por `make`, un atajo de `docker compose`. Los objetivos están en el propio
`Makefile` y `make help` los lista; en Docker Desktop, o sin `make`,
`docker compose -f docker-compose.yml -f docker-compose.desktop.yml up -d` es el equivalente
(mira [instalación](INSTALL.md) para entender por qué hay dos ficheros).

| Necesito | Comando |
|---|---|
| arrancar o parar | `make up` o `make down` |
| arrancar en Windows o macOS | `make up-desktop` |
| ver qué está corriendo | `make status` |
| reiniciar un servicio | `make restart SERVICE=prometheus` |
| leer los logs de uno | `make logs SERVICE=alertmanager` |
| seguir los logs de uno | `make follow SERVICE=ntfy-bridge` |
| validar paneles y documentos | `make check` |
| ejecutar todas las pruebas | `make test` |
| parar y borrar los datos | `make destroy CONFIRM=DESTROY` |

`make destroy` pide confirmación mediante una variable y no por teclado, así que se comporta
igual en Windows, en Linux y en un script. Sin `CONFIRM=DESTROY` no borra nada y sale con
error.

## Leer el estado

El estado de los objetivos de Prometheus es mi primera pregunta cuando algo no funciona:
`curl -s http://127.0.0.1:9090/api/v1/targets | python3 -m json.tool`. Miro `health`, que es
`up` o `down`. En un laboratorio sano hay ocho `up` y ningún `down`: el propio Prometheus,
Alertmanager, node-exporter, cAdvisor, el puente y las tres sondas blackbox (HTTP, TCP y la
dinámica). Un objetivo caído es casi siempre un servicio que no arrancó, no un problema de
red. Para un servicio que no publica puerto entro en la red interna:
`docker compose exec prometheus wget -qO- http://ntfy-bridge:5000/metrics`.

El estado de las alertas es `curl -s http://127.0.0.1:9090/api/v1/alerts | python3 -m json.tool`.
Normalmente hay exactamente una alerta activa, `LatidoDeMonitorizacion`, encendida siempre a
propósito para que un silencio accidental de todo el conjunto se note como una ausencia de
notificaciones. Si hay más de una, hay algo que leer en el [manual de incidentes](RUNBOOK.md).

<a id="silenciar-una-alerta"></a>

## Silenciar una alerta

Para que no llegue a la guardia:

```sh
curl -s -XPOST http://127.0.0.1:9093/api/v2/silences \
  -H 'Content-Type: application/json' \
  -d '{"matchers":[{"name":"alertname","value":"DiscoCasiLleno","isRegex":false}],"startsAt":"2026-01-01T00:00:00Z","endsAt":"2026-01-01T02:00:00Z","comment":"ventana de mantenimiento","createdBy":"operator"}'
```

Un silencio tiene una hora de fin obligatoria. Si necesito más lo renuevo; no hay silencio
eterno, porque el estado real de la máquina puede cambiar mientras tanto. El `comment` no es
opcional en la práctica: es lo que lee el siguiente turno, y escribir "por qué" hace que el
silencio se renueve por inercia mucho después de que el problema haya desaparecido.

## Inhibiciones

Las reglas de inhibición están en [alertmanager.yml](../alertmanager.yml) y son pocas a
propósito. Una inhibición quita el ruido de una cascada, no esconde un problema: mientras un
`TargetCaido` está activo, las alertas de disponibilidad de ese mismo objetivo no aportan
nada, y mientras un `DiscoCriticamenteLleno` está activo, un `DiscoCasiLleno` en el mismo
sistema de archivos es ruido, no información. Un punto ciego: si se silencia el origen de la
cascada, la inhibición deja de aplicarse y vuelven las alertas derivadas. Eso es correcto,
porque un problema principal silenciado significa que alguien ya lo está mirando.

## Rotar estado sin perderlo

`docker compose restart prometheus` no pierde nada que importe. **Prometheus** pierde unos
segundos de métricas, y las cláusulas `for` que estaban a medio cumplir tienen que aguantar el
periodo entero otra vez antes de dispararse: comportamiento correcto, no un fallo.
**Alertmanager** guarda silencios, ventanas temporales y estado de grupos en
`noc-alertmanager-data`. **Grafana** guarda usuarios y preferencias en `noc-grafana-data` y
relee los paneles aprovisionados. **ntfy** guarda topics y suscripciones en `noc-ntfy-data`;
si ese volumen se borra, el topic se recrea vacío y las notificaciones dejan de llegar hasta
que alguien se suscriba otra vez.

<a id="copias-de-seguridad"></a>

## Copias de seguridad

Lo que merece la pena guardar, por orden de importancia: **(1)** `rules/`, los módulos de
`rules/`, `alertmanager.yml`, `prometheus.yml` y `blackbox.yml`, porque son el sistema: sin
ellos el stack arranca pero no vigila nada. **(2)** `.env.example`, nunca `.env`. Las claves
reales se pueden regenerar, el fichero de ejemplo no. **(3)** Los cuatro volúmenes, para
conservar el estado entre reinstalaciones: `noc-prometheus-data` (histórico de métricas),
`noc-alertmanager-data` (silencios, ventanas temporales, estado de grupos),
`noc-grafana-data` (paneles, usuarios, preferencias) y `noc-ntfy-data` (topics,
suscripciones).

Los paneles de Grafana **no** se guardan aparte: viven en `grafana/dashboards/` como JSON y se
releen al arrancar, que es lo que evita dos versiones que no concuerdan. Un volumen se vuelca
con
`docker run --rm -v "$PWD":/w -v noc-prometheus-data:/d:ro -v "$PWD/backup":/b alpine tar czf /b/prometheus-$(date +%F).tar.gz -C /d .`.
Los volúmenes tienen nombres con el prefijo `noc-` a propósito: sin un nombre fijo el volumen
se llama `<carpeta>_prometheus-data`, que cambia si se renombra el directorio, y una copia
silenciosa deja de encontrarlo. Este repositorio no trae copia automática, porque el
laboratorio está pensado para perder su histórico sin consecuencias: las alertas informan de
problemas del sistema vivo, no de la pérdida de histórico.

## Disco y reinicios completos

El laboratorio vigila su propio disco con tres alertas escalonadas
(`DiscoCriticamenteLleno`, `DiscoCasiLleno`, `CrecimientoDeDiscoExcesivo`), así que no hace
falta comprobarlo a mano; `docker system df` y `docker volume ls` responden igualmente. El
crecimiento habitual es `noc-prometheus-data` y las imágenes sin usar. `docker image prune -a`
y `docker volume prune` liberan espacio, pero el segundo borra también los datos de Prometheus
y los silencios de Alertmanager, así que lo uso con el stack parado y solo cuando tengo claro
qué se va. Cuando algo va genuinamente mal y no sé por dónde empezar, `make down` seguido de
`make up` (o `make up-desktop`) es siempre el primer paso y siempre funciona: perder diez
minutos de histórico de métricas es mejor que pasar tres días depurando un estado
inconsistente.
