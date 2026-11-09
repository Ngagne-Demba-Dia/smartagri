# Observabilité

```text
infra/observability/
├── prometheus/
│   ├── prometheus.yml          collecte locale (api, minio, otel-collector)
│   └── rules/
│       ├── platform.yml        API, ingestion, kits, disques
│       └── ml.yml              dérive, inférence, OctOpus, ré-entraînement
├── grafana/
│   ├── provisioning/           source de données + fournisseur de tableaux de bord
│   └── dashboards/smartagri92-overview.json
├── otel/collector.yaml         collecteur OpenTelemetry (OTLP → Prometheus / debug)
└── render_prometheusrule.py    règles → infra/k8s/base/app/prometheusrules.yaml
```

- **Local** : `docker compose --profile observability up -d` ; Prometheus sur `127.0.0.1:9090`,
  Grafana sur `127.0.0.1:3001` (le port 3000 est pris par le tableau de bord web).
- **Kubernetes** : kube-prometheus-stack collecte via les ServiceMonitors (`api`, `inference`) et lit
  l'objet `PrometheusRule` généré. Après toute modification de `rules/*.yml` :
  `python infra/observability/render_prometheusrule.py` (la CI lance `--check`).
- Les règles de disque des nœuds recoupent celles de kube-prometheus-stack ; supprimer l'un des deux
  jeux si les alertes font doublon. Le disque RDS se surveille par CloudWatch (hors Prometheus).

## Contrat de métriques

| Métrique | Type, étiquettes | Producteur | État |
| --- | --- | --- | --- |
| `agri_http_requests_total` | compteur, `method`, `route`, `status` | API | exposée |
| `agri_http_request_seconds` | histogramme, `method`, `route` | API | exposée |
| `agri_telemetry_points_total` | compteur, `outcome` ∈ accepted, duplicate, rejected_point, rejected_value | API | exposée (voie HTTP) |
| `agri_telemetry_ingest_lag_seconds` | histogramme, `source` ∈ mqtt, http | ingestor / API | **à fournir** |
| `agri_device_last_seen_timestamp_seconds` | jauge, `device_id` | exporteur SQL | **à fournir** |
| `agri_inference_requests_total` | compteur, `model`, `outcome` ∈ ok, error | service d'inférence | **à fournir** |
| `agri_inference_request_seconds` | histogramme, `model` | service d'inférence | **à fournir** |
| `agri_octopus_requests_total` | compteur, `operation`, `status` (code HTTP, `timeout`, `network`) | API, CronJob retrain | **à fournir** |
| `agri_model_drift_psi` | jauge, `model`, `feature` | CronJob drift → Pushgateway (`job="agri_drift"`) | **à fournir** |
| `push_time_seconds` | jauge ajoutée par le Pushgateway | drift (`agri_drift`), retrain (`agri_retrain`) | automatique |
| `kube_job_status_failed`, `kube_deployment_status_replicas_available` | kube-state-metrics | cluster | kube-prometheus-stack |

Règles de nommage : préfixe `agri_`, unités de base (secondes, octets), étiquettes à cardinalité bornée
(gabarit de route, jamais l'URL brute ; jamais d'identifiant d'utilisateur). `device_id` est accepté
pour les kits (quelques centaines à quelques milliers de séries).

### Points ouverts

- L'ingestor (pont MQTT) n'a pas de serveur HTTP : ses compteurs `agri_telemetry_points_total` ne sont
  pas collectés. Exposer `/metrics` sur un port dédié (ex. 9100) ou pousser vers le Pushgateway.
- Kits silencieux : la colonne `devices.last_seen_at` existe déjà. Requête suggérée pour un exporteur
  SQL (sql_exporter, postgres_exporter « queries ») en lecture seule :

  ```sql
  SELECT serial AS device_id, EXTRACT(EPOCH FROM last_seen_at) AS last_seen
  FROM devices
  WHERE status = 'active' AND last_seen_at IS NOT NULL;
  ```

- Aucun service n'émet encore d'OTLP ; le collecteur est prêt pour le backend
  (`opentelemetry-instrumentation-fastapi`) et le web.
- MLflow n'est pas collecté (`--expose-prometheus` non activé dans l'image).

## Non vérifié

Aucune règle n'a été évaluée par `promtool check rules` (outil absent du poste ; aucun
téléchargement autorisé). Seule la syntaxe YAML/JSON a été contrôlée. La CI (`iac`) lance promtool.
