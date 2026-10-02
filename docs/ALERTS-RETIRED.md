# Alertas retiradas

Registro de alertas que estuvieron activas y ya no lo están. Existe por una razón concreta:
mientras construía este laboratorio añadí alertas que resultaron ser ruido. Sin este registro,
la siguiente persona con la misma idea asume que es nueva, la vuelve a añadir y repite el
trabajo de demostrar que no funciona.

## Cómo se retira una alerta

Retirar una alerta no es borrar su bloque de `rules/`. En este orden:

1. Quitar la regla de `rules/`.
2. Quitar su sección de `docs/RUNBOOK.md`.
3. Quitar su caso de prueba de `test/*.test.yml`.
4. Anotarla aquí, con el motivo.

Las tres primeras las comprueba `scripts/check.py`. La cuarta no se puede automatizar: el
motivo por el que se retiró una alerta es el único conocimiento que no se deduce de los
ficheros.

## Cómo decido que una alerta es ruido

Retiro una alerta cuando se cumple una de estas cosas, y por ninguna otra:

- **Duplica a otra.** Mismo fallo, misma causa. Dos alertas para un solo fallo significan que
  las dos acaban apagadas.
- **No tiene acción.** Informa de algo que no se puede arreglar ni mirar. Una notificación sin
  acción se convierte en ruido en cuestión de semanas.
- **Nunca se dispara en este sistema.** Cierta siempre, y reajustada cada vez que algo cambia.
  Una alerta que está siempre encendida no informa a nadie.
- **Mide algo que no importa.** El valor es correcto y la señal no dice nada sobre la salud del
  sistema.

## Retiradas

| Alerta | Gravedad que tenía | Por qué se retiró |
|---|---|---|
| `AusenciaDeMetricas` | `warning` | Comparaba `time()` con `node_textfile_mtime_seconds` para detectar métricas congeladas, pero esa métrica viene del colector textfile de node_exporter, que este repositorio no habilita: no se monta ningún directorio de métricas personalizadas, así que la serie no existía y la regla nunca podía dispararse. La única forma de averiguarlo era fijarse en un panel que mostraba "sin datos" de forma permanente. La necesidad de fondo, detectar métricas que dejan de actualizarse, ya la cubre `TargetHostCaido` mediante `absent_over_time`, que sí funciona. Recuperar el caso de uso original exigiría montar un directorio de textfiles y arrancar node_exporter con `--collector.textfile.directory`. |

Una alerta que no puede dispararse no es cobertura, es relleno que hace que el catálogo parezca
más completo de lo que es. `TargetHostCaido` ya carga con eso: su comentario deja constancia de
que una sola regla cubre los dos casos, la pérdida total y los raspados congelados.

## Retirada no es lo mismo que silenciada

La desactivación es un caso aparte. Una alerta que no aplica a una instalación concreta se
silencia con un silencio que tiene hora de fin, no se borra: borrar una regla que aplica en
otro sitio pierde el conocimiento, silenciarla lo conserva. Mira
[operaciones](OPERATIONS.md#silenciar-una-alerta).

## Cobertura de pruebas no es lo mismo que estar activa

Retirar una alerta y probarla son preguntas distintas, y las cifras no son intercambiables. De
las 22 alertas activas, **8 tienen caso de regresión** en `test/*.test.yml`, repartido en 14
casos de evaluación.

| Con caso de regresión (8) | Sin él (14) |
|---|---|
| `CanalNotificacionCaido`<br>`ContenedorReiniciado`<br>`ContenedorUsoMemoriaAlto`<br>`CPUHostAlta`<br>`PrometheusSinScrapear`<br>`TargetCaido`<br>`TargetHostCaido`<br>`LatidoDeMonitorizacion` | `BridgeNotificacionInaccesible`<br>`ContenedorUsoCPUAlto`<br>`CrecimientoDeDiscoExcesivo`<br>`DiscoCasiLleno`<br>`DiscoCriticamenteLleno`<br>`DiscoSoloLectura`<br>`HostReiniciado`<br>`HostSinMemoria`<br>`MemoriaHostAlta`<br>`PuertoTCPInaccesible`<br>`RelojDesincronizado`<br>`ServicioCaido`<br>`SondaDevueltaRespuestaInvalida`<br>`TiempoDeRespuestaAlto` |

Las 14 sin caso no están mal ni retiradas: están activas, con un contrato que `scripts/check.py`
verifica, y cubiertas levantando el stack en vez de con una serie sintética. Las 8 con caso son
aquellas donde un cambio sutil en la expresión sería invisible en un despliegue real, así que
están fijadas.
