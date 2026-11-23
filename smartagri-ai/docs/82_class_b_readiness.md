# 82 — SmartAgri Classe B : Readiness & Dataset Specifications
## Préparation des 6 modèles Classe B pour entraînement immédiat

**Version** : 1.0
**Date** : 2026-11-17
**Auteur** : SmartAgri92 / OctOpus
**Statut** : Prêt pour collecte de données terrain

---

## 0. Contexte : Actifs Classe A disponibles

Les 9 modèles Classe A sont entraînés et mesurés. Les modèles Classe B s'appuient sur eux.

| Modèle Classe A | Champion | Métrique | Rôle pour Classe B |
|-----------------|----------|----------|---------------------|
| **A1 SoilNowcast** | LightGBM | R² = 0.835 | Input B1 Irrigation, B2 Water Savings, B6 Soil Calibration |
| **A2 ET0 Forecast** | CatBoost | R² = 0.9997 | Input B1 Irrigation, B2 Water Savings |
| **A4 Rain Intelligence** | CatBoost | AUC = 0.963 | Input B1 Irrigation, B5 Pest Prediction |
| **A5 Price Forecast** | XGBoost | R² = 0.900 | Contexte économique B2 Water Savings |
| **A6 Crop Calendar** | CatBoost | F1 = 0.980 | Stades phénologiques B1, B4, B5 |
| **A7 NDVI Anomaly** | LightGBM | F1 = 0.994 | Stress végétatif B4 Disease, B5 Pest |
| **A8 Anomaly Intelligence** | IsoForest+AE | F1 best OC-SVM 0.097 | Anomalies climat B3, B5 |

---

## B1. Irrigation ML

### Objectif

Prédire le besoin en irrigation (mm/jour) par parcelle, en intégrant les capteurs d'humidité du sol réels pour dépasser le proxy satellite de SoilNowcast.

### Cas d'usage

- Recommandation de dose quotidienne (mm)
- Planification hebdomadaire d'irrigation
- Optimisation de la consommation d'eau par culture et stade phénologique

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `parcel_id` | string | **OUI** | Terrain | Identifiant unique de la parcelle |
| `timestamp` | datetime | **OUI** | Capteur | Horodatage de la mesure (UTC) |
| `soil_moisture_10cm_pct` | float | **OUI** | Capteur TDR/capacitif | Humidité volumique à 10 cm (%) |
| `soil_moisture_30cm_pct` | float | **OUI** | Capteur TDR/capacitif | Humidité volumique à 30 cm (%) |
| `soil_moisture_60cm_pct` | float | Optionnel | Capteur profond | Humidité à 60 cm si disponible |
| `soil_temp_10cm_c` | float | Optionnel | Capteur thermique | Température sol à 10 cm |
| `irrigation_applied_mm` | float | **OUI** | Compteur/débitmètre | Dose réellement appliquée (mm) |
| `irrigation_duration_min` | float | Optionnel | Timer pompe | Durée d'irrigation (min) |
| `crop_type` | string | **OUI** | Agriculteur | Culture en place |
| `crop_stage` | string | **OUI** | Observation/A6 | Stade phénologique (initial/dev/mid/late) |
| `kc` | float | **OUI** | FAO-56 / A6 | Coefficient cultural du jour |
| `et0_pm_mm` | float | **OUI** | A2 ET0 Forecast | Évapotranspiration de référence |
| `rain_prob_1d` | float | **OUI** | A4 Rain Intelligence | Probabilité pluie J+1 |
| `rain_mm_obs` | float | **OUI** | CHIRPS / pluviomètre | Pluie observée (mm) |
| `soilnowcast_root_pct` | float | **OUI** | A1 SoilNowcast | Prédiction humidité satellite |
| `t_max_c` | float | **OUI** | NASA POWER | Température max jour |
| `wind_2m_ms` | float | Optionnel | NASA POWER | Vent à 2 m |
| `sand_pct` | float | **OUI** | iSDAsoil | Teneur en sable |
| `clay_pct` | float | **OUI** | iSDAsoil | Teneur en argile |
| `fc_ptf_pct` | float | **OUI** | PTF calculé | Capacité au champ |
| `wp_ptf_pct` | float | **OUI** | PTF calculé | Point de flétrissement |
| **`irrigation_need_mm`** | **float** | **CIBLE** | Bilan hydrique expert | Besoin irrigation calculé (cible) |

**Variables obligatoires** : 14
**Variables optionnelles** : 4
**Cible** : `irrigation_need_mm` (régression continue, mm/jour)

### Volume

