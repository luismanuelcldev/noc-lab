# Para qué sirve este proyecto

Es un proyecto de práctica, y lo digo explícitamente porque cambia cómo debe leerse: existe
para mostrar cómo razono sobre monitorización, no solo que sé montar un stack. El objetivo
general es demostrar, con algo que funciona y no solo sobre el papel, el ciclo completo de
un centro de monitorización de TI: **detectar, alertar y notificar cuando un servicio cae.**
 Cualquier panel se descarga; lo que merece la pena enseñar es el razonamiento, por qué esta
métrica y no esa otra, y por qué una alerta que nadie recibe equivale a no tener alerta. Todo
lo de abajo es verificable: cada objetivo nombra el fichero que lo demuestra y el comando que
lo comprueba, así que nada de lo que hay aquí es una afirmación que haya que creer.

<a id="tres-angulos-sobre-el-mismo-servicio"></a>

## 1. Tres ángulos sobre el mismo servicio

Un centro de monitorización no mira una sola cosa. El mismo servicio se vigila desde tres
ángulos independientes, y cada uno caza fallos que los otros no pueden.

| Ángulo | Pregunta que responde | Lo vigila | Dónde |
|---|---|---|---|
| Recursos del equipo | ¿está viva la máquina y cuánto está cargada? | node-exporter | [CPU](../grafana/dashboards/noc-equipo-cpu.json) · [memoria](../grafana/dashboards/noc-equipo-memoria.json) · [disco](../grafana/dashboards/noc-equipo-disco.json) · [red y reloj](../grafana/dashboards/noc-equipo-red-reloj.json) |
| Recursos de contenedores | ¿qué está haciendo este contenedor en concreto? | cAdvisor | [resumen](../grafana/dashboards/noc-contenedores-resumen.json) · [detalle](../grafana/dashboards/noc-contenedores-detalle.json) · [E/S](../grafana/dashboards/noc-contenedores-io.json) |
| Disponibilidad del servicio | ¿responde de verdad el servicio? | blackbox-exporter | [sondas](../grafana/dashboards/noc-sondas.json) · [latencia](../grafana/dashboards/noc-sondas-latencia.json) |

`demo-app` es el servicio vigilado. No ejecuta lógica de negocio: un nginx que sirve dos
ficheros estáticos, cuyo único trabajo ser un servicio HTTP real que se pueda tirar a
propósito, para que la cadena se pruebe contra una caída de verdad y no simulada. Los tres
ángulos no son decoración: 22 alertas se reparten entre ellos a propósito, porque un fallo
visible solo desde un ángulo convierte ese ángulo en un punto ciego para el resto.

**Verifícalo:** `make status` · <http://localhost:3000> · <http://localhost:9090/targets>

<a id="el-pipeline-es-el-proyecto"></a>

## 2. El pipeline es el proyecto

No "tener un panel bonito": la cadena real, en orden. Cada etapa es un componente aparte con
una única responsabilidad y puede fallar por su cuenta, y esa es la razón de la estructura.
Una regla que se dispara cuando el camino de notificación está roto es peor que no tener
ninguna regla, porque enseña al de guardia a ignorarla.

| Etapa | Componente | De qué se ocupa |
|---|---|---|
| 1. Recoger | Prometheus `v3.15.0` | raspado 15s, evaluación 15s, 8 recording rules |
| 2. Evaluar | [rules/](../rules) | 22 reglas, en código, revisadas |
| 3. Alertar | Prometheus | `severity`, `for:`, `service`, `team` |
| 4. Enrutar | [alertmanager.yml](../alertmanager.yml) | 4 rutas, 5 receptores, 4 inhibiciones, silencios |
| 5. Notificar | [ntfy-bridge](../ntfy-bridge) + ntfy | 737 líneas de Python de biblioteca estándar, y luego la entrega |

Las reglas viven en `rules/` y no en la UI de Grafana, y eso es deliberado, no un límite
técnico. La UI es la opción obvia porque está ahí al lado, pero entonces nadie revisa la
regla en un pull request, no existe diff cuando cambia, y dos personas definen la misma
condición con dos nombres y las dos avisan. En código la regla tiene versión, pasa el linter,
se comprueba con `promtool` y la cubren los 14 casos de `test/*.test.yml`.

