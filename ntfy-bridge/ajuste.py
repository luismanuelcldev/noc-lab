"""Configuracion de despliegue, leida una vez del entorno.

Todos los ajustes del puente viven aqui para que los modulos que los usan no
vuelvan a analizar os.environ cada uno, y para que una prueba pueda cambiar un
valor y ver el efecto. Nada de esto es secreto: BRIDGE_TOKEN y NTFY_TOKEN se leen
del entorno al arrancar y nunca se registran.
"""

from __future__ import annotations

import os

# Forma del mensaje.
SEPARATOR = "-" * 38
SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}
# ntfy quiere la forma numerica: su API JSON rechaza los nombres con un 400 que
# culpa al JSON en vez de al tipo del campo.
PRIORITY = {"low": 2, "default": 3, "high": 4, "urgent": 5}
TAGS = {
    "critical": ["rotating_light", "warning"],
    "warning": ["warning"],
    "info": ["information_source"],
}
MAX_MESSAGE_CHARS = int(os.environ.get("MAX_MESSAGE_CHARS", "3000"))

# Entrega a ntfy.
NTFY_URL = os.environ.get("NTFY_URL", "http://ntfy:80")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "noc-alerts")
NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")
NTFY_USER = os.environ.get("NTFY_USER", "")
NTFY_PASSWORD = os.environ.get("NTFY_PASSWORD", "")
MAX_RETRIES = int(os.environ.get("BRIDGE_MAX_RETRIES", "3"))
BACKOFF_BASE = 0.5
BACKOFF_MAX = 8.0
TIMEOUT = 10
# Limite de la politica de reintentos: el 429 es el unico 4xx que merece repetirse,
# porque es el servidor diciendo explicitamente "ahora no". Cualquier otro 4xx es un
# rechazo permanente (token malo, cuerpo sobredimensionado) y reintentarlo solo
# gasta la peticion de Alertmanager.
HTTP_SERVER_ERROR = 500
HTTP_TOO_MANY_REQUESTS = 429

# El puente en si.
# BIND_ADDRESS vale 0.0.0.0 a proposito: el proceso corre dentro de la red de
# Docker, donde 127.0.0.1 lo haria inalcanzable desde todos los demas servicios.
# El aislamiento viene de la red, no de la direccion de escucha.
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "")
MAX_BODY_BYTES = 1024 * 1024
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
BIND_ADDRESS = os.environ.get("BIND_ADDRESS", "0.0.0.0")
BIND_PORT = int(os.environ.get("BIND_PORT", "5000"))
