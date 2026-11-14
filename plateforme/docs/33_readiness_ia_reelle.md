# 33 — Analyse de préparation à l'IA réelle (Sprint D8)

**Statut** : Référence d'industrialisation ML post-Sprint D — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : analyse de `plateforme/ml/` (catalogue `ml/catalog/models.yaml`, programmes OctOpus `ml/src/agriml/octopus/programs/*.yaml`, pipelines `ml/src/agriml/`), identification du premier modèle réellement industrialisable (`soil_nowcast`), données manquantes, délais estimés, risques et ordre de développement des modèles IA futurs.
**Contrainte respectée** : `docs/16_architecture_octopus.md` n'a subi aucune modification.

---

## 1. État réel du sous-système ML (`plateforme/ml/` et `plateforme/backend/app/services/inference/`)

L'inspection du dépôt montre que l'architecture ML et l'infrastructure d'inférence sont déjà structurées de bout en bout :

1. **Catalogue gouverné (`ml/catalog/models.yaml`, `datasets.yaml`, `pretrained.yaml`)** :
   - **26 modèles** couvrant les 10 cas d'usage (`IA-1` à `IA-10` + `TRANSVERSE`), répartis en `MVP` (7), `V1.1` (4), `V2` (9) et `V3` (6).
   - Chaque modèle définit ses jeux obligatoires (`mandatory`), ses variantes (`competition`, `production`, `compromis`), sa métrique primaire, son seuil d'acceptation (`threshold`) et sa chaîne de repli (`fallback`).
