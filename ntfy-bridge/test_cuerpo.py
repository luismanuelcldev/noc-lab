"""Tests del cuerpo del mensaje: el bloque que se lee de verdad en el movil."""

from __future__ import annotations

import unittest

import ajuste
from cuerpo import compose_body, describe
from utiles import alert


class DescribeTest(unittest.TestCase):
    def test_renders_every_field_the_operator_needs(self) -> None:
        text = describe(alert("TargetDown"))
        self.assertIn("[FIRING] TargetDown", text)
        self.assertIn("gravedad  : critical", text)
        self.assertIn("runbook   : http://runbook", text)

    def test_all_labels_share_one_column(self) -> None:
        # Los rotulos llevaban los espacios a mano y "dashboard" desplazaba su dos puntos.
        alerta = alert("TargetDown")
        alerta["annotations"].update(description="d", dashboard_url="u")
        rotulos = {r.index(":") for r in describe(alerta).splitlines() if r.startswith("  ")}
        self.assertEqual(len(rotulos), 1, f"desalineado: {rotulos}")

    def test_survives_an_alert_with_no_labels_or_annotations(self) -> None:
        text = describe({"status": "firing"})
        self.assertIn("AlertaDesconocida", text)
        self.assertIn("gravedad  : none", text)


class ComposeBodyTest(unittest.TestCase):
    def test_truncation_announces_how_many_were_dropped(self) -> None:
        # Cortar en silencio dejaria cerrar el incidente habiendo leido solo una parte.
        body = compose_body([alert(f"Alert{i:02d}") for i in range(60)], False)
        self.assertLessEqual(len(body), ajuste.MAX_MESSAGE_CHARS)
        self.assertIn("de 60 alertas mostradas", body)

    def test_hard_cap_holds_even_when_the_cut_lands_on_a_space(self) -> None:
        # El corte iba a cap - 1 y anadia 3 puntos: podia acabar en cap + 2 y ntfy
        # contestaba 400. Solo se veia con un texto bastante largo, asi que se fuerza.
        for extra in (0, 1, 2, 3, 5):
            largo = len(compose_body([alert(f"Larga{i:03d}" * extra) for i in range(400)], False))
            self.assertLessEqual(largo, ajuste.MAX_MESSAGE_CHARS, f"extra={extra}")
