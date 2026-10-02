# Instalación

## 0. Traer el repositorio

```bash
git clone https://github.com/luismanuelcldev/noc-lab.git
cd noc-lab
```

El nombre del repositorio en GitHub es `noc-lab` y el del producto es `mi-noc`: es lo mismo,
pero conviene saberlo antes de que un `git remote -v` despierte la duda.

## Requisitos

| | Mínimo | Recomendado |
|---|---|---|
| Docker Engine | 24.0 | 27.x |
| Docker Compose | v2.20 (admite `depends_on: condition: service_healthy`) | v2.29 |
| RAM libre | 2 GB | 4 GB |
| Disco | 5 GB | 20 GB (el TSDB crece) |

En el equipo no se instala nada más: ni Python, ni Prometheus, ni Grafana. Todo corre en
contenedores, y los puertos que necesito libres son 3000, 8085, 9090 y 9093 en `127.0.0.1`.

## 1. Configurar las variables

Empiezo por `cp .env.example .env` y luego genero dos secretos, en dos terminales distintas
para no pegar el que no es. **No los escribo a mano**: se generan, se guardan y punto.

```bash
python3 -c "import secrets; print('GF_SECURITY_ADMIN_PASSWORD=' + secrets.token_urlsafe(18))"
python3 -c "import secrets; print('BRIDGE_TOKEN=' + secrets.token_hex(32))"
```

Copio cada uno a `.env` y dejo todas las demás variables tranquilas: cada una tiene un valor
por defecto pensado para un laboratorio, y `docker compose config --quiet` confirma que el
fichero está bien formado, fallando ante una variable sin definir o un `:` suelto si algo va
mal. Tres no tienen valor por defecto a propósito, porque Compose **aborta en vez de
arrancar con un valor inventado**, que es justo lo que haría un `${VAR:-admin}`:
`GF_SECURITY_ADMIN_PASSWORD`, sin la cual Grafana arranca como `admin/admin` en un puerto
publicado; `BRIDGE_TOKEN`, sin el cual el puente acepta cualquier cosa que llegue a su red; y
`PROM_RETENTION_TIME` junto con `PROM_RETENTION_SIZE`, sin límite el TSDB crece hasta llenar
el disco y pararlo todo.

### Referencia rápida

Son 18 variables, y esta tabla es solo el mapa: el porqué de cada una está escrito línea a línea
en [`.env.example`](../.env.example), que es la fuente. Si algo no cuadra, ese fichero gana.

| Variable | Por defecto | Para qué |
|---|---|---|
| `NOC_ENVIRONMENT` | `lab` | evita que las alertas de un entorno lleguen a otro |
| `NOC_MONITOR_NAME` | `mi-noc` | external label de Prometheus |
| `NOC_BIND_ADDRESS` | `127.0.0.1` | **la más importante**: quién alcanza los puertos |
| `PROM_RETENTION_TIME` | *sin defecto* | tope de edad del TSDB |
| `PROM_RETENTION_SIZE` | *sin defecto* | tope de tamaño del TSDB |
| `GF_SECURITY_ADMIN_USER` | `admin` | usuario inicial de Grafana |
| `GF_SECURITY_ADMIN_PASSWORD` | *sin defecto* | contraseña inicial de Grafana |
| `NTFY_TOPIC` | `noc-alerts` | topic donde caen las alertas |
| `NTFY_URL` | `http://ntfy:80` | servicio interno; nunca un SaaS público |
| `NTFY_BASE_URL` | `http://localhost:8085` | URL que usa el **móvil**, no el que envía |
| `NTFY_UPSTREAM_BASE_URL` | vacío | solo iPhone: ntfy.sh despierta la app |
| `NTFY_ENABLE_LOGIN` | `false` | activar antes de exponer el puerto |
| `NTFY_AUTH_DEFAULT_ACCESS` | `read-write` | `deny-all` en cuanto salga a la red |
| `NTFY_USER` / `NTFY_PASSWORD` | vacío | credenciales del puente para publicar |
| `NTFY_TOKEN` | vacío | tiene prioridad sobre el par usuario/contraseña |
| `BRIDGE_TOKEN` | *sin defecto* | lo que Alertmanager envía en `Authorization` |
| `LOG_LEVEL` | `INFO` | `DEBUG` vuelca payloads: nunca en producción |

Las cuatro marcadas *sin defecto* son las que hacen que `docker compose config` falle en vez de
inventar un valor: es una molestia al instalar y una red de seguridad después.

## 2. Arrancar el stack

```bash
docker compose up -d                                    # Linux
docker compose -f docker-compose.yml -f docker-compose.desktop.yml up -d   # Windows o macOS
```

