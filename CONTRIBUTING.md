# Contribuir

Este repositorio es un laboratorio personal, así que hay pocas reglas. Las escribo porque la
mayoría son decisiones que se toman sin pensar y son caras de deshacer después.

## Qué espero de un cambio

Que pase lo que ya se comprueba, y que añada su propia comprobación si introduce algo que
pueda romperse.

```sh
make check
make test
```

Las dos tienen que pasar antes de que abra el cambio. Si algo falla y el fallo tiene pinta de
ser culpa del validador, eso es un hallazgo real: cada comprobación de este repositorio existe
porque este repositorio tuvo el problema que detecta.

Si el cambio toca el camino de las alertas, ejecuto también `make smoke` (o
`make smoke-desktop` en Windows y macOS). Es la única comprobación que necesita el stack
levantado, y el apartado siguiente explica por qué.

<a id="por-que-la-validacion-esta-partida-en-tres"></a>
## Por qué la validación está partida en tres

No es que el pipeline valide poco: es que cada mitad se puede comprobar con una certeza
distinta, y meterlas juntas daría una falsa confianza.

**La sintaxis se comprueba en cada push.** Un paréntesis sin cerrar o una función que no
existe salen en rojo sin levantar nada, y por eso `make check` no necesita el stack: recorre los
50 paneles, valida con `promtool` las 53 expresiones de PromQL, cruza cada alerta contra su
ancla del manual de incidentes y su panel, y revisa que cada `${VAR}` que interpola el compose
esté documentada. También mira que el texto que se lee en pantalla esté en español.

**La existencia de la métrica necesita un Prometheus con historia.** En PromQL un nombre de
métrica es una cadena, así que `rate(node_network_recieve_bytes[5m])` es perfectamente válido:
el error de teclear una métrica no existe hasta que se consulta la serie. Por eso
`make check-datos`, que corre `check.py --strict --prometheus`, es la única comprobación que
avisa de un panel vacío. Y está fuera del pipeline a propósito: un Prometheus recién arrancado
no tiene historia, tres paneles usan ventanas de `[6h]` y `[30d]`, y therein siempre saldrían
vacíos. El pipeline se pondría rojo por el motivo equivocado, y un rojo que miente entrena a
ignorar los rojos.

**La entrega real necesita el stack levantado y un canal con credenciales.** Eso es
`make smoke`: tira `demo-app`, espera a que `ServicioCaido` y `PuertoTCPInaccesible` lleguen a
ntfy con prioridad 5, lo restaura y espera a la resolución con prioridad 2. Una sola entrega
fallida también hace fallar el test. La última espera se lee de `group_interval` del
Alertmanager en vez de estar fijada a fuego, porque el aviso de "ya no te molesta" espera a que
Alertmanager mire el grupo otra vez; por eso el smoke no es determinista a los cinco minutos, sino
de unos seis y hasta once si una alerta tarda en dispararse. Esas dos esperas son un techo de
240 s y 420 s, no un mínimo.

Las tres se ejecutan a mano antes de dar por bueno un cambio, y las tres están en el README para
que se vea que existen en lugar de descubrirlas cuando algo falla.

## Estilo

- **Español en todas partes: código, comentarios y documentación.** Lo escribo en primera
  persona cuando el texto trata de lo que hago, porque un manual que dice "comprueba el disco"
  es una instrucción y uno que dice "compruebo el disco" es un hábito que puedo seguir a las 3
  de la madrugada.
- **La prosa va en UTF-8.** Al pasar el proyecto al español, la restricción anterior de ASCII
  dejó de tener sentido: hace falta la tilde para escribir bien, y las consolas modernas son
  UTF-8. Lo que sí se conserva es la lógica de fondo: un carácter mal renderizado se lleva por
  delante la comprensión de quien lo lee.
- **Los recursos que consume una aplicación pueden usar UTF-8.** Los títulos de panel de
  Grafana usan `·` y `é` a propósito. La regla de codificación es para lo que lee una persona
  en una consola, no para lo que lee Grafana.
