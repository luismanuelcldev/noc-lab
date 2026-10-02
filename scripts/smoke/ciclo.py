"""Lo unico que hace esta prueba: tirar demo-app y vigilar el camino entero."""

from __future__ import annotations

from .base import EXPECTED_ALERTS, FIRING_PATTERN, RESOLVED_PATTERN, Failure, log, run
from .mensajes import read_messages, wait_for_alerts
from .salud import bridge_counters, check_deliveries, check_health, check_idle


def full_cycle(topic: str, wait_firing: int, wait_resolution: int, files: list[str]) -> None:
    """Para demo-app, esperar la alerta, volver a arrancarlo y esperar la resolucion."""
    check_health()
    check_idle()
    before = bridge_counters()
    previous = read_messages(topic, "all")
    # El id del ultimo mensaje es la linea de partida: de aqui en adelante solo
    # se leen ids mas nuevos, asi que esta pasada no se confunde con el historico.
    since = previous[-1]["id"] if previous else "all"

    log("parando demo-app")
    stop = run(["docker", "compose", "-f", "docker-compose.yml", *files, "stop", "demo-app"])
    if stop.returncode:
        raise Failure("no se pudo parar demo-app")

    try:
        log("esperando a que las alertas lleguen a ntfy")
        wait_for_alerts(topic, since, EXPECTED_ALERTS, wait_firing, FIRING_PATTERN)
    finally:
        # demo-app vuelve pase lo que pase. Dejar el laboratorio caido porque la
        # prueba fallo seria la peor forma de fallar.
        log("volviendo a arrancar demo-app")
        run(["docker", "compose", "-f", "docker-compose.yml", *files, "start", "demo-app"])

    log("esperando a que se resuelvan")
    wait_for_alerts(topic, since, EXPECTED_ALERTS, wait_resolution, RESOLVED_PATTERN)
    check_deliveries(before, bridge_counters())
