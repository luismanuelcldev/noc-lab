"""Prueba de humo del camino de la alerta, de extremo a extremo y de regla a movil.

El laboratorio tiene un servicio llamado demo-app que existe para ser tirado. Esto
lo para, espera a que las alertas lleguen de verdad a ntfy, lo vuelve a levantar y
espera a que se resuelvan. Si eso pasa, el camino entero funciona: la alerta
dispara -> Prometheus evalua -> Alertmanager agrupa y enruta -> el puente recibe el
webhook -> formatea el mensaje -> publica en ntfy -> y de vuelta, las alertas se
resuelven.

No es una prueba de correccion de la logica de alertas: no mira el contenido de las
alertas mas alla de sus nombres, no juzga si los umbrales son razonables, y no
sustituye a "promtool test rules". Lo que si atrapa es el fallo mas comun en un
laboratorio como este: todo levantado, cada contenedor en verde, y el movil que no
vibra porque un nombre de topic no cuadra o un token nunca se roto.

Un detalle que va a morder a quien reescriba esto: ntfy responde con NDJSON, un
objeto JSON por linea, asi que suponer un unico objeto con una lista falla con
"extra data" en la segunda linea y parece que no hay mensajes. Y para no mezclar
esta pasada con el historico cacheado, anoto el id del ultimo mensaje *antes* de
romper nada y luego solo leo ids posteriores.

    python scripts/smoke.py                     # 4 min de espera para las que disparan
    python scripts/smoke.py --wait 60           # para cuando el stack va rapido
    python scripts/smoke.py --override          # anade docker-compose.desktop.yml
"""
