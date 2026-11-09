# Serveur MLflow local : métadonnées dans PostgreSQL, artefacts dans MinIO (S3).
# Image minimale, utilisateur non root ; versions épinglées.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir \
      mlflow==2.19.0 \
      psycopg2-binary==2.9.10 \
      boto3==1.35.90 \
 && useradd --uid 10001 --create-home --shell /usr/sbin/nologin mlflow

USER 10001
WORKDIR /home/mlflow
EXPOSE 5000
