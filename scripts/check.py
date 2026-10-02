#!/usr/bin/env python3
"""Lanzador: se queda en esta ruta porque la Makefile, la CI y la documentacion la llaman.

Las comprobaciones viven en el paquete noccheck, junto a este fichero. Esto sigue
siendo un lanzador para que ningun llamante tenga que cambiar y para que el punto
de entrada sea evidente.
"""

from __future__ import annotations

import sys

from noccheck import main

if __name__ == "__main__":
    sys.exit(main())
