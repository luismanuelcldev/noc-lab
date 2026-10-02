"""Leer la configuracion del propio laboratorio.

Es para que la prueba no pueda estar en desacuerdo con ella.
"""

from __future__ import annotations

import base64

from .base import GROUP_INTERVAL_PATTERN, RESOLUTION_GRACE_SECONDS, ROOT


def env_value(name: str) -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def configured_topic() -> str:
    return env_value("NTFY_TOPIC") or "noc-alerts"


def ntfy_auth() -> str | None:
    """La cabecera Basic que usa el movil para leer el topic, o None si es abierto.

    La prueba de humo tiene que leer ntfy igual que lo hace el movil. En cuanto
    el puerto publicado sale de 127.0.0.1 exijo un login, y con
    NTFY_AUTH_DEFAULT_ACCESS=deny-all una lectura anonima del topic responde 403.
    Sin estas cabeceras este script informaria de un laboratorio roto cuando lo
    unico que falla es que el lector nunca inicio sesion.
    """
    user = env_value("NTFY_USER")
    password = env_value("NTFY_PASSWORD")
    if not user or not password:
        return None
    token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def seconds_to_resolve() -> int:
    """Cuanto tiempo tengo que dejar para las alertas resueltas.

    No es un numero inventado: se lee de alertmanager.yml. Prometheus resuelve una
    alerta al instante, pero la notificacion de "todo despejado" solo sale cuando
    Alertmanager vuelve a mirar el grupo, y eso es lo que fija group_interval. Con
    los 5 minutos de este repositorio, una espera de 2 minutos informaria siempre
    de un falso negativo, que es la forma mas confusa de que falle una prueba
    asi: el laboratorio funciona y el script dice que no.
    """
    config = ROOT / "alertmanager.yml"
    if config.exists():
        found = GROUP_INTERVAL_PATTERN.search(config.read_text(encoding="utf-8"))
        if found:
            return int(found.group(1)) * 60 + RESOLUTION_GRACE_SECONDS
    return 420
