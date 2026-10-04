"""Qué hace el puente con un lote entrante que ya ha sido validado.

Aquí no hay HTTP: las comprobaciones previas viven en validacion.py y el transporte en
servidor.py, así que el camino feliz y sus fallos se prueban sin arrancar un servidor.
"""

from __future__ import annotations

import logging

import formato
from entrega import deliver
from metrics import Metrics

LOG = logging.getLogger("ntfy-bridge")

METRICS = Metrics()


def procesar(carga: dict) -> tuple[int, str, dict]:
    """Reenvía un lote a ntfy. Devuelve (estado, etiqueta de métrica, cuerpo).

    La etiqueta se devuelve en vez de registrarse aquí para que solo el transporte toque
    los contadores, y una petición no pueda quedarse sin contar ni contarse dos veces.
    """
    count = len(carga.get("alerts") or [])
    if count == 0:
        # No es un error: Alertmanager manda un lote vacío cuando todo se resuelve, y
        # responder rápido evita reintentos inútiles.
        return 200, "ok", {"delivered": 0, "detail": "lote vacío"}

    METRICS.record_alerts(count)
    LOG.info("lote recibido: %s alerta(s), estado=%s", count, carga.get("status", "firing"))
    title, body, priority, tags, click = formato.build(carga)
    ok, attempts, duration = deliver(title, body, priority, tags, click)
    METRICS.record_delivery(ok, attempts, duration)

    if ok:
        return (
            200,
            "ok",
            {
                "delivered": 1,
                "channel": "ntfy",
                "attempts": attempts,
                "duration_s": round(duration, 4),
            },
        )
    # 502 es lo que hace que Alertmanager reintente el grupo: un ntfy muerto no puede
    # tragarse el incidente en silencio.
    return (
        502,
        "error",
        {
            "error": "ningún destino pudo entregar la notificación",
            "failed_sinks": ["ntfy"],
        },
    )
