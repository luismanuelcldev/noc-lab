"""Publicar el mensaje en ntfy, con espera exponencial.

Alertmanager reintenta con su propio calendario, pero reintentar aqui deja el intento
dentro de las metricas del puente y responde rapido, en vez de tener abierta la peticion
durante todo el group_wait.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import ajuste

LOG = logging.getLogger("ntfy-bridge")


def _auth_headers() -> dict[str, str]:
    """Bearer si hay token configurado; si no, Basic; si no, anonimo."""
    if ajuste.NTFY_TOKEN:
        return {"Authorization": f"Bearer {ajuste.NTFY_TOKEN}"}
    if ajuste.NTFY_USER and ajuste.NTFY_PASSWORD:
        # Autenticacion basica: el laboratorio usa ntfy con el login desactivado, pero
        # una instalacion que lo active no deberia necesitar un cambio de codigo.
        pair = base64.b64encode(f"{ajuste.NTFY_USER}:{ajuste.NTFY_PASSWORD}".encode()).decode()
        return {"Authorization": f"Basic {pair}"}
    return {}


def deliver(
    title: str, body: str, priority: int, tags: list[str], click: str
) -> tuple[bool, int, float]:
    """POST a ntfy. Devuelve (entregado, intentos, segundos)."""
    doc = {
        "topic": ajuste.NTFY_TOPIC,
        "title": title,
        "message": body,
        "priority": priority,
        "tags": tags,
    }
    if click:
        doc["click"] = click
    headers = {"Content-Type": "application/json", **_auth_headers()}
    data = json.dumps(doc).encode("utf-8")

    started = time.monotonic()
    for attempt in range(1, ajuste.MAX_RETRIES + 2):
        try:
            # S310: el esquema viene de ajuste.NTFY_URL, que es configuracion de
            # despliegue y no entrada de la peticion, y el laboratorio habla con ntfy por
            # http a proposito. En un despliegue real aqui se fuerza https.
            with urlopen(  # noqa: S310
                Request(ajuste.NTFY_URL, data=data, headers=headers, method="POST"),  # noqa: S310
                timeout=ajuste.TIMEOUT,
            ) as response:
                response.read()
            return True, attempt, time.monotonic() - started
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            # Un 4xx distinto de 429 no mejora reintentando, asi que se para aqui y
            # se deja que Alertmanager vea el fallo.
            if (
                isinstance(exc, HTTPError)
                and exc.code < ajuste.HTTP_SERVER_ERROR
                and exc.code != ajuste.HTTP_TOO_MANY_REQUESTS
            ):
                LOG.error("ntfy rechazo la notificacion con %s: %s", exc.code, reason)
                return False, attempt, time.monotonic() - started
            if attempt > ajuste.MAX_RETRIES:
                LOG.error("la entrega a ntfy fallo tras %s intentos: %s", attempt, reason)
                return False, attempt, time.monotonic() - started
            wait = min(ajuste.BACKOFF_BASE * (2 ** (attempt - 1)), ajuste.BACKOFF_MAX)
            LOG.warning(
                "el intento %s de entrega fallo (%s); reintento en %.1fs", attempt, reason, wait
            )
            time.sleep(wait)
    return False, ajuste.MAX_RETRIES + 1, time.monotonic() - started
