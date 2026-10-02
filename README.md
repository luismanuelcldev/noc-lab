# mi-noc

Un centro de monitorización de TI que funciona, construido para demostrar que entiendo el
ciclo completo de un NOC: **detectar, alertar, notificar** cuando un servicio cae.

La gracia no es "ver unas gráficas". Cuando un servicio crítico cae a las 3 de la madrugada,
alguien tiene que enterarse por un canal que de verdad mira, con un enlace que le diga qué
hacer, y eso solo cuenta si la cadena se prueba de extremo a extremo en vez de solo
configurarse. Este repositorio es esa cadena: métricas, reglas, enrutado, entrega y paneles.

[![CI](https://github.com/luismanuelcldev/noc-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/luismanuelcldev/noc-lab/actions/workflows/ci.yml)
[![Apache-2.0](https://img.shields.io/badge/licencia-Apache--2.0-blue)](LICENSE) [![Prometheus](https://img.shields.io/badge/prometheus-v3.15.0-orange)](compose/prometheus.yml) [![Grafana](https://img.shields.io/badge/grafana-12.4.11-orange)](compose/grafana.yml) [![Python](https://img.shields.io/badge/python-3.13-blue)](CONTRIBUTING.md) [![Docker](https://img.shields.io/badge/compose-v2-2496ED)](docs/INSTALL.md)

**Actualizado**: 2 de octubre de 2026. Los nueve contenedores levantados y `check.py --strict` con 0 avisos.

## Índice

- [Qué demuestra](#qué-demuestra)
- [Qué hay dentro](#qué-hay-dentro)
- [Inicio rápido](#inicio-rápido)
- [Las cuatro alertas que de verdad miro](#las-cuatro-alertas-que-de-verdad-miro)
- [Decisiones de diseño](#decisiones-de-diseño)
- [Validación](#validación)
- [Documentación](#documentación)
- [Limitaciones y licencia](#limitaciones-y-licencia)

## Qué demuestra

| # | Objetivo | Dónde está |
|---|---|---|
| 1 | Simular la infraestructura que vigilaría un NOC: recursos del equipo, por contenedor y disponibilidad real | [`docs/PROJECT.md`](docs/PROJECT.md#tres-angulos-sobre-el-mismo-servicio) |
| 2 | El pipeline completo: recoger → evaluar → alertar → enrutar → notificar a una persona | [`docs/PROJECT.md`](docs/PROJECT.md#el-pipeline-es-el-proyecto) |
| 3 | La diferencia entre "está encendido" y "está funcionando" | [`docs/PROJECT.md`](docs/PROJECT.md#encendido-no-es-lo-mismo-que-funcionando) |
| 4 | Una respuesta con tiempos definidos: `for:`, detección y fatiga de alertas | [`docs/PROJECT.md`](docs/PROJECT.md#no-dispara-todo-al-instant) |
| 5 | Cerrar el bucle con una notificación real, no solo algo visual | [`docs/PROJECT.md`](docs/PROJECT.md#la-alerta-tiene-que-llegar-a-una-persona) |

```
  1. RECOGER          2. EVALUAR            3. ALERTAR    4. ENRUTAR      5. NOTIFICAR
  +-------------+     +---------------+     +---------+   +-----------+   +-----------+
  | exportadores|     | alert.rules   |     | severity|-->| routing   |-->| una pers. |
  | + sondas    |---->| 22 reglas     |---->| + for:  |   | + grouping|   | en un     |
  | equipo, ctn.|     | 8 recordings  |     | + labels|   | + inhibit.|   | canal real|
  | + sintética |     +---------------+     +---------+   +-----------+   +-----------+
  +-------------+                                                        vía ntfy-bridge
                                                                          (Python, 1 destino)
```

El puente tiene un único destino, ntfy, y lo declara en su propio estado: `"sinks": ["ntfy"]`.

## Qué hay dentro

| Servicio | Imagen | Qué aporta |
|---|---|---|
| Prometheus | `v3.15.0` | métricas, reglas de alerta y recording rules |
| Alertmanager | `v0.34.1` | enrutado por gravedad, agrupación, inhibiciones, silencios |
| Grafana | `12.4.11` | trece cuadros de mando aprovisionados, de solo lectura por configuración |
| node-exporter | `v1.12.1` | **recursos del equipo**: CPU, memoria, disco, red, reloj |
| cAdvisor | `v0.55.1` | **recursos de contenedores**, por contenedor |
| blackbox-exporter | `v0.28.0` | **disponibilidad del servicio**: sondas HTTP, TCP y DNS desde fuera |
| ntfy | `v2.28.0` | canal de notificación, con topics y prioridades |
| ntfy-bridge | este repositorio | agrupa las alertas y las entrega ya formateadas |
| demo-app | `nginx:1.31-alpine` | el servicio vigilado: representa un sistema crítico que puedo romper a propósito |

Los tres ángulos no son intercambiables, y por eso hay tres exportadores: un servicio puede
estar vivo y no funcionar, y `DiscoSoloLectura` lo demuestra. `demo-app` no ejecuta lógica de
negocio; es un servicio HTTP real que puedo tirar a propósito, para que la cadena se pruebe
contra una caída real. Solo Prometheus, Alertmanager, Grafana y ntfy publican un puerto, en
`127.0.0.1` por defecto; la excepción es ntfy en el móvil, que no alcanza loopback y pasa a la
red con login y acceso anónimo denegado.

## Inicio rápido

Requisitos: Docker con Compose v2. Windows y macOS necesitan el override de Desktop.

```bash
git clone https://github.com/luismanuelcldev/noc-lab.git
cd noc-lab
cp .env.example .env
# genera los dos secretos y pégalos en .env:
python3 -c "import secrets;print('GF_SECURITY_ADMIN_PASSWORD='+secrets.token_urlsafe(18))"
python3 -c "import secrets;print('BRIDGE_TOKEN='+secrets.token_hex(32))"

make up              # Linux
make up-desktop      # Windows o macOS
make status          # los nueve contenedores y su salud
```

| Qué | Dónde |
|---|---|
| Paneles | <http://localhost:3000> (`admin` y la contraseña de `.env`) |
| Prometheus | <http://localhost:9090> |
| Alertmanager | <http://localhost:9093> |
| ntfy | <http://localhost:8085> |

Nada llega a la red salvo que edite `NOC_BIND_ADDRESS`. Las 18 variables de `.env` van
documentadas una a una en [`.env.example`](.env.example) y en [INSTALL.md](docs/INSTALL.md).

## Las cuatro alertas que de verdad miro

El catálogo completo, una entrada por alerta con gravedad, umbral y pasos, está en [el manual de incidentes](docs/RUNBOOK.md).

- **`ServicioCaido`** - la sonda HTTP sintética en silencio durante más de un minuto. Es la alerta que declara una caída.
- **`DiscoCriticamenteLleno`** - por debajo del 5% libre: el TSDB deja de escribir, y con él se va la memoria del incidente.
- **`DiscoSoloLectura`** - el sistema de archivos pasó a solo lectura: todo parece "vivo", no se dispara ninguna alerta de recursos y ya no se escribe nada.
- **`HostSinMemoria`** - por debajo de 256 MiB disponibles, donde el kernel puede empezar a matar procesos.

Ninguna es instantánea, y es deliberado: cada `for:` es el tiempo que la condición debe aguantar
antes de que entre una persona. Un sistema que avisa de cada parpadeo enseña a ignorarlo.

## Decisiones de diseño

- **Las alertas viven en `rules/`, no en la UI de Grafana.** Así se revisan en un diff, se validan con `promtool` y los cubren 14 casos de prueba, en vez de vivir donde nadie las revisa. [El pipeline](docs/PROJECT.md#el-pipeline-es-el-proyecto).
- **Ningún secreto está en claro en la configuración.** La contraseña de Grafana y el token que Alertmanager comparte con el puente se inyectan al arrancar y se validan con `amtool`, así que un token mal puesto es un arranque que falla, no una alerta que nadie recibe. [SECURITY.md](docs/SECURITY.md#sin-secretos-en-el-log-de-arranque).
- **El puente es código mío**: 737 líneas de biblioteca estándar repartidas en once ficheros, sin dependencias, así que hay un solo punto por el que los datos salen de la red y es lo bastante pequeño para leerlo de una sentada. [SECURITY.md](docs/SECURITY.md).
- **Todo corre en un solo equipo.** Un laboratorio, no un sistema distribuido: las sondas sintéticas existen porque un laboratorio necesita una forma de fallar a propósito. [Los límites](docs/PROJECT.md#lo-que-este-proyecto-no-demuestra).

## Validación

```bash
make check           # sintaxis del compose, paneles, contrato de alertas, enlaces, entorno
make test            # reglas, configuración, código y formato
make ci              # lo anterior, que es lo que corre el pipeline
make check-datos     # check entero, más las 53 expresiones contra el Prometheus vivo
make smoke-desktop   # de extremo a extremo, necesita el stack levantado, unos seis minutos
```

Las comprobaciones estáticas no arrancan nada: `check.py` recorre los 50 paneles, valida con
`promtool` las 53 expresiones de PromQL y cruza cada alerta contra su ancla del manual y su panel.

La validación está partida en tres: la sintaxis se comprueba en cada push, la existencia de la
métrica necesita un Prometheus con historia, y la entrega real necesita el stack levantado. Lo que
no corre en el pipeline sale del CI a propósito, y el motivo está en [la guía](CONTRIBUTING.md#por-que-la-validacion-esta-partida-en-tres).

La prueba de extremo a extremo es la única que demuestra el objetivo 5, y es la que ejecuté:
`smoke.py` tira `demo-app`, espera a que las alertas lleguen a ntfy con prioridad 5, lo restaura y
espera la resolución con prioridad 2. Una entrega fallida también hace fallar el test.

## Documentación

El índice completo, con qué documento abrir y cuándo, está en [docs/README.md](docs/README.md). Los más usados:

| Documento | Para qué sirve |
|---|---|
| [PROJECT.md](docs/PROJECT.md) | para qué sirve este proyecto y la prueba de cada objetivo |
| [INSTALL.md](docs/INSTALL.md) | instalarlo y llevar la alerta a un móvil |
| [OPERATIONS.md](docs/OPERATIONS.md) | tareas del día a día: escalar, silenciar, rotar, copiar |
| [RUNBOOK.md](docs/RUNBOOK.md) | las 22 alertas, una entrada cada una, con los pasos que dar |
| [ALERTMANAGER.md](docs/ALERTMANAGER.md) | enrutado, agrupación, inhibiciones y silencios |
| [SECURITY.md](docs/SECURITY.md) | modelo de amenaza y qué se hizo al respecto |
| [CONTRIBUTING.md](CONTRIBUTING.md) | los cuatro sitios que tocar al cambiar algo |

## Limitaciones y licencia

Funciona, con la cadena verificada de extremo a extremo en Docker Desktop con WSL2. Las
limitaciones conocidas están en [OPERATIONS.md](docs/OPERATIONS.md#los-nueve-servicios): en
Windows, node-exporter mide la máquina virtual y no el equipo Windows. Y lo que este proyecto no
pretende demostrar, [PROJECT.md](docs/PROJECT.md#lo-que-este-proyecto-no-demuestra) lo dice: un
solo equipo, sin alta disponibilidad ni federation.

Apache-2.0. Ver [LICENSE](LICENSE).