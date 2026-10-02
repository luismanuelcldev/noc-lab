"""Pruebas de la entrega a ntfy, contra un servidor falso que registra el POST."""

from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import ajuste
from entrega import deliver


class FakeNtfy(BaseHTTPRequestHandler):
    """Registra lo que envía el puente y responde con un estado preparado.

    Estado a nivel de clase a propósito: el manejador corre en el hilo del
    servidor, así que el registro tiene que vivir donde el hilo de prueba también
    pueda leerlo.
    """

    received: ClassVar[list[dict]] = []
    statuses: ClassVar[list[int]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        FakeNtfy.received.append(json.loads(self.rfile.read(length)))
        self.send_response(FakeNtfy.statuses.pop(0) if FakeNtfy.statuses else 200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_args: object) -> None:
        pass


class DeliverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeNtfy)
        cls.server.daemon_threads = True
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        ajuste.NTFY_URL = f"http://127.0.0.1:{cls.server.server_address[1]}"
        ajuste.NTFY_TOPIC = "noc-alerts"
        ajuste.BACKOFF_BASE = 0.01

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def setUp(self) -> None:
        FakeNtfy.received.clear()
        FakeNtfy.statuses.clear()

    def test_successful_delivery_reports_one_attempt(self) -> None:
        ok, attempts, duration = deliver("t", "b", 5, ["warning"], "http://am")
        self.assertTrue(ok)
        self.assertEqual(attempts, 1)
        self.assertGreaterEqual(duration, 0.0)
        self.assertEqual(FakeNtfy.received[0]["topic"], "noc-alerts")
        self.assertEqual(FakeNtfy.received[0]["priority"], 5)
        self.assertEqual(FakeNtfy.received[0]["click"], "http://am")

    def test_retries_a_5xx_then_succeeds(self) -> None:
        FakeNtfy.statuses.extend([500, 200])
        ok, attempts, _ = deliver("t", "b", 4, [], "")
        self.assertTrue(ok)
        self.assertEqual(attempts, 2)

    def test_gives_up_after_max_retries(self) -> None:
        FakeNtfy.statuses.extend([503] * (ajuste.MAX_RETRIES + 1))
        ok, attempts, _ = deliver("t", "b", 5, [], "")
        self.assertFalse(ok)
        self.assertEqual(attempts, ajuste.MAX_RETRIES + 1)

    def test_does_not_retry_a_rejected_payload(self) -> None:
        # Un 400 no se va a convertir en un 200 en un segundo intento, así que
        # reintentar solo retrasaría el 502 que le dice a Alertmanager que
        # aplique su espera.
        FakeNtfy.statuses.append(400)
        ok, attempts, _ = deliver("t", "b", 5, [], "")
        self.assertFalse(ok)
        self.assertEqual(attempts, 1)

    def test_sends_no_click_when_there_is_none(self) -> None:
        deliver("t", "b", 3, [], "")
        self.assertNotIn("click", FakeNtfy.received[0])
