# syntax=docker/dockerfile:1.7
# Image de l'API SmartAgri92 (et du pont MQTT, même image, autre commande).
#   API    : CMD par défaut (port 8000)
#   Worker : python -m app.ingestion.mqtt_bridge
#   Alertes: python -m app.jobs.alert_sweep
#   Schéma : python -m app.db.migrate  (MIGRATION_DATABASE_URL = rôle propriétaire)

# --- Étape 1 : construction des roues --------------------------------------------------------
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# --- Étape 2 : exécution ---------------------------------------------------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=prod
RUN groupadd --system --gid 10001 agri \
    && useradd --system --uid 10001 --gid agri --home-dir /app --shell /usr/sbin/nologin agri
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl && rm -rf /wheels
COPY --chown=agri:agri app ./app
COPY --chown=agri:agri scripts ./scripts
# Migrations SQL : contexte de build nommé « migrations » (= plateforme/db/migrations),
# fourni par build-contexts (CI) ou additional_contexts (compose). Exécution :
#   python -m app.db.migrate            (MIGRATIONS_DIR=/app/migrations par défaut)
COPY --from=migrations --chown=agri:agri . ./migrations
USER agri:agri
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
