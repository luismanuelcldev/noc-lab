"""Comprobaciones que necesitan un stack en marcha: expresiones vivas, recordings muertos, vacios.

Un panel que muestra "No data" es indistinguible, desde fuera, de un panel que
muestra un cero sano. Ese es el fallo para el que existe este modulo: una metrica
renombrada deja la expresion valida y el panel en blanco, y nada lo dice.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from .base import ALERT_RULES, aviso, cargados, clave_de, dashboards, error, paneles_de

# Paneles cuyo vacio ES el estado sano, y que significa ese vacio.
# Clave "<uid> / <titulo>", el mismo formato que clave_de(). El registro se comprueba
# en los dos sentidos en cada ejecucion: una entrada que ya no corresponde a un panel
# real es un error, porque una lista blanca caducada deja de proteger el panel para el
# que se escribio y el siguiente resultado vacio se descarta como "ya estaba anotado".
VACIOS_ESPERADOS: dict[str, str] = {
    "noc-equipo-disco / Sistemas de archivos en solo lectura": "vacío = ninguno en solo lectura",
    "noc-equipo-red-reloj / Reinicios del equipo": "vacío = ningún reinicio en 15 minutos",
}

REGISTRO_RECORDING = re.compile(r"^\s*- record:\s*(\S+)", flags=re.M)


def check_expresiones(prometheus: str) -> int:
    """Ejecuta cada expresion de panel y reporta rechazos y vacios."""
    from .paneles import expresiones  # import local: mantiene plano el grafo

    revisadas = 0
    for donde, expr in expresiones():
        revisadas += 1
        url = f"{prometheus}/api/v1/query?query={urllib.parse.quote(expr)}"
        try:
            # S310: la URL se construye con una direccion local de Prometheus y una
            # consulta leida de nuestros propios dashboards, no de entrada externa.
            with urllib.request.urlopen(url, timeout=15) as respuesta:  # noqa: S310
                payload = json.load(respuesta)
        except urllib.error.HTTPError as exc:
            detalle = exc.read().decode("utf-8", "replace")[:200]
            error(f"{donde}: Prometheus rechazó la expresión -> {detalle}")
            continue
        except OSError as exc:
            error(f"no se puede contactar con {prometheus}: {exc}")
            return revisadas

        if payload.get("status") != "success":
            error(f"{donde}: {payload.get('error', 'error desconocido')}")
        elif not payload.get("data", {}).get("result"):
            _informa_vacio(donde)
    return revisadas


def _informa_vacio(donde: str) -> None:
    """Un vacio esperado no avisa; uno inesperado, si. Y al reves de lo obvio.

    El comportamiento correcto de estos paneles ES estar vacios, asi que avisar de
    ello era avisar de que todo va bien: con --strict eso es un fallo permanente y el
    flag quedaba sin usar. Un vacio inesperado avisa, y ese es justo el fallo que
    cazan --strict y la CI: una metrica renombrada deja la expresion valida y el
    panel en blanco. El motivo del vacio esperado se imprime igual, sin entrar en el
    recuento de avisos, para que el informe siga explicando por que esta en blanco.
    """
    motivo = VACIOS_ESPERADOS.get(donde)
    if motivo is None:
        aviso(f"{donde}: sin datos y no está en la lista de vacíos esperados")
    else:
        print(f"  (vacío esperado) {donde}: {motivo}")


def check_registro_vacio() -> None:
    """Cada entrada de VACIOS_ESPERADOS debe seguir apuntando a un panel real."""
    existentes = set()
    for path, dashboard in cargados():
        for panel in paneles_de(dashboard):
            existentes.add(clave_de(path, panel))
    for clave in VACIOS_ESPERADOS:
        if clave not in existentes:
            error(f"VACIOS_ESPERADOS[{clave!r}] ya no corresponde a ningún panel")


def check_recordings_usadas() -> int:
    """Cada recording rule debe ganarse el coste que paga alimentando un panel.

    Una recording rule se evalúa segun su intervalo lea o no la nadie, asi que una
    que no referencia nadie es gasto puro con apariencia de sistema funcionando.
    """
    texto = "\n".join(p.read_text(encoding="utf-8") for p in dashboards())
    total = 0
    for ruta in ALERT_RULES:
        for nombre in REGISTRO_RECORDING.findall(ruta.read_text(encoding="utf-8")):
            total += 1
            if nombre not in texto:
                error(f"recording rule {nombre} ({ruta.name}) no la usa ningún panel")
    return total
