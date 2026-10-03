"""Sintaxis de las expresiones de panel, delegada a promtool.

No se reimplementa aqui un parser de PromQL: promtool tiene el de la version de
Prometheus que ejecuta el laboratorio, y lo unico que aporta este modulo es hacker
las expresiones de los dashboards a la forma que promtool si sabe leer, reglas de
grabacion.

Que caza y que no, para no prometer mas de lo que da:

  - si: parentesis sin cerrar, una funcion que no existe, un selector mal formado.
  - no: una metrica renombrada. `rate(node_network_recieve_bytes[5m])` es PromQL
    valido; solo se ve preguntando a un Prometheus que la tenga: `check-datos`.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from .base import COMPOSE_PARTES, aviso, error

# El nombre de la regla lleva el indice de la expresion: vuelve del error al panel.
PREFIJO = "noccheck_panel_"
FALLO = re.compile(rf'"{PREFIJO}(\d+)": (?:could not parse expression: )?(.*)')
IMAGEN = re.compile(r"image:\s*(prom/prometheus:\S+)")


def imagen_prometheus() -> str:
    """La version de la imagen, leida del compose y no escrita aqui.

    Copiarla seria una cuarta aparicion de la cadena: al subir la version en
    compose/prometheus.yml, este promtool se quedaria en la anterior.
    """
    for parte in COMPOSE_PARTES:
        encontrada = IMAGEN.search(parte.read_text(encoding="utf-8"))
        if encontrada:
            return encontrada.group(1)
    return "prom/prometheus:latest"


def reglas_sinteticas(expresiones: list[str]) -> str:
    """Cada expresion, como regla de grabacion.

    El indice va en el nombre porque un nombre de regla tiene que ser un nombre de
    metrica valido. json.dumps escapa las comillas del valor.
    """
    lineas = ["groups:", "  - name: noccheck", "    rules:"]
    for indice, expr in enumerate(expresiones, start=1):
        lineas.append(f"      - record: {PREFIJO}{indice}")
        lineas.append(f"        expr: {json.dumps(expr)}")
    return "\n".join(lineas) + "\n"


def check_promql() -> int:
    """Valida la sintaxis de cada expresion de panel. Devuelve las revisadas."""
    from .paneles import expresiones

    pares = expresiones()
    if not pares:
        return 0
    with tempfile.TemporaryDirectory() as temporal:
        ruta = Path(temporal) / "expresiones.rules.yml"
        ruta.write_text(reglas_sinteticas([e for _, e in pares]), encoding="utf-8")
        # El temporal nace en 0700 y promtool corre como nobody dentro del contenedor:
        # sin esto su stat falla con "permission denied". En Windows no hay modo, por eso
        # esto solo se ve en la CI. El montaje es del directorio, no del fichero.
        ruta.chmod(0o644)
        ruta.parent.chmod(0o755)
        hecho = _promtool(ruta.parent, ruta.name)
    for indice, detalle in FALLO.findall(hecho):
        error(f"{pares[int(indice) - 1][1]}: {detalle.strip()}")
    return len(pares)


def _promtool(directorio: Path, nombre: str) -> str:
    """Ejecuta `promtool check rules` y devuelve su salida, incluidos los fallos."""
    # La lista se monta en tres trozos porque en una sola no cabe en la linea, y
    # partirla sin concatenacion la devuelve el formateador a un elemento por linea.
    comando = ["docker", "run", "--rm", "--entrypoint", "promtool"]
    comando += ["-v", f"{directorio}:/t:ro", "-w", "/t"]
    comando += [imagen_prometheus(), "check", "rules", nombre]
    try:
        # S603: argumentos escritos aqui, no de entrada. check=False porque el
        # fallo es el caso que hay que leer, no una excepcion.
        hecho = subprocess.run(  # noqa: S603
            comando, capture_output=True, text=True, timeout=180, check=False
        )
    except FileNotFoundError:
        aviso("no se puede ejecutar docker: la sintaxis PromQL no se comprueba")
        return ""
    except subprocess.TimeoutExpired:
        error("la validación de la sintaxis PromQL agotó el tiempo")
        return ""
    salida = (hecho.stderr or "") + (hecho.stdout or "")
    if hecho.returncode and not FALLO.search(salida):
        error(f"promtool no pudo validar las expresiones: {salida.strip()[:200]}")
    return salida
