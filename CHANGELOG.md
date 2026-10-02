# Registro de cambios

Este proyecto sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) y el
[versionado semántico](https://semver.org/).

Las fechas van en formato AAAA-MM-DD.

## [Sin publicar]

### Añadido

- **`scripts/check.py` valida ahora la sintaxis PromQL de las 53 expresiones de panel**, con
  `promtool check rules` sobre un fichero de reglas sintético que el propio módulo genera, y
  con la versión de la imagen leída de `compose/prometheus.yml` en vez de escrita en el código.
  Caza un paréntesis sin cerrar, una función que no existe y un selector mal formado. No caza
  una métrica renombrada, y el módulo lo dice en su docstring en lugar de prometer lo que no
  da: en PromQL un nombre de métrica es una cadena, así que
  `rate(node_network_recieve_bytes[5m])` es válido y promtool lo acepta.
- **`make check-datos`, la mitad que sí caza la métrica renombrada.** Corre
  `check.py --strict --prometheus`, que ejecuta las 53 expresiones contra el Prometheus vivo. Se
  queda fuera del pipeline a propósito: un Prometheus recién arrancado no tiene historia y tres
  paneles usan ventanas de `[6h]` y `[30d]`, así que therein siempre saldrían vacíos y el
  pipeline se pondría rojo por el motivo equivocado.
- **La alerta ahora llega a un móvil, autenticada.** El estado anterior demostraba que la
  cadena terminaba en un puerto publicado en `127.0.0.1`, que un dispositivo no puede
  alcanzar, así que el último eslabón y el más importante quedaba sin probar. `NTFY_BASE_URL`,
  `NTFY_ENABLE_LOGIN` y `NTFY_AUTH_DEFAULT_ACCESS` ahora son configurables, ntfy guarda sus
  usuarios en el volumen de datos mediante `NTFY_AUTH_FILE` para que un `recreate` no deje al
  móvil fuera, y la sección 6 de la guía de instalación documenta todo el procedimiento,
  incluido lo que cuesta la exposición.
- **`NTFY_AUTH_DEFAULT_ACCESS`, con `read-write` por defecto.** Habilitar el login solo es
  teatro: el rol anónimo conserva su acceso de lectura-escritura por defecto a todos los
  topics, así que el topic sigue público y la contraseña no protege nada. `deny-all` es el
  ajuste que de verdad lo cierra, y es el que importa en el momento en que el puerto es
  alcanzable desde la red.
- **`NTFY_UPSTREAM_BASE_URL`, vacío por defecto.** iOS no deja que la app mantenga una
  conexión en segundo plano, así que una notificación que tiene que despertar la app no puede
  venir de un servidor autoalojado. Reenviar una petición de sondeo a ntfy.sh, el servidor
  conectado a la red de push de Apple, es lo que hace que el push funcione con la app cerrada.
  La petición va a un topic con hash con un id de mensaje y ningún contenido, así que el texto
  de la alerta y el nombre del topic nunca salen de la máquina. Vacío por defecto para que un
  laboratorio sin ruta a internet no lo necesite.
- **`scripts/check.py` ganó tres comprobaciones que antes vivían en los validadores
  borrados**, y están cubiertas por pruebas negativas:
  - cada alerta debe llevar `summary`, `description`, `runbook_url` y `dashboard_url`;
  - el ancla de `runbook_url` debe existir en `docs/RUNBOOK.md`;
  - el `dashboard_url` debe apuntar a un panel que existe;
  - cada enlace relativo entre documentos debe resolverse a un fichero y a un ancla.

### Cambiado

- **`make check` y la CI pasan `--strict`.** El flag estaba implementado y documentado, y
  nadie lo activaba, así que un aviso no detenía nada. `ci.yml` y el target `check` lo llevan
  ahora.
- **Un panel vacío que está en la lista de vacíos esperados ya no es un aviso.** Avisar de que
  un panel se comporta como se espera es avisar de que todo va bien, y con `--strict` eso era un
  fallo permanente: el flag no se podía usar contra el Prometheus vivo, que es donde hace
  falta. Ahora el vacío esperado se imprime como tal y solo avisa el vacío que no está
  autorizado, que es justo la métrica renombrada que `--strict` y la CI deben cazar. Los dos
  paneles afectados son los que solo están vacíos en el estado sano: «Sistemas de archivos en
  solo lectura» y «Reinicios del equipo».
- **Las leyendas de serie de los cuadros de mando también pasan al español.** `legendFormat`
  estaba fuera de la regla de idioma por asumirse un identificador, y durante un tiempo lo
  fue: `rules`, `uptime` y `self` eran nombres razonables para un identificador y al mismo
  tiempo inglés en la leyenda que se pinta junto a la línea. Ahora hay dos comprobaciones
  nuevas: una de idioma que distingue una leyenda de prosa de un identificador, y otra que
  avisa cuando un `byName` de un `override` ya no encuentra su columna, que es el modo en que
  se cuela una unidad perdida sin un solo error. Se quedan en inglés los nombres propios y los
  protocolos (`tsdb`, `prometheus`, `http`, `tcp`) y las cabeceras que pone Grafana a partir del
  nombre de la métrica (`Duration of scrape`), porque esos no los decide este repositorio y
  traducirlos rompería el `byName` que les aplica la unidad.
- **El repositorio entero pasa al español**: documentación, comentarios de código, salida de
  scripts, entrypoints y texto de commits. Revierte la decisión anterior de escribir todo en
  inglés. La documentación se escribe en primera persona cuando describe lo que hago, porque un
  manual que dice "comprueba el disco" es una instrucción y uno que dice "compruebo el disco"
  es un hábito que puedo seguir a las 3 de la madrugada.
- **`scripts/` estaba en inglés y la regla de idioma no lo miraba.** Los validadores solo
  revisan los dashboards, las reglas, los compose y `.env.example`, así que sus propios
  comentarios y docstrings nunca entraron en el escaneo y llevan desde que se creó ese
  directorio. Ahora también están en español, incluidos los mensajes de error y el texto de
  `--help`, que son lo que ve alguien cuando algo falla. Sigue en inglés lo que no es prosa:
  el diccionario `INGLES` de `palabras.py`, los nombres propios, `Duration of scrape` y los
  `for`/`by` de PromQL citados en los fixtures.
- **Los 22 nombres de alerta, y los nombres de métrica derivados, se quedan en español y no se
  tocan.** Son los identificadores de `rules/`, de los casos de prueba y de cada ancla de
  `runbook_url`. Renombrar uno es un cambio de ruptura para cualquier cosa que ya haya recibido
  una notificación.
- Las anclas del manual de incidentes siguen siendo el contrato: coinciden con el
  `runbook_url` de cada regla y con el caso de prueba, y por eso no se renombran sin querer.
- **La cifra del puente pasa a 715 líneas** repartidas en 10 módulos de producción,
  tras separar el formateo del cuerpo del mensaje. `docs/SECURITY.md` y el README reflejan la
  cifra real.
- **Se retira el parámetro `profile` del webhook.** El `query string` se ignora a propósito: el
  enrutado vivía en una URL que nada validaba. Ahora esa decisión es el nombre del receiver de
  Alertmanager y la URL es solo el endpoint.
- **El `Dockerfile` del puente se había quedado corto.** La lista de módulos copiados a la imagen
  no incluía `cuerpo.py`, `utiles.py` ni `validacion.py`, así que una imagen construida desde el
  árbol actual arrancaba sin ellos. La lista ahora cubre los diez módulos de producción; `utiles.py`
  se deja fuera a propósito, porque solo lo usan las pruebas.
- **El puente se reparte en dos módulos.** `validacion.py` recoge lo que se decide sin socket
  (token, cuerpo y cuerpo de error) y `webhook.py` se queda con la entrega. La superficie HTTP
  ya tenía 100 líneas y no cabía; partirlo por esa frontera, y no por la longitud, deja ambos
  módulos con holgura y mantiene los casos probables sin arrancar un servidor.

### Arreglado

- **Dos ficheros `.pyc` de módulos que ya no existen.** `ntfy-bridge/__pycache__/` conservaba
  `notify.cpython-313.pyc` y `test_bridge.cpython-313.pyc`, de un `notify.py` y un
  `test_bridge.py` que se borraron al dividir el puente en módulos. No llegaban a Git, porque
  `.gitignore` ya cubre `*.py[cod]`, así que solo molestaban a quien leía el árbol de trabajo:
  dos ficheros que un `import` podía encontrar y que no corresponden a nada. El bytecode válido
  se regenera solo, y `.gitignore` no ha necesitado cambios.
- **`check.py` fallaba en la CI desde el principio.** El módulo de configuración delegaba en
  `promtool` y `amtool` con `docker compose exec`, que exige los contenedores en marcha, y la
  CI no levanta el stack: su propio comentario dice que ninguno de sus pasos lo necesita. Con el
  stack parado devolvía tres errores, `service "prometheus" is not running`, y salía con código
  1. No se había visto porque el repositorio todavía no tenía ningún commit y la CI nunca había
  corrido. Ahora ese módulo solo ejecuta `docker compose config -q`, que no necesita contenedores,
  y los tres validadores externos se quedan donde ya estaban y mejor: en la CI, que los invoca
  con `docker run --entrypoint` y la misma imagen fijada que el compose.
- **`scripts/smoke.py` fallaba con `HTTP Error 403` en el momento en que el topic quedaba
  protegido.** Leía ntfy de forma anónima, lo que estaba bien mientras el puerto estaba en
  loopback y es incorrecto en cuanto se deniega el acceso anónimo: el script reportaba un
  laboratorio roto cuando lo único roto era que el lector nunca iniciaba sesión. Ahora lee con
  las mismas credenciales Basic que usan el móvil y el puente, tomadas de `.env`, y solo cae a
  una lectura anónima cuando no hay credenciales configuradas. Una prueba que no distingue
  entre "el canal de notificación está caído" y "no tengo permiso para mirar el canal de
  notificación" no es una prueba del canal.
- **El panel `Memoria frente al límite, por contenedor` no mostraba nada útil.** El panel tenía
  una sola consulta que devolvía cada etiqueta de contenedor como una columna, mientras que sus
  overrides y transformaciones esperaban `Working set (MiB)`, `Limit (MiB)` y `% of limit`, así
  que ninguna coincidía y la tabla se renderizaba como una lista ilegible de columnas
  `container_label_com_docker_compose_*`. Ahora tiene tres consultas, una por columna, unidas
  por el nombre del contenedor:
  - cada consulta agrega con `max by (name)`, que elimina el ruido de etiquetas;
  - la consulta del porcentaje conserva la guarda `> 0`, así que un contenedor sin límite de
    memoria muestra un porcentaje vacío en vez de `+Inf`;
  - cada consulta lleva un `legendFormat` fijo, así que los nombres de columna unidos son los
    que el panel espera y no lo que el datasource decida llamarlos;
  - las transformaciones son `labelsToFields` (columnas), `joinByField` (outer) y `organize`,
    que es lo que necesita Grafana 12, porque con `format: table` devuelve un frame por serie
    con las etiquetas pegadas al campo de valor en vez de como columnas.
  El panel ahora lista los 12 contenedores que reporta el equipo, 9 de ellos con límite, y los
  overrides de `Limit` y `%` y el orden por `% of limit` por fin se aplican. Los otros tres
  paneles de tipo `table` quedan igual a propósito: muestran sus etiquetas crudas, que son
  ruido y no un defecto.
- **El manual de incidentes documentaba umbrales que no eran los de las reglas.** La reescritura
  usa los valores reales, y las correcciones destacadas son: memoria del equipo al 90% usado (no
  85%), CPU del equipo al 85% (no 90%), desfase de reloj 50 ms (no 30 s), "equipo sin memoria"
  a 256 MiB disponibles (no 2%), memoria de contenedor al 90% del límite (no 85%), CPU de
  contenedor 0.80 **núcleos** en vez de un porcentaje, y `Watchdog` disparándose siempre en vez
  de tras un retardo. `CanalNotificacionCaido` queda además documentada por lo que de verdad
  mide: el propio gauge `ntfy_bridge_delivery_success` del puente por sink, no los contadores de
  Alertmanager.
- Dos comandos que recomendaba el manual no podían funcionar: `timedatectl` no existe dentro
  del contenedor de node-exporter, y `ps -o ... --sort` tampoco está soportado ahí. Los dos
  quedan sustituidos por comandos que verifiqué contra el stack en marcha.
- La carpeta de Grafana se aprovisiona como `Centro de monitorización`, pero Grafana no
  renombra una carpeta existente durante el aprovisionamiento, así que los paneles conservaban
  el nombre viejo. La carpeta se renombra en la base de datos y se confirmó que los
  `dashboard_url` de las alertas usan `/d/<uid>`, que no depende del nombre de la carpeta.
- `GF_SECURITY_ADMIN_PASSWORD` solo se aplica cuando Grafana crea su base de datos. En un
  volumen ya existente, el usuario guardado conserva la contraseña vieja y la de `.env` se
  ignora en silencio. La instalación documenta ahora el comando de restablecimiento.
- El título del panel de memoria se cita correctamente en el manual (`Memoria frente al límite,
  por contenedor`) y no con el nombre viejo en inglés.
- **Las 30 URLs de las alertas apuntaban a un repositorio que no existe.** Los `runbook_url` de
  las 22 reglas de `rules/` y los de sus casos en `test/*.test.yml` decían
  `github.com/luismanuelcldev/mi-noc`, y el repositorio real es `noc-lab`. Se corrigen los 30 en
  el mismo paso, porque promtool compara `exp_annotations` como conjunto completo: si solo se
  tocaran las reglas, los 14 casos de prueba fallarían. `check.py` no lo detectaba, porque
  `scripts/noccheck/enlaces.py` excluye las URLs externas por el prefijo `https://` y solo valida
  los enlaces relativos entre documentos.
- **El README afirmaba que el puente publica a ntfy, a un webhook genérico o a correo.** No lo
  hace: `"sinks": ["ntfy"]`, y no hay un segundo destino en ninguna línea del código. La misma
  promesa estaba ya corregida en `docs/SECURITY.md`; el README se había quedado atrás.
- **La cifra del puente estaba desfasada en tres documentos.** Decían 715 líneas repartidas en
  10 módulos de producción; son 737 líneas en once ficheros. Se corrigen el README,
  `docs/PROJECT.md` y `docs/SECURITY.md`.
- **`docs/ALERTMANAGER.md` no estaba en la tabla de documentación del README**, existía desde
  hacía meses y era el único documento sin enlazar desde la raíz.

### Añadido

- **`docs/README.md`**, el índice de los nueve documentos: qué resuelve cada uno y cuándo lo
  lees, más las cuatro cosas que no viven en ningún fichero y por qué no se pueden automatizar.
- **La instalación empieza por `git clone`.** Ningún documento decía cómo traer el repositorio:
  los ocho empezaban directamente en `cp .env.example .env`, como si el árbol ya estuviera en el
  disco. También explica que el repositorio se llama `noc-lab` y el producto `mi-noc`, que es
  la duda natural al ver el `git remote -v`.
- **Tabla de referencia de las 18 variables de `.env`** en `docs/INSTALL.md`, agrupadas por lo
  que hacen y marcando las cuatro sin valor por defecto, que son las que hacen que Compose aborte
  en vez de inventar un valor.
- **El README tiene índice, badges y fecha de actualización**, sin crecer: se quedó en las 160
  líneas que tenía, y lo que no cabía bajó a `CONTRIBUTING.md` en lugar de recortarse. Ahí está
  ahora `Por qué la validación está partida en tres`, el razonamiento que antes ocupaba media
  sección del README.

### Eliminado

- Cinco documentos y sus motivos, plegados en los que sobrevivieron: cinco scripts de validación
  fusionados en `scripts/check.py`, el catálogo de alertas fusionado en el manual de incidentes,
  y los registros de arquitectura y decisiones fusionados en el README y el documento de
  seguridad. Menos documentos, y ninguno que contradiga a otro.
- `requirements.txt`, `requirements-dev.txt` y los `pyproject.toml` por paquete. El puente ahora
  usa solo la biblioteca estándar de Python, así que no hay nada que instalar ni que parchear.

## [1.0.0] - 2026-01

Primera versión completa del laboratorio. No hay versiones anteriores: el proyecto se publicó
directamente en este estado.

### Añadido

**El stack de observabilidad**

- Prometheus `v3.15.0` con 8 objetivos de raspado y 15 días de retención.
- Alertmanager `v0.34.1` con agrupación por `alertname` e `instance`, intervalos de repetición
  diferenciados por gravedad y cuatro webhooks de entrega.
- Grafana `12.4.11` con trece cuadros de mando aprovisionados (estado, objetivos, puente, sondas, sondas
  de latencia, almacenamiento, los cuatro de recursos del equipo y los tres de contenedores).
  50 paneles en total.
- node-exporter `v1.12.1` y cAdvisor `v0.55.1` para métricas de máquina y por contenedor.
  v0.55.1 no es arbitrario: es la versión más antigua que lee contenedores con Docker 28 y
  posteriores. Con la anterior, cAdvisor los ve a través de la API pero no puede asociarles
  métricas, y todo el panel de contenedores se lee como "No data" sin que ningún health check
  se queje.
- blackbox-exporter `v0.28.0` con sondas HTTP y TCP para las comprobaciones de disponibilidad.
- ntfy `v2.28.0` como canal de notificación.

**El puente de notificaciones**

- `ntfy-bridge`: un servicio mío que traduce las alertas de Alertmanager en mensajes de ntfy.
  Entrega a varios destinos en paralelo, con reintentos y límites de tamaño. Autentica cada
  petición con `Authorization: Bearer` y compara en tiempo constante.
- Gravedad traducida a prioridad de ntfy como un entero JSON: `critical` a 5, `warning` a 3,
  `info` a 2.
- Sus propias métricas, tres de las cuales alimentan las alertas que vigilan la propia cadena de
  notificación.
- 31 pruebas que cubren el formateo, los reintentos, la validación de la cabecera de
  autorización, los límites y la configuración desde el entorno.

**Las alertas**

- 22 reglas de alerta en 5 grupos: `metaservicio` (5), `disponibilidad` (4), `disco_host` (4),
  `recursos_host` (6) y `contenedores` (3).
- 8 recording rules que precalculan lo que consultan los paneles.
- Casos de regresión de reglas con `promtool test rules`, comparando etiquetas y anotaciones
  completas.
- Las anotaciones obligatorias en cada regla, incluido un `runbook_url` que apunta a la sección
  correspondiente del manual de incidentes.

**La documentación y su verificación**

- Validadores estáticos que no necesitan un stack en marcha.
- `ruff` con las reglas de seguridad de bandit activadas, configurado una vez en la raíz para
  que el análisis cubra también los scripts de validación y no solo el puente.
- Un manual de incidentes con una entrada por alerta: síntoma, comprobación, causa y
  procedimiento.
- Documentación repartida entre instalación, arquitectura, operaciones, seguridad, diagnóstico,
  desarrollo y alertas retiradas.
- Integración continua que ejecuta los validadores, las comprobaciones de `promtool` y `amtool`
  y las pruebas, sin arrancar el stack.
- Escaneo de secretos con `gitleaks` sobre lo versionado. La comprobación anterior, que solo
  miraba si existía `.env`, no hacía nada: `.env` está en `.gitignore`, así que nunca aparece en
  un checkout de la CI.
- Una prueba de extremo a extremo (`smoke.py`, con `make smoke`) que tira `demo-app`, comprueba
  que las alertas llegan a ntfy y se resuelven cuando vuelve, y verifica que el puente no
  registró entregas fallidas. La espera de la resolución se lee del `group_interval` de
  Alertmanager en vez de ser un número fijo. No está en el pipeline: necesita el stack levantado
  y tarda unos seis minutos.

### Arreglado

Estos se arreglaron mientras se construía, antes de la primera publicación. Se anotan porque
explican por qué algunas comprobaciones parecen excesivas.

- Falsos positivos de `DiscoSoloLectura` en WSL y Docker Desktop, causados por los sistemas de
  archivos de la máquina virtual ligera. Arreglado excluyendo esos tipos y rutas de sistema de
  archivos en los dos ficheros de compose.
- La prioridad de ntfy se enviaba como cadena. ntfy espera un entero entre 1 y 5, así que la
  notificación llegaba con la prioridad por defecto en vez de la correcta.
- Los paneles no aparecían en Grafana por un montaje de volumen que escondía los ficheros de
  aprovisionamiento propios de la imagen. Ahora se montan solo las rutas necesarias.
- Una alerta estaba documentada en dos grupos a la vez.
- Una alerta no tenía sección en el manual, así que su `runbook_url` apuntaba a un ancla
  inexistente. Para `promtool` eso es texto válido y no lo detecta.

### Decidido

- Un puente propio en vez de una integración de fábrica, para que haya exactamente un punto por
  el que los datos salen de la red y sea lo bastante pequeño para leerlo de una sentada.
- Las alertas viven solo en Prometheus, nunca también en Grafana, para que se revisen en código
  y se validen con `promtool`.
- Un token por destino de notificación, sin almacén de secretos, inyectado por cada entrypoint
  al arrancar y validado con `amtool` para que un token mal puesto haga fallar el arranque en
  vez de tragarse las alertas en silencio.
- Todo el stack en una sola máquina, con las limitaciones que eso implica en Windows y macOS.

### Conocido

- El health check del datasource de Alertmanager en Grafana `12.4.11` devuelve HTTP 500 aunque
  Alertmanager responda bien a esa misma petición. Es un fallo de Grafana, no del laboratorio.
- En Windows y macOS, node-exporter mide la máquina virtual de Docker Desktop, no el sistema
  operativo del equipo. Es una limitación de dónde corre el contenedor.
- `make` no viene con Windows. Los objetivos son atajos de comandos de `docker compose` y se
  pueden copiar a mano.