2. **Quatre programmes OctOpus prêts (`ml/src/agriml/octopus/programs/`)** :
   - `soil_moisture_nowcast.yaml` (`soil_nowcast`, tâche `forecast`, cible `soil_moisture_pct`, horizons `24, 48, 72 h`, `purged_time` groupé par `device_id`, `gap_hours: 72`).
   - `irrigation_need.yaml` (`irr_need_24h`, tâche `regression`, cible `target_need_mm_24h`, `purged_time` groupé par `field_key`, `MAE <= 3 mm`).
   - `disease_image_classification.yaml` (`vis_disease`, classification multi-classe avec seuil d'abstention `0.7`).
   - `yield_forecast.yaml` (`yield_forecast`, régression quantile `p10/p50/p90` par parcelle).
3. **Passerelle d'inférence backend (`backend/app/services/inference/`)** :
   - `local.py` : chargement de paquets locaux (`.joblib` / `.onnx`) vérifiés par empreinte **SHA-256** enregistrée dans la table `model_registry`.
   - `octopus.py` : client HTTPS vers OctOpus pour l'entraînement et le scoring batch.
   - `registry.py` : sélection du modèle au stage `production` le plus récent, avec traçabilité complète dans le bloc `provenance` (`source: "agriml" | "octopus"`, `fallback_step: 0..2`).

---

## 2. Premier modèle véritablement industrialisable : `soil_nowcast` (service 2 `soil_forecast`)

### Pourquoi `soil_nowcast` est le premier candidat réel (avant tous les autres modèles ML)

| Critère d'industrialisation | `soil_nowcast` (`soil_forecast` 1–48/72 h) | `irr_need_24h` (`irrigation_need` ML) | `vis_disease` (`diagnosis_analyze`) | `yield_forecast` (rendement `p10–p90`) |
| :--- | :--- | :--- | :--- | :--- |
| **Cible (label) auto-supervisée** | **Oui (100 % automatique)** : la cible $y(t+h) - y(t)$ est l'humidité mesurée par la sonde à $t+24\text{ h}$, $t+48\text{ h}$, $t+72\text{ h}$. Aucune annotation humaine requise. | **Non au MVP** : la cible « besoin observé » exige un **débitmètre** (V1.1) pour connaître le volume réellement apporté (`models.yaml` l. 124). | **Non** : exige des milliers de photos de terrain doublement annotées par deux conseillers (`models.yaml` l. 270). | **Non** : exige plusieurs saisons complètes de pesées de récolte réelles par parcelle (`models.yaml` l. 691). |
| **Capteurs requis déjà présents sur le kit v1.1** | **Oui** : sonde d'humidité du sol, BME280 (T, HR), état pompe (`pump_on`), seuils (`threshold_start_pct`), plus météo Open-Meteo (`et0_mm`, pluie). | **Non** : requiert le débitmètre sur la conduite d'irrigation. | **Non** : requiert la collecte mobile/ESP32-CAM en conditions réelles. | **Partiel** : dépend en amont de `ndvi_gapfill` et `phenology_stage` (Sentinel-1/2). |
| **Programme OctOpus & pipeline `agriml`** | **Déjà écrits et testés** (`ml/src/agriml/forecast/soil_moisture.py` + `soil_moisture_nowcast.yaml`). | Pipeline écrit (`agriml/irrigation/need.py`), mais cible dépendante du débitmètre. | Programme écrit, mais dépend du corpus d'images locales. | Pipeline écrit (`agriml/yield_forecast/`), mais dépend d'années de campagnes. |
| **Chaîne de repli sûre** | **Oui** : persistance $y(t+h)=y(t)$, puis bilan hydrique `irr_water_balance`. | **Oui** : `irr_water_balance` (déjà en `real` depuis D1 !). | **Oui** : `503 MODEL_UNAVAILABLE` ou abstention `< 0.7` vers conseiller. | **Oui** : `forecast: null` ou statistiques régionales. |

**Conclusion** : **`soil_nowcast` (exposant `GET /v1/fields/{id}/soil-forecast`) est le premier modèle ML supervisé réellement industrialisable dès que les kits pilotes auront accumulé des séries temporelles continues.**

---

## 3. Données manquantes par famille de modèles

| Modèle / Service | Jeu obligatoire (`ml/catalog/models.yaml`) | Ce qui manque aujourd'hui en base / sur le terrain | Volume minimal requis pour le passage en `production` |
| :--- | :--- | :--- | :--- |
| **`sm_calibration`** *(prérequis physique de `soil_nowcast`)* | `iot.telemetry_clean`, `sols.field_profile`, `sols.lab_results` | Prélèvements gravimétriques (poids humide / poids sec à l'étuve 105 °C) appariés aux lectures ADC de la sonde capacitive par type de sol (*dior*, *deck*, *hollaldé*). | `>= 10` prélèvements par classe de texture (`RMSE <= 3 points de %`). |
| **`soil_nowcast`** (`soil_forecast`) | `features.soil_nowcast` (`measurements` horaires + météo `as-of`) | Historique continu de télémétrie horaire réelle des kits pilotes couvrant cycles d'arrosage et de dessèchement. | **Minimum pilote (V1.1/V2 initial)** : 6 à 8 semaines continues sur `>= 5` kits (`~7 000` points horaires). **Cible nominale V2** : 1 saison sèche + 1 hivernage (`skill >= 20 %` vs persistance à 24 h). |
| **`fert_reco` / `risk_rules`** (`fertilization`, `pest_risk`) | `sols.field_profile`, `agronomie.crop_params`, `phyto.reference` | Tables de barèmes de fumure ISRA et règles phytosanitaires ISRA/DPV validées et signées par les agronomes. | Tables de référence statiques validées (`<= 20 %` d'écart sur 50 cas revus par un agronome). |
| **`irr_need_24h`** (`irrigation_need` ML) | `features.irrigation_need`, `iot.irrigation_events` | **Débitmètre** installé sur les pompes pour mesurer le volume réel apporté et construire la cible `besoin observé - bilan FAO-56`. | `>= 1` campagne irriguée avec débitmètre (`MAE <= 3 mm`). |
| **`vis_disease`** (`diagnosis_analyze`) | `features.disease_images`, `phyto.reference` | Corpus de photos de feuilles prises au champ au Sénégal (Niayes, vallée) et doublement annotées par deux conseillers. | `>= 2 000` photos pour `vis_quality` ; `>= 500` photos par couple (culture, maladie) pour `vis_disease` (`F1 macro >= 0,80`, `rappel malade >= 0,90`). |
| **`asst_asr`** (`assistant_transcribe`) | `features.asr_speech` | Enregistrements vocaux agricoles en wolof (`wo`) et pulaar (`ff`) avec consentement explicite écrit et transcription vérifiée + lexique `KenLM`. | `20 à 50 heures` d'audio agricole transcrit en wolof (`WER <= 25 %`), puis pulaar. |
| **`ndvi_gapfill` / `phenology_stage` / `yield_forecast`** | `satellite.field_indices`, `features.phenology`, `features.yield` | Connecteur d'ingestion Sentinel-2 / Sentinel-1 par contour GeoJSON de parcelle + relevés de stades BBCH et rendements pesés en fin de campagne. | Sentinel-2 : historique 2 ans immédiat par API ; `yield_forecast` : `>= 2` campagnes de rendements observés sur `>= 50` parcelles. |

---

## 4. Délais estimés de mise en production réelle

| Horizon | Jalon et livrables IA / Règles | Délai estimé (à compter du déploiement des kits pilotes) |
| :--- | :--- | :--- |
| **Phase 1 — Immédiat (S0 à S+4)** | - Validation agronomique ISRA/DPV des tables `fertilization_reference` et `pest_reference` → bascule de `fertilization` et `pest_risk` de `mock` à `real` (mode `rules`).<br>- Étalonnage gravimétrique initial des sondes (`sm_calibration`) à l'installation des kits.<br>- Déploiement d'un serveur local `faster-whisper` (`fr`) pour `assistant_transcribe` si l'usage vocal en français est souhaité dès le pilote. | **2 à 4 semaines** |
| **Phase 2 — Court terme (M+2 à M+3)** | - Entraînement du premier modèle ML réel **`soil_nowcast`** (LightGBM quantile `p10/p50/p90` sur le delta d'humidité à 24/48/72 h) sur les 6–8 premières semaines de télémétrie des kits pilotes.<br>-Implémentation de la route `GET /v1/fields/{id}/soil-forecast` servie par `LocalBundleBackend` (`model_registry`) avec repli sur persistance / `irr_water_balance`.<br>- Ingestion Sentinel-2 (`ndvi_gapfill` Whittaker + `vis_canopy` ExG) pour `vegetation` (`GET /v1/fields/{id}/vegetation`). | **8 à 12 semaines** |
| **Phase 3 — Moyen terme (M+4 à M+6, fin de 1re campagne)** | - **`irr_need_24h`** (LightGBM sur résidu FAO-56) sur les parcelles équipées d'un débitmètre.<br>- **`anomaly_ml`** (Isolation Forest sur résidus de `soil_nowcast` + corrélations inter-capteurs).<br>- **`water_savings`** (`GET /v1/reports/kpis`) avec intervalles de confiance à 90 % sur les parcelles équipées de débitmètre.<br>- Premier lot de photos terrain annotées pour **`vis_disease`** (cultures prioritaires : oignon et tomate). | **4 à 6 mois** |
| **Phase 4 — Long terme (M+6 à M+12, multi-saisons)** | - **`soil_nowcast` V2 complet** (hivernage + saison sèche).<br>- **`asst_asr` wolof** (`XLS-R 300M` + `KenLM` sur corpus agricole consenti).<br>- **`yield_forecast`** (`p10/p50/p90` conforme, validation *leave-one-season-out*).<br>- **`irr_scheduler`** (`irrigation_plan` MPC 72 h OR-Tools) et **`price_forecast`** (après convention SIM / ARM). | **6 à 12 mois** |

---

## 5. Risques majeurs et garde-fous obligatoires

1. **Erreur de sonde capacitive non étalonnée (`sm_calibration`)** :
   - *Risque* : comme l'indique `ml/catalog/models.yaml` l. 869, *« Tous les modèles d'irrigation héritent de l'erreur de cette sonde : à faire avant le ML »*.
   - *Parade* : stocker les lectures ADC sec et eau par kit et étalonner par classe de texture (*dior*, *deck*, *hollaldé*) dès la pose.
2. **Biais thermique du boîtier (`wx_local_bias`)** :
   - *Risque* : le capteur BME280 chauffe au soleil s'il n'est pas dans un abri ventilé, ce qui fausse l'ET0 locale et la correction de biais.
   - *Parade* : conserver l'ET0 Open-Meteo / Hargreaves exploitée au niveau de la parcelle comme référence tant que l'abri ventilé du kit n'est pas validé.
3. **Fuite temporelle (*data leakage*) lors de l'entraînement** :
   - *Risque* : utiliser la météo réanalysée a posteriori au lieu de la prévision *as-of* (`meteo.forecast_asof`), ou mélanger aléatoirement les points d'un même kit entre train et test.
   - *Parade* : utiliser exclusivement la validation `purged_time` (`gap_hours: 72`) groupée par `device_id` / `field_key` déjà codée dans `ml/src/agriml/validation/splits.py` et imposée par les programmes OctOpus.
4. **Dérive domaine laboratoire → terrain en vision (`vis_disease`)** :
   - *Risque* : déployer un modèle entraîné sur PlantVillage provoquerait des erreurs massives au champ.
   - *Parade* : maintenir le seuil d'abstention `>= 0.7`, l'exigence d'évaluation sur holdout terrain local (`F1 macro >= 0.80`, `rappel malade >= 0.90`, `ECE <= 0.05`) et le renvoi honnête de `503 MODEL_UNAVAILABLE` tant que ce seuil n'est pas atteint.
5. **Souveraineté des données vocales et personnelles (`asst_asr`, `agri_risk_score`)** :
   - *Risque* : exporter des enregistrements vocaux identifiants ou des données personnelles vers des API tierces sans base légale.
   - *Parade* : appliquer les garde-fous `guardrails.drop` / `pseudonymize` des programmes OctOpus et privilégier l'inférence locale pour l'audio.

---

## 6. Ordre recommandé des futurs développements IA

1. **Étape 1 — Référentiels agronomiques et étalonnage physique (V1.1)** :
   - Charger les barèmes ISRA (`fertilization`) et règles ISRA/DPV (`pest_risk`) validés → activer ces deux services déjà prêts côté backend.
   - Réaliser l'étalonnage gravimétrique `sm_calibration` sur les parcelles pilotes.
2. **Étape 2 — Premier modèle ML en production : `soil_nowcast` (`soil_forecast`)** :
   - Entraîner le modèle LightGBM multi-horizon (`24, 48, 72 h`, quantiles `p10, p50, p90`) via `agriml.forecast.soil_moisture` et le programme OctOpus `soil_moisture_nowcast`.
   - Enregistrer le bundle signé SHA-256 dans `model_registry` et brancher `GET /v1/fields/{id}/soil-forecast` en `real`.
3. **Étape 3 — Télédétection et suivi cultural sans coût matériel (`ndvi_gapfill` + `phenology_stage`)** :
   - Brancher l'ingestion Sentinel-2 / Whittaker pour alimenter `GET /v1/fields/{id}/vegetation` en `real`.
4. **Étape 4 — Besoin en eau ML (`irr_need_24h`) et anomalies multivariées (`anomaly_ml`)** :
   - Exploiter les résidus de `soil_nowcast` pour `anomaly_ml` et les relevés des débitmètres pilotes pour remplacer le repli FAO-56 (`fallback_step=2`) de `irrigation_need` par le modèle LightGBM sur résidu (`fallback_step=0`).
5. **Étape 5 — Vision terrain (`vis_disease`) et ASR wolof (`asst_asr`)** :
   - Dès que les campagnes d'annotation photo et audio auront atteint leurs seuils de volume et de qualité, injecter les bundles vérifiés dans `app.state.vision_analyzer` (`POST /v1/diagnoses/analyze`) et `app.state.transcriber` (`POST /v1/assistant/transcribe`), dont toute la chaîne technique est désormais prête et testée.
6. **Étape 6 — Modèles multi-saisons V3 (`yield_forecast`, `irr_scheduler`, `price_forecast`)** :
   - Activer le modèle de rendement `p10–p90` après au moins deux campagnes complètes et l'optimiseur MPC 72 h (`irrigation_plan`) sur les exploitations multi-parcelles.
