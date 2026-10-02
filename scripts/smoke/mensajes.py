"""Leer ntfy y esperar a los nombres de alerta que el laboratorio debe producir."""

from __future__ import annotations

import json
import re
import time

from .base import NTFY, Failure, get, log
from .entorno import ntfy_auth


def read_messages(topic: str, since: str) -> list[dict]:
    """Mensajes de un topic. ntfy responde NDJSON: un objeto JSON por linea."""
    url = f"{NTFY}/{topic}/json?poll=1&since={since}"
    auth = ntfy_auth()
    headers = {"Authorization": auth} if auth else {}
    return [json.loads(line) for line in get(url, headers).splitlines() if line.strip()]


def wait_for_alerts(
    topic: str, since: str, expected: tuple[str, ...], seconds: int, pattern: re.Pattern[str]
) -> None:
    """Esperar a las alertas esperadas y anotando cada una segun llega.

    El topic entero se relee en cada pasada en vez de mantener una suscripcion
    abierta. Sobre el papel es peor, pero sobrevive a un reinicio de ntfy a mitad
    de la espera, que es justo cuando mas doleria perder la prueba.
    """
    deadline = time.monotonic() + seconds
    found: set[str] = set()
    while time.monotonic() < deadline:
        for message in read_messages(topic, since):
            name = pattern.search(str(message.get("message", "")))
            if name and name.group(1) in expected and name.group(1) not in found:
                found.add(name.group(1))
                log(
                    f"  {name.group(1)} -> {message.get('title', '')}"
                    f" (priority {message.get('priority')})"
                )
        if found >= set(expected):
            return
        time.sleep(5)
    missing = [alert for alert in expected if alert not in found]
    raise Failure(
        f"{', '.join(missing)} no llegaron en {seconds} segundos.\n"
        "Eso no significa necesariamente que las reglas esten mal: mira "
        "ntfy_bridge_alerts_received_total para saber si el puente recibio algo, "
        "y los logs de ntfy-bridge para saber si fallo la publicacion."
    )
