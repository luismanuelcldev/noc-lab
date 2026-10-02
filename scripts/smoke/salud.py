"""Salud del stack y los contadores de entrega del propio puente."""

from __future__ import annotations

from .base import NO_HEALTHCHECK, Failure, log, query, run

# Las dos alertas que este test provoca. Se usan tambien como precondicion.
ALERTAS_DEL_CICLO = frozenset({"ServicioCaido", "PuertoTCPInaccesible"})


def check_idle() -> None:
    """Negarse a empezar mientras las alertas bajo prueba ya estan disparando.

    Alertmanager no anuncia dos veces el mismo grupo: solo vuelve a notificar tras
    repeat_interval, que son horas. Una pasada que arranca encima de un grupo que
    otra dejo abierto espera, por tanto, un mensaje de disparo que no puede llegar
    nunca, y luego informa de un laboratorio sano como roto. Decirlo en una linea
    es mejor que esperar cuatro minutos para terminar en un falso negativo.
    """
    abiertas = sorted(
        {
            serie["metric"]["alertname"]
            for serie in query('ALERTS{alertstate="firing"}')
            if serie["metric"].get("alertname") in ALERTAS_DEL_CICLO
        }
    )
    if abiertas:
        raise Failure(
            f"estas alertas ya estan disparando, asi que Alertmanager no las "
            f"anunciara otra vez: {', '.join(abiertas)}\n"
            "Espera a que se resuelvan (group_interval, unos cinco minutos) y vuelve a "
            "lanzarlo. El laboratorio no tiene nada malo."
        )


def check_health() -> None:
    """Negarse a empezar salvo que el stack este sano, para evitar falsos negativos."""
    result = run(["docker", "compose", "ps", "--format", "{{.Service}}:{{.Health}}"])
    if result.returncode != 0:
        raise Failure(
            "docker compose ps fallo. Esta el motor de contenedores en marcha?\n"
            f"{result.stderr.strip()}"
        )

    unhealthy = [
        f"{service}={health or NO_HEALTHCHECK}"
        for service, _, health in (row.partition(":") for row in result.stdout.splitlines())
        if health not in ("healthy", "")
    ]
    if unhealthy:
        raise Failure(
            "contenedores poco sanos solo darian falsos negativos:\n  " + "\n  ".join(unhealthy)
        )
    log(f"los {len(result.stdout.splitlines())} contenedores estan en marcha")

    down = [s["metric"].get("job", "?") for s in query("up") if s["value"][1] != "1"]
    if down:
        raise Failure(
            "Prometheus no ve algunos targets, asi que la prueba no puede pasar:\n  "
            + "\n  ".join(sorted(down))
        )
    log(f"Prometheus ve {len(query('up'))} targets, todos en marcha")


def bridge_counters() -> dict[str, float]:
    """Leer los contadores del puente, que resumen lo que entrego de verdad."""
    series = query("sum by (result) (increase(ntfy_bridge_deliveries_total[10m]))")
    if not series:
        return {}
    return {s["metric"].get("result", "?"): float(s["value"][1]) for s in series}


def check_deliveries(before: dict[str, float], after: dict[str, float]) -> None:
    """Que lleguen las alertas no basta: el puente no puede haber fallado al enviar.

    Un result="failed" que sube significa que una notificacion se perdio en algun
    momento, que es justo el fallo que un movil en silencio no delata.
    """
    failed = after.get("failed", 0.0) - before.get("failed", 0.0)
    delivered = after.get("ok", 0.0) - before.get("ok", 0.0)
    log(f"el puente entrego {delivered:.0f} mensaje(s) y fallo {failed:.0f}")
    if failed:
        raise Failure(
            f"el puente registro {failed:.0f} entregas fallidas. Las alertas "
            "llegaron, pero algo no se pudo enviar."
        )