- **Una leyenda de Grafana es texto, no un identificador.** `legendFormat` se pinta junto a la
  línea de la serie, así que `rules` o `uptime` son inglés en pantalla y se traducen. Lo que no
  se traduce es lo que no es prosa: los nombres propios y los protocolos (`tsdb`, `prometheus`,
  `http`, `tcp`) y la plantilla `{{etiqueta}}`, que la rellena Grafana con el nombre de la
  etiqueta. Si traduces una leyenda y el panel tiene un `byName` que la apuntaba, cambia las
  dos: el validador lo comprueba, porque un `byName` desalineado quita la unidad sin avisar.
- **Los comentarios explican por qué, no qué.** El código ya dice qué hace. Un comentario que
  repite la línea siguiente no ayuda a nadie y se queda viejo.
- **Un comentario por bloque, y solo cuando se gana su sitio.**
- **`ruff format` decide el formato.** No se discute en la revisión.

## Qué necesita un cambio de verdad

Un cambio que toca uno de estos no es una edición, es una decisión, y razono sobre ella por
escrito antes de escribir el código:

- Las **22 reglas de alerta**. Añadir una alerta no es escribir una expresión: es decidir a
  quién despierta, cuánto tarda en dispararse, si se repite, si la inhibe otra y qué hacer al
  recibirla. La nueva sección del manual de incidentes es la parte obligatoria y la más
  importante, porque es lo que alguien lee a las 3 de la madrugada.
- Los **nueve servicios de compose** y su seguridad. Un puerto que pasa de `127.0.0.1` a
  `0.0.0.0` cambia el modelo de amenaza entero.
- La **autenticación del puente o de Grafana**.
- Los **validadores**. Tienen que seguir produciendo un resultado útil. Un validador que se
  queja demasiado acaba ignorado, lo que es peor que no tenerlo.

## Añadir una alerta

El orden importa, porque el ancla del manual de incidentes pasa a formar parte del contrato de
la regla.

1. Añade la regla al grupo correcto en `rules/`, con sus cuatro anotaciones obligatorias:
   `summary`, `description`, `runbook_url` y `dashboard_url`.
2. Añade la sección a `docs/RUNBOOK.md`, con un ancla explícita que coincida con el
   `runbook_url` de la regla:
   ```markdown
   <a id="mi-alerta"></a>
   ## Mi alerta
   ```
   El ancla va en el idioma del título: los dos son español, así que coinciden de forma natural.
3. Añade el caso de prueba a `test/*.test.yml`.
4. Ejecuta `python scripts/check.py`. Cruza las reglas contra las anclas del manual de
   incidentes y contra los paneles, y falla si falta cualquiera de los tres sitios.

Añadir una regla sin su documentación es un error que el validador detecta, no una decisión de
estilo.

## Retirar una alerta

Retirar no es borrar el bloque de `rules/`. En este orden:

1. Quitar la regla de `rules/`.
2. Quitar su sección de `docs/RUNBOOK.md`.
3. Quitar su caso de prueba de `test/*.test.yml`.
4. Anotarla en [ALERTS-RETIRED.md](docs/ALERTS-RETIRED.md) con el motivo.

Las tres primeras las comprueba `scripts/check.py`. La cuarta no se puede automatizar: el
motivo por el que se retiró una alerta es el único conocimiento que no se deduce de los
ficheros.

## Cómo verifico una alerta nueva

Con el stack levantado, y no antes:

```sh
# 1. la regla se dispara cuando debe
curl -s http://127.0.0.1:9090/api/v1/alerts | python3 -m json.tool

# 2. la notificación llega con la gravedad correcta
#    para el servicio que vigila, o espera a que se dispare sola.
```

Una alerta que no he visto dispararse de verdad, con la notificación real, no está probada. Los
casos de `test/*.test.yml` comprueban que la regla es sintácticamente válida; no comprueban que
signifique lo que su autor cree.

## Reportar un problema

Cuando abro un reporte incluyo la salida de:

```sh
docker compose ps
docker compose logs --tail=50 <service>
```

y empiezo por `make status`, que resuelve la mayoría de los casos. Los pasos específicos de
alerta están en [el manual de incidentes](docs/RUNBOOK.md).

## Higiene de los reportes

No incluyo valores de `.env` en un reporte. Para demostrar que una variable está definida,
basta con su nombre y el hecho de que está puesta. Las claves de este repositorio son locales y
generadas al azar, pero el hábito de no pegar secretos en un reporte es el que merece la pena
conservar.
