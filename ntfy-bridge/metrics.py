"""Contadores del puente.

Por que hay que monitorizar un componente de notificacion: es el ultimo eslabon de la
cadena. Si se rompe, las alertas siguen disparando y Prometheus sigue viendolas, pero
no se lo cuenta nadie a nadie. Ese modo de fallo es el silencio, el peor que puede
tener un centro de monitorizacion.

A mano en vez de prometheus_client porque el conjunto de metricas es pequeno y fijo y una
dependencia mas no aportaria nada. El texto lo genera exposicion.py.
"""

from __future__ import annotations

import threading
import time

import exposicion


class Metrics:
    """Contadores en memoria que se renderizan en formato de exposicion de Prometheus.

    Hace falta el cerrojo porque el servidor con hilos atiende peticiones en paralelo: sin
    el, los numeros de un cuadro de mando pueden no cuadrar con la realidad, y a estos
    volumenes el coste del cerrojo es irrelevante y la correccion no.
    """

    def __init__(self) -> None:
        """Arranca el reloj de uptime y los mapas de contadores vacios.

        time.monotonic y no time.time: la serie de uptime no debe saltar atras cuando
        NTP corrige el reloj del anfitrion, que es justo el tipo de desfase que
        RelojDesincronizado existe para detectar.
        """
        self._lock = threading.Lock()
        self._start = time.monotonic()
        self._requests: dict[str, int] = {}
        self._deliveries: dict[str, dict[str, int]] = {}
        self._last: dict[str, int] = {}
        self._alerts = 0
        self._duration = 0.0

    def record_request(self, status: str) -> None:
        """Cuenta una peticion HTTP. Un estado desconocido se conserva, no se descarta."""
        with self._lock:
            self._requests[status] = self._requests.get(status, 0) + 1

    def record_alerts(self, count: int) -> None:
        """Cuenta las alertas de un lote, ignorando un negativo sin sentido."""
        with self._lock:
            self._alerts += max(0, count)

    def record_delivery(self, delivered: bool, attempts: int, duration: float) -> None:
        """Registra una secuencia de intentos de entrega.

        delivery_success guarda el ULTIMO resultado y no un total acumulado: un
        contador acumulado se quedaria en 0 durante horas tras un fallo puntual y
        la alerta de canal muerto no volveria a dispararse nunca.
        """
        with self._lock:
            row = self._deliveries.setdefault("ntfy", {"ok": 0, "failed": 0, "retries": 0})
            row["ok" if delivered else "failed"] += 1
            row["retries"] += max(0, attempts - 1)
            self._last["ntfy"] = 1 if delivered else 0
            self._duration += max(0.0, duration)

    def render(self) -> str:
        """Toma una foto bajo el cerrojo y pasa los numeros a exposicion.py.

        La copia importa: leer los mapas sin el cerrojo es como un cuadro de mando
        que acaba mostrando una peticion que se conto pero todavia no se entrego,
        o dos muestras de instantes distintos en la misma linea.
        """
        with self._lock:
            return exposicion.render(
                uptime=time.monotonic() - self._start,
                requests=dict(self._requests),
                deliveries={k: dict(v) for k, v in self._deliveries.items()},
                last=dict(self._last),
                alerts=self._alerts,
                duration=self._duration,
            )
