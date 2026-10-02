"""Estado compartido, rutas y ayudas para los validadores del proyecto.

Todos los módulos de aqui informan por los mismos dos acumuladores, para que la
CLI ordene la salida y decida el codigo de salida en un unico sitio en vez de que
cada comprobacion invente el suyo.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent

GRAFANA = RAIZ / "grafana"
DASHBOARDS = GRAFANA / "dashboards"
DATASOURCES = GRAFANA / "provisioning" / "datasources" / "datasources.yml"
CARPETA_GRAFANA = GRAFANA / "provisioning" / "dashboards" / "dashboards.yml"

RULES = RAIZ / "rules"
ALERT_RULES = sorted(RULES.glob("*.rules.yml"))

COMPOSE = RAIZ / "docker-compose.yml"
# El compose raíz solo hace de índice: cada servicio vive en compose/<servicio>.yml.
COMPOSE_PARTES = sorted((RAIZ / "compose").glob("*.yml"))
ENV_EXAMPLE = RAIZ / ".env.example"
RUNBOOK = RAIZ / "docs" / "RUNBOOK.md"

errores: list[str] = []
avisos: list[str] = []


def error(msg: str) -> None:
    errores.append(msg)


def aviso(msg: str) -> None:
    avisos.append(msg)


def paneles_de(dashboard: dict[str, Any]):
    """Genera cada panel, bajando a las filas plegadas."""
    for panel in dashboard.get("panels", []):
        yield panel
        if panel.get("type") == "row":
            yield from paneles_de(panel)


def clave_de(path: pathlib.Path, panel: dict[str, Any]) -> str:
    """Como se nombra un panel en cada mensaje y en VACIOS_ESPERADOS.

    Se construye en un solo sitio a proposito: la comprobacion en vivo y el registro
    que autoriza los paneles que se esperan vacios tienen que ponerse de acuerdo, y
    dos grafias de la misma clave hacian que un panel autorizado se informara como
    inesperado en cada pasada.
    """
    return f"{path.stem} / {panel.get('title', '<sin titulo>')}"


def dashboards() -> list[pathlib.Path]:
    """Cada fichero de dashboard, en un orden estable para que la salida no se baraje."""
    return sorted(DASHBOARDS.glob("*.json"))


def cargados() -> list[tuple[pathlib.Path, dict[str, Any]]]:
    """Parsea cada dashboard e informa de los que no son JSON valido.

    Un dashboard que no parsea se salta en vez de ser fatal: las comprobaciones
    estructurales siguen corriendo sobre el resto, asi que un fichero roto no
    esconde todo lo demas que este mal.
    """
    out: list[tuple[pathlib.Path, dict[str, Any]]] = []
    for path in dashboards():
        try:
            out.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except json.JSONDecodeError as exc:
            error(f"{path.name}: JSON no valido ({exc})")
    return out
