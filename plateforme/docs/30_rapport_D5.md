# 30 — Rapport d'exécution du Sprint D5 (`diagnosis_analyze` : blocage modèle documenté et préparation complète de l'intégration)

**Statut** : Préparation technique complète livrée et testée (`POST /v1/diagnoses/analyze`) ; maintenu en `mock` pour la démo tant qu'aucun bundle `vis_disease` entraîné sur photos de terrain n'est enregistré — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : `disease_diagnosis` / alias `diagnosis_analyze` (`POST /v1/diagnoses/analyze` et `POST /v1/diagnoses`, service 8 de Doc 16 § 9.3).
**Références** : `docs/16_architecture_octopus.md` § 5.5 et § 9.3 (intouché), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md` § 3.6, `ml/catalog/models.yaml` (`vis_disease`), `ml/programs/disease_image_classification.yaml`.

---

## 1. État initial et vérification des prérequis ML

La règle du plan validé pour D5 est explicite :
> *« Ne brancher en réel que si de vraies photos étiquetées et un modèle exploitable existent. Sinon : documenter le blocage et préparer l'intégration complète. »*

### 1.1 Vérification dans le dépôt (`ml/` et `backend/`)
1. **Données d'entraînement (`features.disease_images` / `images.labelled`)** :
   - Le programme OctOpus `ml/programs/disease_image_classification.yaml` et le catalogue `ml/catalog/models.yaml` (`vis_disease`, l. 251-277) exigent un jeu de photos de terrain locales doublement étiquetées par deux conseillers agricoles (`StratifiedGroupKFold` par plante, `F1 macro >= 0,80`, `rappel malade >= 0,90`, `ECE <= 0,05`).
   - Comme le souligne `ml/catalog/models.yaml` l. 275 : *« PlantVillage est photographié en laboratoire : sans photos de terrain locales, le F1 s'effondre. »*
   - **Constat** : aucun jeu de photos terrain annotées ni aucun bundle ONNX/TFLite/joblib vérifié (`model_registry` / `./models`) n'est présent dans le dépôt.
2. **Routes backend existantes** :
   - `POST /v1/diagnoses` existait déjà (`backend/app/api/v1/diagnoses.py`) pour enregistrer un verdict transmis par l'application mobile ou un kit caméra et déclencher l'alerte `disease_suspected` après 3 diagnostics consécutifs (`confidence >= 0.7`).
   - En revanche, la route d'analyse synchrone `POST /v1/diagnoses/analyze` attendue par l'écran Diagnostic (`DiagnosisInputSchema` → `DiagnosisSchema`) n'était pas encore exposée par le backend.

---

## 2. Modifications réalisées

### Backend (`plateforme/backend/`)
- **`app/schemas/monitoring.py`** :
  - Ajout de `DiagnosisAnalyzeIn` validant `image_base64`, `content_type` (`image/jpeg`, `image/png`, `image/webp`), `field_id`, `device_id`, `captured_at`, et imposant qu'au moins un rattachement (`field_id` ou `device_id`) soit fourni (`422 VALIDATION_ERROR` sinon).
- **`app/services/diagnoses.py`** :
  - Définition du protocole injectable `VisionAnalyzer` (`VisionPrediction`, `VisionCandidate`).
  - Garde-fou de taille : vérification stricte de la limite `256 Kio` (`UPLOAD_MAX_BYTES = 262 144` octets et `UPLOAD_MAX_RAW_BYTES`), renvoyant `413 PAYLOAD_TOO_LARGE` au-delà.
  - Contrôle d'accès multi-organisation sur `field_id` et `device_id` (`404 NOT_FOUND` si étranger ou incohérent) et vérification de `captured_at <= now` (`400 INVALID_DATES`).
  - En l'absence de `VisionAnalyzer` chargé (`app.state.vision_analyzer is None`) : renvoi honnête de **`503 MODEL_UNAVAILABLE`**.
  - Lorsqu'un `VisionAnalyzer` est injecté : application de la règle d'abstention de Doc 16 (`top_prob < settings.disease_min_confidence` soit `0.7` → `abstained = True`, `label = "suspect"`, `disease_code = None`) et construction du bloc `provenance` (`model_name = "vis_disease"`, `confidence.kind = "class_probability"`).
- **`app/api/v1/diagnoses.py`** :
  - Ajout de la route `POST /v1/diagnoses/analyze`.

### Tests (`plateforme/backend/tests/` et `plateforme/web/tests/live/`)
- **`backend/tests/test_sprint_d4_d5_d6.py`** (`test_d5_diagnosis_analyze_validation_503_and_abstention`) :
  - Vérifie le `503 MODEL_UNAVAILABLE` sans bundle, le `413 PAYLOAD_TOO_LARGE` au-delà de 256 Kio, le `404 NOT_FOUND` inter-organisation, le verdict nominal (`prob = 0.84` → `abstained = False`) et l'abstention (`prob = 0.52 < 0.7` → `abstained = True`, `label = "suspect"`, `disease_code = None`).
- **`web/tests/live/prepared-services.live.ts`** :
  - Vérifie en live à travers le BFF Next le comportement de `POST /v1/diagnoses/analyze` (`503 MODEL_UNAVAILABLE` et `404 NOT_FOUND`).

---

## 3. Tests exécutés

1. **Backend (`pytest`)** : `test_d5_diagnosis_analyze_validation_503_and_abstention` et `test_alerting.py` passants à 100 %.
2. **Contrat live (`vitest.live.config.ts`)** : test live BFF → FastAPI passant à 100 %.

---

## 4. Risques et conditions de levée du blocage

1. **Risque de faux négatifs terrain** : un modèle entraîné uniquement sur des images de laboratoire (type PlantVillage) échouerait sur des feuilles poussiéreuses ou éclairées en plein soleil sahélien. Le renvoi honnête de `503 MODEL_UNAVAILABLE` (ou l'abstention `< 0.7`) évite tout faux diagnostic rassurant.
2. **Condition de bascule en `real` avec inférence active** :
   - Collecte et double annotation d'au moins 2 000 photos de terrain (oignon, tomate, chou, carotte, pomme de terre) dans les Niayes et la vallée du fleuve.
   - Validation du programme OctOpus `disease_image_classification` (`F1 macro >= 0.80`, `rappel malade >= 0.90`, `ECE <= 0.05`) et enregistrement du bundle ONNX int8 signé par SHA-256 dans `model_registry`.

---

## 5. Prochaines étapes (Sprint D6)

- Comparer les fournisseurs ASR (**OpenAI Whisper**, **Azure Speech**, **Google Speech-to-Text**) face à la cible locale (`XLS-R 300M`) pour le wolof (`wo`), le pulaar (`ff`) et le français (`fr`), et livrer la préparation complète de **`assistant_transcribe`** (`POST /v1/assistant/transcribe`).
