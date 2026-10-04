# Seguridad

Qué decisiones de seguridad toma este laboratorio y por qué. No es un sistema de producción:
es un laboratorio de observabilidad construido para parecerse a uno, de modo que se pueda
razonar sobre él. Aun así el modelo de amenazas es el de producción, porque los dos casos de
uso son el mismo: recibir una alerta de confianza ya autenticada y no filtrar información
interna hacia fuera.

## El principio: de dentro hacia fuera

Todo el movimiento de datos va en una sola dirección. Prometheus, Alertmanager, Grafana y los
exportadores aceptan peticiones. El único componente que envía datos a un tercero es
`ntfy-bridge`, y solo cuando dispara una alerta. Eso no es un accidente de implementación, es
la decisión de diseño principal: escribí el puente yo, en 737 líneas de biblioteca estándar de
Python repartidas en once ficheros, en vez de añadir una integración, para que haya exactamente un
punto por el que los datos salen de la red, que sea lo bastante pequeño para leerse de una
sentada y que no tenga ninguna dependencia que alguien tenga que parchear después.

<a id="puntos-en-loopback"></a>

## Puntos atados a la interfaz de loopback

Cada puerto publicado usa `127.0.0.1:PORT:PORT` y no `PORT:PORT`. La diferencia no es comodidad,
es aislamiento: con `0.0.0.0` cualquier otra máquina de la red llega a los cuadros de mando de
Grafana, a la API de Alertmanager y al topic de notificación; con `127.0.0.1` no llegan, sin
depender del cortafuegos del anfitrión. Los servicios que no publican puerto son `demo-app`,
`cadvisor`, `node-exporter`, `blackbox-exporter` y `ntfy-bridge`; Prometheus y Alertmanager los
encuentran por nombre de servicio, y el puente expone sus métricas en el puerto 5000 dentro de
su contenedor, al que solo llega `mesh`.

Aquí conviene ser preciso, porque es donde la gente tiende a pasarse. La red `mesh` **no** está
marcada `internal: true`, así que Docker sí la deja salir a Internet y cualquier contenedor
conectado a ella alcanza esos puntos. Lo que protegen de verdad el laboratorio es que no se
publica ningún puerto al anfitrión y que los cuatro que sí se publican están atados a
`127.0.0.1`. Marcar `mesh` como interna impediría al puente llegar a un topic externo de ntfy,
que es uno de los destinos que la configuración admite.

<a id="la-excepcion-y-lo-que-cuesta"></a>

### La única excepción, y lo que cuesta

