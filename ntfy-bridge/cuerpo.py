"""El cuerpo del mensaje: lo que se lee de verdad cuando suena el movil.

Decisiones que salen de como se lee una alerta de noche:

* Una notificacion por grupo, no por alerta: si un despliegue tumba 40 pods, el
  operador quiere un mensaje con 40 lineas, no 40 vibraciones.
* Los enlaces viajan dentro del cuerpo, porque una notificacion de movil no
  tiene botones y el operador no deberia tener que ir a buscar el panel.
* El cuerpo tiene tope, y el tope anuncia el numero exacto de alertas que se
  dejan fuera. Cortar en silencio dejaria cerrar el incidente al operador
  habiendo leido 8 de 40.

Los rotulos se alinean con ljust y no con espacios a mano, porque alinear a mano
fue el bug que arrastraba este par de ficheros: un rotulo un caracter mas largo
desplaza su dos puntos y no se nota hasta que alguien lo lee de noche.
"""

from __future__ import annotations

import ajuste

ANCHO = 9  # en espanol los mas largos son servicio, detalles y detectado
ROTULOS = (
    ("summary", "resumen"),
    ("description", "detalles"),
    ("runbook_url", "runbook"),
    ("dashboard_url", "dashboard"),
)


def linea(rotulo: str, valor: str) -> str:
    """Un renglon `  rotulo : valor` con todos los dos puntos en la misma columna."""
    return f"  {rotulo.ljust(ANCHO)} : {valor}"


def describe(alert: dict) -> str:
    """Dibujar una alerta como el bloque rotulado que lee el de turno."""
    labels = alert.get("labels") or {}
    notes = alert.get("annotations") or {}
    lineas = [
        f"[{str(alert.get('status', 'firing')).upper()}] "
        f"{labels.get('alertname', 'AlertaDesconocida')}",
        linea("gravedad", labels.get("severity", "none")),
        linea("servicio", labels.get("service", "sin-servicio")),
        linea("destino", labels.get("instance", "sin-destino")),
    ]
    for clave, rotulo in ROTULOS:
        if notes.get(clave):
            lineas.append(linea(rotulo, notes[clave]))
    if alert.get("startsAt"):
        lineas.append(linea("detectado", alert["startsAt"]))
    return "\n".join(lineas)


def _aviso(mostradas: int, total: int) -> str:
    """El texto que anuncia cuantas alertas se han quedado fuera."""
    return (
        f"\n\n[Recortado para que quepa en el canal: {mostradas} de {total} "
        f"alertas mostradas. Las otras {total - mostradas} estan en Alertmanager.]"
    )


def compose_body(alerts: list[dict], resolved: bool) -> str:
    """Montar el cuerpo del mensaje, recortando solo si no cabe en el canal.

    El recorte anuncia el numero exacto de alertas que se pierden. Cortar en
    silencio dejaria al operador cerrar el incidente habiendo leido 8 de 40.
    """
    header = f"{'RESOLVED' if resolved else 'ACTIVE'} | {len(alerts)} alerta(s)"
    blocks = [describe(a) for a in alerts]
    # La reserva se mide con el aviso de verdad y no con un 90 a ojo. En espanol
    # el aviso es mas largo que en ingles, y una constante que no se recalcula
    # sola deja el cuerpo dos caracteres por encima del tope sin que se note.
    cifras = len(str(max(len(blocks), 1)))
    reserva = len(_aviso(int("9" * cifras), int("9" * cifras)))
    # Los dos saltos de linea entre cabecera, separador y bloques tambien cuentan,
    # y antes no se contaban: el 90 a ojo traia de sobra justo lo que faltaba.
    esqueleto = len(header) + len(ajuste.SEPARATOR) + 2
    budget = ajuste.MAX_MESSAGE_CHARS - esqueleto - reserva
    shown, used = [], 0
    for block in blocks:
        if used + len(block) > budget:
            break
        shown.append(block)
        used += len(block)
    body = header + "\n" + ajuste.SEPARATOR + "\n" + "\n\n".join(shown or blocks[:1])
    if len(shown) < len(blocks):
        body += _aviso(len(shown), len(blocks))
    # Ultimo recurso: un emoji puede contar como un caracter y dibujarse como
    # dos, asi que el tope duro sigue aplicando. El limite del canal no se negocia.
    # El corte va a cap - 3 porque los puntos son parte del cuerpo: con cap - 1 el
    # resultado podia acabar en cap + 2, y ntfy contesta 400 a un cuerpo de mas.
    cap = ajuste.MAX_MESSAGE_CHARS
    return body if len(body) <= cap else body[: cap - 3].rstrip() + "..."
