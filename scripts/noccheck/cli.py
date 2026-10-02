"""Punto de entrada de la linea de comandos: un informe, un codigo de salida.

Ejecuta todas las comprobaciones y las resume en una sola pasada.

python scripts/check.py                        # solo lo estatico
python scripts/check.py --prometheus http://localhost:9090
python scripts/check.py --strict                # los avisos pasan a ser errores
python scripts/check.py --solo estilo idioma   # una seccion cada vez
"""

from __future__ import annotations

import argparse

from . import alertas as mod_alertas
from . import columnas as mod_columnas
from . import config as mod_config
from . import datos as mod_datos
from . import enlaces as mod_enlaces
from . import entorno as mod_entorno
from . import estilo as mod_estilo
from . import grafana as mod_grafana
from . import idioma as mod_idioma
from . import paneles as mod_paneles
from . import promql as mod_promql
from .base import avisos, errores

# Una linea y no una tupla partida: el formateador devuelve a un elemento por linea
# cualquier coleccion que no quepa, y esta se queda en nueve.
SECCIONES = "paneles alertas enlaces entorno config estilo idioma promql datos".split()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida el proyecto: estructura, contrato de alertas, enlaces, datos y estilo."
    )
    parser.add_argument(
        "--prometheus",
        default="",
        help="URL de un Prometheus vivo, activa la comprobación de datos",
    )
    parser.add_argument("--strict", action="store_true", help="tratar los avisos como errores")
    parser.add_argument(
        "--solo",
        nargs="+",
        choices=SECCIONES,
        metavar="SECCION",
        help=f"ejecutar solo estas secciones: {' '.join(SECCIONES)}",
    )
    args = parser.parse_args()

    activas = set(args.solo or SECCIONES)
    quiere_datos = "datos" in activas

    if "paneles" in activas:
        total = mod_paneles.check_static()
        print(f"  {total} paneles inspeccionados")
    if "alertas" in activas:
        print(f"  {mod_alertas.check_alertas()} alertas con contrato completo")
    if "enlaces" in activas:
        print(f"  {mod_enlaces.check_enlaces()} enlaces entre documentos")
    if "entorno" in activas:
        mod_entorno.check_entorno()
    if "estilo" in activas:
        ficheros = mod_estilo.check_lineas()
        print(f"  {ficheros} ficheros dentro del presupuesto de {mod_estilo.MAX_LINEAS} líneas")
    if "idioma" in activas:
        print(f"  {mod_idioma.check_todo()} textos visibles revisados")
        mod_grafana.check_destinos_de_enlaces()
        mod_columnas.check_byName()
    if "config" in activas:
        mod_config.check_config()
    if "promql" in activas:
        print(f"  {mod_promql.check_promql()} expresiones con sintaxis PromQL válida")
    if quiere_datos:
        mod_datos.check_registro_vacio()
        # El recuento es de reglas revisadas; las huérfanas se informan como error.
        print(f"  {mod_datos.check_recordings_usadas()} recording rules revisadas")
        if args.prometheus:
            print(f"  {mod_datos.check_expresiones(args.prometheus)} expresiones ejecutadas")

    _informe(args.strict)
    return 1 if errores else (1 if args.strict and avisos else 0)


def _informe(strict: bool) -> None:
    for mensaje in avisos:
        print(f"  AVISO  {mensaje}")
    for mensaje in errores:
        print(f"  ERROR  {mensaje}")
    if errores:
        print(f"FALLO: {len(errores)} error(es), {len(avisos)} aviso(s)")
    elif strict and avisos:
        print(f"FALLO (estricto): {len(avisos)} aviso(s)")
    else:
        print(f"OK: {len(avisos)} aviso(s)")
