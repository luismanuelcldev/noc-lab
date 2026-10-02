# Extremo a extremo.
#
# El unico test que necesita el stack en marcha, y deliberadamente fuera de la
# CI: nueve contenedores, un arranque de mas de un minuto y el group_interval de
# 5 minutos de Alertmanager hacen que una CI que levanta y tira el stack sea mas
# lenta y mas fragil que el propio laboratorio. Es una prueba de banco, no de
# pipeline.

smoke: ## Tira demo-app y comprueba que la alerta salta y se resuelve (Linux)
	$(PYTHON) scripts/smoke.py

smoke-desktop: ## Igual, con el override de Docker Desktop
	$(PYTHON) scripts/smoke.py --override
