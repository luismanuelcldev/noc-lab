"""Regresion de es_prosa, que distingue una leyenda de un identificador.

El fallo que cubre: es_prosa devolvia False en cuanto la leyenda tenia una
plantilla `{{...}}`, con lo que `{{instancia}} uptime` se escapaba de la
revision de idioma con "uptime" en ingles a la vista. La plantilla no es prosa,
pero solo la parte de la leyenda que hay alrededor de ella.

Los casos negatives no son_IDENTIFICADORES puros por gusto: son lo que evita que
el validador exija traducir `prometheus_http` o `tcp` a algo que en ingles sigue
siendo `prometheus_http` y `tcp`.
"""

from __future__ import annotations

import unittest

from noccheck.leyendas import es_prosa


class TestEsProsa(unittest.TestCase):
    def test_plantilla_sola_no_es_prosa(self) -> None:
        self.assertFalse(es_prosa("{{etiqueta}}"))
        self.assertFalse(es_prosa("{{instancia}} - {{puerto}}"))
        self.assertFalse(es_prosa("{{a}} {{b}}"))

    def test_palabra_suelta_si_es_prosa(self) -> None:
        self.assertTrue(es_prosa("uptime"))
        self.assertTrue(es_prosa("memoria usada"))

    def test_la_plantilla_no_tapa_el_resto(self) -> None:
        """El caso del fallo: plantilla delante, ingles detras."""
        self.assertTrue(es_prosa("{{instancia}} uptime"))
        self.assertTrue(es_prosa("{{servicio}} p95"))
        self.assertTrue(es_prosa("{{instancia}} cpu en uso"))

    def test_nombres_propios_no_son_prosa(self) -> None:
        self.assertFalse(es_prosa("tcp"))
        self.assertFalse(es_prosa("prometheus"))
        self.assertFalse(es_prosa("cadvisor"))
        self.assertFalse(es_prosa("{{job}} prometheus"))
        self.assertFalse(es_prosa("prometheus_http"))

    def test_prosa_inglesa_dentro_de_un_nombre_de_metrica(self) -> None:
        """Quitar los nombres propios deja prosa, y la prosa se revisa."""
        self.assertTrue(es_prosa("prometheus_http_requests"))
        self.assertTrue(es_prosa("{{job}} http_errors"))
        self.assertTrue(es_prosa("prometheus_scrape"))


if __name__ == "__main__":
    unittest.main()