| Seuil | Lignes | Justification |
|-------|--------|---------------|
| **Minimal** | 5 000 | 10 parcelles × 1 saison (150 jours) × 3-4 lectures/jour |
| **Recommandé** | 50 000 | 30 parcelles × 2 saisons × 3 lectures/jour |
| **Optimal** | 200 000 | 50+ parcelles × 3+ saisons, multi-région |

### Métriques d'évaluation

| Métrique | Seuil production | Justification |
|----------|-----------------|---------------|
| **RMSE** | < 3 mm/jour | Erreur acceptable pour dose irrigation |
| **MAE** | < 2 mm/jour | Erreur absolue moyenne |
| **R²** | > 0.85 | Cohérence avec SoilNowcast (R² = 0.835) |
| **MAPE par culture** | < 15% | Fiabilité par type de culture |
| **Biais saisonnier** | < 1 mm | Pas de surestimation systématique |

### Modèles candidats

1. **LightGBM** (baseline, champion SoilNowcast)
2. **XGBoost** (robustesse, champion Price Forecast)
3. **CatBoost** (champion ET0/Rain, gestion native catégorielles)
4. **Random Forest** (interprétabilité, benchmark)
5. **Réseau de neurones séquentiel** (LSTM/GRU si séries temporelles suffisantes)

### Pipeline d'entraînement

```
1. Jointure capteurs terrain + SoilNowcast + Rain Intelligence + ET0
2. Feature engineering :
   - deficit_mm = (fc_ptf_pct - soil_moisture_30cm_pct) × profondeur_racinaire
   - etc_mm = et0_pm_mm × kc
   - rain_effective_mm = rain_mm_obs × 0.8 (ruissellement 20%)
   - delta_moisture = soil_moisture_t - soil_moisture_t-1
   - soilnowcast_residual = soil_moisture_30cm_pct - soilnowcast_root_pct
3. Validation : GroupKFold k=5, groupe = parcel_id
4. Optimisation Optuna (100 trials)
5. SHAP values + erreurs par groupe
```

### Pipeline d'inférence

```
Input : parcel_id + timestamp
  → Requête SoilNowcast → soil_moisture prédite
  → Requête Rain Intelligence → rain_prob
  → Requête ET0 → et0_pm_mm
  → Lookup FAO-56 → kc selon crop_stage
  → Feature engineering identique
  → Modèle Irrigation ML → irrigation_need_mm
  → Post-processing : max(0, irrigation_need_mm)
  → Réponse : dose (mm), confiance, explication
Latence cible : < 200 ms
```

### Critères de passage en production

- [ ] R² > 0.85 sur validation spatiale (parcelles non vues)
- [ ] MAE < 2 mm sur minimum 3 cultures différentes
- [ ] Zéro recommandation d'irrigation quand pluie > 10 mm prévue à 80%+
- [ ] Test sur 2 saisons complètes (sèche + hivernage)
- [ ] Validation agronomique par expert ISRA/ANCAR
- [ ] Monitoring drift sur 30 jours en production shadow

---

## B2. Water Savings

### Objectif

Quantifier les économies d'eau réalisées grâce à l'irrigation intelligente SmartAgri, par rapport à l'irrigation traditionnelle (gravitaire, aspersion non pilotée).

### Cas d'usage

- Calcul ROI pour agriculteurs et investisseurs
- Rapport d'impact environnemental
- Benchmark régional des pratiques

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `parcel_id` | string | **OUI** | Terrain | Identifiant parcelle |
| `date` | date | **OUI** | Système | Jour de mesure |
| `water_applied_mm` | float | **OUI** | Compteur | Volume réel appliqué (mm) |
| `water_traditional_mm` | float | **OUI** | Pratique locale | Volume pratique traditionnelle (mm) |
| `irrigation_method` | string | **OUI** | Observation | gravitaire/goutte/aspersion/SmartAgri |
| `crop_type` | string | **OUI** | Agriculteur | Culture en place |
| `crop_stage` | string | **OUI** | Observation/A6 | Stade phénologique |
| `yield_kg_ha` | float | **OUI** | Récolte | Rendement final (kg/ha) |
| `yield_quality` | string | Optionnel | Expert | Qualité (A/B/C) |
| `parcel_area_ha` | float | **OUI** | GPS/cadastre | Surface de la parcelle |
| `soil_type` | string | **OUI** | Analyse/iSDAsoil | Type de sol dominant |
| `et0_pm_mm` | float | **OUI** | A2 ET0 Forecast | Cumul ET0 période |
| `rain_total_mm` | float | **OUI** | CHIRPS/pluvio | Cumul pluie période |
| `soilnowcast_mean_pct` | float | **OUI** | A1 SoilNowcast | Humidité moyenne période |
| `cost_water_fcfa` | float | Optionnel | Facture/estimation | Coût de l'eau (FCFA) |
| `cost_energy_fcfa` | float | Optionnel | Facture | Coût énergie pompage |
| **`water_saving_pct`** | **float** | **CIBLE** | Calculé | (traditional - applied) / traditional × 100 |

