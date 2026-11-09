# 24 — Rapport de maturité du backend et de l'IA

> Sprint D, phases 5 à 7. Document de travail interne, confidentiel (partenaires uniquement).
> Date : 2026-11-09. S'appuie sur `22_backend_gap_analysis.md` (écarts) et `23_integration_plan.md` (ordre D0 à D5).
> Tout ce qui suit est vérifié dans le code ou dans les artefacts du dépôt ; ce qui ne l'est pas est marqué « à confirmer » ou « estimation ».

## 1. Verdict en dix lignes

1. Le **backend de base est solide** : 40 routes `/v1`, enveloppe, JWT, isolement par organisation, rôles, limiteurs, 123 tests. Il sert déjà la météo, le moteur FAO-56, les alertes, les KPI, l'assistant et l'enregistrement des diagnostics.
2. **13 des 18 services du Doc 16 n'ont pas (ou pas toute) leur route** (10 sans route, 3 partielles) ; aucune route n'envoie le bloc `provenance`.
3. **L'intégration n'est pas encore faisable service par service** : la bascule de simulation est globale (`AGRI_MOCK`). Il faut un mode hybride (D0).
4. **Un bug latent** (`payload.crop`, objet contre chaîne) fera échouer `/recommandations` en mode réel (502 `BAD_RESPONSE`).
5. **Aucun modèle ML n'est utilisable en production aujourd'hui.** Tous sont entraînés sur des données synthétiques ; un seul paquet existe (rendement), et il ne peut pas être servi (ses variables n'existent pas dans le backend).
6. Les chiffres de `ml/RESULTS_SMOKE.md` prouvent que **la chaîne d'entraînement fonctionne**, pas qu'un modèle est bon.
7. **OctOpus ML** : cinq programmes décrits, client interne écrit, contrat **non confirmé**, aucune exécution réelle.
8. Premier service réel : **`irrigation_need`, confirmé**, en règles FAO-56 (`source: rules`). Ce n'est pas du ML, et le rapport ne le présente pas comme tel.
9. Premier service **ML** réaliste : `soil_forecast`, mais seulement après des mesures réelles et un réentraînement (V2).
10. Charge estimée du sprint : 36 à 42 j-ingénieur hors attentes de données (doc 23 § 12).

## 2. État du backend

| Axe | État | Preuve |
|---|---|---|
| Routes `/v1` | 40 codées (+ 3 d'infrastructure) | doc 22 § 2 |
| Enveloppe, erreurs, JWT, RLS multi-organisation | En place, testés | `test_envelope_health.py`, `test_auth.py`, `test_cross_org.py` |
| Rôles et limiteurs | En place (120/min, 10/min `auth`, 20/min assistant) | `core/constants.py`, `core/config.py` |
| Ingestion de télémétrie | En place, 6 fichiers de test | `test_telemetry.py`, `test_mqtt_bridge.py`… |
| Alertes par règles | En place | `test_alerting.py` |
| Moteur FAO-56 | En place (Hargreaves, Kc par stade, 7 cultures) ; ne tient pas compte de la pluie annoncée | `services/agronomy.py` |
| Couche d'inférence | Écrite (`none/local/octopus`, registre, SHA-256, colonnes personnelles interdites) mais **jamais exercée** : aucun test, aucune ligne de registre dans le jeu de démonstration | `services/inference/`, absence de `ModelRegistry` dans `seed.py` |
| Provenance (Doc 16 § 9.2) | Non codée | aucune occurrence de `provenance` ou `fallback_step` dans `app/` |
| Chaîne de repli (R12) | Non codée : un seul backend essayé, puis 503 | `factory.py`, `base.py` |
| Tests | 123 fonctions, 13 fichiers ; aucun d'inférence, de provenance ni d'`yield-forecast` hors isolement | doc 22 § 2 |

Note : le répertoire de travail n'est pas un dépôt git (constat de l'environnement). Il n'y a donc ni historique ni retour arrière par commit : voir risque R-07.

## 3. État de l'intégration Frontend ↔ API

| Axe | État |
|---|---|
| Gel du Frontend | RC : build de production, Playwright, 610 tests, accessibilité et responsive validés |
| Contrats | Zod sur les 18 services, strictement alignés sur le Doc 16 § 9.4 |
| Bascule | Globale (`AGRI_MOCK=1` ou `API_BASE_URL`) |
| Mocks | Répondent seulement pour les identifiants des jeux de démonstration du Frontend ; une route non simulée donne 404 |
| Routes existantes validées contre le Zod | Aucune validation automatique avec l'API réelle (le test de contrat « live » n'existe pas) |
| Conformité connue | Météo, rendement, retour de recommandation, alertes : formes compatibles. Recommandations : **non conforme** (E1). Assistant : forme compatible, flux non implémenté |
| Provenance | Acceptée `null` sur les routes existantes ; **exigée** sur les routes nouvelles |

