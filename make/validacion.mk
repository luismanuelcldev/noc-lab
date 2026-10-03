# Validacion. Ninguno de estos targets necesita el stack en marcha, y es
# deliberado: una CI que levanta nueve contenedores para comprobar que la
# documentacion esta bien es una CI que falla por su propia complejidad.
#
# `check` lleva --strict porque sin el ningun aviso detiene nada: el flag estaba
# documentado y nadie lo activaba, y un aviso que no rompe el pipeline es un
# aviso que nadie lee. El unico aviso que puede aparecer es un panel vacio que no
# esta en VACIOS_ESPERADOS, que es justo la metrica renombrada que se busca.

check: ## Dashboards, contrato de alertas, enlaces, entorno y sintaxis
	$(PYTHON) scripts/check.py --strict

rules: ## Sintaxis de las reglas con promtool
	$(PROMTOOL) check rules $(RULES)

test: rules ## Ejecuta los casos de regresion de reglas
	$(PROMTOOL) test rules test/*.test.yml

bridge: ## Tests unitarios del puente (solo biblioteca estandar)
	$(PYTHON) -m unittest discover -s ntfy-bridge -q

validadores: ## Tests unitarios de los validadores
	$(PYTHON) -m unittest discover -s scripts -p 'test_*.py' -q

config: ## Valida los dos ficheros compose sin arrancar nada
	$(COMPOSE) config --quiet && echo "docker-compose.yml es valido"
	$(COMPOSE_DESKTOP) config --quiet && echo "docker-compose.desktop.yml es valido"

config-services: ## Valida prometheus.yml y alertmanager.yml con sus propias herramientas
	$(PROMTOOL) check config prometheus.yml
	$(AMTOOL) check-config alertmanager.yml

lint: ## Analisis estatico
	$(PYTHON) -m ruff check .

fmt: ## Comprobacion de formato; no cambia nada
	$(PYTHON) -m ruff format --check .

ci: config rules test config-services bridge validadores lint fmt check ## Todo lo que ejecuta la CI

# La unica comprobacion que NO esta en `ci`, y por que. Las 53 expresiones se
# ejecutan contra un Prometheus vivo, y un Prometheus recien arrancado no tiene
# historia: tres paneles usan ventanas de [6h] y [30d], asi que ahi siempre estan
# vacios y un pipeline que los tratara como fallo seria un pipeline rojo por el
# motivo equivocado. Levantarlo en la CI no compra la metrica renombrada, que es
# lo unico que esto caza de verdad.
check-datos: ## check entero, mas las 53 expresiones contra el Prometheus vivo
	$(PYTHON) scripts/check.py --strict --prometheus $(PROMETHEUS)