Un móvil no alcanza `127.0.0.1`, así que un laboratorio cuyas alertas solo llegan a un portátil no
demuestra lo que dicen demostrar. La sección 6 de [INSTALL.md](INSTALL.md#la-alerta-en-el-movil)
es la excepción deliberada, y marca con precisión la frontera entre lo que aporta y lo que no.
`NOC_BIND_ADDRESS=0.0.0.0` mueve **los cuatro** puertos publicados, no solo el de ntfy. Eso es una
propiedad del fichero compose, no una función de las instrucciones del móvil, y es la razón por
la que no lo trato como un apunte inocuo: con él vienen Grafana y Prometheus, y ninguno de los
dos debería ser alcanzable desde la red. La descripción honesta del estado resultante es *una red
doméstica privada con un Prometheus sin autenticar, un Grafana sin autenticar y un ntfy
auténtico sobre HTTP sin cifrar*: aceptable para demostrar e inaceptable para operar.

Lo que evita que ntfy sea el peor de los tríos es el par de ajustes que solo funcionan juntos.
`NTFY_ENABLE_LOGIN=true` sin `NTFY_AUTH_DEFAULT_ACCESS=deny-all` es teatro: el rol anónimo
conserva su acceso de lectura y escritura por defecto a todos los topics, así que el login no
cambia nada y cualquiera en la red puede leer las alertas y publicar falsas en el topic. Con
`deny-all` el anónimo no saca nada y solo un usuario con permiso explícito sobre el topic puede
leerlo o publicar en él, y eso se comprueba sin móvil:
`curl -s -o /dev/null -w '%{http_code}\n' "http://<LAN-IP>:8085/<topic>/json?poll=1"` devuelve
403 sin autenticar y 200 con `-u <user>:<password>`.

Lo que esta excepción no hace. **No es TLS:** el tráfico es HTTP en claro, así que en una red no
confiable las credenciales y el texto de la alerta los lee cualquiera que esté en el camino. Una
red doméstica es un sitio defendible para eso; una red de oficina compartida no lo es, y es el
argumento más fuerte contra darla por configurada. **No es un cortafuegos:** nada aquí filtra
paquetes, y la protección es que se deniega el acceso anónimo, no que el punto esté oculto.
**No vale por qué el nombre del topic sea oscuro:** lo que protege el topic es `deny-all`, y el
nombre es como mucho defensa en profundidad. Para cualquier cosa que vaya más allá de un
laboratorio personal la respuesta es un proxy inverso con TLS y certificados de cliente, o un
proveedor de identidad real delante de ntfy, sin ningún punto publicado, y Tailscale o una
superposición equivalente si la red no es mía. El valor de loopback en `.env.example` vale por sí
mismo; la excepción vive en `.env`, que no se versiona, y no en los valores por defecto
versionados.

## Secretos

`ntfy-bridge` es el único componente con secretos de verdad, porque es el único que habla con un
servicio externo. Necesita los siguientes, con una separación deliberada:

| Secreto | Para qué se usa |
|---|---|
| `BRIDGE_TOKEN` | token que el puente exige en la cabecera `Authorization` |
| `NTFY_TOKEN` | credencial del topic de ntfy |
| `NTFY_USER` y `NTFY_PASSWORD` | autenticación básica contra el servidor de ntfy, si lo hay |
| `GF_SECURITY_ADMIN_PASSWORD` | contraseña del administrador de Grafana |

Eso es todo lo que hay hoy: el puente declara `"sinks": ["ntfy"]` y no admite más destinos. Las
variables `SMTP_*`, `WEBHOOK_URL` y `WEBHOOK_BEARER_TOKEN` aparecen en `docs/SECURITY.md` en
versiones anteriores y en algunos `.env` de trabajo, pero **ningún componente las lee**. Si aparece
una con valor, no está protegiendo nada: es ruido que conviene borrar. Cuando se añada un destino
de correo o un webhook genérico, se documentan aquí y en `.env.example` el mismo día.

`BRIDGE_TOKEN` y `NTFY_TOKEN` no son lo mismo y no hacen lo mismo: el primero protege la entrada
al puente y el segundo la salida hacia ntfy. Un único token para los dos dejaría que quien pueda
publicar en el topic también inserte alertas falsas, así que mantengo un token por destino y por
dirección.

Hay un caso que merece entenderse, porque es la clase de fallo que más tiempo cuesta: si se deja
`BRIDGE_TOKEN` vacío, el puente **no exige autenticación**. Eso es coherente con un Alertmanager
que no manda cabecera, y es el valor por defecto. En cuanto hay un token definido en el puente,
Alertmanager tiene que mandarlo también, y como Alertmanager no expande variables de entorno, el
token acaba escrito a mano en su configuración. Eso es exactamente el fallo que el entrypoint
evita: `docker/alertmanager-entrypoint.sh` recibe el token como variable de entorno, lo inyecta en
los webhooks que apuntan al puente sobre una copia en `tmpfs` con modo `600`, y valida el
resultado con `amtool` antes de arrancar. Un token mal formado o una configuración inválida paran
el contenedor, así que un token mal escrito es un arranque que falla y no un 401 que aparece a las
tres de la mañana. Los dos casos que quedan, un token vacío y un puente con la cabecera rota, están
en [CanalNotificacionCaido](RUNBOOK.md#canal-notificacion-caido). `.env.example` está versionado
y no contiene ningún valor real, solo nombres y explicaciones; `.env` está en `.gitignore` y
nunca debe subirse. Las claves locales se generan al azar en la instalación, así que no hay
claves que reutilizar entre entornos porque no hay ningún valor que reutilizar.

<a id="sin-secretos-en-el-log-de-arranque"></a>

## Sin secretos en el log de arranque

Los entrypoints de Prometheus y Alertmanager sustituyen los marcadores de plantilla por los
valores del entorno al arrancar, y después escriben el fichero en disco con los valores ya
resueltos, dentro de un volumen de Docker. El motivo es que Prometheus y Alertmanager no expanden
variables de entorno en su configuración. Las dos opciones son un gestor de secretos externo o
esta sustitución en el arranque; para un laboratorio en una sola máquina la segunda basta, y evita
una dependencia que tendría que respaldar y parchear yo. El fichero generado solo lo lee el
propietario del volumen y vive en el volumen, no en la imagen, y el entrypoint de Alertmanager da
un paso más: escribe en `tmpfs` con modo `600` en vez de dejar el fichero resuelto en disco.
Conviene ser exacto sobre por qué `.gitignore` ignora `/data/`: este compose usa volúmenes
**con nombre** (`noc-prometheus-data` y compañía), que gestiona Docker aparte y que nunca
aparecen en el árbol de trabajo. La regla está ahí como red de seguridad para el caso de que
alguien cambie a un montaje de directorio, que metería el historial completo de métricas y la
contraseña de administrador dentro del repositorio. Cuesta una línea y evita un accidente que
ningún `git rm` deshace.

## La superficie de ataque, en detalle

De los nueve servicios, solo cuatro publican un puerto. Los otros cinco viven en la red `mesh` sin
publicar nada al anfitrión, y su único cliente legítimo es otro contenedor del stack. Que
`node-exporter` y `cadvisor` no se publiquen no es exageración: existen para obtener información
detallada del sistema y de sus contenedores, y no hay ninguna razón para alcanzarlos desde fuera.
Prometheus se comunica con ellos por nombre de servicio dentro de `mesh`, y el puente es el único
servicio que implementa autenticación, con comparación en tiempo constante, porque una comparación
de cadenas que no tiene en cuenta una diferencia filtra qué prefijo del token es correcto por
largo que sea el token.

| Servicio | Puerto publicado | Alcanzable desde | Autenticación |
|---|---|---|---|
| `prometheus` | 127.0.0.1:9090 | el operador, por loopback | ninguna |
| `alertmanager` | 127.0.0.1:9093 | el operador, por loopback | ninguna |
| `grafana` | 127.0.0.1:3000 | el operador, por loopback | usuario administrador y contraseña |
| `ntfy` | 127.0.0.1:8085, o la dirección de la LAN cuando se usa la sección 6 de [INSTALL.md](INSTALL.md#la-alerta-en-el-movil) | el operador, el puente y el móvil | usuario y contraseña básicos, con `auth-default-access=deny-all`; un token bearer si se configura uno |
| `node-exporter` | ninguno | contenedores en `mesh` | ninguna |
| `cadvisor` | ninguno | contenedores en `mesh` | ninguna |
| `blackbox-exporter` | ninguno | contenedores en `mesh` | ninguna |
| `ntfy-bridge` | ninguno | contenedores en `mesh` | `Authorization: Bearer` con `BRIDGE_TOKEN` |
| `demo-app` | ninguno | contenedores en `mesh` | ninguna |

<a id="cadvisor-privileged"></a>

## cAdvisor, que necesita `privileged`

Es el único componente del stack que corre con `privileged: true` y con el host montado, y no hay
forma de evitarlo: cAdvisor lee las métricas de cgroup del kernel, que no se publican por ninguna
API. Lo asumo como riesgo y escribo lo que lo hace aceptable:

| Medida | Por qué |
|---|---|
| Los cinco montajes en solo lectura | Necesita leer `/`, `/var/run`, `/sys`, `/var/lib/docker` y `/dev/disk`, pero no escribir en ninguno |
| Sin puerto publicado | Su único cliente legítimo es Prometheus, por nombre de servicio dentro de `mesh` |
| Solo en `mesh`, nunca en `edge` | No alcanza la red que toca el host |
| Límite de CPU y memoria | Acota el daño si el exportador se descontrola |

Y lo que la política común **no** le aporta: `no-new-privileges` viene de `_base.yml`, pero
`privileged: true` concede todas las capacidades, así que en este servicio concreto esa medida no
protege nada. Lo dejo escrito para que nadie la cuente como una mitigación de cAdvisor.

## Grafana

La contraseña de administrador viene de `GF_SECURITY_ADMIN_PASSWORD` en `.env`, no del valor por
defecto de la imagen: sin ella Grafana arranca como `admin/admin` y quien llegue al puerto 3000
tiene el control. Solo se aplica cuando Grafana crea su base de datos, así que si el volumen ya
existe el usuario guardado conserva su contraseña anterior, y documento el reinicio en [la
instalación](INSTALL.md#abrirlo). Los cuadros de mando se montan en solo lectura, porque un stack
de observabilidad no necesita paneles editables y permitirlo abre la puerta a que un cambio hecho
a mano se pierda al reiniciar sin ningún aviso. El registro de auditoría de Grafana está
activado.

## Lo que este repositorio no hace

- No instala un cortafuegos. El aislamiento es por puerto y por red, no por filtrado de paquetes,
  y en una máquina de laboratorio atar puertos a `127.0.0.1` da el mismo resultado con menos
  piezas que mantener.
- No cifra nada en reposo. Los volúmenes guardan lo que guardan, en claro: aceptable en un
  laboratorio y en ningún otro sitio.
- No automatiza las copias de seguridad. Ver [operaciones](OPERATIONS.md#copias-de-seguridad).
- No aplica capacidades reducidas a todos los contenedores. El ancla `x-hardening` aplica
  `no-new-privileges`, política de reinicio y rotación de logs a los nueve, y el puente añade
  `read_only: true` y `cap_drop: ALL`. Los exportadores conservan las capacidades por defecto
  porque necesitan leer del anfitrión, y reducirlas a mano tiende a romperlos de maneras
  difíciles de notar: la superficie de ataque se acepta conscientemente en los cinco servicios que
  no publican puerto.
- No fija límites de memoria y CPU a nivel de contenedor, sino `deploy.resources.limits`, que es
  lo que Docker Compose interpreta en un despliegue normal. Si el motor es Kubernetes, las claves
  son las mismas.

## Lo que la auditoría comprueba de verdad

Pongo esto porque una lista de controles que no se ejecutan es peor que no tener lista. La CI
ejecuta **gitleaks** sobre el repositorio para detectar secretos subidos; no se ejecuta en mi
máquina, solo en la cadena. `.gitignore` cubre `.env`, `data/`, copias de seguridad, claves
privadas, artefactos de compilación de Python y restos de editores. **ruff** se ejecuta con las
reglas bandit `S` seleccionadas, que detectan contraseñas escritas a mano y superficie de ataque
innecesaria en el código. `scripts/check.py` valida que cada fuente de datos de los cuadros de
mando existe, que Prometheus acepta cada expresión, que cada alerta lleva sus cuatro anotaciones y
apunta a un ancla del runbook que existe, que todos los enlaces relativos entre documentos
resuelven y que cada `${VAR}` que el compose interpola está documentada en `.env.example`.
`amtool check-config` y `promtool check config` validan el enrutado y la configuración de raspado
con las herramientas que son dueñas de esos formatos.
