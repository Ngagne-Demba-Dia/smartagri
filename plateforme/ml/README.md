# agriml — apprentissage automatique de Smart Agri92

Confidentiel — réservé aux partenaires de travail.

Le paquet `agriml` sert à la fois à la **compétition** (score maximal, validation sans fuite, ensembles)
et à la **production** (bundle signé, parité d'inférence, porte champion/challenger, réentraînement).
Le même code de variables sert dans les deux cas. La méthode est décrite dans
`../docs/08_competition_ia.md` et l'intégration OctOpus ML dans `../docs/09_octopus_ml.md`.
Les résultats de contrôle obtenus sur données **synthétiques** sont dans `RESULTS_SMOKE.md`.

## Installation

```bash
cd plateforme/ml
python -m pip install -e .                      # cœur : numpy, pandas, scikit-learn, xgboost, pyarrow
python -m pip install -e ".[dev]"               # pytest, pytest-cov, ruff
# extras facultatifs, chargés à la demande (sans eux, le code ignore proprement le backend) :
#   boosting (lightgbm, catboost) · tuning (optuna) · tracking (mlflow) · vision (torch, timm, onnx…)
#   deep (torch, tensorflow, keras) · octopus (httpx) · pipelines (dvc, airflow) · notebooks
```

Le client OctOpus (`agriml.octopus.client`) est écrit ici, sur `httpx`. Le paquet PyPI au nom proche
n'a aucun lien avec OctOpus ML et ne doit jamais être installé ni ajouté aux dépendances.

## Commandes

Toutes les commandes se lancent depuis `plateforme/ml` (ou avec `PYTHONPATH=src` sans installation).

| Étape | Commande |
|---|---|
| Données synthétiques | `python scripts/make_synthetic.py --out data/synthetic --seed 42` |
| Carnet d'EDA | `python scripts/build_eda_notebook.py --execute` |
| Entraînement tabulaire | `python -m agriml.train --config configs/yield_regression.yaml [--no-tuning]` |
| Évaluation (tranches, calibration) | `python -m agriml.evaluate --run artifacts/yield_regression` |
| Prédiction (parité) | `python -m agriml.predict --run artifacts/yield_regression --input <csv> --output <csv> [--history <csv>]` |
| Bundle signé | `python -m agriml.export --run artifacts/yield_regression --out bundles/yield_regression` |
| Humidité du sol J+1..J+3 | `python -m agriml.forecast.soil_moisture --config configs/soil_moisture_forecast.yaml` |
| Vision (maladies) | `python -m agriml.vision.train_vision --config configs/vision_disease.yaml [--epochs N --max-folds K]` |
| Instantané OctOpus | `python -m agriml.octopus.exporter --program yield_forecast --train <csv> --test <csv> --version <v> --out <dir>` |
| Réentraînement + porte | `python -m agriml.mlops.retrain_flow --config <yaml> --holdout <csv> --model-name <nom> [--reference <csv> --current <csv> --force]` |
| Tests | `python -m pytest -q` |

Orchestration : `dvc.yaml` + `params.yaml` (données → entraînement → évaluation → export) et
`pipelines/airflow/retrain_dag.py` (dérive hebdomadaire → réentraînement + porte). Ni DVC ni Airflow ne
sont installés dans l'environnement de développement actuel : ces deux fichiers sont à vérifier au premier
déploiement ; la logique de branchement du DAG est testée sans Airflow.

## Arborescence

```text
ml/
├── configs/                 # une expérience = un YAML (CV, variables, modèles, ensemble, holdout)
├── src/agriml/
│   ├── config.py cv.py metrics.py adversarial.py selection.py ensemble.py tuning.py
│   ├── train.py predict.py evaluate.py export.py submission.py tracking.py
│   ├── features/            # agronomie (GDD, ET0, VPD, bilan hydrique), temporel, télédétection, encodage
│   ├── models/              # fabrique (hgb, xgb, rf, linéaires, lightgbm/catboost optionnels), MLP torch/keras
│   ├── forecast/            # humidité du sol, MOS météo, conseil d'irrigation
│   ├── vision/              # plis StratifiedGroupKFold, augmentations, distillation, export ONNX
│   ├── monitoring/drift.py  # PSI/KS, politique de réentraînement
│   ├── mlops/               # registre local/MLflow, promotion, flux de réentraînement
│   └── octopus/             # client HTTP, exporteur pseudonymisant, programmes YAML, synchronisation
├── scripts/                 # données synthétiques, carnet d'EDA
├── pipelines/airflow/       # DAG de réentraînement
├── notebooks/               # 01_eda.ipynb (la version exécutée est ignorée par Git)
├── tests/                   # pytest, données minuscules, aucun accès réseau
├── artifacts/ bundles/ data/synthetic/   # sorties générées, ignorées par Git (voir .gitignore)
└── dvc.yaml params.yaml pyproject.toml
```

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `OCTOPUS_BASE_URL` | URL de l'instance OctOpus ML (HTTPS obligatoire hors `localhost`) |
| `OCTOPUS_API_KEY` | Clé d'API OctOpus ; lue depuis l'environnement, jamais journalisée |
| `AGRIML_PSEUDO_SALT` | Sel HMAC-SHA256 de pseudonymisation de l'exporteur ; fourni par le gestionnaire de secrets, jamais écrit sur disque |
| `AGRIML_PSEUDO_SALT_ID` | Identifiant du sel (tracé dans le manifeste à la place du sel) |
| `AGRIML_NOTIFY_WEBHOOK` | Webhook de notification du flux de réentraînement ; absent = notification dans le journal seulement |
| `MLFLOW_TRACKING_URI` | Serveur MLflow (si `mlflow` est installé ; sinon suivi local JSON/CSV) |
| `LOKY_MAX_CPU_COUNT` | Fixé par défaut à l'import d'`agriml` pour éviter un avertissement joblib sous Windows |

## Règles qui ne se négocient pas

- Les transformations apprises (encodage cible, imputation, normalisation) sont ajustées dans le pli d'entraînement.
- Le holdout figé ne sert jamais au réglage, et il n'est jamais envoyé à OctOpus (`holdout_sent: false`).
- Le règlement d'une compétition est lu avant tout téléversement de ses données vers un tiers.
- Une base de référence `agriml` précède tout run OctOpus.
- Aucune donnée privée, aucun secret, aucun artefact généré dans Git.
