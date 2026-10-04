"""Los contadores del puente en formato de exposicion de Prometheus.

Separado de metrics.py porque esto es solo generacion de texto: la clase que lleva los
numeros no necesita saber como se escribe una muestra, y aqui se ven de un vistazo
todas las series que publica el servicio y por que.

Cada muestra lleva su # HELP y su # TYPE. No es decoracion: sin el tipo, rate() se
comporta mal y el panel enseña numeros equivocados sin quejarse.
"""

from __future__ import annotations

PREFIX = "ntfy_bridge"


def render(
    uptime: float,
    requests: dict[str, int],
    deliveries: dict[str, dict[str, int]],
    last: dict[str, int],
    alerts: int,
    duration: float,
) -> str:
    """Construye el texto de exposicion desde una foto coherente de los contadores."""
    measured = sum(row["ok"] + row["failed"] for row in deliveries.values())
    out: list[str] = []

    def emit(name: str, kind: str, help_: str, samples: list[str]) -> None:
        if samples:
            out.append(f"# HELP {name} {help_}")
            out.append(f"# TYPE {name} {kind}")
            out.extend(samples)

    emit(f"{PREFIX}_up", "gauge", "Siempre 1 mientras el servicio responde.", [f"{PREFIX}_up 1"])
    emit(
        f"{PREFIX}_uptime_seconds",
        "gauge",
        "Segundos desde el arranque del proceso.",
        [f"{PREFIX}_uptime_seconds {uptime:.3f}"],
    )
    emit(
        f"{PREFIX}_http_requests_total",
        "counter",
        "Peticiones HTTP recibidas, por resultado.",
        [f"{PREFIX}_http_requests_total {sum(requests.values())}"]
        + [
            f'{PREFIX}_http_requests_by_result_total{{result="{k}"}} {v}'
            for k, v in sorted(requests.items())
        ],
    )
    emit(
        f"{PREFIX}_alerts_received_total",
        "counter",
        "Alertas individuales recibidas de Alertmanager.",
        [f"{PREFIX}_alerts_received_total {alerts}"],
    )
    emit(
        f"{PREFIX}_delivery_success",
        "gauge",
        "Ultimo resultado por destino: 1 entregada, 0 fallida. Sostiene la alerta de canal muerto.",
        [f'{PREFIX}_delivery_success{{sink="{s}"}} {last.get(s, 1)}' for s in sorted(deliveries)],
    )
    emit(
        f"{PREFIX}_deliveries_total",
        "counter",
        "Entregas por destino y resultado.",
        [
            f'{PREFIX}_deliveries_total{{sink="{s}",result="{k}"}} {v}'
            for s, row in sorted(deliveries.items())
            for k, v in sorted(row.items())
            if k in {"ok", "failed"}
        ],
    )
    emit(
        f"{PREFIX}_delivery_retries_total",
        "counter",
        "Reintentos gastados en la entrega, por destino.",
        [
            f'{PREFIX}_delivery_retries_total{{sink="{s}"}} {row["retries"]}'
            for s, row in sorted(deliveries.items())
        ],
    )
    emit(
        f"{PREFIX}_delivery_duration_seconds_sum",
        "counter",
        "Segundos acumulados entregando.",
        [f"{PREFIX}_delivery_duration_seconds_sum {duration:.6f}"],
    )
    emit(
        f"{PREFIX}_delivery_duration_seconds_count",
        "counter",
        "Entregas que se midieron.",
        [f"{PREFIX}_delivery_duration_seconds_count {measured}"],
    )
    return "\n".join(out) + "\n"