**Variables obligatoires** : 12
**Variables optionnelles** : 4
**Cible** : `water_saving_pct` (régression, %)

### Volume

| Seuil | Lignes | Justification |
|-------|--------|---------------|
| **Minimal** | 500 | 20 parcelles × 1 saison, pairées (SmartAgri vs traditionnel) |
| **Recommandé** | 5 000 | 50 parcelles × 2 saisons × paires |
| **Optimal** | 20 000 | 100+ parcelles, multi-région, multi-saison |

### Métriques d'évaluation

| Métrique | Seuil production | Justification |
|----------|-----------------|---------------|
| **RMSE** | < 5% points | Précision sur l'économie estimée |
| **R²** | > 0.80 | Fiabilité de la prédiction |
| **Biais** | < 2% points | Pas de surestimation des économies |
| **IC 95%** | reporté | Intervalle de confiance obligatoire par prédiction |

### Modèles candidats

1. **LightGBM / XGBoost / CatBoost** (régression standard)
2. **Modèle à effets mixtes** (effet parcelle aléatoire)
3. **Causal Inference** (propensity score matching SmartAgri vs traditionnel)
4. **Bilan hydrique physique** (ETc - pluie effective = besoin net)

### Pipeline d'entraînement

```
1. Appariement parcelles SmartAgri ↔ parcelles traditionnelles (même zone, même sol, même culture)
2. Calcul water_saving_pct = (traditional - applied) / traditional × 100
3. Feature engineering : WUE = yield / water, ETc/ET0 ratio
4. Validation : Leave-One-Parcel-Out (LOPO) ou GroupKFold
5. Analyse de sensibilité par méthode d'irrigation
```

### Pipeline d'inférence

```
Input : parcel_id + période + méthode
  → Historique consommation (compteur)
  → Baseline traditionnelle (modèle ou référence zonale)
  → Calcul saving + IC 95%
Latence : batch quotidien acceptable
```

### Critères de passage en production

- [ ] Minimum 2 saisons complètes de données pairées
- [ ] R² > 0.80 sur parcelles non vues
- [ ] Validation croisée avec bilan hydrique physique (écart < 10%)
- [ ] Intervalle de confiance systématique sur chaque prédiction
- [ ] Audit externe des chiffres d'économie avant communication

---

## B3. Pump Health

### Objectif

Prédire les pannes de pompes d'irrigation avant qu'elles ne surviennent (maintenance prédictive), afin de réduire les temps d'arrêt et les pertes de récolte.

### Cas d'usage

- Alerte préventive 24-72h avant panne
- Planification de maintenance
- Estimation durée de vie résiduelle (RUL)
- Diagnostic de cause de défaillance

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `pump_id` | string | **OUI** | Registre | Identifiant unique pompe |
| `timestamp` | datetime | **OUI** | Capteur/PLC | Horodatage mesure (Hz ou min) |
| `current_a` | float | **OUI** | Capteur ampéremétrique | Courant moteur (A) |
| `voltage_v` | float | **OUI** | Capteur tension | Tension alimentation (V) |
| `vibration_mm_s` | float | **OUI** | Accéléromètre | Vibration RMS (mm/s) |
| `temperature_c` | float | **OUI** | Sonde PT100/NTC | Température moteur (°C) |
| `pressure_bar` | float | **OUI** | Capteur pression | Pression refoulement (bar) |
| `flow_rate_m3h` | float | **OUI** | Débitmètre | Débit (m³/h) |
| `rpm` | float | Optionnel | Tachymètre | Vitesse rotation (tr/min) |
| `noise_db` | float | Optionnel | Microphone | Niveau sonore (dB) |
| `power_factor` | float | Optionnel | Analyseur réseau | Facteur de puissance |
| `pump_model` | string | **OUI** | Registre | Modèle de pompe |
| `pump_age_days` | int | **OUI** | Registre | Âge de la pompe (jours) |
| `last_maintenance_days` | int | **OUI** | Log maintenance | Jours depuis dernière maintenance |
| `operating_hours` | float | **OUI** | Compteur horaire | Heures de fonctionnement cumulées |
| `ambient_temp_c` | float | Optionnel | A2 / NASA POWER | Température ambiante |
| **`failure_within_72h`** | **bool** | **CIBLE classif** | Log pannes | Panne dans les 72h suivantes |
| **`rul_hours`** | **float** | **CIBLE régress** | Log pannes | Durée de vie résiduelle (h) |
| **`failure_type`** | **string** | **CIBLE multi** | Diagnostic | Type de panne (mécanique/électrique/hydraulique/colmatage) |

