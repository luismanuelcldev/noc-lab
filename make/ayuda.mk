# `make` sin argumentos.
#
# Atajos de todo lo que hago mas de una vez, para que el comando que tengo que recordar
# sea corto y la forma correcta de hacerlo quede escrita en un unico sitio. `make` no
# viene con Windows, pero cada target es un atajo de `docker compose` o de un script de
# Python, asi que se pueden copiar a mano sin perdida. En Linux y macOS, instalar make.

.DEFAULT_GOAL := help

help: ## Muestra esta ayuda
	@echo "mi-noc: atajos del laboratorio de observabilidad"
	@echo ""
	@echo "Arrancar, segun el sistema:"
	@echo "  make up            Linux"
	@echo "  make up-desktop    Windows o macOS con Docker Desktop"
	@echo ""
	@echo "Primeros pasos:"
	@echo "  make status        que servicios existen y si funcionan"
	@echo "  make check         dashboards, contrato de alertas, enlaces y entorno"
	@echo "  make ci            reglas, config, codigo del puente y formato"
	@echo ""
	@echo "Con el stack arrancado, y solo a mano:"
	@echo "  make check-datos   check entero, mas las 53 expresiones contra Prometheus"
	@echo "  make smoke         en Linux, tira demo-app y comprueba la cadena entera"
	@echo "  make smoke-desktop en Windows o macOS, lo mismo"
	@echo ""
	@echo "Ciclo de vida:"
	@echo "  make down          parar el stack, conservar los datos"
	@echo "  make destroy       pararlo y borrar los volumenes (irreversible)"
	@echo "  make logs SERVICE=prometheus      ultimas lineas de un servicio"
	@echo "  make follow SERVICE=ntfy-bridge   seguimiento en vivo de un servicio"
	@echo "  make restart SERVICE=grafana      reiniciar un servicio"