Necesito el segundo fichero en Docker Desktop porque no implementa el montaje `ro,rslave` que
usa el fichero base; con `make` los objetivos son `make up` y `make up-desktop`, elegidos a
mano porque `make` no sabe en qué sistema corre. Equivocarse se nota: es fácil olvidar el
override, y un stack arrancado sin él falla con un error de montaje que no se explica solo, y
por eso los objetivos son distintos y con nombre explícito en vez de uno que adivine.

## 3. Confirmar que funciona

`make status` tarda entre 60 y 90 segundos: los healthchecks son deliberados y las sondas
sintéticas necesitan dos ciclos de raspado antes de tener histórico. Considero el arranque
correcto cuando los 9 contenedores dicen `running (healthy)` y **ninguno está en `starting` ni
en `unhealthy`**, porque un healthcheck que falla impide que `depends_on` libere al siguiente
y deja el stack a medio levantar; los 8 de 8 objetivos están `up` en
<http://localhost:9090/targets>; solo `LatidoDeMonitorizacion` está `firing`; y los logs del
puente no traen líneas de error. Si se dispara algo más, paro y averiguo qué es, porque un
stack recién arrancado con alertas disparadas suele ser un falso positivo y no un problema
real, y `scripts/check.py` lista qué se está disparando y por qué.

<a id="abrirlo"></a>

## 4. Abrirlo

| Qué | Dónde | Credenciales |
|---|---|---|
| Paneles | <http://localhost:3000> | `admin` y la contraseña de `.env` |
| Prometheus | <http://localhost:9090> | ninguna |
| Alertmanager | <http://localhost:9093> | ninguna |
| ntfy | <http://localhost:8085> | ninguna |

Los trece cuadros de mando aprovisionados viven en la carpeta **Centro de monitorización**, y no los
edito en la UI: los cambios hechos ahí se pierden al reiniciar, así que todo cambio va a los
ficheros JSON del repositorio. **Un detalle de Grafana que cuesta una hora a la gente:**
`GF_SECURITY_ADMIN_PASSWORD` solo se aplica cuando Grafana crea su base de datos, así que si
el volumen ya existe el usuario guardado conserva la contraseña antigua y la de `.env` se
ignora. Si no puedo entrar, o uso la contraseña que puse la primera vez, o la restablezco con
`docker compose exec grafana sh -c 'grafana cli admin reset-admin-password "$GF_SECURITY_ADMIN_PASSWORD"'`, leyéndola de la propia variable del contenedor para que el secreto no aparezca nunca en el historial de mi shell ni en la lista de procesos.

## 5. Demostrar que toda la cadena funciona

