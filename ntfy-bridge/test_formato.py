"""Tests de la cabecera del mensaje: titulo, prioridad y etiquetas."""

from __future__ import annotations

import unittest

from formato import build
from utiles import alert


class BuildTest(unittest.TestCase):
    def test_firing_critical_becomes_urgent(self) -> None:
        title, body, priority, tags, click = build(
            {
                "status": "firing",
                "groupLabels": {"service": "prometheus"},
                "alerts": [alert("TargetDown")],
                "externalURL": "http://am",
            }
        )
        self.assertEqual(title, "[CRITICAL] prometheus")
        self.assertEqual(priority, 5)
        self.assertIn("rotating_light", tags)
        self.assertIn("TargetDown", body)
        self.assertEqual(click, "http://am")

    def test_resolved_drops_to_low_priority(self) -> None:
        # Despertar a alguien a las 3am para decir que el incidente ha acabado es
        # un fallo de operacion, no un detalle, asi que un lote resuelto no es urgente.
        title, _, priority, tags, _ = build(
            {
                "status": "resolved",
                "groupLabels": {"alertname": "TargetDown"},
                "alerts": [alert("TargetDown", status="resolved")],
            }
        )
        self.assertTrue(title.startswith("RESOLVED:"))
        self.assertEqual(priority, 2)
        self.assertEqual(tags, ["white_check_mark"])

    def test_worst_severity_wins_and_count_is_shown(self) -> None:
        alerts = [alert("A", "info"), alert("B", "warning"), alert("C", "info")]
        title, _, priority, _, _ = build(
            {"status": "firing", "groupLabels": {"service": "api"}, "alerts": alerts}
        )
        self.assertEqual(title, "[WARNING] api (3)")
        self.assertEqual(priority, 4)

    def test_summary_text_from_templates_wins(self) -> None:
        # Quien manda en el texto es la configuracion de alertas, no este codigo.
        _, body, _, _, _ = build(
            {"status": "firing", "alerts": [alert("A")], "summary_text": "custom prose"}
        )
        self.assertEqual(body, "custom prose")

    def test_empty_batch_does_not_crash(self) -> None:
        _, body, _, _, _ = build({"status": "firing", "alerts": []})
        self.assertIn("Lote de alertas vacio", body)

    def test_ignores_entries_that_are_not_alerts(self) -> None:
        _, body, _, _, _ = build({"status": "firing", "alerts": [alert("A"), "basura", None]})
        self.assertIn("A", body)
        self.assertNotIn("basura", body)
