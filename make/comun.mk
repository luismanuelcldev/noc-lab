# Variables compartidas por todos los targets.
#
# ROOT es el DIRECTORIO del repositorio, sin barra final. Hace falta el patron
# patsubst porque `abspath` devuelve la ruta del fichero y no la de su carpeta: con
# solo abspath el montaje de promtool acababa siendo "/w/Makefile:/w:ro", el Makefile
# montado en lugar del repositorio. `firstword` y no `lastword` porque, dividido el
# Makefile en make/*.mk, la ultima entrada de MAKEFILE_LIST es el .mk que se esta
# incluyendo, no el raiz; y patsubst quita la barra final, que en Windows devuelve la
# invertida que Docker no entiende.
ROOT   := $(patsubst %/,%,$(dir $(abspath $(firstword $(MAKEFILE_LIST)))))

# Sin virtualenv: el puente usa solo la biblioteca estandar, asi que el
# interprete es el python3/python que haya en el PATH.
PYTHON ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)

# `promtool check rules` NO acepta un directorio, de ahi el wildcard y no una lista
# escrita a mano: esa lista se queda obsoleta en cuanto alguien anade un modulo, y ese
# modulo deja de validarse mientras el target sigue pasando.
RULES := $(wildcard rules/*.yml)

# promtool y amtool desde las imagenes fijadas: promtool tiene que coincidir con la
# version de Prometheus, y el entrypoint de su imagen es `prometheus`, no `promtool`.
# Montaje de solo lectura y barras normales porque el contenedor es Linux.
PROMTOOL := docker run --rm --entrypoint promtool \
              -v "$(ROOT):/w:ro" -w /w prom/prometheus:v3.15.0
AMTOOL   := docker run --rm --entrypoint amtool \
              -v "$(ROOT):/w:ro" -w /w prom/alertmanager:v0.34.1

# Linux frente a Docker Desktop no se puede detectar de forma fiable desde un
# Makefile: `uname` no existe en la shell de Windows, y bajo WSL responde "Linux"
# cuando el motor es el de Desktop. Son dos targets y una variable sobrescribible,
# que cubre el caso raro que queda: make up COMPOSE="docker compose -f otro.yml"
COMPOSE         ?= docker compose -f docker-compose.yml
COMPOSE_DESKTOP ?= docker compose -f docker-compose.yml -f docker-compose.desktop.yml

# Prometheus para la comprobacion en vivo de los paneles, en el mismo puerto que
# publica el compose: check-datos debe hablar con el Prometheus que el operador tiene
# delante, no con otro.
PROMETHEUS ?= http://127.0.0.1:9090
