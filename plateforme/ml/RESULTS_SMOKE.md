# Résultats des essais de contrôle — données SYNTHÉTIQUES

Confidentiel — réservé aux partenaires de travail.

> **Données synthétiques uniquement** (`scripts/make_synthetic.py`, graine 42). Ces chiffres prouvent que la
> chaîne s'exécute de bout en bout et que ses garde-fous fonctionnent. Ils ne disent **rien** de la qualité d'un
> modèle sur des données réelles et ne doivent pas être cités comme performances.

Environnement : Windows 11, processeur seul, Python 3.13.5 (Anaconda), scikit-learn 1.6.1, xgboost, torch CPU,
tensorflow/keras. **Absents** (replis utilisés) : optuna, mlflow, lightgbm, catboost, timm, onnx, dvc, airflow,
pytest-cov. Dates : 26 et 27/10/2026. Commandes lancées depuis `plateforme/ml` avec `PYTHONPATH=src`.

## 1. Rendement (régression) — `configs/yield_regression.yaml`

CV `purged_time` (5 plis × 3 graines = 15 plis), métrique RMSE (plus bas = mieux).

| Essai | hgb | xgb | ridge | Retenu | Holdout figé |
|---|---|---|---|---|---|
| Sans réglage (`--no-tuning`) | **0,70315** | 0,94001 | 1,86395 | hgb | 0,65964 |
| Avec réglage (recherche aléatoire, Optuna absent) | **0,70315** (± 0,14501) | 0,88141 (± 0,16385) | 1,86395 (± 0,04548) | hgb | 0,65964 |

- Référence constante : RMSE 8,415. AUC adversariale train/test : 0,600 (décalage faible).
- Réglage : « Optuna non installé : recherche aléatoire graine-fixée (8 essais) » ;
  « Optimisation xgb (random) : 4 essais, 4 élagués, meilleur rmse = 0.90375 ».
- Ensembles sur l'OOF : moyenne 0,88466 ; montée de colline 0,70315 (hgb seul) ; poids optimisés 0,69388 ;
  stacking 0,69855. Méthode configurée : montée de colline, donc modèle final = hgb.
- Holdout avec réglage : hgb 0,65964 ; xgb 0,84845 ; ridge 1,91209 ; final 0,65964.
- MLflow absent : suivi local JSON/CSV dans `artifacts/_smoke_tuning/`. Durée réelle 4 min 09 s, code de sortie 0.
- Parité `predict` contre `submission.csv` : écart maximal 1,07 × 10⁻¹⁴.
- Bundle : sha256 `c0e2d24b…fa3`, `verify_bundle` OK ; un fichier modifié lève `BundleIntegrityError` (test).

## 2. Risque maladie (binaire) — `configs/disease_risk_binary.yaml`

CV `stratified_group` par parcelle (le test contient de nouvelles parcelles), métrique AUC (plus haut = mieux).

| Modèle | AUC CV |
|---|---|
| logreg | **0,93503** (retenu) |
| xgb | 0,92948 |
| hgb | 0,92805 |
| rf | 0,92210 |

Holdout 0,95336. AUC adversariale 0,627. Calibration : Brier 0,0668, ECE 0,0128. Seuil F1 optimal sur l'OOF 0,327
(F1 0,639). Parité d'inférence : écart 0.

## 3. Séries temporelles

**Humidité du sol J+1..J+3** (`configs/soil_moisture_forecast.yaml`, 4 plis purgés, intervalle 72 h) :

| Horizon | RMSE modèle | RMSE persistance | Gain |
|---|---|---|---|
| 24 h | 4,931 | 8,563 | 42,4 % |
| 48 h | 6,679 | 11,727 | 43,0 % |
| 72 h | 8,620 | 13,537 | 36,3 % |

**Correction MOS** (température prévue) : RMSE 2,179 → 0,879.

## 4. Vision (maladies) — `configs/vision_disease.yaml`

5 plis `StratifiedGroupKFold` × 12 époques, images 96 px, n = 90, processeur : exactitude OOF 0,6778,
F1 macro 0,6465, logloss 0,7642, durée 132,2 s. **Export ONNX non vérifié** : le paquet `onnx` est absent.

## 5. Réseaux de neurones tabulaires (extra `deep`)

| Backend | Régression (RMSE) | Binaire (AUC) | Multiclasse (logloss) |
|---|---|---|---|
| torch_mlp | 7,1893 | 0,9603 | 0,4148 |
| keras_mlp | 6,1602 | 0,9430 | 0,4694 |

Aller-retour pickle : écart 0.

## 6. Carnet d'EDA — `notebooks/01_eda.ipynb`

