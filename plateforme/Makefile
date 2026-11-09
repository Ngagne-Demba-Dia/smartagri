# Raccourcis de développement Smart Agri92. « make help » liste les cibles.
# Les recettes supposent un shell POSIX (Linux, macOS, WSL ou Git Bash sous Windows).

SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
PYTHON ?= python
MOSQUITTO_IMAGE ?= eclipse-mosquitto:2.0.20
# pytest-cov peut manquer en local : « make test-backend COV_BACKEND= » lance les tests sans couverture.
COV_BACKEND ?= --cov=app --cov-report=term-missing --cov-fail-under=80
COV_ML ?= --cov=agriml --cov-report=term-missing --cov-fail-under=80
SMOKE_CONFIG ?= configs/yield_regression.yaml
K8S_OUT ?= .build/k8s
S ?=

.PHONY: help check-env up up-obs down logs ps test-backend test-ml smoke-ml prometheus-rules lint k8s-render migrate seed mqtt-passwd

help: ## Liste les cibles disponibles
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

check-env: ## Vérifie .env et le fichier de mots de passe MQTT
	@test -f .env || { echo "Fichier .env absent : cp .env.example .env puis remplacer chaque CHANGER_MOI"; exit 1; }
	@if grep -q 'CHANGER_MOI' .env; then echo ".env contient encore des CHANGER_MOI"; exit 1; fi
	@test -s infra/mosquitto/secrets/passwd || { echo "infra/mosquitto/secrets/passwd absent : make mqtt-passwd"; exit 1; }

up: check-env ## Démarre la pile locale (db, mqtt, minio, api, ingestor, mlflow)
	$(COMPOSE) up -d --build

up-obs: check-env ## Démarre la pile avec Prometheus et Grafana (profil observability)
	$(COMPOSE) --profile observability up -d --build

down: ## Arrête la pile (les volumes nommés sont conservés)
	$(COMPOSE) --profile observability down

logs: ## Suit les journaux (make logs S=api pour un seul service)
	$(COMPOSE) logs -f --tail=200 $(S)

ps: ## État des services
	$(COMPOSE) ps

test-backend: ## Tests backend (SQLite via l'ORM) avec couverture >= 80 %
	cd backend && APP_ENV=test $(PYTHON) -m pytest $(COV_BACKEND)

test-ml: ## Tests du package agriml
	cd ml && PYTHONPATH=src $(PYTHON) -m pytest $(COV_ML)

smoke-ml: ## Entraînement de fumée sur données synthétiques (rapide, CPU)
	cd ml && $(PYTHON) scripts/make_synthetic.py --only yield
	cd ml && PYTHONPATH=src $(PYTHON) -m agriml.train --config $(SMOKE_CONFIG) --no-tuning --output-dir $(CURDIR)/.build/ml-smoke

prometheus-rules: ## Régénère l'objet PrometheusRule Kubernetes depuis infra/observability/prometheus/rules
	$(PYTHON) infra/observability/render_prometheusrule.py

lint: ## Lint et format Python (ruff)
	ruff check backend ml
	ruff format --check backend ml

k8s-render: ## Rend les overlays kustomize dev et prod dans .build/k8s
	@mkdir -p $(K8S_OUT)
	kubectl kustomize infra/k8s/overlays/dev > $(K8S_OUT)/dev.yaml
	kubectl kustomize infra/k8s/overlays/prod > $(K8S_OUT)/prod.yaml
	@echo "Rendu écrit dans $(K8S_OUT)/"

migrate: check-env ## Applique les migrations du schéma (service migrate, aussi lancé par make up)
	$(COMPOSE) run --rm --build migrate

seed: ## Données de démonstration (module backend app.seed, à confirmer avec l'équipe backend)
	$(COMPOSE) exec api python -m app.seed

mqtt-passwd: ## Génère infra/mosquitto/secrets/passwd (haché) depuis .env
	@test -f .env || { echo "Fichier .env absent : cp .env.example .env"; exit 1; }
	docker run --rm --env-file .env -v "$(CURDIR)/infra/mosquitto/secrets:/work" $(MOSQUITTO_IMAGE) sh -c '\
	  mosquitto_passwd -c -b /work/passwd "$$MQTT_INGESTOR_USER" "$$MQTT_INGESTOR_PASSWORD" && \
	  mosquitto_passwd -b /work/passwd "$$MQTT_API_USER" "$$MQTT_API_PASSWORD" && \
	  mosquitto_passwd -b /work/passwd healthcheck "$$MQTT_HEALTH_PASSWORD" && \
	  chown 1883:1883 /work/passwd && chmod 0600 /work/passwd'
	@echo "infra/mosquitto/secrets/passwd généré ; redémarrer le broker : docker compose restart mqtt"
