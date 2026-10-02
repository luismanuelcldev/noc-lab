# Ciclo de vida del stack.

up: ## Arranca el stack (Linux)
	$(COMPOSE) up -d

up-desktop: ## Arranca el stack (Windows o macOS con Docker Desktop)
	$(COMPOSE_DESKTOP) up -d

down: ## Para el stack sin borrar los datos
	$(COMPOSE) down

status: ## Estado de los nueve servicios
	$(COMPOSE) ps

ps: ## Lista los contenedores del proyecto
	$(COMPOSE) ps

logs: ## Ultimas lineas de un servicio: make logs SERVICE=alertmanager
ifndef SERVICE
	$(error falta SERVICE. Por ejemplo: make logs SERVICE=prometheus)
endif
	$(COMPOSE) logs --tail=100 $(SERVICE)

follow: ## Sigue un servicio en vivo: make follow SERVICE=ntfy-bridge
ifndef SERVICE
	$(error falta SERVICE. Por ejemplo: make follow SERVICE=ntfy-bridge)
endif
	$(COMPOSE) logs -f $(SERVICE)

restart: ## Reinicia un servicio: make restart SERVICE=grafana
ifndef SERVICE
	$(error falta SERVICE. Por ejemplo: make restart SERVICE=grafana)
endif
	$(COMPOSE) restart $(SERVICE)

destroy: ## Para el stack y borra los volumenes. NO HAY MARCHA ATRAS
	@echo "Esto borra los volumenes de Prometheus y Grafana, junto con los"
	@echo "silencios activos de Alertmanager. No se puede deshacer."
	@echo ""
	@echo "Para ejecutarlo de verdad:"
	@echo "    make destroy CONFIRM=DESTROY"
ifneq ($(CONFIRM),DESTROY)
	@echo "Falta la confirmacion. No se ha borrado nada."
	@false
else
	$(COMPOSE) down -v
	@echo "Listo. El stack esta parado y los volumenes han desaparecido."
endif