Exécuté sans erreur en 15 s environ. Train (3000, 39), test (600, 38). Cible : moyenne 7,10, écart-type 8,41,
asymétrie 1,211. 300 groupes, tous présents dans le train et le test. Années du train jusqu'à 2021–2023, test
2024–2025. 0 identifiant commun, 0 doublon, aucune variable à |r| > 0,95. AUC adversariale 0,6371 sans la colonne
temps, 1,0 avec (le test est dans le futur : le temps se traite par la CV).

## 7. Sélection de variables — `tests/test_selection.py`

5 tests passés :
- l'importance nulle (forêt aléatoire, 12 cibles permutées) garde `signal` et rejette deux variables de bruit,
  sans modifier le DataFrame d'entrée ;
- avec Ridge, le chemin par coefficients fonctionne ; KNeighbors lève `TypeError` ;
- la permutation hors-pli place `signal` en tête (régression RMSE et binaire AUC) ;
- l'élagage adversarial retire seulement la colonne qui dérive (AUC > 0,9 → ≤ 0,6).

## 8. Exporteur OctOpus — `agriml.octopus.exporter`

Le sel n'existe que dans l'environnement de la commande. Il est généré à la volée et jamais écrit sur disque.
`AGRIML_NOTIFY_WEBHOOK` n'est pas défini.

```bash
env -u AGRIML_NOTIFY_WEBHOOK \
  AGRIML_PSEUDO_SALT="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  AGRIML_PSEUDO_SALT_ID=smoke-2026-10-27 \
  python -m agriml.octopus.exporter --program yield_forecast \
    --train data/synthetic/yield/yield_train.csv --test data/synthetic/yield/yield_test.csv \
    --version 20261027-smoke01 --out <scratch>/smoke/octopus_export --source-query synthetic:yield
```

- **Succès (code 0)**. Journal :
  - « Garde-fous sans effet (colonnes absentes) : ['address', 'email', 'farm_key', 'owner_name', 'phone'] » ;
  - « Instantané yield écrit (3000 lignes, 39 colonnes) » ;
  - « manifest.json sha256 = b57e40d4bb68d6953fea2eac41b21972b41a4091e81450e02c45874c66a2d652 ».

  Fichiers écrits : `README.md`, `manifest.json`, `train.parquet`, `test.parquet`. Contenu du manifeste :
  - 3000 lignes de train et 600 de test ;
  - préfixe `octopus/yield/v=20261027-smoke01/` ;
  - HMAC-SHA256 avec `salt_id` smoke-2026-10-27 ; `field_id` pseudonymisé ;
  - `lat_r`/`lon_r` arrondis à 0,01 ;
  - **`holdout_sent: false`**.

  La chaîne du sel apparaît 0 fois dans les sorties.
- **Refus (code 2)** : avec une colonne `contact` contenant des e-mails, le journal affiche « Export refusé,
  données interdites : [train] contact : 3000 valeur(s) ressemblant à un e-mail ». Aucun dossier de sortie n'est
  créé.

## 9. Réentraînement et porte — `agriml.mlops.retrain_flow`

Holdout étiqueté `<scratch>/smoke/yield_holdout_labeled.csv` (les étiquettes du test synthétique). Référence
`yield_train`, données courantes `yield_test`, tranches par `crop`. Webhook non défini : la notification va dans
le journal.

| Essai | Résultat | Durée |
|---|---|---|
| Sans dérive | « Dérive : réentraîner=False [] » ; « Pas de dérive : aucun réentraînement. » | 5,7 s, code 0 |
| Forcé (`--force`) | Holdout : hgb 0,65964 ; xgb 0,91652 ; final 0,65964. « yield_regression v1 : non promu (gain relatif +0.00% < 1%) » | 3 min 05 s, code 0 |

Le résumé `retrain_20261027T102559Z.json` indique : réentraîné, version 1, backend null, `promote: false`.
Challenger et champion valent tous deux 0,659636 sur 600 lignes. RMSE par culture :

| Culture | RMSE |
|---|---|
| arachide | 0,102 |
| chou | 1,736 |
| maïs | 0,177 |
| mil | 0,098 |
| oignon | 0,989 |
| pomme de terre | 0,920 |
| riz | 0,325 |
| sorgho | 0,104 |
| tomate | 0,654 |

La porte refuse un challenger identique au champion, comme prévu.

## 10. Ce qui n'a pas été vérifié

- Export ONNX (vision), Optuna, MLflow (dont `register_model`), LightGBM, CatBoost, timm : non installés.
- `dvc.yaml` et le DAG Airflow : jamais exécutés. Seule la logique de branchement du DAG est testée.
- Aucune instance OctOpus réelle contactée ; les corps de requête restent « à vérifier ».
- Couverture de tests non mesurée (`pytest-cov` absent).
