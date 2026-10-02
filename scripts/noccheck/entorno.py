"""Cada ${VAR} que el compose interpola tiene que estar documentado en .env.example.

Una variable sin documentar es una que nadie pone, y el valor por defecto que se
aplica en su lugar es un sistema de monitorizacion apuntando al sitio equivocado.
Una variable documentada pero que ya no se usa es lo contrario: manda a quien lea
el ejemplo a buscar un ajuste que dejo de importar.
"""

from __future__ import annotations

import pathlib
import re

from .base import COMPOSE, COMPOSE_PARTES, ENV_EXAMPLE, aviso, error

INTERPOLACION = re.compile(r"\$\{([A-Z0-9_]+)[:}]")
DECLARACION = re.compile(r"^([A-Z0-9_]+)=", flags=re.M)


def ficheros_compose() -> list[pathlib.Path]:
    """El índice raíz más cada parte: las variables viven sobre todo en las partes."""
    return [COMPOSE, *COMPOSE_PARTES]


def check_entorno() -> None:
    """Contrasta las variables del compose con el fichero de ejemplo."""
    if not ENV_EXAMPLE.exists() or not COMPOSE.exists():
        error(".env.example o docker-compose.yml no existen")
        return

    usadas = {
        variable
        for ruta in ficheros_compose()
        for variable in INTERPOLACION.findall(ruta.read_text(encoding="utf-8"))
    }
    documentadas = {
        coincidencia.group(1)
        for coincidencia in DECLARACION.finditer(ENV_EXAMPLE.read_text(encoding="utf-8"))
    }

    for nombre in sorted(usadas - documentadas):
        error(f"el compose usa ${{{nombre}}} pero .env.example no lo documenta")
    for nombre in sorted(documentadas - usadas):
        aviso(f".env.example documenta {nombre}, que el compose ya no usa")
