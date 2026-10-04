FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NTFY_URL="http://ntfy:80" \
    NTFY_TOPIC="noc-alerts" \
    LOG_LEVEL="INFO"

# Cuenta sin shell: el codigo que acaba ejecutandose aqui no hereda root ni
# puede abrir una sesion interactiva.
RUN adduser -S -u 1001 -H -s /sbin/nologin bridge

WORKDIR /app
# Los diez modulos de produccion, ordenados para poder revisar la lista contra el
# arbol. utiles.py se queda fuera a proposito: solo lo usan las pruebas.
COPY --chown=root:root app.py ajuste.py cuerpo.py entrega.py exposicion.py \
     formato.py metrics.py servidor.py validacion.py webhook.py ./

USER bridge
EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=3).status==200 else 1)"]

ENTRYPOINT ["python", "app.py"]

