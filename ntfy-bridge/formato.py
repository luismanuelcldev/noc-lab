"""La cabecera del mensaje: titulo, prioridad y etiquetas de la notificacion.

Decisiones que salen de como se lee una alerta de noche:

* La gravedad mas alta del grupo decide el color, la prioridad y el icono. Las
  etiquetas las elige Alertmanager, asi que se recalcula aqui el peor caso.
* Un lote resuelto nunca es urgente: despertar a alguien a las 3am para decir
  que el incidente ha acabado es un fallo de operacion, no un detalle.
* Gana el texto ya formateado: si las plantillas de Alertmanager nos dieron
  prosa, la configuracion manda en el texto y este modulo no lo reescribe.

El cuerpo lo dibuja cuerpo.py, y los tokens RESOLVED, ACTIVE y CRITICAL se
quedan en ingles a proposito: el smoke test los busca con una expresion regular
y, en un telefono de guardia, un RESOLVED se distingue de un ACTIVE de un
vistazo.
"""

from __future__ import annotations

import ajuste
import cuerpo


def build(payload: dict) -> tuple[str, str, int, list[str], str]:
    """Convertir un lote de Alertmanager en (titulo, cuerpo, prioridad, tags, url)."""
    alerts = [a for a in (payload.get("alerts") or []) if isinstance(a, dict)]
    group_labels = payload.get("groupLabels") or {}
    resolved = str(payload.get("status", "firing")).lower() == "resolved"

    if resolved:
        title = f"RESOLVED: {group_labels.get('alertname', 'alertas')}"
        priority, tags = ajuste.PRIORITY["low"], ["white_check_mark"]
    else:
        worst = max(
            (str((a.get("labels") or {}).get("severity", "info")).lower() for a in alerts),
            key=lambda s: ajuste.SEVERITY_RANK.get(s, 0),
            default="info",
        )
        label = "CRITICAL" if worst == "critical" else worst.upper()
        title = f"[{label}] {group_labels.get('service') or 'NOC'}"
        if len(alerts) > 1:
            title += f" ({len(alerts)})"
        if worst in ("critical", "warning"):
            priority = ajuste.PRIORITY["urgent" if worst == "critical" else "high"]
        else:
            priority = ajuste.PRIORITY["default"]
        tags = ajuste.TAGS.get(worst, ajuste.TAGS["info"])

    body = str(payload.get("summary_text") or "").strip()
    if not body:
        body = cuerpo.compose_body(alerts, resolved) if alerts else "Lote de alertas vacio."
    return title[:200], body, priority, tags, str(payload.get("externalURL") or "")
