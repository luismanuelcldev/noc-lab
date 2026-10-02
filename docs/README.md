# Documentación

Nueve documentos y ninguno sobra. La trampa de un repositorio así es escribir el mismo runbook
tres veces y que las tres versiones se queden viejas por su cuenta; aquí cada cosa vive en un
sitio y este índice dice cuál es. Si buscas una alerta concreta, el sitio es
[RUNBOOK.md](RUNBOOK.md). Si buscas saber por qué el proyecto existe, es [PROJECT.md](PROJECT.md).

## Por dónde empezar

| Si quieres... | Abre |
|---|---|
| Saber qué demuestra esto y cómo está probado | [PROJECT.md](PROJECT.md) |
| Levantarlo y ver la alerta en el móvil | [INSTALL.md](INSTALL.md) |
| Saber qué hacer a las 3 de la madrugada | [RUNBOOK.md](RUNBOOK.md) |
| Entender a quién despierta cada alerta y por qué | [ALERTMANAGER.md](ALERTMANAGER.md) |
| Operarlo a diario: escalar, silenciar, rotar, copiar | [OPERATIONS.md](OPERATIONS.md) |
| Saber qué secretos existen y dónde | [SECURITY.md](SECURITY.md) |
| Cambiar algo sin romper el contrato | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Saber qué cambió y cuándo | [CHANGELOG.md](../CHANGELOG.md) |

## Los siete de aquí

Los siete de `docs/`. Los otros dos, `CONTRIBUTING.md` y `CHANGELOG.md`, viven en la raíz porque
los lee quien va a cambiar algo y quien sigue los cambios, no quien acaba de clonar.

| Documento | Qué resuelve | Cuándo lo leo |
|---|---|---|
| [PROJECT.md](PROJECT.md) | Para qué sirve el laboratorio y qué prueba cada objetivo, con los cinco ángulos del pipeline | Antes de cambiar la arquitectura |
| [INSTALL.md](INSTALL.md) | Requisitos, variables, arranque, la alerta en el móvil y qué hacer cuando algo no arranca | La primera vez, y cuando algo falla |
| [OPERATIONS.md](OPERATIONS.md) | Los nueve servicios, el estado, silencios, rotación y copias de seguridad | En el día a día, con el stack ya levantado |
| [RUNBOOK.md](RUNBOOK.md) | Las 22 alertas, una entrada cada una con gravedad, umbral y pasos | Cuando suena una alerta |
| [ALERTMANAGER.md](ALERTMANAGER.md) | Enrutado por gravedad, agrupación, tiempos e inhibiciones | Al tocar `alertmanager.yml` |
| [SECURITY.md](SECURITY.md) | Modelo de amenaza, los secretos y por qué el arranque falla si un token está mal | Al tocar la autenticación o la exposición de puertos |
| [ALERTS-RETIRED.md](ALERTS-RETIRED.md) | Qué reglas existieron, por qué se retiraron y por qué retirarlas no es borrarlas | Al preguntarse "esto faltaba" |

## Las cuatro cosas que no viven en ningún sitio

Hay conocimiento que no se deduce leyendo ficheros, y por eso está escrito:

- **El motivo de una retirada.** `ALERTS-RETIRED.md` lo guarda porque es lo único que un
  validador no puede comprobar: quitar el bloque de `rules/` no deja rastro de por qué.
- **El porqué de la validación partida en tres.** Está en
  [CONTRIBUTING.md](../CONTRIBUTING.md#por-que-la-validacion-esta-partida-en-tres), y explica
  por qué `check-datos` y `smoke` están fuera del pipeline en vez de estar rotos.
- **La duración real del smoke.** De unos seis minutos, hasta once. Los ceilings de 240 s y
  420 s son un techo, no un mínimo, y confundirlos hace creer que el test va fallar.
- **Lo que este proyecto no demuestra.** Un solo equipo, sin alta disponibilidad ni federation.
  Está en [PROJECT.md](PROJECT.md#lo-que-este-proyecto-no-demuestra) porque un NOC de mentira
  que parece de verdad es peor que uno que admite su límite.