## 4. Phase 5 — Étude IA du dossier `ml/`

### 4.1 Ce qu'il contient

| Élément | Contenu vérifié |
|---|---|
| Catalogue | `ml/catalog/models.yaml` : **39 modèles** décrits (MVP 9, V1.1 4, V2 15, V3 11), avec données obligatoires, mode d'inférence, latence, repli |
| Bibliothèque `agriml` | Entraînement tabulaire (hgb, xgb, rf, logreg, ridge, réseaux `torch`/`keras`), validations croisées (`purged_time`, `stratified_group`), ensembles (moyenne, montée de colline, poids optimisés, stacking), réglage, validation adversariale, export de paquet signé SHA-256, prévision d'humidité du sol multi-horizon, correction météo MOS, vision (images), client OctOpus |
| Programmes OctOpus | 5 fichiers : `irrigation_need`, `soil_moisture_nowcast`, `yield_forecast`, `disease_image_classification`, `competition_template` |
| Données | `ml/data/synthetic/` : `disease`, `images`, `telemetry`, `weather_mos`, `yield`, générées par `scripts/make_synthetic.py` (graine 42). **Aucun jeu `irrigation_need`.** |
| Artefacts entraînés | `yield_regression`, `disease_risk_binary`, `soil_moisture_forecast`, `vision_disease` (+ essais `_smoke_tuning`, `_tracking`) |
| Paquets prêts à servir | **1** : `ml/bundles/yield_regression` (membres : `hgb`, graines 42, 7, 2025, 5 plis) |

### 4.2 Les modèles sont-ils exploitables ?

Résultats des essais (tous sur données **synthétiques**, citation interdite comme performance : `RESULTS_SMOKE.md`).

| Artefact | Résultat de l'essai | Obstacle à l'exploitation en production | Exploitable ? |
|---|---|---|---|
| `yield_regression` (paquet) | RMSE CV 0,703 ; holdout 0,660 ; référence constante 8,415 ; empreintes vérifiées | **Les variables ne correspondent pas au backend.** Le paquet attend 65 variables numériques (dont **36 indices NDVI/EVI** et 11 `agro_*`) plus `region`, `crop`, `soil_type`, `lat`, `lon`, pH, etc. `yield_forecast.feature_row` fournit `crop`, `soil_type`, `area_ha`, moyennes capteur sur 30 jours, heures de pompe… Aucune ingestion NDVI n'existe. De plus, aucun enregistrement `model_registry` (nom attendu : `yield_t_ha`) | **Non** |
| `disease_risk_binary` | AUC CV 0,935 ; holdout 0,953 ; ECE 0,013 | Données synthétiques ; pas de paquet signé ; correspond à `pest_risk_ml` (V2), pas au risque par règles (V1.1) | **Non** |
| `soil_moisture_forecast` | RMSE 4,93 / 6,68 / 8,62 à 24/48/72 h contre persistance 8,56 / 11,73 / 13,54 (gain 36 à 43 %) | `forecaster.joblib` est un objet `agriml` dont `predict` renvoie un tableau de deltas : le chargeur du backend n'accepte qu'un estimateur numérique ou un dictionnaire de quantiles. Il faudrait un adaptateur ou un export ONNX, et `agriml` dans l'environnement du backend (le backend n'en dépend pas). Pas de paquet signé. Données synthétiques | **Non** (le plus proche) |
| `vision_disease` | Exactitude OOF 0,678, F1 macro 0,647 (n = 90 images, 96 px) | Poids PyTorch (`fold*_ema.pt`) ; **export ONNX non vérifié** (`onnx` absent) ; jeu minuscule et synthétique ; seuil de calibration inconnu | **Non** |
| Réseaux tabulaires `deep` | Scores d'essai seulement | Aucun cas d'usage associé | **Non** |

