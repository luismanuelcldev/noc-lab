"""Sintaxis del compose, delegada a la herramienta que es duena del formato.

Aqui no se reimplementa ningun parser. Docker Compose tiene un validador que ya
conoce su formato mejor que cualquier comprobacion escrita encima, y lo unico que
aporta es ejecutarlo y leer su codigo de salida.

Las reglas y el enrutado de Alertmanager no se comprueban aqui, a proposito. Sus
validadores son promtool y amtool, y la CI ya los ejecuta con la misma imagen
fijada que el compose, sin levantar el stack. Este modulo no los repetia por
docker compose exec porque si: en la CI eso es service "prometheus" is not
running, y un modulo que se llama desde la puerta estatica tiene que funcionar
con el stack parado.
"""

from __future__ import annotations

import subprocess

from .base import aviso, error

PASOS = (("compose", ["docker", "compose", "config", "-q"]),)


def check_config() -> None:
    """Ejecuta `docker compose config`. Si no esta docker, es aviso y no error."""
    for nombre, comando in PASOS:
        try:
            # S603: los comandos estan escritos aqui, no construidos con entrada.
            # check=False porque se inspecciona el codigo de retorno para poder
            # enseñar el stderr de la herramienta, que es la parte util del fallo.
            hecho = subprocess.run(  # noqa: S603
                comando, capture_output=True, text=True, timeout=90, check=False
            )
        except FileNotFoundError:
            aviso(f"no se puede ejecutar {comando[0]}: no está en el PATH, se omite {nombre}")
            continue
        except subprocess.TimeoutExpired:
            error(f"{nombre}: la validación agotó el tiempo")
            continue
        if hecho.returncode != 0:
            detalle = (hecho.stderr or hecho.stdout).strip().splitlines()[:3]
            error(f"{nombre}: {' / '.join(detalle)}")