`make smoke-desktop`, o `make smoke` en Linux, es el paso que separa "tengo un stack" de
"tengo monitorización": tira el servicio sintético, comprueba que la alerta llega de verdad a
ntfy, lo vuelve a levantar y espera a la resolución, después de confirmar que los nueve
contenedores están sanos para que un fallo de arranque no se confunda con un fallo de
alertas. Tarda unos seis minutos —once si una alerta tarda en dispararse, porque 240 s y 420 s
son un techo— y no hay nada que ganar apurándolo, porque las alertas
necesitan un minuto para dispararse y las resoluciones esperan al siguiente `group_interval`,
cinco minutos más, que el script lee de `alertmanager.yml` en vez de fijarlo a fuego por si
alguien lo cambia. Si no llega ningún mensaje, el problema no está en las reglas sino en algún
punto entre Prometheus y ntfy, y compruebo en este orden: <http://localhost:9090/targets> todo
`up`; <http://localhost:9093/#/silences> nada silenciado por accidente;
`docker compose logs alertmanager` por errores de entrega; las métricas del puente
`ntfy_bridge_delivery_success` y `result="rejected"`; y las entradas del manual de incidentes
para [BridgeNotificacionInaccesible](RUNBOOK.md#bridge-inaccesible) y

Antes del smoke, `python scripts/check.py --strict --prometheus http://127.0.0.1:9090` (o
`make check-datos`) recorre los 50 paneles y ejecuta sus 53 expresiones contra el Prometheus que
acabo de levantar. Es el paso que separa "los paneles tienen sintaxis correcta" de "los paneles
enseñan datos": una métrica renombrada deja la expresión válida y el panel en blanco, y sin esta
comprobación eso no lo dice nadie. Está fuera del pipeline a propósito, porque un Prometheus
recién arrancado no tiene historia y tres paneles usan ventanas de `[6h]` y `[30d]`.
[CanalNotificacionCaido](RUNBOOK.md#canal-notificacion-caido), que cubren los desajustes de
token que causan casi todos los fallos silenciosos.

<a id="la-alerta-en-el-movil"></a>

## 6. La alerta en el móvil

Todo lo anterior demuestra que la cadena funciona desde mi escritorio. Un centro de
monitorización no es un centro de monitorización hasta que la alerta llega a la persona que
tiene que actuar, y aquí es donde "el laboratorio está levantado" y "alguien recibió el aviso
de verdad" resultan ser afirmaciones distintas.

**Mueve los cuatro ajustes a la vez, nunca uno solo.** Un móvil no puede alcanzar
`127.0.0.1`, y los atajos obvios son todos peores que hacerlo bien. En `.env`:
`NOC_BIND_ADDRESS=0.0.0.0`, `NTFY_BASE_URL=http://<la-IP-LAN-de-esta-máquina>:8085`,
`NTFY_ENABLE_LOGIN=true`, `NTFY_AUTH_DEFAULT_ACCESS=deny-all`. El primero publica ntfy en la
red, pero también Prometheus y Grafana, que se quedan sin autenticación y no son de fiar
desde otra máquina. El segundo es la dirección que usa el *móvil*, donde `localhost` está
activamente mal porque en el móvil `localhost` es el propio móvil y todos los enlaces del
mensaje no llevan a ninguna parte; en Windows es la IPv4 del adaptador de Wi-Fi, no la de WSL
ni la de Hyper-V, y `ipconfig` la encuentra. Los dos últimos son un solo mando y no dos,
porque el login por sí solo no cambia nada mientras el rol anónimo conserve su acceso de
lectura-escritura por defecto a todos los topics. Una reserva DHCP en el router es la
solución de verdad si le cambia el número a la máquina.

**Crea el usuario y dale el topic.** Los usuarios viven en un fichero dentro del volumen
`ntfy-data`, así que sobreviven a `docker compose up --force-recreate`; perderlos deja al
móvil fuera, y ese es el fallo que este paso existe para evitar.
`docker compose exec ntfy ntfy user add --role=user <user>` pide la contraseña, así que nunca
llega al historial de mi shell, y luego
`docker compose exec ntfy ntfy access <user> <topic> read-write` no es opcional: un usuario
sin permiso sobre el topic existe y no puede hacer nada, lo que se lee exactamente igual que
un móvil roto. `ntfy user list` confirma las dos cosas. Las mismas credenciales van a `.env`
como `NTFY_USER` y `NTFY_PASSWORD`, porque el puente también tiene que publicar como alguien.

**Comprueba el lado del servidor antes de tocar el móvil,** porque es más rápido averiguarlo
aquí que a través de una pantalla de móvil.
`curl -s -o /dev/null -w '%{http_code}\n' "http://<LAN-IP>:8085/<topic>/json?poll=1"` tiene
que responder 403 sin autenticación, la misma lectura con `-u "<user>:<password>"` tiene que
funcionar, y `docker compose logs ntfy-bridge | tail` tiene que mostrar al puente publicando
como el usuario. Un 200 en la primera significa que el topic está abierto a cualquiera en la
red y que el móvil no es el problema; que las entregas fallen en la última significa que el
puente no está autenticándose y que las alertas no llegan siquiera al topic.

**El iPhone.** Instala la app de ntfy y luego añade este servidor y solo este, con la URL
**exacta** de `NTFY_BASE_URL`, incluidos el esquema y el puerto, porque ntfy deriva de ese
valor los enlaces internos de la app y un desajuste produce notificaciones que abren una
página de error: `http://<LAN-IP>:8085`, no `https`, sin barra final. Pon las credenciales,
confirma que la app se declara conectada, y en `http` permite la conexión cuando te la pida, o
nada funcionará después. Suscríbete a `<topic>` con el nombre exacto, porque la suscripción es
lo que hace sonar al móvil de verdad: un servidor correcto sin suscripción está callado.
Permite las notificaciones y activa Alertas Críticas o Sensibles al Tiempo para que una
`priority 5` pueda atravesar el modo Concentración. Las palabras cambian entre versiones de la
app, pero el flujo es siempre servidor, credenciales, suscripción, permiso.

**El push de iOS, y qué significa activarlo.** Esta es la parte que decide si una notificación
llega con la app cerrada. La app mantiene un socket directo con mi servidor solo mientras está
abierta, e iOS no le deja tener uno en segundo plano, así que la notificación viene de
`ntfy.sh`, el servidor conectado a la red de push de Apple, y mi servidor le reenvía una
petición de sondeo: `NTFY_UPSTREAM_BASE_URL=https://ntfy.sh`. Sin eso, el push en un iPhone
solo funciona mientras la app está en primer plano, y una alerta real, por definición, no lo
está. Lo que sale de mi red es más fino de lo que parece: `server.go` reenvía a
`<upstream>/<hash del topic>` llevando el id del mensaje y ningún contenido, y luego la app
vuelve a `NTFY_BASE_URL` a por el mensaje real, así que ntfy.sh y Apple se enteran de que un
servidor sin identificar publicó en un topic imposible de adivinar y nada más. El coste es el
límite de peticiones de la instancia pública, que `NTFY_UPSTREAM_ACCESS_TOKEN` con mi propia
cuenta eleva. Android y la app web ignoran todo esto y hablan directamente con mi servidor.
Para ver un reenvío real, pon `NTFY_LOG_LEVEL=debug`, ejecuta
`docker compose up -d --force-recreate ntfy`, para `demo-app` y luego
`docker compose logs ntfy | grep "poll request"`, que imprime
`Publishing poll request to https://ntfy.sh/<hash>`: la línea es `DEBUG`, así que con el
`info` por defecto no hay nada que buscar y su ausencia no significa nada, y la URL termina en
un hash en vez de en `noc-alerts`, que es la prueba de que el nombre del topic no es lo que
salió de la red.

**La prueba que cuenta.** Para el servicio sintético y deja el móvil, pantalla apagada, fuera
de la habitación: `docker compose stop demo-app`, luego `docker compose start demo-app`.
Espero una notificación `priority 5` nombrando el servicio en el minuto siguiente a que se
dispare la regla, y luego una resolución `priority 2` en cuanto el servicio vuelve y
Alertmanager mira el grupo otra vez, que es un `group_interval` después. La diferencia de
prioridad es el mapeo de gravedad del puente, y es una buena comprobación de que estoy mirando
mi propia alerta y no otra notificación que llegó por casualidad. Si no llega: funciona en
primer plano pero no cerrada significa que `NTFY_UPSTREAM_BASE_URL` está sin poner o que la
URL base no coincide; nada en absoluto con la app declarándose conectada significa que la
suscripción o el nombre del topic están mal carácter a carácter; un 401 o un 403 significa que
las credenciales están mal o que el usuario no tiene permiso sobre el topic; una notificación
sin enlace, o un enlace que falla, significa que `NTFY_BASE_URL` es `localhost` o no coincide
con el servidor de la app.

**Volverlo a dejar como estaba,** que importa más de lo que suena: `NOC_BIND_ADDRESS=127.0.0.1`
y `docker compose up -d`. El usuario y su permiso se quedan en el volumen, así que esto solo
cierra la puerta, no pierde la configuración. Dejar un laboratorio así en una red abierta a
propósito no es algo que quiera olvidar haber hecho una vez.

## Problemas habituales de instalación

- **Puerto ya asignado, o `noc-prometheus` en `unhealthy`:** cierra el otro servicio en vez de tocar `"${NOC_HTTP_PORT:-3000}:3000"`, porque el puerto del equipo y el del contenedor son distintos; y mira `docker compose logs prometheus`, porque un Prometheus unhealthy casi siempre es un `GF_SECURITY_ADMIN_PASSWORD` o un `BRIDGE_TOKEN` sin definir, o un YAML roto.
- **node-exporter con métricas vacías en Windows:** esperado, no es un fallo, porque Docker Desktop mide la máquina virtual en vez del equipo, y el stack está configurado para que no produzca alertas.
- **El menú de paneles de Grafana está vacío, o todos los paneles están vacíos:** lo primero es un montaje de volumen que esconde los ficheros de aprovisionamiento propios de la imagen, así que monto solo los subdirectorios `datasources` y `dashboards` en vez de `./grafana/provisioning` entero, confirmado con `docker compose logs grafana | grep -i -E "provision|dashboard|datasource"`. Lo segundo es distinto: el datasource no puede alcanzar Prometheus desde la red de Docker, así que la dirección es el nombre del servicio `http://prometheus:9090` y no `127.0.0.1`.
- **Datasource de Alertmanager en rojo en Grafana:** un fallo conocido de Grafana `12.4.11`, no del laboratorio. El health check devuelve 500 contra un datasource recién creado mientras Alertmanager responde bien, cosa que confirma un 200 de `http://127.0.0.1:9093/api/v2/status`. Un carácter corrupto donde debería ir una tilde es en cambio la codificación de la consola y no del log: los ficheros son UTF-8 y la ventana desde la que los leo no, así que `docker compose logs --no-color <service> > log.txt` y después `Get-Content log.txt -Encoding UTF8`.

## Desinstalar

`docker compose -f docker-compose.yml -f docker-compose.desktop.yml down -v`. El `-v`
**borra los volúmenes**: TSDB, silencios de Alertmanager, usuarios de Grafana y mensajes de
ntfy. Sin él `down` conserva los datos y el siguiente `up` los recupera, que es lo que uso
cuando quiero mantener las métricas históricas.
