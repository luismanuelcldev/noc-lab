"""Fixtures compartidas por las pruebas del puente.

La fabrica de alertas vive aqui para que los modulos de prueba describan el mismo
lote de la misma manera, y para que un cambio en su forma se haga en un sitio.
"""

from __future__ import annotations


def alert(name: str, severity: str = "critical", status: str = "firing") -> dict:
    """Una alerta tal como la manda Alertmanager, con todos los campos que lee el puente."""
    return {
        "status": status,
        "labels": {
            "alertname": name,
            "severity": severity,
            "service": "prometheus",
            "instance": "localhost:9090",
        },
        "annotations": {"summary": f"{name} is firing", "runbook_url": "http://runbook"},
        "startsAt": "2026-01-01T00:00:00Z",
    }
