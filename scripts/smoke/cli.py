"""Linea de comandos: argumentos, salida y codigo de salida."""

from __future__ import annotations

import argparse
import contextlib
import sys

from .base import Failure
from .ciclo import full_cycle
from .entorno import configured_topic, seconds_to_resolve


def main() -> int:
    with contextlib.suppress(AttributeError, ValueError, OSError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Prueba de humo del camino de la alerta, de extremo a extremo"
    )
    parser.add_argument(
        "--wait",
        "--espera",
        dest="wait",
        type=int,
        default=240,
        help="segundos de espera para las alertas en estado firing (por defecto 240)",
    )
    parser.add_argument(
        "--wait-resolution",
        "--espera-resolucion",
        dest="wait_resolution",
        type=int,
        default=None,
        help="segundos de espera para las resueltas (por defecto: group_interval + 2 min)",
    )
    parser.add_argument(
        "--override", action="store_true", help="cargar tambien docker-compose.desktop.yml"
    )
    args = parser.parse_args()

    wait_resolution = args.wait_resolution or seconds_to_resolve()
    files = ["-f", "docker-compose.desktop.yml"] if args.override else []
    topic = configured_topic()

    print("Prueba de humo del camino de la alerta")
    print(f"  topic de ntfy      : {topic}")
    print(f"  espera de disparo  : {args.wait} s")
    print(f"  espera de resuelto : {wait_resolution} s")
    print()

    try:
        full_cycle(topic, args.wait, wait_resolution, files)
    except Failure as error:
        print(f"\nFAILED: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpida.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"\nFALLO: no se pudo alcanzar ntfy ni Prometheus: {error}", file=sys.stderr)
        return 1

    print("\nOK: el camino entero de la alerta funciona.")
    print("  la regla dispara -> Alertmanager agrupa -> el puente formatea -> ntfy entrega")
    print("  y las alertas se resuelven cuando el servicio vuelve.")
    return 0
