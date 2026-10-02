"""La superficie HTTP del puente: tres endpoints y sus codigos de estado.

Solo transporte. Que hacer con un lote se decide en webhook.py, asi que cada
rama aqui es o "enrutalo" o "responde con un codigo que haga que Alertmanager
se comporte bien", y las dos se prueban sin arrancar un servidor.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler

import ajuste
import webhook
from validacion import ERRORES, autorizado, leer
from webhook import METRICS

LOG = logging.getLogger("ntfy-bridge")


class Handler(BaseHTTPRequestHandler):
    """Enruta los endpoints y convierte los resultados en etiquetas de metrica.

    Cada rama registra exactamente un resultado de peticion, porque el panel y
    la alerta CanalNotificacionCaido leen esos contadores: una peticion que no
    se cuenta ni como ok ni como rejected es un punto ciego que nadie notaria.
    """

    server_version = "ntfy-bridge/2.0"
    protocol_version = "HTTP/1.1"

    def reply(self, code: int, body: str, content_type: str = "application/json") -> None:
        """Envia una respuesta completa con Content-Length explicito.

        La longitud es obligatoria: con HTTP/1.1 y keep-alive, una respuesta
        sin ella hace que el cliente espere un cuerpo que no llega nunca.
        """
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        """Sirve salud, disponibilidad y metricas. Todo lo demas es un 404."""
        METRICS.record_request("ok")
        if self.path == "/healthz":
            self.reply(200, json.dumps({"status": "ok", "service": "ntfy-bridge"}))
        elif self.path == "/readyz":
            # Disponibilidad, no vivacidad: es otra pregunta que "esta arriba".
            self.reply(200, json.dumps({"status": "ready", "sinks": ["ntfy"]}))
        elif self.path == "/metrics":
            self.reply(200, METRICS.render(), "text/plain; version=0.0.4")
        else:
            self.reply(404, json.dumps({"error": "no encontrado"}))

    def do_POST(self) -> None:
        """Acepta un lote de Alertmanager y lo reenvia a ntfy.

        Los codigos de estado sostienen peso, no son decoracion: 502 es lo que
        hace que Alertmanager reintente el grupo, y 413/400 lo detienen de
        reintentar una peticion que nunca puede funcionar.
        """
        if self.path.split("?")[0] != "/webhook":
            METRICS.record_request("rejected")
            self.reply(404, json.dumps({"error": "no encontrado"}))
            return
        if not autorizado(self.headers.get("Authorization", "")):
            METRICS.record_request("rejected")
            LOG.warning("webhook rechazado: token invalido desde %s", self.client_address[0])
            self.reply(401, json.dumps({"error": "no autorizado"}))
            return

        # Un cuerpo sobredimensionado no se lee en absoluto: leerlo dejaria a
        # un emisor decidir cuanto reserva el proceso.
        length = int(self.headers.get("Content-Length") or 0)
        cuerpo = self.rfile.read(length) if length <= ajuste.MAX_BODY_BYTES else b""
        carga, error = leer(cuerpo)
        if carga is None:
            METRICS.record_request("rejected")
            self.reply(error, json.dumps(ERRORES[error]))
            return

        estado, etiqueta, respuesta = webhook.procesar(carga)
        METRICS.record_request(etiqueta)
        self.reply(estado, json.dumps(respuesta))

    def log_message(self, fmt: str, *args: object) -> None:
        """Manda el log de acceso de la clase base a DEBUG en vez de a stderr.

        El de por defecto escribe una linea por peticion a stderr, que a nivel
        INFO entierra las lineas de entrega que si importan.
        """
        LOG.debug("%s - %s", self.client_address[0], fmt % args)
