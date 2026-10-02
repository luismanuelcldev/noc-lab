"""La regla de idioma de Prometheus y Alertmanager, y el punto de entrada conjunto.

Que se revisa aqui y por que no se extiende mas: en Prometheus el unico texto que
lee una persona es el summary de una alerta y su description, y en Alertmanager son
los nombres de receptor y de ruta. Los nombres de metrica, de etiqueta y de job son
identificadores referenciados desde consultas, asi que traducirlos romperia cada
expresion que los nombra, y nadie lo pidio.
"""

from __future__ import annotations

import re

from .base import ALERT_RULES, RAIZ, error
from .palabras import check_ingles

RECEIVER = re.compile(r'^\s*receiver:\s*"?([^"\n]+)"?', flags=re.M)
ROUTE_ID = re.compile(r'^\s*route_id:\s*"?([^"\n]+)"?', flags=re.M)
CAMPO = re.compile(r"^\s*(summary|description):\s*(.*)$")
# Un \" dentro de una cadena entrecomillada es un escape, no el final de la cadena.
# Sin esto el valor se corta en el primer \" y el resto del texto pasa sin revisar.
DOBLES = re.compile(r'"((?:[^"\\]|\\.)*)"')
SIMPLES = re.compile(r"'((?:[^']|'')*)'")
ALERTMANAGER = RAIZ / "alertmanager.yml"


def valor_de(linea: str) -> str | None:
    """La cadena que guarda un escalar YAML de una linea, con sus escapes resueltos."""
    coincidencia = CAMPO.match(linea)
    if not coincidencia:
        return None
    resto = coincidencia.group(2)
    if resto.startswith('"'):
        encontrado = DOBLES.match(resto)
        return re.sub(r"\\(.)", r"\1", encontrado.group(1)) if encontrado else None
    if resto.startswith("'"):
        encontrado = SIMPLES.match(resto)
        return encontrado.group(1).replace("''", "'") if encontrado else None
    return resto.split("#", 1)[0].strip() or None


def check_prometheus() -> int:
    """Summaries y descripciones de alerta: el texto que llega a un movil a las 3."""
    total = 0
    for ruta in ALERT_RULES:
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if not CAMPO.match(linea):
                continue
            valor = valor_de(linea)
            if valor is None:
                error(f"{ruta.name}:{numero}: summary/description no es un escalar de una línea")
                continue
            total += 1
            check_ingles(f"{ruta.name} / {CAMPO.match(linea).group(1)}", valor)
    return total


def check_alertmanager() -> int:
    """Nombres de receptor y de ruta, que es lo que lista la interfaz de Alertmanager."""
    if not ALERTMANAGER.exists():
        return 0
    total = 0
    texto = ALERTMANAGER.read_text(encoding="utf-8")
    for patron, etiqueta in ((RECEIVER, "receiver"), (ROUTE_ID, "route_id")):
        for valor in patron.findall(texto):
            total += 1
            check_ingles(f"alertmanager.yml / {etiqueta} ({valor})", valor)
    return total


def check_todo() -> int:
    """Todas las comprobaciones de idioma de los tres sistemas. Devuelve los textos."""
    from . import grafana, leyendas

    return (
        grafana.check_dashboards()
        + grafana.check_enlaces_de_paneles()
        + grafana.check_provisioning()
        + leyendas.check_leyendas()
        + check_prometheus()
        + check_alertmanager()
    )