**Verifícalo:** `make smoke-desktop`. Confirma que los nueve contenedores están sanos, tira
`demo-app`, espera a que `ServicioCaido` y `PuertoTCPInaccesible` lleguen al canal con
prioridad 5, lo levanta y espera a la resolución con prioridad 2. Una sola entrega fallida
también hace fallar el test, así que "la alerta se disparó" nunca se confunde con "la alerta
llegó". Tarda unos seis minutos —hasta once si una alerta tarda en dispararse, porque 240 s y
420 s son un techo, no un mínimo— y es inherente: una alerta necesita un minuto para dispararse
y la resolución espera al siguiente `group_interval`, que el script lee de `alertmanager.yml`
en vez de fijarlo a fuego para que no se quede viejo.

<a id="que-vive-en-scripts"></a>

## Dónde vive el código, y por qué hay tantos ficheros

`scripts/` tiene 25 ficheros. La pregunta razonable es por qué no está en cuatro o cinco ficheros
grandes. La respuesta es una regla: **ningún fichero del proyecto puede pasar de 100 líneas**, y la
hace cumplir `noccheck/estilo.py`, no una revisión a ojo. Con 1.522 líneas de lógica y un techo de
100, el mínimo son 16 ficheros. Los que hay no son una decisión arbitraria, son lo que sale de
aplicar ese tope.

Son dos paquetes con entradas distintas:

| Fichero | Qué hace |
|---|---|
| `check.py` | punto de entrada de la validación. 16 líneas porque solo traduce argumentos y llama a `noccheck` |
| `smoke.py` | punto de entrada de la prueba de humo. Igual, 16 líneas |
| `noccheck/` | los validadores: uno por sección de `--solo`, más los que comparten biblioteca |
| `smoke/` | la prueba de extremo a extremo, en seis piezas |

Dentro de `noccheck/`:

| Módulo | Entrada pública | Qué comprueba |
|---|---|---|
| `cli.py` | `main` | reparte las secciones y resume el informe en un código de salida |
| `base.py` | `error`, `aviso` | estado compartido, rutas y ayudas que usan todos los demás |
| `paneles.py` | `check_static` | estructura de los paneles: targets, datasources, uids |
| `alertas.py` | `check_alertas` | que cada alerta lleve `summary`, `description`, `runbook_url` y `dashboard_url` |
| `enlaces.py` | `check_enlaces` | que cada enlace relativo entre documentos resuelva a fichero y ancla |
| `entorno.py` | `check_entorno` | que cada `${VAR}` del compose esté documentada en `.env.example` |
| `config.py` | `check_config` | la sintaxis del compose, delegada a `docker compose config` |
| `estilo.py` | `check_lineas` | el presupuesto de 100 líneas |
| `idioma.py` | `check_todo` | el texto visible de Prometheus y Alertmanager, en español |
| `palabras.py` | `check_ingles` | el vocabulario inglés que no puede aparecer en pantalla |
| `leyendas.py` | `check_leyendas` | las leyendas de serie, que también se leen |
| `columnas.py` | `check_byName` | que un `byName` encuentre la columna a la que aplica la unidad |
| `grafana.py` | `check_provisioning` | datasources, carpetas y destinos de los enlaces de panel |
| `promql.py` | `check_promql` | la sintaxis PromQL de las expresiones, delegada a `promtool` |
| `datos.py` | `check_expresiones` | lo que necesita el stack en marcha: expresiones, recordings, vacíos |

Y dentro de `smoke/`: `cli.py` reparte argumentos, `ciclo.py` (`full_cycle`) tira `demo-app` y
vigila el camino entero, `salud.py` comprueba los nueve contenedores y los contadores del puente,
`mensajes.py` lee ntfy y espera las alertas, `entorno.py` lee la configuración del laboratorio, y
`base.py` envuelve HTTP y subprocesos.