**Variables obligatoires** : 12
**Variables optionnelles** : 4
**Cibles** : 3 (classification binaire, régression RUL, classification multi-classes)

### Volume

| Seuil | Lignes | Justification |
|-------|--------|---------------|
| **Minimal** | 50 000 | 20 pompes × 6 mois × 15 mesures/jour, minimum 30 événements panne |
| **Recommandé** | 500 000 | 50 pompes × 2 ans × mesures horaires |
| **Optimal** | 5 000 000 | 100+ pompes, mesures haute fréquence, multi-marque |

**Contrainte critique** : ratio pannes/normal très déséquilibré (< 1%). Minimum 30 événements de panne réels pour entraîner.

### Métriques d'évaluation

| Métrique | Cible classif | Cible RUL | Justification |
|----------|--------------|-----------|---------------|
| **Recall** | > 0.90 | — | Manquer une panne = perte récolte |
| **Precision** | > 0.50 | — | Fausses alertes tolérables (maintenance préventive) |
| **F1** | > 0.65 | — | Compromis recall/precision |
| **RMSE RUL** | — | < 50h | Précision estimation durée de vie |
| **Coût asymétrique** | 10:1 | — | FN coûte 10× plus qu'un FP |

### Modèles candidats

1. **XGBoost + SMOTE** (déséquilibre, interprétabilité)
2. **LightGBM + focal loss** (déséquilibre natif)
3. **Isolation Forest** (pré-filtre anomalies capteurs)
4. **LSTM / Transformer temporel** (séquences capteurs haute fréquence)
5. **Survival Analysis** (Cox proportional hazards pour RUL)
6. **Random Forest** (baseline interprétable)

### Pipeline d'entraînement

```
1. Collecte séries temporelles capteurs + logs de maintenance
2. Labellisation : failure_within_72h depuis logs pannes
3. Feature engineering :
   - Rolling stats (mean, std, max sur 1h/6h/24h/7j)
   - Dérivées (delta_current, delta_vibration)
   - Ratio : power_consumed / flow_rate (efficacité)
   - Heures depuis dernier redémarrage
4. Gestion déséquilibre : SMOTE / undersampling / class_weight
5. Validation : GroupKFold groupe=pump_id (pas de fuite temporelle)
6. Optimisation seuil de décision asymétrique
```

### Pipeline d'inférence

```
Input : pump_id + mesures temps réel
  → Buffer 24h de mesures
  → Feature engineering rolling
  → Modèle classif → P(panne 72h)
  → Modèle RUL → heures restantes estimées
  → Seuils : P > 0.3 → WATCH, P > 0.6 → WARNING, P > 0.8 → CRITICAL
  → Alerte SMS/push + recommandation maintenance
Latence : < 500 ms (temps réel)
Fréquence : toutes les 15 min
```

### Critères de passage en production

- [ ] Recall > 0.90 sur au moins 30 événements de panne réels
- [ ] Test sur minimum 3 modèles de pompes différents
- [ ] Validation sur 6 mois consécutifs (pas uniquement rétrospectif)
- [ ] Faux positifs < 2/semaine/pompe (acceptabilité terrain)
- [ ] Intégration alerte SMS/push fonctionnelle
- [ ] Procédure de recalibration saisonnière documentée

---

## B4. Disease Detection

### Objectif

Détecter les maladies des cultures (fongiques, bactériennes, virales) à partir de photos prises au smartphone, en identifiant la maladie et en recommandant un traitement.

### Cas d'usage

- Diagnostic par photo (smartphone)
- Identification de la maladie spécifique
- Recommandation de traitement (via SmartAgri Knowledge)
- Suivi de propagation à l'échelle parcelle/région

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `image_id` | string | **OUI** | Système | Identifiant unique image |
| `image_path` | string | **OUI** | Smartphone | Chemin fichier image (JPEG/PNG) |
| `image_width` | int | **OUI** | Métadonnées | Largeur pixels (min 640) |
| `image_height` | int | **OUI** | Métadonnées | Hauteur pixels (min 640) |
| `capture_date` | datetime | **OUI** | EXIF/saisie | Date de prise de vue |
| `gps_lat` | float | Optionnel | EXIF/GPS | Latitude |
| `gps_lon` | float | Optionnel | EXIF/GPS | Longitude |
| `crop_type` | string | **OUI** | Agriculteur | Culture (tomate, oignon, riz, mil...) |
| `plant_part` | string | **OUI** | Annotateur | Partie photographiée (feuille/tige/fruit/racine) |
| `ndvi_anomaly` | float | Optionnel | A7 NDVI Anomaly | Score anomalie NDVI cellule |
| `humidity_pct` | float | Optionnel | A1 SoilNowcast | Humidité sol prédite |
| `rain_7d_mm` | float | Optionnel | CHIRPS | Cumul pluie 7 jours |
| **`disease_name`** | **string** | **CIBLE** | Expert phytopathologiste | Nom de la maladie |
| **`disease_class`** | **string** | **CIBLE** | Expert | Classe : healthy/fungal/bacterial/viral/nutrient/pest |
| **`severity`** | **string** | **CIBLE** | Expert | Sévérité : mild/moderate/severe |

