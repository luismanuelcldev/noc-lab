"""Lo que se puede decidir de un lote entrante sin tocar la red.

Son las tres preguntas que se responden antes de mirar un socket: el token es válido,
este cuerpo es aceptable y qué código hay que devolver. app.py queda solo como
transporte, así que los casos interesantes se prueban sin arrancar un servidor.
"""

from __future__ import annotations

import hmac
import json

import ajuste

# Cuerpos de error, indexados por el estado que el transporte debe usar.
ERRORES = {
    413: {"error": "cuerpo demasiado grande"},
    400: {"error": "se esperaba un objeto JSON"},
}


def autorizado(header: str) -> bool:
    """Comprueba el token bearer cuando hay uno configurado.

    compare_digest en vez de == porque una comparación a secas filtra información de
    tiempo. Sin BRIDGE_TOKEN la comprobación se salta, para este laboratorio interno.
    """
    if not ajuste.BRIDGE_TOKEN:
        return True
    if not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].strip(), ajuste.BRIDGE_TOKEN)


def leer(cuerpo: bytes) -> tuple[dict | None, int]:
    """Valida el cuerpo crudo de la petición. Devuelve (carga, estado); 0 va bien.

    413 y 400 son los dos finales para Alertmanager: no debe reintentar un
    cuerpo que nunca podrá aceptarse, o el grupo se reenviaría para siempre.
    """
    if len(cuerpo) > ajuste.MAX_BODY_BYTES:
        return None, 413
    try:
        payload = json.loads(cuerpo or b"{}")
    except json.JSONDecodeError:
        return None, 400
    if not isinstance(payload, dict):
        return None, 400
    return payload, 0