Los dos ficheros que parecen relleno y no lo son: `check.py` y `smoke.py` son los dos puntos de
entrada que ejecutan la CI y los `make`, y los dos `__init__.py` son lo que hace de `noccheck` y
`smoke` paquetes de Python. Ninguno se puede borrar.

**Verifícalo:** `python scripts/check.py --help` lista las nueve secciones que acepta `--solo`, y
las tres banderas disponibles.

<a id="encendido-no-es-lo-mismo-que-funcionando"></a>

## 3. "Encendido" no es lo mismo que "funcionando"

node-exporter y cAdvisor responden a *"¿está viva la máquina y cuánto está cargada?"*.
blackbox-exporter responde a *"¿responde el servicio?"*. Preguntas distintas, y la respuesta
honesta a la segunda no se deduce de la primera. La prueba más clara es una alerta que nadie
espera: **`DiscoSoloLectura`**. El sistema de archivos pasa a solo lectura y todas las
métricas de recursos se quedan normales: CPU bien, memoria bien, equipo respondiendo, sondas
siguiendo con un 200. El servicio tiene un aspecto perfecto de salud y no funciona en
absoluto, porque no se está escribiendo nada. Una instalación que solo vigilara recursos no se
enteraría hasta que alguien intentara leer un log. El caso simétrico es
`SondaDevueltaRespuestaInvalida`: el puerto responde 200, las métricas del equipo son
perfectas y el servicio devuelve un portal cautivo o una página de mantenimiento en lugar de
contenido. Solo la detecta una sonda que lee el cuerpo.

| Fallo | Métricas de equipo/contenedor | Sonda sintética |
|---|---|---|
| Proceso muerto | `up = 0` | `up = 0` |
| Disco en solo lectura | **nada** | **nada** (sigue respondiendo) |
| Página de mantenimiento en vez del servicio | **nada** | detectado, se comprueba el cuerpo |
| Aplicación lenta, recursos ociosos | **nada** | detectado, por `probe_duration_seconds` |

La primera fila es la única que ambas ven, y por eso exactamente vigilar solo recursos da una
falsa sensación de cobertura. **Verifícalo:** `docker compose exec prometheus wget -qO- http://demo-app:80 | head -3`; el cuerpo contiene `noc-canary-ok` a propósito, así que `fail_if_body_not_matches_regexp` en `blackbox.yml` se dispara si una página de mantenimiento lo sustituye.

<a id="no-dispara-todo-al-instant"></a>

## 4. No se dispara todo al instante

Un sistema de alertas que avisa de cada parpadeo enseña a la gente a ignorarlo, y uno que
nadie lee no detecta nada. Un centro de monitorización se juzga por las alertas que llegan
cuando deben **y** por las que se quedaron calladas, y de las dos mitades solo se habla de
la primera. Por eso toda regla lleva un `for:`, y los valores forman una escalera que sigue a
la gravedad: ninguno para el interruptor de hombre muerto, 1m para que caiga un servicio o el
camino de notificación, 2m-5m para un componente concreto que se porta mal, 10m-30m para
tendencias y agotamiento.

