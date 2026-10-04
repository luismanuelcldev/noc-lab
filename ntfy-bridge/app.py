#!/usr/bin/env python3
"""Puente de notificacion: reenvia los webhooks de Alertmanager a ntfy.

Por que existe: es la ultima pieza de la cadena. Si se rompe, las alertas siguen
disparando y Prometheus sigue viendolas, pero no se lo cuenta nadie a nadie. Ese
modo de fallo es el silencio, el peor que puede tener un centro de monitorizacion.

Por que solo biblioteca estandar: tres endpoints y un POST saliente no justifican
un framework web. Dejar flask, requests y gunicorn elimino la superficie de
dependencias, una etapa de construccion de 3,2 GB de cache y unos 150 MB de imagen.

Aqui solo vive el ciclo de vida del proceso: la superficie HTTP es servidor.py y las
decisiones estan repartidas en validacion.py, webhook.py, formato.py, cuerpo.py,
entrega.py y metrics.py, todas comprobables sin levantar un servidor.
"""

from __future__ import annotations

import logging
from http.server import ThreadingHTTPServer

import ajuste
from servidor import Handler

LOG = logging.getLogger("ntfy-bridge")


def main() -> None:
    """Configura el log y sirve hasta que se pare el proceso.

    ThreadingHTTPServer porque un sistema de monitorizacion que se bloquea en una
    entrega lenta mientras otra alerta espera es un sistema que se come alertas.
    """
    logging.basicConfig(
        level=ajuste.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    LOG.info("arrancando en %s:%s", ajuste.BIND_ADDRESS, ajuste.BIND_PORT)
    server = ThreadingHTTPServer((ajuste.BIND_ADDRESS, ajuste.BIND_PORT), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
