"""Todo lo que el operador lee en Grafana: titulos, tooltips, carpeta y datasources.

Grafana es donde la exigencia de español aprieta más, porque aquí el texto no es
una notificación: es la superficie de trabajo entera, la lista de dashboards, las
cabeceras de los paneles y el tooltip que debería explicar para qué sirve un panel.
"""

from __future__ import annotations

import re

from .base import CARPETA_GRAFANA, DATASOURCES, cargados, error, paneles_de
from .palabras import check_ingles

NOMBRE = re.compile(r'^\s*name:\s*"?([^"\n]+)"?', flags=re.M)


def check_dashboards() -> int:
    """Títulos, tooltips y textos de mapping. Devuelve los textos revisados."""
    total = 0
    for ruta, dashboard in cargados():
        total += 1
        check_ingles(f"{ruta.name} / título del dashboard", dashboard.get("title", ""))
        for panel in paneles_de(dashboard):
            total += 2
            donde = f"{ruta.name} / {panel.get('title', '<sin titulo>')}"
            check_ingles(f"{donde} / título", panel.get("title", ""))
            check_ingles(f"{donde} / descripción", panel.get("description", ""))
            total += _mappings(panel, f"{donde} / valor")
        total += _enlaces_de_nivel(dashboard, f"{ruta.name} / enlace del dashboard")
    return total


def _mappings(panel: dict, donde: str) -> int:
    """Los textos de mapping se pintan DENTRO del panel: son tan visibles como el título."""
    total = 0
    mappings = (panel.get("fieldConfig", {}).get("defaults", {}) or {}).get("mappings") or []
    for mapping in mappings:
        for valor in (mapping.get("options") or {}).values():
            if isinstance(valor, dict) and valor.get("text"):
                total += 1
                check_ingles(donde, valor["text"])
    return total


def _enlaces_de_nivel(cont: dict, donde: str) -> int:
    total = 0
    for enlace in cont.get("links") or []:
        total += 1
        check_ingles(donde, enlace.get("title", ""))
    return total


def check_enlaces_de_paneles() -> int:
    """Etiquetas de los enlaces de panel, que viven dentro del panel y no arriba."""
    total = 0
    for ruta, dashboard in cargados():
        for panel in paneles_de(dashboard):
            total += _enlaces_de_nivel(panel, f"{ruta.name} / {panel.get('title', '<sin titulo>')}")
    return total


def check_destinos_de_enlaces() -> None:
    """Un enlace de tipo 'dashboards' navega por tags, no por URL.

    Los cuatro dashboards originales traían el enlace «Go to...» con tags: [] y
    url: "", que Grafana acepta sin queja y renderiza como un desplegable vacío.
    Nada falla, nada se ve, y el enlace queda muerto para siempre. Comprobar que
    las tags del enlace coinciden con las de algún dashboard convierte ese fallo
    silencioso en un error el primer día.
    """
    existentes: set[str] = set()
    for _, dashboard in cargados():
        existentes.update(str(t) for t in dashboard.get("tags") or [])
    for ruta, dashboard in cargados():
        for enlace in dashboard.get("links") or []:
            if enlace.get("type") != "dashboards":
                continue
            tags = [str(t) for t in enlace.get("tags") or []]
            if not tags:
                error(f"{ruta.name}: enlace de navegación sin tags, el desplegable sale vacío")
            elif not set(tags) & existentes:
                error(f"{ruta.name}: las tags {tags} no coinciden con ningún dashboard")


def check_provisioning() -> int:
    """La carpeta de Grafana y los nombres de datasource, también en pantalla."""
    total = 0
    if CARPETA_GRAFANA.exists():
        texto = CARPETA_GRAFANA.read_text(encoding="utf-8")
        for valor in re.findall(r'^\s*folder:\s*"?([^"\n]+)"?', texto, flags=re.M):
            total += 1
            check_ingles(f"dashboards.yml / carpeta ({valor})", valor)
    if DATASOURCES.exists():
        for valor in NOMBRE.findall(DATASOURCES.read_text(encoding="utf-8")):
            total += 1
            check_ingles(f"datasources.yml / datasource ({valor})", valor)
    return total