**Conclusion : zéro modèle exploitable en production.** Ce qui est exploitable aujourd'hui, c'est la **chaîne** (entraînement reproductible, validation, signature, vérification d'intégrité) et les **règles** (FAO-56, alertes, niveaux NPK).

### 4.3 Dépendances de données

| Besoin | Disponible ? |
|---|---|
| Télémétrie réelle de kits (humidité, T, HR, NPK, débit) | Format d'ingestion prêt ; **volume réel inconnu** (le dépôt ne contient que du synthétique) |
| Étiquettes d'irrigation (`target_need_mm_24h`) | **Absentes** : ni jeu `irrigation_need` ni vérité terrain |
| Météo | Open-Meteo via le backend (cache) ; pas d'historique d'erreur de prévision pour les modèles `wx_*` |
| Indices de végétation (NDVI, EVI) | **Aucune source ingérée** |
| Référentiel phytosanitaire (`phyto.reference`) | **Absent** ; requis par `risk_rules` et `pest_phenology` |
| Barème de fertilisation par culture et stade | **Absent** |
| Photos réelles étiquetées | **Absentes** |
| Audio wolof et peul | **Absent** |
| Prix de marché | **Absents** |

### 4.4 État d'OctOpus ML

| Point | État |
|---|---|
| Programmes | 5 fichiers décrits (tâche, cible, métrique, validation, garde-fous, critères d'acceptation). `irrigation_need` : MAE ≤ 3 mm au holdout, gain relatif ≥ 2 %, écart CV/holdout ≤ 0,15, planifié chaque lundi (`0 2 * * 1`) |
| Client | Écrit (httpx, interne à `agriml/octopus/client.py`, et côté backend `services/inference/octopus.py`), contrat d'API **« à vérifier »** |
| Exécutions | Aucune trace d'un run réel (les essais du 26–27/10/2026 sont locaux, suivi JSON/CSV ; MLflow absent) |
| Répliques manquantes en local | `optuna`, `mlflow`, `lightgbm`, `catboost`, `timm`, `onnx`, `dvc`, `airflow`, `pytest-cov` |
| Rôle dans la chaîne de repli | Étape 1 (lot OctOpus), utilisable seulement après confirmation du contrat et de l'espace `prod` (Doc 16 § 5.5) |

**Verdict :** OctOpus n'est pas sur le chemin critique du sprint D. Il le devient quand de vraies données justifieront un modèle.

## 5. Phase 6 — Premier service réellement branchable

### 5.1 Comparaison

Échelle : ● acquis, ◐ partiel, ○ absent. « Facilité » = effort d'intégration estimé.

| Candidat | Données | Modèle | Facilité | Valeur métier | Note |
|---|---|---|---|---|---|
| **`irrigation_need`** | ● télémétrie, météo, cycle, seuils déjà en base | ● règles FAO-56 codées et testées | ● 3 à 4 j, aucun nouveau schéma | ● cœur du MVP (économie d'eau) | Pas de ML, mais conforme au contrat (`source: rules`) |
| `device_health` | ● télémétrie et alertes | ● règles d'alertes | ● 3 j | ◐ utile, moins central | Bon second (D2) |
| `kit_parameters` | ◐ seuils oui, NPK et étalonnage d'usine | ◐ règles | ◐ 4 à 6 j + migration | ◐ dépend du firmware (backlog E1) | D2 |
| `fertilization` | ◐ capteur NPK « indicatif » | ○ barème absent | ◐ 3 j | ◐ risque de conseil nuisible | Bloqué par la donnée |
| `pest_risk` | ○ référentiel absent | ○ règles à rédiger | ◐ 4 j | ◐ | Bloqué par la donnée |
| `soil_forecast` | ○ pas de mesures réelles suffisantes | ◐ modèle d'essai synthétique | ○ adaptateur + route + signature | ● | V2 ; premier service ML visé |
| `yield_forecast` | ○ NDVI absent | ◐ paquet synthétique incompatible | ○ | ◐ décisionnel, saisonnier (V3) | Route existe déjà ; non prioritaire |
| `diagnosis_analyze` | ○ photos réelles absentes | ○ | ○ | ● | Risque élevé d'erreur de verdict |
| `assistant_transcribe` | ○ | ○ | ○ | ◐ | Fournisseur externe ou 503 |

### 5.2 Décision

**`irrigation_need` reste le meilleur premier service**, pour quatre raisons vérifiées :

1. Ses trois entrées (mesure d'humidité, météo à 24 h, cycle actif) existent déjà dans la base et le code.
2. Son moteur existe et est testé (`recommend_irrigation` : FAO-56, `RAIN_SKIP_MM`, `IRRIGATION_EFFICIENCY`).
3. Le contrat l'autorise explicitement sans ML : Doc 16 § 9.4 « confiance `none` (bilan MVP), `interval` (V2) ».
4. Il porte la valeur métier principale du MVP et conduit l'écran le plus consulté.

**Réserves à connaître :**

- Il ne démontre pas de capacité d'**IA** : il valide l'architecture (route, provenance, repli, hybride BFF, contrat live). C'est la bonne chose à valider en premier.
- La pluie annoncée n'est pas encore branchée (E2) ; sans elle, `defer` serait toujours faux. D0 doit la corriger avant D1.
- La version ML (`irr_need_24h`) est **bloquée** : pas de jeu `irrigation_need`, pas de vérité terrain. Les règles resteront le repli et le champion jusqu'à une campagne de mesures réelles.

**Premier service ML à viser après le sprint :** `soil_forecast`, une fois qu'on dispose de mesures réelles et d'un modèle réentraîné, signé et vérifié, avec adaptateur de format. Pas `yield_forecast` (variables absentes), pas la vision (données absentes).

## 6. Risques

| # | Risque | Gravité | Probabilité | Parade |
|---|---|---|---|---|
| R-01 | Réponse API non conforme au Zod en mode réel (E1 en est un cas avéré) : écrans en erreur 502 | Haute | Haute | Test de contrat « live » (D0) avant tout retrait de simulation |
| R-02 | Un modèle entraîné sur du synthétique est présenté comme fiable | Haute | Moyenne | Aucune route ML ouverte sans passer les critères du Doc 16 § 5.3 ; provenance obligatoire ; jamais de chiffre de `RESULTS_SMOKE.md` en démonstration |
| R-03 | Verdict de diagnostic faux sur photo | Haute | Moyenne si livré trop tôt | `MODEL_UNAVAILABLE` 503 plutôt qu'un verdict inventé ; abstention sous 0,7 |
| R-04 | Conseil de fertilisation inadapté | Haute | Moyenne | Mention « indicatif », barème validé par l'agronome, refus sans cycle actif ni capteur NPK valide |
| R-05 | Le kit n'applique pas `agro` (backlog firmware E1) | Moyenne | Certaine | L'API émet le bloc, l'écran ne promet rien (doc 12) |
| R-06 | Contrat OctOpus différent de celui supposé | Moyenne | Moyenne | Étape 1 de la chaîne désactivée ; règles en repli |
| R-07 | Pas de dépôt git : aucun historique ni retour arrière | Moyenne | Certaine | Sauvegarde avant D0 et à chaque étape ; envisager `git init` (décision du chef de projet) |
| R-08 | Données agronomiques (barème, règles, référentiel) non livrées : D3 bloqué | Moyenne | Moyenne | Reporter D3 ; ne pas inventer de valeurs |
| R-09 | Mode hybride mal conçu : une route réelle contourne la validation Zod | Moyenne | Faible | La validation reste dans le BFF pour les deux chemins ; test dédié |
| R-10 | Confidentialité des photos et de l'audio envoyés à un tiers | Haute | Selon choix | Pas de fournisseur externe sans accord écrit ; colonnes personnelles interdites déjà codées pour l'inférence tabulaire |

## 7. Dette technique

| # | Dette | Où | Conséquence |
|---|---|---|---|
| D-01 | `payload.crop` objet / chaîne (E1) | `recommendations.py` / `field.ts` | 502 en mode réel |
| D-02 | `rain_forecast_mm` jamais alimenté (E2) | `agronomy.py` | conseil sans pluie annoncée |
| D-03 | Provenance absente partout (E3) | `app/` | contrat Doc 16 § 9.2 non tenu |
| D-04 | Chaîne de repli non codée (E4) | `inference/factory.py` | 503 au lieu des règles |
| D-05 | Bascule de simulation globale (E5) | `web/lib/mock-config.ts` | pas d'intégration progressive |
| D-06 | Aucun test d'inférence (E6) ; `yield-forecast` seulement testé en isolement | `backend/tests/` | couche d'inférence non éprouvée |
| D-07 | `model_registry` vide dans le jeu de démonstration | `seed.py` | aucune démonstration de bout en bout d'un modèle |
| D-08 | `yield_forecast` sans repli par règles | `yield_forecast.py` | 503 `MODEL_UNAVAILABLE` quand le modèle manque |
| D-09 | Réponse de l'assistant en JSON unique ; Doc 16 prévoit un flux ; `citations`/`refusal` absents côté API | `assistant.py` | écart mineur au contrat, couvert par des valeurs par défaut du Zod |
| D-10 | Dépendances ML optionnelles absentes (onnx, mlflow, lightgbm…) ; `agriml` non déclaré comme dépendance du backend | `ml/`, `backend/` | export ONNX et chargement d'objets `agriml` impossibles en l'état |
| D-11 | Contrat OctOpus à confirmer (E7) | `octopus/client.py` | étape 1 inutilisable |

## 8. Ordre recommandé des développements

1. **D0 — Préparation** (8,5 j) : hybride par route, bloc de provenance, repli minimal, correction E1 et E2, test de contrat live, gabarit de test d'inférence.
2. **D1 — `irrigation_need`** (3 à 4 j) : premier service réel, en règles.
3. **D2 — `kit_parameters` + `device_health`** (7 à 9 j).
4. **D3 — `fertilization` + `pest_risk`** (7 j) : **seulement si** le barème et les règles agronomiques sont livrés ; sinon passer à D4.
5. **D4 — `diagnosis_analyze`** (5 à 8 j) : **seulement si** un paquet vérifié et des images réelles existent ; sinon la route renvoie 503 et reste simulée.
6. **D5 — `assistant_transcribe`** (5 j) : après choix d'un fournisseur.
7. **Hors sprint** : collecte de télémétrie réelle → réentraînement de `soil_forecast` → premier service ML (V2) ; confirmation du contrat OctOpus ; satellite (NDVI) avant tout retour sur `yield_forecast`.

## 9. Décisions attendues du chef de projet

| # | Décision | Recommandation |
|---|---|---|
| 1 | E1 : corriger l'API ou le Zod ? | Corriger l'API (aucune modification du Frontend) |
| 2 | Hybride BFF par liste de routes (`AGRI_REAL_ROUTES`) : acceptable comme « adaptation imposée » ? | Oui, 1 j, sans toucher aux écrans |
| 3 | Fournir à l'ingénierie : barème de fertilisation, règles ravageurs, référentiel phytosanitaire | À planifier avant D3 |
| 4 | Fournisseur de transcription (ou renoncement en V1) | Reporter la décision à D5 |
| 5 | `git init` du répertoire de travail | Oui, avant D0 |
| 6 | Réponse de l'assistant en flux : implémenter ou réviser le Doc 16 en v1.1 | Réviser le Doc 16 (JSON unique), sans coût de développement ; à valider |

## 10. Propositions pour le backlog v1.1

(Non réalisées, conformément à la consigne : aucune nouvelle fonctionnalité Frontend pendant le sprint.)

- Panneau d'état « route réelle ou simulée » par service, utile aux partenaires en démonstration.
- Export du schéma Zod vers un JSON Schema partagé, validé aussi côté pytest.
- Jeu de démonstration backend avec une ligne `model_registry` factice et un bundle de test signé, pour exercer la couche d'inférence de bout en bout.

## 11. Ce qui reste inchangé

Doc 16 et baseline v1, contrats des 18 services, architecture IA baseline v1, Frontend RC : **aucun fichier modifié** dans le cadre de ces trois documents. Les corrections et adaptations listées ci-dessus sont des **propositions** à valider ; aucune n'est encore appliquée.
