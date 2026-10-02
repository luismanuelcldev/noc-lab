"""El presupuesto de lineas, aplicado por maquina y no por revision.

La convencion de que ningun fichero pasa de 100 lineas era una costumbre. Es
decirlo en un CONTRIBUTING y confiar en que se respete durante un tiempo no
funciona: el fichero crece un dia, luego otro, y cuando llega el dia de partirlo
en dos ya nadie recuerda por que estaba entero. Automatizarlo es la unica forma
de que la regla sobreviva a la persona que la escribio.

La regla de idioma vive aparte, en palabras.py, y no aqui. Son dos motivos
distintos con costas distintas, y juntas no cabian en 100 lineas.

Lo que se excluye, y el motivo de cada exclusion:

    *.md   la documentacion crece por explicacion, no por codigo
    *.mo   los ficheros traducidos los genera una herramienta externa
    *.lock los genera una herramienta externa y no los revisa nadie
    LICENSE  es texto legal, no mio

Los directorios excluidos son de herramientas, no codigo: .git es el
repositorio, el resto son cachés y entornos virtuales.

Que el presupuesto se cumpla no significa que el fichero este bien partido.
Solo significa que nadie ha anadido 400 lineas de golpe sin que nadie lo viera.
"""

from __future__ import annotations

from .base import RAIZ, error

MAX_LINEAS = 100

EXCLUIDOS_SUFIJO = {".md", ".mo", ".po", ".lock"}
EXCLUIDOS_NOMBRE = {"LICENSE"}
EXCLUIDOS_DIR = {".git", ".ruff_cache", ".pytest_cache", "__pycache__", ".venv"}


def ficheros_de_codigo():
    """Cada fichero del proyecto al que se le aplica el presupuesto, en orden estable."""
    for ruta in sorted(RAIZ.rglob("*")):
        if not ruta.is_file():
            continue
        relative = ruta.relative_to(RAIZ)
        if any(parte in EXCLUIDOS_DIR for parte in relative.parts):
            continue
        if ruta.suffix in EXCLUIDOS_SUFIJO or ruta.name in EXCLUIDOS_NOMBRE:
            continue
        yield relative, ruta


def check_lineas() -> int:
    """Ningun fichero por encima del presupuesto. Devuelve los ficheros inspeccionados."""
    total = 0
    for relative, ruta in ficheros_de_codigo():
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue  # binario, no es codigo
        total += 1
        if len(lineas) > MAX_LINEAS:
            error(f"{relative}: {len(lineas)} lineas (presupuesto {MAX_LINEAS})")
    return total
