"""La leyenda de cada serie tambien se lee, y tambien tiene que estar en espanol.

Una leyenda es la etiqueta que Grafana pinta junto a la linea de una serie, asi que
es texto de la misma condicion que un titulo: lo lee una persona mirando el
panel. No estaba cubierta porque `legendFormat` se asumia como un identificador,
y durante un tiempo lo fue: `rules`, `uptime` y `self` eran nombres razonables
para un identificador y al mismo tiempo ingles en pantalla.

La distincion que hace falta es entre una leyenda y un identificador, no entre
dos tipos de cadena:

- Una leyenda que solo lleva la plantilla `{{etiqueta}}` no dice nada: el
  contenido lo pone Grafana con el nombre de la etiqueta, que es un
  identificador y se queda como este.
- Una leyenda con palabras sueltas (`rules`, `uptime`) si es prosa, y la prosa
  se traduce.
- Los nombres propios y los protocolos (`tsdb`, `prometheus`, `http`, `tcp`) no
  son prosa: son como se escribe el nombre, y traducirlos no los hace mas
  claros. Se listan a proposito en NOMBRES_PROPIOS, y mantener esa lista cuando
  aparezca uno nuevo es el coste que evita traducir `tcp` a `tcp` por reflejo.

Va en su propio modulo y no en grafana.py porque ese ya esta a 98 de 100 lineas
del presupuesto, y porque esto es la regla de idioma igual que lo es un titulo.
"""

from __future__ import annotations

import re

from .base import cargados, paneles_de
from .palabras import check_ingles

# Nombres que se escriben asi en cualquier idioma. No son prosa, son el nombre.
NOMBRES_PROPIOS = frozenset(
    {
        "alertmanager",
        "cadvisor",
        "cpu",
        "dns",
        "grafana",
        "http",
        "https",
        "ip",
        "json",
        "ntfy",
        "ntp",
        "oom",
        "prometheus",
        "promql",
        "ram",
        "ssh",
        "tcp",
        "tsdb",
        "udp",
        "veth",
        "wsl",
        "yaml",
    }
)


def es_prosa(leyenda: str) -> bool:
    """Si una leyenda es texto nuestro o solo un identificador que se muestra.

    La plantilla y los nombres propios se quitan antes de mirar, porque son las
    dos cosas que hacen que una leyenda sea prosa sin que haya que traducirla:
    `{{etiqueta}}` es un identificador, y `prometheus` se escribe asi en todos los
    idiomas. Si despues de quitarlas queda algo, es prosa y se revisa.

    El orden importa. Antes se devolvia False en cuanto aparecia una plantilla,
    lo que hacia que `{{instancia}} uptime` se escapara de la revision con el
    "uptime" en ingles a la vista: la plantilla ocultaba el resto de la leyenda.
    """
    sin_plantilla = re.sub(r"\{\{[^}]*\}\}", " ", leyenda)
    minuscula = sin_plantilla.lower()
    for nombre in NOMBRES_PROPIOS:
        minuscula = minuscula.replace(nombre, " ")
    return bool(minuscula.strip(" .,-_/"))


def check_leyendas() -> int:
    """Revisa las leyendas de serie de todos los paneles. Devuelve los textos."""
    total = 0
    for ruta, dashboard in cargados():
        for panel in paneles_de(dashboard):
            donde = f"{ruta.name} / {panel.get('title', '<sin titulo>')}"
            for objetivo in panel.get("targets") or []:
                leyenda = str(objetivo.get("legendFormat") or "").strip()
                if not leyenda:
                    continue
                total += 1
                if es_prosa(leyenda):
                    check_ingles(f"{donde} / leyenda", leyenda)
    return total
