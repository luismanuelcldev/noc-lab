"""Los enlaces relativos de Markdown tienen que resolver a un fichero, y a un anchor de dentro.

La documentacion se pudre en silencio: renombrar una seccion o mover un fichero
deja el texto del enlace en su sitio y lleva al lector a un 404 en mitad de un
incidente, que es el peor momento posible para descubrirlo.
"""

from __future__ import annotations

import pathlib
import re

from .base import RAIZ, error

DOCUMENTOS = sorted(RAIZ.glob("*.md")) + sorted((RAIZ / "docs").glob("*.md"))
EXTERNOS = ("http://", "https://", "mailto:")


def check_enlaces() -> int:
    """Devuelve el numero de enlaces relativos revisados."""
    anchors = _anchores()
    revisados = 0
    for documento in DOCUMENTOS:
        texto = documento.read_text(encoding="utf-8")
        for etiqueta, destino in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", texto):
            if destino.startswith(EXTERNOS):
                continue
            revisados += 1
            ruta, _, anchor = destino.partition("#")
            resuelta = (documento.parent / ruta).resolve() if ruta else documento.resolve()
            if not resuelta.exists():
                error(f"{documento.name}: enlace [{etiqueta}] apunta a un fichero inexistente")
            elif anchor and anchor not in anchors.get(resuelta, set()):
                error(f"{documento.name}: enlace [{etiqueta}] apunta a un anchor inexistente")
    return revisados


def _anchores() -> dict[pathlib.Path, set[str]]:
    """Las etiquetas <a id> explicitas mas los slugs que GitHub deduce de los titulos.

    Hacen falta las dos: la documentacion usa etiquetas explicitas para titulos cuyo
    slug seria ambiguo, y enlaces relativos sin fragmento para el resto.
    """
    encontrados: dict[pathlib.Path, set[str]] = {}
    for documento in DOCUMENTOS:
        texto = documento.read_text(encoding="utf-8")
        anchors = set(re.findall(r'<a id="([^"]+)"></a>', texto))
        for heading in re.findall(r"^#{1,6}\s+(.+?)\s*$", texto, flags=re.M):
            slug = re.sub(r"[^\w\s-]", "", heading.lower())
            anchors.add(re.sub(r"\s+", "-", slug.strip()))
        encontrados[documento.resolve()] = anchors
    return encontrados
