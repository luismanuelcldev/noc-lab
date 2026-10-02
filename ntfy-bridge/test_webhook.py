"""Pruebas de la decision de entrega a partir de un lote ya validado.

La validacion previa vive en test_validacion.py; aqui se comprueba que el
resultado de la entrega se traduce al estado y a la etiqueta de metrica que
Alertmanager y el panel necesitan.
"""

from __future__ import annotations

import unittest

import ajuste
import webhook
from utiles import alert


class ProcesarTest(unittest.TestCase):
    def test_an_empty_batch_is_ok_and_delivers_nothing(self) -> None:
        # Alertmanager manda esto cuando todo se resuelve; fallarlo haria que
        # reintentara un lote sin nada dentro.
        estado, etiqueta, cuerpo = webhook.procesar({"alerts": []})
        self.assertEqual(estado, 200)
        self.assertEqual(etiqueta, "ok")
        self.assertEqual(cuerpo["delivered"], 0)

    def test_an_unreachable_ntfy_answers_502_so_alertmanager_retries(self) -> None:
        original = ajuste.NTFY_URL
        ajuste.NTFY_URL = "http://127.0.0.1:9"  # aqui no escucha nadie
        ajuste.BACKOFF_BASE = 0.01
        try:
            estado, etiqueta, cuerpo = webhook.procesar(
                {"status": "firing", "alerts": [alert("TargetDown")]}
            )
        finally:
            ajuste.NTFY_URL = original
        self.assertEqual(estado, 502)
        self.assertEqual(etiqueta, "error")
        self.assertEqual(cuerpo["failed_sinks"], ["ntfy"])
