#!/bin/sh
# Generar prometheus.yml y arrancar Prometheus.
#
# Prometheus no expande variables de entorno en su fichero de configuracion: una
# linea "monitor: ${NOC_MONITOR_NAME}" se carga tal cual, con la etiqueta dentro.
# Tampoco hay ninguna bandera para cambiarlo, --web.external-url es otra cosa, asi
# que unas external labels parametrizadas obligan a generar el fichero antes de
# arrancar.
#
# El fichero viene montado en solo lectura, asi que la generacion ocurre en
# /etc/prometheus y no en /tmp: rule_files usa rutas relativas que Prometheus
# resuelve contra el directorio de configuracion, y una generacion en /tmp
# arrancaria sin reglas y sin ningun aviso.
#
# Fallar es mejor que arrancar mal. Una variable que falta, un valor invalido o un
# "${" sin sustituir sale con 1 y Prometheus no arranca, porque la alternativa es
# dos entornos que se diferencian por la etiqueta equivocada.

set -eu

SRC="/etc/prometheus/prometheus.yml"
DST="/etc/prometheus/prometheus.rendered.yml"

log() { echo "[render-config] $*" >&2; }

# Solo letras, digitos, punto, guion y guion bajo: cualquier otra cosa puede romper
# el YAML o la sustitucion de sed, que es como un valor entrecomillado acaba
# corrompiendo el fichero.
validate() {
    name="$1"
    value="$2"

    if [ -z "${value}" ]; then
        log "ERROR: ${name} esta vacia o no esta definida. Revisa .env (copia .env.example)."
        exit 1
    fi

    case "${value}" in
        *[!A-Za-z0-9._-]*)
            log "ERROR: ${name} contiene caracteres no permitidos: '${value}'"
            log "       Solo se aceptan letras, digitos, punto, guion y guion bajo."
            exit 1
            ;;
    esac

    if [ -z "$(echo "${value}" | tr -d '.-_')" ]; then
        log "ERROR: ${name} solo contiene separadores: '${value}'"
        exit 1
    fi
}

validate "NOC_MONITOR_NAME" "${NOC_MONITOR_NAME:-}"
validate "NOC_ENVIRONMENT" "${NOC_ENVIRONMENT:-}"

if [ ! -f "${SRC}" ]; then
    log "ERROR: no se encuentra ${SRC}. Revisa el bind mount de docker-compose.yml."
    exit 1
fi

# Se trabaja sobre una copia: ${SRC} es de solo lectura. "|" es el delimitador de
# sed y los valores de arriba no pueden contenerlo, asi que la sustitucion es segura.
cp "${SRC}" "${DST}"
chmod 644 "${DST}"
sed -i \
    -e "s|\${NOC_MONITOR_NAME}|${NOC_MONITOR_NAME}|g" \
    -e "s|\${NOC_ENVIRONMENT}|${NOC_ENVIRONMENT}|g" \
    "${DST}"

# Esta comprobacion es la que convierte un fallo silencioso en uno visible. Las
# lineas de comentario se saltan a proposito: documentar que el fichero lleva
# marcadores es legitimo, y un grep ingenuo sobre todo el fichero haria fallar cada
# arranque.
if grep -v '^[[:space:]]*#' "${DST}" | grep -q '\${'; then
    log "ERROR: quedan variables sin sustituir en el fichero generado:"
    grep -n '\${' "${DST}" | grep -v ':[[:space:]]*#' >&2 || true
    log "       Comprueba que las variables estan en .env y que los nombres"
    log "       usados en prometheus.yml son los que maneja este script."
    exit 1
fi

log "external labels: monitor=${NOC_MONITOR_NAME} environment=${NOC_ENVIRONMENT}"
log "generado en ${DST}"

exec /bin/prometheus "$@"
