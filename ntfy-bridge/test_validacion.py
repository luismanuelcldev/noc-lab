"""Pruebas de la validacion previa: token, cuerpo y cuerpo de error.

Son los casos que deciden que estado HTTP ve Alertmanager, asi que se prueban
sin socket: un codigo equivocado aqui es lo que hace que Alertmanager o bien
abandone un incidente o bien lo reintente para siempre.
"""

from __future__ import annotations

import json
import unittest

import ajuste
import validacion
from utiles import alert


class AutorizadoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original = ajuste.BRIDGE_TOKEN

    def tearDown(self) -> None:
        ajuste.BRIDGE_TOKEN = self.original

    def test_open_when_no_token_configured(self) -> None:
        ajuste.BRIDGE_TOKEN = ""
        self.assertTrue(validacion.autorizado(""))

    def test_rejects_wrong_or_missing_token(self) -> None:
        ajuste.BRIDGE_TOKEN = "secreto"
        self.assertTrue(validacion.autorizado("Bearer secreto"))
        self.assertFalse(validacion.autorizado("Bearer otro"))
        self.assertFalse(validacion.autorizado("secreto"))
        self.assertFalse(validacion.autorizado(""))


class LeerTest(unittest.TestCase):
    def test_accepts_a_well_formed_batch(self) -> None:
        carga, error = validacion.leer(json.dumps({"alerts": [alert("A")]}).encode())
        self.assertEqual(error, 0)
        self.assertEqual(carga["alerts"][0]["labels"]["alertname"], "A")

    def test_an_empty_body_is_an_empty_batch(self) -> None:
        carga, error = validacion.leer(b"")
        self.assertEqual(error, 0)
        self.assertEqual(carga, {})

    def test_rejects_a_body_that_is_not_json(self) -> None:
        self.assertEqual(validacion.leer(b"no soy json"), (None, 400))

    def test_rejects_json_that_is_not_an_object(self) -> None:
        carga, error = validacion.leer(b"[1, 2, 3]")
        self.assertIsNone(carga)
        self.assertEqual(error, 400)

    def test_an_oversized_body_is_refused_without_being_parsed(self) -> None:
        enorme = b"{}" + b"a" * ajuste.MAX_BODY_BYTES
        self.assertEqual(validacion.leer(enorme), (None, 413))


class ErroresTest(unittest.TestCase):
    def test_every_error_code_has_a_body(self) -> None:
        # do_POST indexa ERRORES[code], asi que un codigo nuevo sin cuerpo
        # convertiria un rechazo limpio en un 500.
        for code in (400, 413):
            self.assertIn(code, validacion.ERRORES)
            self.assertIn("error", validacion.ERRORES[code])
