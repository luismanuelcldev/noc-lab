"""Validadores del proyecto: paneles, alertas, enlaces, configuracion, estilo y datos.

Un modulo por asunto, para que cada uno se lea por separado y para que una
comprobacion se pueda ejecutar sola mientras se arregla otra cosa:

    base      estado compartido, rutas, carga de dashboards
    paneles   estructura de dashboards y expresiones de panel en vivo
    alertas   las cuatro anotaciones y el ancla del runbook de cada alerta
    enlaces   los enlaces relativos de markdown resuelven a fichero y ancla
    entorno   variables del compose documentadas en .env.example
    config    validacion con promtool, amtool y compose
    estilo    el presupuesto de lineas
    palabras  la regla de idioma
    idioma    aplica la regla de idioma a Grafana, Prometheus y Alertmanager
    datos     expresiones en vivo, recording rules muertas, paneles que se
              esperan vacios
    leyendas  las leyendas de serie, que tambien se leen
    columnas  que el byName de un override encuentre su columna
"""

from __future__ import annotations

from .cli import main

__all__ = ["main"]
