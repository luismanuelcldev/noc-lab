#!/bin/sh
# Inyecta el token de autenticacion de Alertmanager y arranca Alertmanager. El
# razonamiento completo, con las tres opciones descartadas, en docs/ALERTMANAGER.md.
#
# El puente exige "Authorization: Bearer <token>" en /webhook, y Alertmanager no puede
# enviarlo: no expande variables de entorno en su configuracion, asi que
# "credentials: ${BRIDGE_TOKEN}" enviaria esa cadena literal. Un BRIDGE_TOKEN vacio deja
# en cambio un endpoint que acepta cualquier cosa desde cualquier contenedor de esa red,
# y un token escrito a mano mete un secreto en el repo. Esta es la tercera via: el token
# llega como variable de entorno y acaba en una copia en memoria al arrancar.
#
# El render cae en /tmp porque CONTIENE el token: /etc/alertmanager sale en "docker
# diff" porque es la capa del contenedor, y /tmp es un tmpfs. Un token mal formado o una
# configuracion rechazada paran el script a proposito: un Alertmanager muerto es obvio y
# uno con la cabecera rota es un fallo mudo.

set -eu

SRC="/etc/alertmanager/alertmanager.yml"
DST="/tmp/alertmanager.rendered.yml"

log() { echo "[render-config] $*" >&2; }

if [ ! -f "${SRC}" ]; then
    log "ERROR: ${SRC} no existe. Comprueba el bind mount en docker-compose.yml."
    exit 1
fi

TOKEN="${BRIDGE_TOKEN:-}"

if [ -z "${TOKEN}" ]; then
    log "WARNING: BRIDGE_TOKEN esta vacio, asi que el puente ACEPTA peticiones sin autenticar."
    log "         Aceptable en este laboratorio autoalojado, donde el puente no publica puertos y"
    log "         solo se alcanza desde la red interna. Fuera de aqui, pon BRIDGE_TOKEN en .env."
    cp "${SRC}" "${DST}"
    chmod 600 "${DST}"
else
    # "openssl rand -hex 32" produce solo [0-9a-f] y cumple esto.
    case "${TOKEN}" in
        *[!A-Za-z0-9_-]*)
            log "ERROR: BRIDGE_TOKEN contiene caracteres que no estan permitidos."
            log "       Solo se aceptan letras, digitos, guion y guion bajo."
            log "       Genera uno valido con: openssl rand -hex 32"
            exit 1
            ;;
    esac

    if [ -z "$(echo "${TOKEN}" | tr -d '._-')" ]; then
        log "ERROR: BRIDGE_TOKEN solo contiene separadores."
        exit 1
    fi

    log "inyectando la autorizacion Bearer en los webhooks que apuntan al puente"

    # awk y no sed: inserta varias lineas de una vez sin depender de las diferencias
    # de sed al escapar saltos de linea en un patron. Solo los webhooks cuya URL apunta
    # al puente reciben la cabecera, de modo que un receiver nuevo no recibe un token
    # que nunca pidio, y el bloque END avisa si el patron dejara de casar con nada.
    awk -v token="${TOKEN}" '
        { print }
        /- url: "http:\/\/ntfy-bridge/ {
            print "        http_config:"
            print "          authorization:"
            print "            type: Bearer"
            print "            credentials: \"" token "\""
            injected++
        }
        END {
            if (injected == 0) {
                print "WARNING: ningun webhook apunta al puente; no se inyecto token" > "/dev/stderr"
            }
        }
    ' "${SRC}" > "${DST}"

    chmod 600 "${DST}"

    # Confirma que la inyeccion ha entrado. El fichero se queda en el tmpfs y un reinicio
    # vuelve a renderizar desde el origen, sin token.
    rendered_hits=$(grep -c "credentials:" "${DST}" || true)
    if [ "${rendered_hits}" -eq 0 ]; then
        log "ERROR: no se ha podido inyectar la cabecera de autorizacion."
        log "       Comprueba que los receivers siguen usando el prefijo de URL"
        log "       http://ntfy-bridge que este script busca aqui."
        rm -f "${DST}"
        exit 1
    fi
    log "cabecera inyectada en ${rendered_hits} receiver(s)"
fi

# amtool viene en la imagen de Alertmanager, asi que validar aqui detecta un error de
# sintaxis ahora en vez de un bucle de reinicio despues.
if ! amtool check-config "${DST}" > /dev/null 2>&1; then
    log "ERROR: la configuracion renderizada no es valida:"
    amtool check-config "${DST}" >&2 || true
    rm -f "${DST}"
    exit 1
fi
log "configuracion validada con amtool"

exec /bin/alertmanager "$@"