La tabla completa, con las 22 alertas y el razonamiento de cada una, está en
[el manual de incidentes](RUNBOOK.md#no-dispara-todo-al-instant), junto con los otros tres
temporizadores (`evaluation_interval`, `group_wait`, `group_interval`) y por qué el tiempo
real de notificación es el `for:` más hasta un intervalo de evaluación más el `group_wait`. Lo
que hay que señalar es el compromiso, no los números: un `for:` más corto detecta antes y
notifica más, y a partir de cierto punto deja de ser un sistema de monitorización. Un falso
positivo no cuesta una métrica, cuesta atención, y la atención es lo único sobre lo que
funciona todo esto.

<a id="la-alerta-tiene-que-llegar-a-una-persona"></a>

## 5. La alerta tiene que llegar a una persona

La última eslabón, y la que separa un sistema de monitorización de un panel. Una alerta que
nadie ve a tiempo no vale nada, diga lo que diga la regla. Que `demo-app` caiga tiene que
producir una notificación en un móvil, no un panel rojo que nadie tiene abierto.

| Pieza | Función |
|---|---|
| `alertmanager.yml` | decide la ruta, agrupa alertas hermanas, espera `group_wait` antes de enviar |
| [ntfy-bridge](../ntfy-bridge) | mi código: agrupa el lote, elige una gravedad para el grupo, formatea, entrega, reintenta |
| ntfy | guarda el topic, las prioridades y las suscripciones |
| el móvil | la persona. La parte que no se puede automatizar ni falsificar. |

La gravedad del grupo decide la prioridad, y eso es lo que hace que el móvil se comporte de
otra forma: `low=2`, `default=3`, `high=4`, `urgent=5`, así una crítica interrumpe y una
degradación se queda callada hasta que la abro. ntfy está autoalojado a propósito: las
propias alertas nunca salen de la máquina, porque el puente publica a `NTFY_URL`, que apunta a
mi propio contenedor.

Eso no es lo mismo que no hablar nunca con ntfy.sh, y la diferencia merece precisión. Para
notificar a un iPhone con la app cerrada, el servidor reenvía una petición de sondeo a
`NTFY_UPSTREAM_BASE_URL`, porque ntfy.sh es el servidor conectado a la red de push de Apple y
el mío no. Lo que cruza ese límite es una petición a un topic con hash que lleva un id de
mensaje y ningún contenido; luego la app vuelve a mi servidor a por la alerta real. Así que
ntfy.sh y Apple se enteran de que un servidor sin identificar publicó en un topic
imposible de adivinar. No se enteran del topic, del host ni de la alerta. Eso es un relé de
push, no una fuga de datos, y es una cosa distinta de mandar las alertas a una instancia
pública, que es exactamente lo que pasaría si `NTFY_URL` apuntara a ntfy.sh. El topic tampoco
es público, y eso exige dos ajustes que por separado no sirven de nada: el login por sí solo
deja intacto el acceso anónimo, porque el valor por defecto es lectura-escritura en todos los
topics. Es `deny-all` lo que hace que un cliente sin sesión no reciba nada, así que la única
forma de leer o publicar en `noc-alerts` es ser el usuario que creé, que es a la vez el móvil
y el puente. Un nombre de topic difícil de adivinar no sustituye a eso.

**Verifícalo:** `make smoke-desktop` demuestra la cadena entera hasta el canal. Después, el
paso que necesita a una persona: instala la app de ntfy, añade el servidor, suscríbete al
topic y para `demo-app` con el móvil en la mano. El procedimiento, incluido qué hacer cuando
la prioridad sale mal, está en [instalación](INSTALL.md#la-alerta-en-el-movil).

<a id="lo-que-este-proyecto-no-demuestra"></a>

## Lo que este proyecto no demuestra

Prefiero escribir los límites abajo que dejarlos para que los encuentre quien lea esto después.

- **Es un solo equipo, no un sistema distribuido.** Las alertas de nivel de equipo describen una máquina. Un NOC real se federa entre sedes, y eso no es lo que hace esto.
- **No hay rotación de guardia, ni ticketing, ni bucle de acuse de recibo.** La notificación llega a un móvil; nada registra que una persona la leyera o actuara. Un NOC real cierra ese bucle, y es lo que construiría después.
- **No hay alta disponibilidad.** Cada servicio es un único contenedor. Si cae Grafana los paneles desaparecen; las alertas siguen funcionando, que es la parte que importa, pero la visualización no.
- **14 de las 22 alertas no tienen caso de regresión.** Las 22 están comprobadas por contrato y 8 están fijadas con series sintéticas, porque un cambio sutil en esas expresiones sería invisible en un despliegue real. Las otras 14 se verifican levantando el stack. La lista honesta está en [ALERTS-RETIRED.md](ALERTS-RETIRED.md).
- **En Windows, node-exporter mide la máquina virtual, no el equipo.** Es una limitación documentada de Docker Desktop, no un fallo, y por eso las alertas de nivel de equipo en esa plataforma no son las que hay que creerse.
