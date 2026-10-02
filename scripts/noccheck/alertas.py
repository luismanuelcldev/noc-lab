"""El contrato de alerta: cuatro anotaciones y un anchor de manual que exista de verdad.

Las anotaciones son el contrato entre una regla y la persona que se despierta a las
3 de la madrugada. Una regla sin summary, o con un enlace al manual que apunta a
una seccion renombrada, genera una notificacion sobre la que nadie puede actuar.
La comprobacion del anchor es la que caza el renombrado, porque la URL sigue
respondiendo 200 mientras senala a la pagina equivocada.
"""

from __future__ import annotations

import re

from .base import ALERT_RULES, DASHBOARDS, RUNBOOK, error

CAMPOS = ("summary", "description", "runbook_url", "dashboard_url")


def check_alertas() -> int:
    """Devuelve el numero de alertas con el contrato verificado."""
    if not ALERT_RULES or not RUNBOOK.exists():
        error("rules/*.rules.yml o docs/RUNBOOK.md no existen")
        return 0

    anchors = set(re.findall(r'<a id="([^"]+)"></a>', RUNBOOK.read_text(encoding="utf-8")))
    uids = {ruta.stem for ruta in DASHBOARDS.glob("*.json")}

    total = 0
    for ruta in ALERT_RULES:
        texto = ruta.read_text(encoding="utf-8")
        for bloque in re.split(r"^\s*- alert: ", texto, flags=re.M)[1:]:
            nombre = bloque.splitlines()[0].strip()
            total += 1
            _comprueba_campos(nombre, bloque)
            _comprueba_runbook(nombre, bloque, anchors)
            _comprueba_dashboard(nombre, bloque, uids)
    return total


def _comprueba_campos(nombre: str, bloque: str) -> None:
    for campo in CAMPOS:
        if not re.search(rf"^\s+{campo}:\s*\S", bloque, flags=re.M):
            error(f"alerta {nombre}: sin anotación {campo}")


def _comprueba_runbook(nombre: str, bloque: str, anchors: set[str]) -> None:
    encontrado = re.search(r'^\s+runbook_url:\s*"?([^"\n]+)', bloque, flags=re.M)
    if not encontrado:
        return
    url = encontrado.group(1)
    if "#" not in url:
        error(f"alerta {nombre}: runbook_url sin anchor")
    elif url.rsplit("#", 1)[1] not in anchors:
        error(f"alerta {nombre}: runbook_url apunta a un anchor que no existe en RUNBOOK")


def _comprueba_dashboard(nombre: str, bloque: str, uids: set[str]) -> None:
    encontrado = re.search(r'^\s+dashboard_url:\s*"?([^"\n]+)', bloque, flags=re.M)
    if not encontrado:
        return
    uid = re.search(r"/d/([A-Za-z0-9_-]+)", encontrado.group(1))
    if uid and uid.group(1) not in uids:
        error(f"alerta {nombre}: dashboard_url apunta a un dashboard desconocido {uid.group(1)!r}")