**Variables obligatoires** : 8
**Variables optionnelles** : 4
**Cibles** : 3 (classification multi-classes, sous-catégorie, sévérité)

### Classes cibles prioritaires (cultures Sénégal)

| Culture | Maladies prioritaires |
|---------|----------------------|
| **Tomate** | Mildiou, oïdium, flétrissement bactérien, alternariose |
| **Oignon** | Pourriture basale, mildiou, thrips (dégâts visibles) |
| **Riz** | Pyriculariose, brunissure, bactériose |
| **Mil/Sorgho** | Charbon, ergot, mildiou |
| **Mangue** | Anthracnose, bactériose, cochenilles |
| **Arachide** | Cercosporiose, rouille, aflatoxine (symptômes foliaires) |

### Volume

| Seuil | Images | Justification |
|-------|--------|---------------|
| **Minimal** | 2 000 | 200 images × 10 classes (7 maladies + 3 cultures saines) |
| **Recommandé** | 10 000 | 500 images × 20 classes, multi-stade |
| **Optimal** | 50 000 | Transfer learning efficace, fine-tuning solide |

**Contrainte critique** : annotation par expert phytopathologiste obligatoire. Pas d'auto-labellisation.

### Métriques d'évaluation

| Métrique | Seuil production | Justification |
|----------|-----------------|---------------|
| **Accuracy top-1** | > 0.85 | Identification correcte |
| **Accuracy top-3** | > 0.95 | Maladie dans les 3 premières propositions |
| **F1 macro** | > 0.80 | Équilibre entre classes rares et fréquentes |
| **Recall "severe"** | > 0.90 | Ne pas manquer une maladie grave |
| **Confusion healthy↔disease** | < 5% | Éviter faux diagnostics sur plante saine |

### Modèles candidats

1. **EfficientNet-B0** (baseline, léger, bon transfer learning)
2. **MobileNetV3** (optimisé smartphone, < 5 Mo)
3. **ResNet-18** (robustesse, benchmark académique)
4. **ConvNeXt-Tiny** (moderne, performance/taille)
5. **YOLOv8-cls** (classification rapide, même famille que détection)
6. **Vision Transformer ViT-Tiny** (si volume > 10K images)

### Pipeline d'entraînement

```
1. Collecte terrain : photos smartphone en conditions réelles
2. Annotation : expert phytopathologiste (double annotation si possible)
3. Nettoyage : suppression floues, mal cadrées, < 640px
4. Augmentation : rotation, flip, brightness, crop, Mixup
5. Pré-entraînement : ImageNet → fine-tune sur dataset terrain
6. Validation : stratified split 70/20/10, pas de fuite par parcelle
7. Optimisation : learning rate, augmentation, regularization
8. Export : TFLite (INT8 < 10 Mo) + ONNX
```

### Pipeline d'inférence

```
Input : photo smartphone (JPEG)
  → Redimensionnement 224×224 / 640×640
  → Normalisation ImageNet
  → Modèle classification → top-3 classes + probabilités
  → Filtre confiance : < 0.4 → "incertain, consultez un expert"
  → Enrichissement : SmartAgri Knowledge → traitement recommandé
  → Réponse : maladie, sévérité, traitement, confiance
Latence : < 100 ms (on-device TFLite) ou < 500 ms (API)
```

### Critères de passage en production

- [ ] Minimum 2 000 images annotées par expert
- [ ] F1 macro > 0.80 sur 10+ classes
- [ ] Test sur 3+ cultures différentes en conditions terrain réelles
- [ ] Modèle < 10 Mo (TFLite INT8) fonctionnel sur smartphone milieu de gamme
- [ ] Zéro recommendation de traitement chimique sans diagnostic confirmé > 70%
- [ ] Validation par phytopathologiste ISRA/ANCAR sur 100 cas de test

---

## B5. Pest Prediction

### Objectif

Prédire l'apparition de ravageurs (insectes, rongeurs, oiseaux) 3 à 14 jours à l'avance, en combinant données météo, phénologie et historique d'observations.

