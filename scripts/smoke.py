#!/usr/bin/env python3
"""Lanzador: se queda en esta ruta porque la Makefile y la documentacion la llaman.

La prueba vive en el paquete smoke, junto a este fichero, con la misma forma que
check.py y su paquete noccheck. Esto sigue siendo un lanzador para que ningun
llamante tenga que cambiar y para que el punto de entrada sea evidente.
"""

from __future__ import annotations

import sys

from smoke.cli import main

if __name__ == "__main__":
    sys.exit(main())
