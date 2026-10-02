"""Comprobaciones estructurales sobre los dashboards de Grafana.

Grafana no valida un dashboard al cargarlo mas alla de parsearlo, asi que los
fallos que importan son los que alguien solo nota a las 3 con un incidente abierto:
un panel que apunta a un datasource inexistente, dos paneles con el mismo id, una
expresion PromQL que no es una cadena.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .base import DATASOURCES, cargados, clave_de, error, paneles_de

EXPRESION_VACIA = re.compile(r"^\s*$")


def uids_conocidos() -> set[str]:
    """UIDs de datasource declarados en el aprovisionamiento, para validar referencias."""
    if not DATASOURCES.exists():
        return set()
    return set(re.findall(r"uid:\s*(\S+)", DATASOURCES.read_text(encoding="utf-8")))


def check_static() -> int:
    """Parsea cada dashboard y valida su estructura. Devuelve los paneles contados."""
    total = 0
    uids = uids_conocidos()

    for path, dashboard in cargados():
        vistos_titulos: set[str] = set()
        vistos_ids: set[str] = set()

        for panel in paneles_de(dashboard):
            total += 1
            titulo = panel.get("title", "<sin titulo>")
            donde = f"{path.name} / {titulo}"

            if titulo in vistos_titulos:
                error(f"{donde}: titulo de panel duplicado")
            vistos_titulos.add(titulo)

            panel_id = str(panel.get("id", ""))
            if panel_id in vistos_ids:
                error(f"{donde}: id de panel duplicado {panel_id}")
            vistos_ids.add(panel_id)

            for target in panel.get("targets") or []:
                expr = target.get("expr")
                if expr is not None and not isinstance(expr, str):
                    error(f"{donde}: expr no es una cadena")
                datasource = (target.get("datasource") or {}).get("uid")
                if datasource and uids and datasource not in uids:
                    error(f"{donde}: uid de datasource desconocido {datasource!r}")

            _comprueba_enlaces_de(donde, panel, uids)

    return total


def _comprueba_enlaces_de(donde: str, panel: dict[str, Any], uids: set[str]) -> None:
    """Un enlace de dashboard sin url ni tags es un desplegable que no lleva a ningun sitio.

    Grafana lo dibuja igual que uno que funciona, asi que parece correcto y no hace
    nada: el operador elige «Ir a...» y vuelve al dashboard que ya tenia delante,
    lo que se lee como «los otros dashboards estan rotos».
    """
    for enlace in panel.get("links") or []:
        if not enlace.get("url") and not enlace.get("tags"):
            error(f"{donde}: enlace '{enlace.get('title')}' sin url ni tags (desplegable muerto)")
        for etiqueta in enlace.get("tags") or []:
            if not str(etiqueta).strip():
                error(f"{donde}: enlace '{enlace.get('title')}' con un tag vacio")


def expresiones() -> list[tuple[str, str]]:
    """Cada par (donde, expr) de cada dashboard, deduplicado por expresion.

    Deduplicar importa: dos paneles que enseñan la misma cifra deberian contarse una
    vez, si no la comprobacion en vivo paga dos veces la misma consulta e informa dos
    veces del mismo problema.
    """
    vistas: dict[str, str] = {}
    for path, dashboard in cargados():
        for panel in paneles_de(dashboard):
            for target in panel.get("targets") or []:
                expr = target.get("expr")
                if not isinstance(expr, str) or EXPRESION_VACIA.match(expr):
                    continue
                clave = json.dumps(expr, sort_keys=True)
                vistas.setdefault(clave, clave_de(path, panel))
    return [(donde, expr) for expr, donde in ((json.loads(k), v) for k, v in vistas.items())]