### Cas d'usage

- Alerte précoce ravageurs (criquets, chenilles, mouches blanches)
- Recommandation de traitement préventif
- Optimisation du timing de traitement (réduction pesticides)
- Cartographie du risque ravageurs par région

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `observation_id` | string | **OUI** | Système | Identifiant observation |
| `date` | date | **OUI** | Observateur | Date d'observation |
| `cell_id` | int | **OUI** | Grille SmartAgri | Cellule 0,05° |
| `parcel_id` | string | Optionnel | Terrain | Identifiant parcelle si disponible |
| `pest_species` | string | **OUI** | Expert entomologiste | Espèce identifiée |
| `pest_category` | string | **OUI** | Classification | insecte/acarien/rongeur/oiseau/nematode |
| `severity_score` | int | **OUI** | Observation | Échelle 0-5 (0=absent, 5=infestation sévère) |
| `trap_count` | int | Optionnel | Piège | Nombre d'individus capturés |
| `crop_type` | string | **OUI** | Observation | Culture attaquée |
| `crop_stage` | string | **OUI** | Observation/A6 | Stade phénologique |
| `t_mean_c` | float | **OUI** | NASA POWER | Température moyenne J |
| `t_min_c` | float | **OUI** | NASA POWER | Température min |
| `rh_mean_pct` | float | **OUI** | NASA POWER | Humidité relative moyenne |
| `rain_7d_mm` | float | **OUI** | CHIRPS | Cumul pluie 7 jours |
| `rain_prob_7d` | float | **OUI** | A4 Rain Intelligence | Probabilité pluie à 7 jours |
| `wind_2m_ms` | float | **OUI** | NASA POWER | Vent moyen |
| `ndvi` | float | Optionnel | A7 Sentinel-2 | NDVI de la cellule |
| `ndvi_anomaly_flag` | bool | Optionnel | A7 NDVI Anomaly | Anomalie végétation détectée |
| `soil_moisture_pct` | float | Optionnel | A1 SoilNowcast | Humidité sol prédite |
| **`pest_outbreak_7d`** | **bool** | **CIBLE classif** | Observations suivantes | Infestation dans les 7 jours |
| **`severity_7d`** | **int** | **CIBLE régress** | Observations suivantes | Score sévérité à J+7 |

**Variables obligatoires** : 13
**Variables optionnelles** : 4
**Cibles** : 2 (classification binaire, régression sévérité)

### Ravageurs prioritaires (Sénégal)

| Ravageur | Cultures | Conditions favorables |
|----------|----------|----------------------|
| **Criquet pèlerin** | Mil, sorgho, maraîchage | T > 30°C, humidité après sécheresse |
| **Chenille légionnaire** | Maïs, mil, sorgho | Début hivernage, T 25-30°C |
| **Mouche blanche** | Tomate, aubergine | Saison sèche chaude, T > 35°C |
| **Thrips** | Oignon | Saison sèche, RH < 40% |
| **Noctuelle de la tomate** | Tomate, poivron | Après pluies, T 20-28°C |
| **Foreur de tiges** | Riz, mil | Stade montaison, T > 25°C |

### Volume

| Seuil | Lignes | Justification |
|-------|--------|---------------|
| **Minimal** | 2 000 | 50 points × 2 cultures × 20 semaines, minimum 200 événements outbreak |
| **Recommandé** | 10 000 | 100 points × 2 ans × relevé hebdomadaire |
| **Optimal** | 50 000 | Réseau national sentinelle, multi-année |

### Métriques d'évaluation

| Métrique | Seuil production | Justification |
|----------|-----------------|---------------|
| **AUC** | > 0.85 | Discrimination outbreak/normal |
| **Recall** | > 0.85 | Ne pas manquer une infestation |
| **Precision** | > 0.50 | Traitement préventif acceptable |
| **F1** | > 0.65 | Équilibre |
| **Lead time** | > 5 jours | Temps de préparation du traitement |

### Modèles candidats

1. **CatBoost** (catégorielles natives : pest_species, crop_type)
2. **XGBoost + feature engineering temporel**
3. **LightGBM** (rapidité, benchmark)
4. **Logistic Regression** (baseline interprétable)
5. **Bayesian Network** (raisonnement causal pest ↔ weather)

### Pipeline d'entraînement

```
1. Collecte observations terrain (réseau sentinelle ANCAR/DPV)
2. Jointure météo (NASA POWER, CHIRPS) + phénologie (A6 Crop Calendar)
3. Feature engineering :
   - Growing Degree Days (GDD) cumulés
   - Jours consécutifs T > seuil thermique espèce
   - Humidité × température (interaction)
   - Historique : même espèce même cellule année N-1
4. Gestion déséquilibre : SMOTE + class_weight
5. Validation : GroupKFold groupe=cell_id, respect temporel
6. SHAP par espèce de ravageur
```

