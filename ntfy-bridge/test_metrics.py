"""Pruebas de los contadores y de su formato de exposición."""

from __future__ import annotations

import unittest

from metrics import Metrics


class MetricsTest(unittest.TestCase):
    def test_exposes_every_family_the_dashboards_query(self) -> None:
        m = Metrics()
        m.record_request("ok")
        m.record_request("rejected")
        m.record_alerts(3)
        m.record_delivery(True, 2, 0.25)
        text = m.render()
        for name in (
            "ntfy_bridge_up",
            "ntfy_bridge_uptime_seconds",
            "ntfy_bridge_http_requests_by_result_total",
            "ntfy_bridge_alerts_received_total",
            "ntfy_bridge_delivery_success",
            "ntfy_bridge_deliveries_total",
            "ntfy_bridge_delivery_retries_total",
            "ntfy_bridge_delivery_duration_seconds_sum",
            "ntfy_bridge_delivery_duration_seconds_count",
        ):
            self.assertIn(name, text, f"{name} missing from exposition")
        self.assertIn('ntfy_bridge_delivery_success{sink="ntfy"} 1', text)

    def test_failed_delivery_drives_the_gauge_to_zero(self) -> None:
        m = Metrics()
        m.record_delivery(True, 1, 0.1)
        m.record_delivery(False, 4, 0.1)
        self.assertIn('ntfy_bridge_delivery_success{sink="ntfy"} 0', m.render())

    def test_counts_requests_by_result(self) -> None:
        m = Metrics()
        m.record_request("ok")
        m.record_request("ok")
        m.record_request("rejected")
        text = m.render()
        self.assertIn('ntfy_bridge_http_requests_by_result_total{result="ok"} 2', text)
        self.assertIn('ntfy_bridge_http_requests_by_result_total{result="rejected"} 1', text)
        self.assertIn("ntfy_bridge_http_requests_total 3", text)

    def test_a_negative_alert_count_cannot_move_the_counter_backwards(self) -> None:
        m = Metrics()
        m.record_alerts(5)
        m.record_alerts(-3)
        self.assertIn("ntfy_bridge_alerts_received_total 5", m.render())

    def test_every_declared_family_also_declares_its_type(self) -> None:
        # Sin # TYPE, rate() se comporta mal y el panel enseña cifras
        # equivocadas sin quejarse. Las muestras que comparten familia (la misma
        # métrica con otro conjunto de etiquetas) se emiten bajo un único par
        # HELP/TYPE, así que el invariante es por familia, no por línea.
        m = Metrics()
        m.record_request("ok")
        m.record_delivery(True, 1, 0.5)
        text = m.render()
        declarados = {line.split()[2] for line in text.splitlines() if line.startswith("# HELP")}
        tipados = {line.split()[2] for line in text.splitlines() if line.startswith("# TYPE")}
        self.assertEqual(declarados, tipados)
        for linea in text.splitlines():
            if linea and not linea.startswith("#"):
                self.assertRegex(linea, r"^ntfy_bridge_\w+(\{.*\})? -?[\d.]+$")
