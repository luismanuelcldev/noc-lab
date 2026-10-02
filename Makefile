# Atajos del laboratorio, en make/. Este fichero solo los incluye: cada grupo de
# targets vive en su propio .mk, y `make help` sigue dando la lista completa.
#
#   comun.mk       variables compartidas
#   ayuda.mk       `make` sin argumentos
#   ciclo.mk       arrancar, parar, logs
#   validacion.mk  check, reglas, tests, lint
#   extremo.mk     prueba extremo a extremo

include make/comun.mk
include make/ayuda.mk
include make/ciclo.mk
include make/validacion.mk
include make/extremo.mk

.PHONY: help up up-desktop down status logs follow restart destroy ps \
        check rules test bridge config config-services lint fmt ci \
        smoke smoke-desktop