### Pipeline d'inférence

```
Input : cell_id + crop_type + date
  → Météo NASA POWER 14 jours (obs + prévision)
  → Rain Intelligence probabilités 1-3 jours
  → Crop Calendar stade actuel
  → Feature engineering
  → Modèle → P(outbreak 7 jours) par espèce
  → Seuils espèce-spécifiques
  → Alerte + recommandation (via Knowledge)
Latence : batch quotidien acceptable
```

### Critères de passage en production

- [ ] Minimum 2 000 observations annotées par entomologiste terrain
- [ ] AUC > 0.85 sur minimum 4 espèces de ravageurs
- [ ] Validation sur 2 saisons (sèche + hivernage)
- [ ] Lead time moyen > 5 jours sur alertes confirmées
- [ ] Zéro recommandation de pesticide sans espèce identifiée > 60% confiance
- [ ] Intégration réseau sentinelle DPV pour feedback continu

---

## B6. Soil Calibration

### Objectif

Calibrer et corriger les prédictions de SoilNowcast (proxy satellite) avec des mesures de capteurs d'humidité du sol réels, pour chaque type de sol et chaque profondeur.

### Cas d'usage

- Correction locale de SoilNowcast par mesures terrain
- Estimation de la précision réelle par zone
- Transfer learning vers de nouvelles parcelles
- Détection de dérive de capteurs

### Schéma du dataset attendu

| Variable | Type | Obligatoire | Source | Description |
|----------|------|-------------|--------|-------------|
| `measurement_id` | string | **OUI** | Système | Identifiant mesure |
| `timestamp` | datetime | **OUI** | Capteur | Horodatage UTC |
| `cell_id` | int | **OUI** | Grille SmartAgri | Cellule 0,05° |
| `parcel_id` | string | **OUI** | Terrain | Identifiant parcelle |
| `depth_cm` | int | **OUI** | Installation | Profondeur capteur (10/30/60 cm) |
| `sensor_type` | string | **OUI** | Fiche technique | TDR/capacitif/tensiomètre |
| `sensor_model` | string | **OUI** | Fiche technique | Marque et modèle exact |
| `soil_moisture_measured_pct` | float | **OUI** | Capteur terrain | Humidité mesurée (% volumique) |
| `soilnowcast_predicted_pct` | float | **OUI** | A1 SoilNowcast | Prédiction satellite |
| `sand_pct` | float | **OUI** | iSDAsoil/labo | Teneur en sable |
| `clay_pct` | float | **OUI** | iSDAsoil/labo | Teneur en argile |
| `soc_g_kg` | float | **OUI** | iSDAsoil/labo | Carbone organique |
| `bulk_density_g_cm3` | float | **OUI** | iSDAsoil/labo | Densité apparente |
| `soil_lab_moisture_pct` | float | Optionnel | Analyse labo | Humidité gravimétrique (référence) |
| `rain_24h_mm` | float | **OUI** | CHIRPS/pluvio | Pluie dernières 24h |
| `t_mean_c` | float | **OUI** | NASA POWER | Température moyenne |
| `land_use` | string | **OUI** | Observation | Occupation du sol (culture/jachère/forêt) |
| **`bias_pct`** | **float** | **CIBLE régress** | Calculé | soilnowcast - measured (biais en %) |
| **`correction_factor`** | **float** | **CIBLE régress** | Calculé | measured / soilnowcast |

**Variables obligatoires** : 15
**Variables optionnelles** : 1
**Cibles** : 2 (biais et facteur de correction, régressions continues)

### Volume

| Seuil | Lignes | Justification |
|-------|--------|---------------|
| **Minimal** | 5 000 | 10 capteurs × 1 saison × 3 lectures/jour × 150 jours |
| **Recommandé** | 30 000 | 30 capteurs × 2 saisons × 3 lectures/jour |
| **Optimal** | 100 000 | 50+ capteurs, multi-profondeur, multi-type sol, 2+ ans |

**Contrainte** : mesures gravimétriques labo mensuelles obligatoires pour calibrer les capteurs eux-mêmes.

### Métriques d'évaluation

| Métrique | Seuil production | Justification |
|----------|-----------------|---------------|
| **RMSE biais** | < 3% points | Précision de la correction |
| **MAE biais** | < 2% points | Erreur absolue acceptable |
| **R² correction** | > 0.90 | Fiabilité de la calibration |
| **Biais résiduel** | < 0.5% point | Correction quasi-parfaite en moyenne |
| **Stabilité temporelle** | CV < 10% | Pas de dérive de la correction sur 6 mois |

