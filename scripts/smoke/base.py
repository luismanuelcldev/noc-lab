"""Constantes compartidas y las envolturas mas finas posibles sobre HTTP y subprocesos."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import time
import urllib.parse
import urllib.request

# Raiz del repositorio. Este fichero es scripts/smoke/base.py, de ahi parents[2] y
# no el parent.parent que usaba el script plano.
ROOT = pathlib.Path(__file__).resolve().parents[2]

# Direcciones de host. Solo hacen falta las cuatro publicadas en loopback: el
# punto es probar el camino que recorre una persona, no algo que solo existe
# dentro de Docker.
PROMETHEUS = "http://127.0.0.1:9090"
NTFY = "http://127.0.0.1:8085"

# Las dos disparan cuando se para demo-app, y compruebo las dos porque miden cosas
# distintas: la sonda HTTP y el puerto TCP. Que solo dispare una significa que la
# otra sonda no esta mirando lo que cree que mira.
EXPECTED_ALERTS = ("ServicioCaido", "PuertoTCPInaccesible")

FIRING_PATTERN = re.compile(r"\[FIRING\]\s+(\S+)")
RESOLVED_PATTERN = re.compile(r"\[RESOLVED\]\s+(\S+)")
GROUP_INTERVAL_PATTERN = re.compile(r"^\s*group_interval:\s*(\d+)m", re.MULTILINE)

# Holgura para la espera de la resolucion ademas de group_interval, para que un
# primer sondeo lento del grupo no se lea como una resolucion que no llega.
RESOLUTION_GRACE_SECONDS = 120
NO_HEALTHCHECK = "no healthcheck"


class Failure(Exception):
    """Un fallo de la prueba cuyo mensaje dice que hacer a continuacion."""


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def get(url: str, headers: dict[str, str] | None = None) -> str:
    # S310: toda URL de aqui es una direccion local del laboratorio o una consulta
    # a Prometheus construida desde un literal, nunca desde entrada de usuario.
    request = urllib.request.Request(url, headers=headers or {})  # noqa: S310
    with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
        return response.read().decode("utf-8", "replace")


def query(expression: str) -> list[dict]:
    return (
        json.loads(get(f"{PROMETHEUS}/api/v1/query?query={urllib.parse.quote(expression)}"))
        .get("data", {})
        .get("result", [])
    )


def run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    # S603: el comando se construye de literales y de los ficheros compose pasados
    # en la linea de comandos, nunca de texto que llega por la red.
    return subprocess.run(  # noqa: S603
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
