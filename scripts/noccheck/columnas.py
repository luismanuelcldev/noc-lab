"""Las cabeceras de tabla las fija el panel, y un byName que no casa se pierde.

Un panel de tabla pinta una columna por campo, y Grafana le pone un nombre legible
derivado del nombre de la metrica: `scrape_duration_seconds` sale como "Duration of
scrape". Ese nombre lo decide Grafana, no este repositorio, asi que no se puede
exigir que este en espanol y no tiene sentido intentarlo.

Lo que el panel si controla es el `byName` de sus overrides, que son los que
aplican la unidad y los umbrales de cada columna. Y ahi esta el fallo que se cuela
sin quejarse: un `byName` que ya no encuentra su campo deja de aplicar la unidad y
la columna sale en bytes crudos, sin un solo error en ninguna parte.

Por eso la comprobacion no es de idioma sino de coherencia interna: si el panel
declara un override para una columna, esa columna tiene que existir, y solo hay dos
sitios legitimos donde puede venir: la leyenda de un objetivo o el indice de
columnas de una transformacion `organize`. Traducir una leyenda sin tocar el
`byName` que la apuntaba rompe la unidad en silencio, y asi es como se manifesto.
"""

from __future__ import annotations

from typing import Any

from .base import cargados, error, paneles_de

# Columnas cuyo nombre pone Grafana, no este repositorio. `up` trae
# `scrape_duration_seconds` y la tabla lo enseña como "Duration of scrape"; el
# `byName` que le pone la unidad tiene que usar ese nombre literal, asi que no
# se puede traducir sin romperlo. Se listan aqui a proposito: es el sitio donde
# se ve que se ha decidido dejarlos en ingles, en vez de que la lista viva en la
# cabeza de quien lee el panel. Si Grafana cambia su nomenclatura, el fallo sale
# aqui y no como una columna sin unidades.
DE_GRAFANA = frozenset(
    {
        "Duration of scrape",
        "Duration",
        "Value",
        "Time",
        "Uptime",
    }
)


def _columnas_del_panel(panel: dict[str, Any]) -> set[str]:
    """Los nombres de columna que el panel declara de forma explicita.

    Solo los declarados a mano, no los que Grafana deducira de la metrica: un
    nombre deducido no se puede exigir aqui: pertenece a Grafana, no al panel.
    """
    conocidas: set[str] = set()
    for objetivo in panel.get("targets") or []:
        leyenda = str(objetivo.get("legendFormat") or "").strip()
        if leyenda:
            conocidas.add(leyenda)
    for transformacion in panel.get("transformations") or []:
        opciones = transformacion.get("options") or {}
        conocidas.update(str(k) for k in opciones.get("indexByName") or {})
        conocidas.update(str(v) for v in (opciones.get("renameByName") or {}).values())
    return conocidas


def check_byName() -> int:
    """Cada override byName debe apuntar a una columna que el panel declara."""
    total = 0
    for ruta, dashboard in cargados():
        for panel in paneles_de(dashboard):
            donde = f"{ruta.name} / {panel.get('title', '<sin titulo>')}"
            conocidas = _columnas_del_panel(panel)
            overrides = (panel.get("fieldConfig", {}) or {}).get("overrides") or []
            for override in overrides:
                emparejador = override.get("matcher") or {}
                if emparejador.get("id") != "byName":
                    continue
                campo = str(emparejador.get("options") or "").strip()
                if not campo:
                    continue
                total += 1
                if campo in conocidas or campo in DE_GRAFANA:
                    continue
                error(
                    f"{donde}: el override de '{campo}' no encuentra su columna; "
                    "ese nombre no coincide con ninguna leyenda ni con el indice "
                    "de columnas, asi que la unidad no se aplicaria"
                )
    return total