### Modèles candidats

1. **Régression linéaire par type de sol** (baseline interprétable)
2. **LightGBM** (non-linéarité sol × profondeur × saison)
3. **CatBoost** (catégorielles sensor_type, soil_type)
4. **Quantile Regression** (intervalle d'incertitude sur la correction)
5. **Bayesian Ridge** (estimation d'incertitude native)
6. **Kalman Filter adaptatif** (correction temps réel avec update séquentiel)

### Pipeline d'entraînement

```
1. Collecte paires (mesure capteur, prédiction SoilNowcast) sur même timestamp
2. Contrôle qualité capteurs : suppression aberrants, dérive, saturation
3. Calcul cibles : bias = soilnowcast - measured, correction = measured / soilnowcast
4. Feature engineering :
   - Interaction sol (sand×clay, soc×bulk_density)
   - Saison (doy_sin, doy_cos)
   - État hydrique (jours depuis dernière pluie > 5mm)
   - Profondeur × type sol
5. Validation : GroupKFold groupe=parcel_id
6. Analyse résiduelle par type de sol et profondeur
```

### Pipeline d'inférence

```
Input : cell_id + parcel_id + timestamp
  → SoilNowcast prédiction brute
  → Lookup type sol, profondeur capteur
  → Modèle calibration → correction_factor
  → soil_moisture_calibrated = soilnowcast × correction_factor
  → IC 95% sur la valeur calibrée
  → Monitoring : alerte si |correction| > 2× historique (dérive capteur)
Latence : < 50 ms (lookup + multiplication)
```

### Critères de passage en production

- [ ] Minimum 5 000 paires mesure/prédiction sur 10+ parcelles
- [ ] RMSE biais < 3% sur sol sableux ET argileux
- [ ] R² correction > 0.90 sur parcelles non vues
- [ ] Mesures gravimétrique labo validant les capteurs (mensuel)
- [ ] Détection de dérive capteur fonctionnelle (alerte < 48h)
- [ ] Recalibration automatique trimestrielle
- [ ] Validation croisée avec SoilNowcast R² = 0.835 : la correction doit améliorer, pas dégrader

---

## Synthèse : Matrice de faisabilité

| Modèle | Données terrain requises | Volume min | Dépendance Classe A | Bloqueur principal |
|--------|--------------------------|------------|---------------------|-------------------|
| **B1 Irrigation ML** | Capteurs sol + compteur eau | 5 000 | A1, A2, A4, A6 | Installation capteurs |
| **B2 Water Savings** | Paires SmartAgri/traditionnel | 500 | A1, A2, A5 | Parcelles de comparaison |
| **B3 Pump Health** | Capteurs pompe (courant, vibration) | 50 000 | — | Instrumentation pompes |
| **B4 Disease Detection** | Photos annotées expert | 2 000 | A7 | Expert phytopathologiste |
| **B5 Pest Prediction** | Observations entomologiques | 2 000 | A4, A6, A7 | Réseau sentinelle |
| **B6 Soil Calibration** | Capteurs + labo | 5 000 | A1 | Installation capteurs |

### Ordre de déploiement recommandé

1. **B6 Soil Calibration** — améliore A1 SoilNowcast, bénéfice immédiat pour tous les autres modèles
2. **B1 Irrigation ML** — valeur métier directe, utilise B6 + A1 + A2 + A4
3. **B4 Disease Detection** — indépendant des capteurs, collecte photos possible immédiatement
4. **B2 Water Savings** — dépend de B1 fonctionnel
5. **B5 Pest Prediction** — dépend du réseau sentinelle
6. **B3 Pump Health** — nécessite instrumentation complète des pompes

### Coût estimé de collecte de données

| Modèle | Équipement | Durée minimale | Coût estimé (FCFA) |
|--------|-----------|----------------|-------------------|
| B1 | 10 capteurs TDR + 10 compteurs | 6 mois | 3-5 M |
| B2 | Même que B1 + parcelles témoin | 12 mois | 1-2 M (supplémentaire) |
| B3 | 20 kits capteurs pompe | 6 mois | 5-10 M |
| B4 | Smartphones + expert annotation | 3 mois | 1-2 M |
| B5 | Pièges + observateurs réseau | 12 mois | 2-3 M |
| B6 | 30 capteurs + analyses labo | 6 mois | 4-6 M |

---

*Document produit par SmartAgri92 / OctOpus — PAS Challenge 2026*
*Basé sur les métriques mesurées des 9 modèles Classe A entraînés.*
*Aucun entraînement lancé. Aucune donnée synthétique générée. Aucun faux label créé.*
