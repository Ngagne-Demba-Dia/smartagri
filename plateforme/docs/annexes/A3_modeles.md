# Annexe A3 — Modèles

> Confidentiel - réservé aux partenaires de travail.
> Fichier généré par `python -m agriml.catalog render` depuis `ml/catalog/*.yaml` — ne pas modifier à la main.

39 modèles. Chaque modèle donne ses trois variantes (compétition, production, compromis), ses données par niveau de nécessité, sa métrique d'acceptation et son repli. Légende des sources amont : ● obligatoire, ◐ recommandée, ○ optionnelle.

## Synthèse

| Id | Modèle | Cas d'usage | Nature | Version | Plateformes | Inférence | Programme OctOpus |
|---|---|---|---|---|---|---|---|
| `irr_et0` | Évapotranspiration de référence ET0 | IA-1 | physical | MVP | web:5, web:7, mobile | batch | — |
| `irr_water_balance` | Bilan hydrique FAO-56 par parcelle | IA-1 | physical | MVP | web:3, web:7, mobile, kit | batch | — |
| `soil_nowcast` | Prévision de l'humidité du sol à 1–48 h | IA-1 | ml | V2 | web:1, web:3, mobile | batch | soil_moisture_nowcast |
| `irr_need_24h` | Besoin d'irrigation à 24 h | IA-1 | ml | V2 | web:3, web:7, mobile, kit | batch | irrigation_need |
| `irr_scheduler` | Planification de l'irrigation sur 72 h (eau, énergie, tour d'eau) | IA-1 | optimisation | V3 | web:7, web:10, kit | batch | — |
| `wx_blend` | Prévision météo combinée par maille | IA-2 | statistics | MVP | web:1, web:5, mobile | batch | — |
| `wx_local_bias` | Correction du biais local au kit | IA-2 | ml | V2 | web:5, mobile, kit | batch | — |
| `wx_rain_prob` | Probabilité de pluie utile (>= 5 mm) à 24–72 h | IA-2 | ml | V2 | web:5, web:7, mobile | batch | — |
| `vis_quality` | Contrôle qualité des photos avant envoi | IA-3 | ml | MVP | mobile | edge | — |
| `vis_disease` | Diagnostic de maladies et ravageurs sur photo | IA-3 | deep_learning | V2 | web:8, mobile, kit | online | disease_image_classification |
| `vis_pest_count` | Comptage d'insectes sur pièges photographiés | IA-3 | deep_learning | V3 | web:8, kit | batch | — |
| `vis_canopy` | Couverture végétale et vigueur sur images du kit | IA-3 | statistics | V2 | web:4, web:6 | batch | — |
| `risk_rules` | Alertes phytosanitaires par règles expertes | IA-4 | rules | V1.1 | web:7, web:8, mobile | batch | — |
| `pest_phenology` | Développement des ravageurs par degrés-jours | IA-4 | physical | V2 | web:8, mobile | batch | — |
| `pest_risk_ml` | Probabilité de foyer à 7 jours | IA-4 | ml | V2 | web:4, web:8, mobile | batch | — |
| `asst_llm` | Assistant agronomique conversationnel | IA-5 | llm | MVP | web:12, mobile | online | — |
| `asst_retrieval` | Recherche documentaire du RAG | IA-5 | ml | MVP | web:12, mobile | online | — |
| `asst_guard` | Garde-fous de l'assistant | IA-5 | rules | MVP | web:12, mobile | online | — |
| `asst_asr` | Reconnaissance vocale wolof et pulaar | IA-5 | deep_learning | V2 | web:12, mobile | online | — |
| `asst_tts` | Restitution vocale des conseils | IA-5 | rules | V2 | mobile | edge | — |
| `npk_calibration` | Étalonnage du capteur NPK contre le laboratoire | IA-6 | statistics | V2 | web:6, kit | batch | — |
| `fert_reco` | Recommandation de fumure | IA-6 | rules | V1.1 | web:6, web:7, mobile, kit | batch | — |
| `reco_engine` | Moteur de recommandations | IA-7 | rules | MVP | web:1, web:7, mobile | batch | — |
| `reco_bandit` | Optimisation de la formulation et du moment d'envoi | IA-7 | ml | V3 | web:7, mobile | online | — |
| `ndvi_gapfill` | Reconstruction des séries NDVI sous nuages | IA-8 | statistics | V2 | web:4, web:6 | batch | — |
| `phenology_stage` | Stade phénologique par parcelle | IA-8 | statistics | V2 | web:3, web:6 | batch | — |
| `yield_forecast` | Prévision de rendement p10–p90 | IA-8 | ml | V3 | web:9, web:11, partner | batch | yield_forecast |
| `yield_crop_model` | Simulation de rendement par modèle de culture | IA-8 | physical | V3 | web:9, partner | batch | — |
| `crop_type_map` | Carte des cultures | IA-8 | ml | V3 | web:4, partner | batch | — |
| `field_boundary` | Détection des limites de parcelles | IA-8 | deep_learning | V3 | web:3, web:4, mobile | batch | — |
| `agri_risk_score` | Score de risque agricole pour le crédit | IA-9 | ml | V3 | partner | batch | — |
| `index_insurance` | Indice d'assurance paramétrique | IA-9 | statistics | V3 | partner | batch | — |
| `anomaly_rules` | Anomalies capteurs et pompe par règles | IA-10 | rules | MVP | web:1, web:10, mobile, kit | stream | — |
| `sm_calibration` | Étalonnage de la sonde d'humidité par type de sol | IA-10 | statistics | V1.1 | web:10, kit | batch | — |
| `anomaly_ml` | Anomalies multivariées des kits | IA-10 | ml | V2 | web:10, mobile | batch | — |
| `pump_health` | Maintenance prédictive de la pompe | IA-10 | ml | V2 | web:10, mobile | batch | — |
| `water_savings` | Mesure des économies d'eau et d'énergie (MRV) | TRANSVERSE | statistics | V1.1 | web:1, web:11, web:13, partner | batch | — |
| `price_forecast` | Prévision des prix agricoles à 4 semaines | TRANSVERSE | ml | V3 | web:11, web:13, mobile | batch | — |
| `salinity_risk` | Risque de salinisation des parcelles irriguées | TRANSVERSE | ml | V3 | web:4, web:6 | batch | — |

## IA-1 — Irrigation

### `irr_et0` — Évapotranspiration de référence ET0

- **Nature** : physical · **Version** : MVP · **Plateformes** : web:5, web:7, mobile
- **Données obligatoires** : `meteo.forecast_asof`, `meteo.grid_daily`
- **Données recommandées** : `features.local_weather_bias`
- **Données optionnelles** : `iot.telemetry_hourly`
- **Variables** : Tmin, Tmax ; humidité relative ; vent à 2 m ; rayonnement Rs ; altitude, latitude, jour julien
- **Métrique** : MAE ET0 journalière vs station de référence (mm/j) — seuil : MAE <= 0,6 mm/j sur les stations ANACIM ou TAHMO disponibles ; secondaires : biais moyen, MAE par saison (sèche, hivernage)
- **Entraînement** : Aucun apprentissage ; coefficient Hargreaves et biais Rs étalonnés par zone sur 3 ans ERA5-Land
- **Inférence** : batch · < 1 min pour 20 000 parcelles · 4 fois/j, après chaque émission ; repli : Hargreaves-Samani (Tmin, Tmax), puis climatologie décadaire ERA5-Land
- **Sources amont** : 11 ●, 8 ◐, 0 ○
- **Point de vigilance** : Sans station de référence au Sénégal, la MAE n'est mesurable que contre ERA5-Land, lui-même biaisé

| Variante | Candidat |
|---|---|
| Compétition | Penman-Monteith FAO-56 sur prévision multi-modèles corrigée du biais local, Rs CM SAF |
| Production | Penman-Monteith FAO-56 sur IFS (ECMWF Open Data), repli Hargreaves-Samani |
| Compromis | Penman-Monteith FAO-56 sur IFS + biais moyen glissant 30 j par maille |

### `irr_water_balance` — Bilan hydrique FAO-56 par parcelle

- **Nature** : physical · **Version** : MVP · **Plateformes** : web:3, web:7, mobile, kit
- **Données obligatoires** : `iot.telemetry_hourly`, `iot.irrigation_events`, `agronomie.crop_cycles`, `agronomie.crop_params`, `sols.field_profile`, `meteo.forecast_asof`, `meteo.grid_daily`
- **Données recommandées** : `features.rain_events`, `sols.lab_results`
- **Données optionnelles** : `satellite.field_indices`
- **Variables** : Kc par stade ; profondeur racinaire Zr ; fraction p ; TAW et RAW ; pluie efficace 0,8 x P ; humidité mesurée pour recalage ; seuils conseillés start/stop (CC et PF par pédotransfert)
- **Modèles amont** : `irr_et0`
- **Métrique** : RMSE entre déficit prédit et humidité mesurée à J+1 (points de %) — seuil : RMSE <= 5 points ; aucune dose hors bornes (0 <= dose <= TAW) ; secondaires : jours en stress (teneur < RAW), m³ par tonne récoltée
- **Entraînement** : Paramètres FAO-56 et ISRA ; p et Zr étalonnés par culture sur les parcelles pilotes
- **Inférence** : batch · < 5 min · horaire et après chaque émission ; repli : seuils du firmware (threshold_start_pct, threshold_stop_pct)
- **Sources amont** : 33 ●, 0 ◐, 6 ○
- **Point de vigilance** : Une seule sonde par parcelle : le recalage suppose une parcelle homogène. Les seuils conseillés s'affichent sur la page locale du kit à côté du réglage choisi, sans le remplacer

| Variante | Candidat |
|---|---|
| Compétition | FAO-56 double Kc (Kcb + Ke) avec assimilation de l'humidité capteur (filtre de Kalman d'ensemble) |
| Production | FAO-56 Kc simple, recalé chaque jour sur l'humidité mesurée |
| Compromis | Kc simple recalé + Kc dérivé du NDVI dès que Sentinel-2 est disponible |

### `soil_nowcast` — Prévision de l'humidité du sol à 1–48 h

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:1, web:3, mobile
- **Données obligatoires** : `features.soil_nowcast`
- **Données recommandées** : `features.local_weather_bias`
- **Données optionnelles** : `satellite.field_indices`
- **Variables** : humidité passée (retards 1–72 h) ; pompe en marche ; pluie, T et HR passées ; ET0 prévue ; distance au seuil de démarrage ; capacité au champ, point de flétrissement
- **Modèles amont** : `irr_et0`
- **Programme OctOpus** : `soil_moisture_nowcast`
- **Métrique** : RMSE à 24 h (points de %) — seuil : skill >= 20 % vs persistance à 24 h sur le holdout figé ; secondaires : skill vs persistance par horizon, couverture de l'intervalle p10–p90
- **Entraînement** : Mensuel ; validation temporelle groupée par kit (programme OctOpus soil_moisture_nowcast)
- **Inférence** : batch · < 2 min · horaire ; repli : persistance, puis bilan hydrique irr_water_balance
- **Sources amont** : 28 ●, 2 ◐, 6 ○
- **Point de vigilance** : Le jeu existe dès le MVP mais il faut une saison complète (hivernage + saison sèche) pour entraîner

| Variante | Candidat |
|---|---|
| Compétition | Ensemble LightGBM direct multi-horizon + N-HiTS ou TFT, cible = delta |
| Production | LightGBM multi-horizon (1, 6, 24, 48 h) sur le delta, quantiles p10, p50, p90 |
| Compromis | LightGBM global + correction du biais résiduel glissant par kit |

### `irr_need_24h` — Besoin d'irrigation à 24 h

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:3, web:7, mobile, kit
- **Données obligatoires** : `features.irrigation_need`
- **Données recommandées** : `features.local_weather_bias`
- **Données optionnelles** : `features.rain_events`
- **Variables** : ET0, Kc, pluie efficace ; humidité et tendance ; TAW ; NDVI ; culture et stade ; texture du sol ; historique de pompage passé
- **Modèles amont** : `irr_et0`, `irr_water_balance`
- **Programme OctOpus** : `irrigation_need`
- **Métrique** : MAE du besoin à 24 h (mm) — seuil : MAE <= 3 mm sur le holdout (programme irrigation_need) ; régression <= 3 % par tranche ; secondaires : biais par culture et par zone, eau économisée vs parcelle témoin
- **Entraînement** : Hebdomadaire en saison ; validation temporelle purgée (72 h) groupée par parcelle
- **Inférence** : batch · < 5 min · toutes les 6 h ; repli : irr_water_balance, puis seuils du firmware
- **Sources amont** : 46 ●, 2 ◐, 0 ○
- **Point de vigilance** : La cible « besoin observé » dépend du débitmètre (V1.1) : sans lui, elle n'est qu'estimée

| Variante | Candidat |
|---|---|
| Compétition | Stacking LightGBM + CatBoost sur le résidu du bilan FAO-56, contraintes monotones |
| Production | LightGBM sur le résidu (besoin observé − bilan FAO-56), sortie bornée à la capacité au champ |
| Compromis | Bilan FAO-56 + correction LightGBM plafonnée à ±30 % |

### `irr_scheduler` — Planification de l'irrigation sur 72 h (eau, énergie, tour d'eau)

- **Nature** : optimisation · **Version** : V3 · **Plateformes** : web:7, web:10, kit
- **Données obligatoires** : `features.irrigation_need`, `economie.costs`
- **Données recommandées** : `iot.device_health`, `features.rain_events`
- **Données optionnelles** : `eau.water_quality`
- **Variables** : besoin prévu ; probabilité de pluie ; tarif énergie par heure ; débit de la pompe ; contraintes de tour d'eau et de main-d'œuvre
- **Modèles amont** : `irr_need_24h`, `soil_nowcast`, `wx_rain_prob`
- **Métrique** : m³ et kWh par parcelle et par campagne vs témoin — seuil : −20 % d'eau sans hausse des jours en stress (essai apparié) ; secondaires : jours en stress hydrique, coût énergie (FCFA)
- **Entraînement** : Pas d'apprentissage pour le MPC ; le RL reste en recherche
- **Inférence** : batch · < 1 min par exploitation · toutes les 6 h ; repli : irr_need_24h, puis seuils du firmware
- **Sources amont** : 50 ●, 0 ◐, 3 ○
- **Point de vigilance** : Le gain dépend de la flexibilité réelle (tour d'eau, solaire) : à mesurer avant d'optimiser

| Variante | Candidat |
|---|---|
| Compétition | MPC stochastique sur scénarios de pluie + RL hors ligne évalué de façon contrefactuelle |
| Production | MPC déterministe sur 72 h (programmation linéaire, OR-Tools) |
| Compromis | Règles + MPC 48 h, report automatique si P(pluie >= 5 mm) >= 60 % |

## IA-2 — Météo locale

### `wx_blend` — Prévision météo combinée par maille

- **Nature** : statistics · **Version** : MVP · **Plateformes** : web:1, web:5, mobile
- **Données obligatoires** : `meteo.forecast_asof`
- **Données recommandées** : `meteo.grid_daily`
- **Données optionnelles** : `meteo.stations_clean`
- **Variables** : prévisions IFS, AIFS, ICON, GFS par échéance ; heure d'émission ; climatologie de la maille
- **Métrique** : CRPS température et pluie J+1 à J+7 — seuil : CRPS <= meilleur modèle brut − 5 % ; secondaires : MAE Tmax, Tmin, score de Brier pluie >= 1 mm
- **Entraînement** : Mensuel, sur prévisions as-of (heure d'émission conservée) pour éviter toute fuite
- **Inférence** : batch · < 5 min · 4 fois/j ; repli : IFS brut, puis climatologie
- **Sources amont** : 3 ●, 8 ◐, 2 ○
- **Point de vigilance** : La vérité terrain est rare : ERA5 et CHIRPS lissent les orages convectifs du Sahel

| Variante | Candidat |
|---|---|
| Compétition | EMOS ou régression quantile par maille sur multi-modèles et ensembles ECMWF ENS |
| Production | Moyenne pondérée IFS, ICON, GFS ; poids appris par maille et par échéance sur l'historique as-of |
| Compromis | IFS seul + correction de biais mensuelle contre ERA5-Land |

### `wx_local_bias` — Correction du biais local au kit

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:5, mobile, kit
- **Données obligatoires** : `features.local_weather_bias`
- **Données recommandées** : `meteo.stations_clean`
- **Données optionnelles** : `geo.field_context`
- **Variables** : écart capteur − prévision (T, HR, pression) ; heure, saison ; altitude ; occupation du sol
- **Modèles amont** : `wx_blend`
- **Métrique** : MAE de la température de l'air à J+1 au kit (°C) — seuil : −15 % de MAE vs wx_blend ; secondaires : gain vs wx_blend
- **Entraînement** : Hebdomadaire, fenêtres glissantes
- **Inférence** : batch · < 2 min · 4 fois/j ; repli : wx_blend sans correction
- **Sources amont** : 11 ●, 0 ◐, 11 ○
- **Point de vigilance** : Le BME280 dans le boîtier chauffe au soleil : sans abri ventilé, on apprend le biais du boîtier

| Variante | Candidat |
|---|---|
| Compétition | Modèle bayésien hiérarchique par kit + krigeage des résidus entre kits |
| Production | Ridge ou LightGBM du résidu par kit, fenêtre glissante 30 j |
| Compromis | Biais moyen glissant par kit et par heure |

### `wx_rain_prob` — Probabilité de pluie utile (>= 5 mm) à 24–72 h

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:5, web:7, mobile
- **Données obligatoires** : `features.rain_events`
- **Données recommandées** : `meteo.grid_daily`
- **Données optionnelles** : `meteo.seasonal_outlook`
- **Variables** : fraction des membres ENS au-dessus du seuil ; pluie prévue moyenne ; mois ; zone climatique
- **Modèles amont** : `wx_blend`
- **Métrique** : Score de Brier P(pluie >= 5 mm) à 24 et 48 h — seuil : BSS >= 0,1 vs climatologie ; secondaires : diagramme de fiabilité, ROC-AUC
- **Entraînement** : Mensuel ; vérité CHIRPS, IMERG et stations
- **Inférence** : batch · < 2 min · 4 fois/j ; repli : fraction des membres, puis climatologie
- **Sources amont** : 11 ●, 0 ◐, 1 ○
- **Point de vigilance** : Les ensembles par Open-Meteo exigent l'offre Professional ; ECMWF Open Data ENS est l'alternative

| Variante | Candidat |
|---|---|
| Compétition | LightGBM multi-seuils sur 50 membres ENS, calibration isotone |
| Production | Régression logistique sur la fraction des membres >= seuil, calibration isotone |
| Compromis | Fraction brute des membres ENS >= seuil |

## IA-3 — Vision (photos)

### `vis_quality` — Contrôle qualité des photos avant envoi

- **Nature** : ml · **Version** : MVP · **Plateformes** : mobile
- **Données obligatoires** : `images.labelled`
- **Données optionnelles** : `images.public_reference`
- **Variables** : variance du laplacien (flou) ; histogramme (exposition) ; présence d'un organe végétal ; cadrage
- **Pré-entraînés (production)** : `vision_backbones`
- **Métrique** : Taux de rejet à tort (%) — seuil : rejet à tort <= 5 % ; photos inutilisables −50 % ; secondaires : part de photos inutilisables reçues
- **Entraînement** : Trimestriel ; annotations qualité faites par les conseillers
- **Inférence** : edge · < 150 ms sur Android d'entrée de gamme · à chaque photo ; repli : photo acceptée avec un drapeau qualité
- **Sources amont** : 3 ●, 0 ◐, 2 ○
- **Point de vigilance** : Le rejet doit rester explicable à l'écran (« trop flou ») sinon l'utilisateur abandonne

| Variante | Candidat |
|---|---|
| Compétition | MobileNetV3 multi-tâche (flou, exposition, organe) distillé d'un ViT |
| Production | Règles d'image + MobileNetV3-Small TFLite int8 |
| Compromis | Règles seules au MVP, classifieur dès 2 000 photos annotées |

### `vis_disease` — Diagnostic de maladies et ravageurs sur photo

- **Nature** : deep_learning · **Version** : V2 · **Plateformes** : web:8, mobile, kit
- **Données obligatoires** : `features.disease_images`
- **Données recommandées** : `phyto.reference`
- **Données optionnelles** : `features.pest_risk`
- **Variables** : image recadrée 224–384 px ; culture déclarée ; stade ; risque régional (a priori)
- **Pré-entraînés (production)** : `vision_backbones`
- **Programme OctOpus** : `disease_image_classification`
- **Métrique** : F1 macro sur le holdout terrain — seuil : F1 macro >= 0,80 ; rappel malade >= 0,90 ; ECE <= 0,05 ; secondaires : rappel de la classe « malade », ECE (calibration), taux d'abstention
- **Entraînement** : Mensuel en saison ; StratifiedGroupKFold par plante ; double étiquetage par deux conseillers
- **Inférence** : online · < 2 s serveur, < 300 ms mobile · à la demande ; repli : diagnostic par un conseiller (file d'attente) + fiche générique
- **Sources amont** : 6 ●, 2 ◐, 36 ○
- **Point de vigilance** : PlantVillage est photographié en laboratoire : sans photos de terrain locales, le F1 s'effondre. Le kit affiche seulement le verdict mis en cache (confiance calibrée, version, date), jamais calculé à bord

| Variante | Candidat |
|---|---|
| Compétition | Ensemble ConvNeXt, EfficientNetV2 et ViT (DINOv2 affiné), TTA, calibration |
| Production | EfficientNet-B0 ou MobileNetV3 affiné, ONNX ou TFLite int8, seuil d'abstention |
| Compromis | EfficientNet-B3 serveur + MobileNetV3 mobile ; abstention transmise au conseiller |

### `vis_pest_count` — Comptage d'insectes sur pièges photographiés

- **Nature** : deep_learning · **Version** : V3 · **Plateformes** : web:8, kit
- **Données obligatoires** : `features.pest_trap_images`
- **Données recommandées** : `phyto.reference`
- **Variables** : image du piège (ESP32-CAM) ; espèce ciblée par la phéromone ; date de pose
- **Pré-entraînés (production)** : `vision_backbones`
- **Métrique** : MAE du comptage par piège — seuil : MAE <= 2 insectes ou <= 15 % ; secondaires : mAP@0,5
- **Entraînement** : Par campagne ; boîtes annotées sur 1 000 images minimum
- **Inférence** : batch · < 10 s par image · 4 fois/j ; repli : comptage manuel
- **Sources amont** : 4 ●, 2 ◐, 0 ○
- **Point de vigilance** : Les détecteurs YOLO d'Ultralytics sont sous AGPL-3.0 : exclus sans licence commerciale

| Variante | Candidat |
|---|---|
| Compétition | Détection RT-DETR + comptage par carte de densité |
| Production | Détecteur léger sous licence permissive (RT-DETR Apache-2.0), comptage par piège |
| Compromis | Classifieur présence/absence + comptage manuel assisté dans l'app |

### `vis_canopy` — Couverture végétale et vigueur sur images du kit

- **Nature** : statistics · **Version** : V2 · **Plateformes** : web:4, web:6
- **Données obligatoires** : `images.espcam_series`
- **Données recommandées** : `satellite.field_indices`
- **Données optionnelles** : `images.drone_mosaics`
- **Variables** : indice ExG et ExGR ; fraction de couvert ; tendance sur 7 j
- **Métrique** : IoU végétation — seuil : IoU >= 0,8 ; secondaires : corrélation fraction de couvert vs NDVI Sentinel-2
- **Entraînement** : Aucun pour ExG ; U-Net trimestriel
- **Inférence** : batch · < 1 s par image · 4 fois/j ; repli : NDVI Sentinel-2 seul
- **Sources amont** : 1 ●, 10 ◐, 3 ○
- **Point de vigilance** : Ombres et sol humide trompent ExG : prendre les photos à heure fixe

| Variante | Candidat |
|---|---|
| Compétition | Segmentation SegFormer ou U-Net végétation/sol + suivi temporel |
| Production | ExG + seuillage d'Otsu, suivi de la fraction de couvert |
| Compromis | ExG puis U-Net léger dès 500 masques annotés |

## IA-4 — Risques phytosanitaires

### `risk_rules` — Alertes phytosanitaires par règles expertes

- **Nature** : rules · **Version** : V1.1 · **Plateformes** : web:7, web:8, mobile
- **Données obligatoires** : `meteo.forecast_asof`, `agronomie.crop_cycles`, `phyto.reference`
- **Données recommandées** : `phyto.outbreaks`
- **Données optionnelles** : `meteo.grid_daily`
- **Variables** : T, HR, pluie, durée d'humectation estimée ; culture et stade ; alertes officielles de la zone
- **Métrique** : Précision des alertes (% confirmées par observation) — seuil : précision >= 50 % ; <= 3 alertes par parcelle et par mois ; secondaires : rappel sur foyers signalés, alertes par parcelle et par saison
- **Entraînement** : Révision des seuils chaque campagne avec les agronomes
- **Inférence** : batch · < 1 min · quotidien ; repli : relais des alertes DPV
- **Sources amont** : 7 ●, 7 ◐, 8 ○
- **Point de vigilance** : Trop d'alertes = alertes ignorées : le plafond mensuel est une exigence, pas un réglage

| Variante | Candidat |
|---|---|
| Compétition | Règles + modèle d'humectation foliaire calibré sur capteurs |
| Production | Règles ISRA et DPV : seuils T, HR, pluie × stade × culture |
| Compromis | Règles + relais des alertes DPV et FAMEWS par zone |

### `pest_phenology` — Développement des ravageurs par degrés-jours

- **Nature** : physical · **Version** : V2 · **Plateformes** : web:8, mobile
- **Données obligatoires** : `meteo.grid_daily`, `phyto.reference`, `agronomie.crop_cycles`
- **Données recommandées** : `features.local_weather_bias`
- **Données optionnelles** : `phyto.outbreaks`
- **Variables** : degrés-jours cumulés (seuils de littérature) ; date de semis ; premières captures
- **Modèles amont** : `wx_blend`
- **Métrique** : Erreur sur la date du pic de vol (jours) — seuil : <= 7 jours ; secondaires : date de la 1re génération
- **Entraînement** : Seuils de littérature ; recalage par campagne
- **Inférence** : batch · < 1 min · quotidien ; repli : calendrier de risque régional
- **Sources amont** : 12 ●, 11 ◐, 7 ○
- **Point de vigilance** : Seuils thermiques publiés hors Sahel : à valider avec l'ISRA

| Variante | Candidat |
|---|---|
| Compétition | Modèles à distribution de retard calibrés sur pièges |
| Production | Degrés-jours par ravageur (chenille légionnaire, Tuta absoluta, mouche des fruits) |
| Compromis | Degrés-jours recalés sur la première capture |

### `pest_risk_ml` — Probabilité de foyer à 7 jours

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:4, web:8, mobile
- **Données obligatoires** : `features.pest_risk`
- **Données recommandées** : `features.rain_events`
- **Données optionnelles** : `features.pest_trap_images`
- **Variables** : météo passée et prévue ; foyers voisins (distance, date) ; NDVI ; culture, stade ; degrés-jours
- **Modèles amont** : `pest_phenology`
- **Métrique** : PR-AUC P(foyer à 7 j) — seuil : PR-AUC >= 2 × prévalence et précision >= risk_rules ; secondaires : score de Brier, précision dans le top 10 %
- **Entraînement** : Mensuel en saison ; validation spatiale par blocs et temporelle
- **Inférence** : batch · < 2 min · quotidien ; repli : risk_rules
- **Sources amont** : 39 ●, 0 ◐, 2 ○
- **Point de vigilance** : Les absences de foyer ne sont pas observées : biais de signalement à corriger

| Variante | Candidat |
|---|---|
| Compétition | Modèle spatio-temporel (GNN sur graphe de parcelles) + LightGBM |
| Production | LightGBM calibré P(foyer à 7 j) par couple culture-ravageur |
| Compromis | Régression logistique pénalisée + règles en garde-fou |

## IA-5 — Assistant conversationnel

### `asst_llm` — Assistant agronomique conversationnel

- **Nature** : llm · **Version** : MVP · **Plateformes** : web:12, mobile
- **Données obligatoires** : `connaissances.rag_chunks`
- **Données recommandées** : `agronomie.crop_cycles`, `meteo.forecast_asof`
- **Données optionnelles** : `features.rain_events`
- **Variables** : passages récupérés et cités ; contexte de la parcelle (culture, stade) ; outils météo et bilan
- **Pré-entraînés (production)** : `claude_api`
- **Modèles amont** : `asst_retrieval`, `asst_guard`
- **Métrique** : Exactitude agronomique notée par les agronomes (% correct et sûr) — seuil : >= 90 % correct ; 0 produit non homologué CSP recommandé ; secondaires : citations valides, taux d'escalade, coût par question, latence p95
- **Entraînement** : Pas d'entraînement : prompts, corpus et outils versionnés ; évaluation hebdomadaire
- **Inférence** : online · p95 < 8 s en streaming · à la demande ; repli : FAQ validées + escalade vers un conseiller
- **Sources amont** : 8 ●, 5 ◐, 8 ○
- **Point de vigilance** : Le contexte de parcelle part vers l'API hors du Sénégal : minimiser et encadrer le transfert

| Variante | Candidat |
|---|---|
| Compétition | claude-opus-5-5, raisonnement adaptatif, outils et citations |
| Production | claude-opus-5-5 avec RAG, outils bornés, réponses citées, cache de prompt |
| Compromis | claude-haiku-5-5 pour les questions fréquentes, routage vers claude-opus-5-5 si complexe |

### `asst_retrieval` — Recherche documentaire du RAG

- **Nature** : ml · **Version** : MVP · **Plateformes** : web:12, mobile
- **Données obligatoires** : `connaissances.rag_chunks`
- **Données recommandées** : `langue.assistant_eval`
- **Variables** : BM25 ; embeddings multilingues ; filtres culture, zone, saison ; date de la fiche
- **Pré-entraînés (production)** : `embedding_models`
- **Métrique** : Recall@5 sur les questions de référence — seuil : Recall@5 >= 0,85 ; secondaires : nDCG@10, MRR
- **Entraînement** : Aucun au MVP ; reranker affiné en V2 sur les paires validées
- **Inférence** : online · < 300 ms · à la demande ; repli : BM25 seul
- **Sources amont** : 8 ●, 1 ◐, 0 ○
- **Point de vigilance** : Les embeddings ouverts sont faibles en wolof : traduire la requête ou indexer des gloses

| Variante | Candidat |
|---|---|
| Compétition | Hybride BM25 + embeddings + reranker cross-encoder affiné |
| Production | Hybride BM25 + embeddings multilingues auto-hébergés, filtres de métadonnées |
| Compromis | BM25 + métadonnées seulement au MVP |

### `asst_guard` — Garde-fous de l'assistant

- **Nature** : rules · **Version** : MVP · **Plateformes** : web:12, mobile
- **Données obligatoires** : `phyto.reference`, `langue.assistant_eval`
- **Variables** : liste CSP des matières actives homologuées ; doses maximales ; sujets hors champ ; données personnelles ; tentatives d'injection
- **Métrique** : Réponses dangereuses non bloquées (jeu adversarial) — seuil : 0 réponse dangereuse ; faux blocages <= 5 % ; secondaires : faux blocages
- **Entraînement** : Jeu adversarial enrichi chaque mois
- **Inférence** : online · < 100 ms (règles) · chaque réponse ; repli : refus poli + escalade vers un conseiller
- **Sources amont** : 3 ●, 0 ◐, 0 ○
- **Point de vigilance** : La liste CSP change : sa date de mise à jour doit être affichée et contrôlée

| Variante | Candidat |
|---|---|
| Compétition | Classifieur dédié + LLM-juge + listes CSP |
| Production | Liste blanche CSP + règles de dose + LLM-juge sur échantillon |
| Compromis | Liste CSP + règles ; revue humaine des réponses phytosanitaires |

### `asst_asr` — Reconnaissance vocale wolof et pulaar

- **Nature** : deep_learning · **Version** : V2 · **Plateformes** : web:12, mobile
- **Données obligatoires** : `features.asr_speech`
- **Variables** : audio 16 kHz ; vocabulaire agricole ; modèle de langue n-gram
- **Pré-entraînés (production)** : `xlsr_models`
- **Pré-entraînés (recherche seulement)** : `mms_models`, `nllb_models`
- **Métrique** : WER wolof — seuil : WER <= 25 % sur le vocabulaire agricole ; secondaires : CER, WER pulaar, WER par région
- **Entraînement** : Local uniquement (voix identifiante, jamais exportée), consentement explicite
- **Inférence** : online · < 3 s pour 10 s d'audio · à la demande ; repli : saisie texte, boutons, message vocal transmis au conseiller
- **Sources amont** : 4 ●, 0 ◐, 2 ○
- **Point de vigilance** : MMS et NLLB sont non commerciaux et ignorent le pulaar du Sénégal : collecter un corpus

| Variante | Candidat |
|---|---|
| Compétition | XLS-R 1B affiné + LM n-gram ; MMS comparé en recherche seulement |
| Production | XLS-R 300M affiné (CTC) en wolof, puis pulaar après collecte ; LM KenLM |
| Compromis | Wolof seul ; pulaar par boutons et messages vocaux transmis au conseiller |

### `asst_tts` — Restitution vocale des conseils

- **Nature** : rules · **Version** : V2 · **Plateformes** : mobile
- **Données obligatoires** : `langue.speech_corpus`
- **Données recommandées** : `connaissances.rag_chunks`
- **Variables** : gabarits de messages ; segments enregistrés (nombres, cultures, actions)
- **Métrique** : Compréhension mesurée en test utilisateur (%) — seuil : >= 90 % de messages compris ; secondaires : MOS
- **Entraînement** : Aucun en production ; TTS en recherche
- **Inférence** : edge · < 500 ms · à chaque alerte ; repli : texte + pictogrammes
- **Sources amont** : 3 ●, 7 ◐, 0 ○
- **Point de vigilance** : Les voix enregistrées sont des données personnelles : contrat de cession avec chaque locuteur

| Variante | Candidat |
|---|---|
| Compétition | TTS neuronal (VITS) entraîné sur un corpus consenti |
| Production | Messages assemblés à partir de segments enregistrés par des locuteurs consentants |
| Compromis | Gabarits enregistrés pour les alertes, texte français lu pour le reste |

## IA-6 — Fertilisation

### `npk_calibration` — Étalonnage du capteur NPK contre le laboratoire

- **Nature** : statistics · **Version** : V2 · **Plateformes** : web:6, kit
- **Données obligatoires** : `features.npk_calibration`
- **Données recommandées** : `sols.lab_results`
- **Variables** : lecture N, P, K brute ; conductivité ; humidité ; température du sol ; type de sol
- **Métrique** : Accord de classe avec le laboratoire (kappa de Cohen) — seuil : kappa >= 0,6 sur 3 classes, sinon aucune valeur en mg/kg affichée ; secondaires : R² et MAE par nutriment
- **Entraînement** : À chaque campagne d'analyses (>= 30 paires capteur-labo par type de sol)
- **Inférence** : batch · < 1 min · quotidien ; repli : valeurs de laboratoire, sinon iSDAsoil ou SoilGrids
- **Sources amont** : 15 ●, 0 ◐, 0 ○
- **Point de vigilance** : Les sondes NPK RS485 bon marché mesurent surtout la conductivité : rester en classes

| Variante | Candidat |
|---|---|
| Compétition | Modèle bayésien hiérarchique par lot de capteurs et type de sol |
| Production | Régression robuste (Huber) par type de sol, corrigée de l'humidité |
| Compromis | Classes faible / moyen / élevé au lieu de mg/kg |

### `fert_reco` — Recommandation de fumure

- **Nature** : rules · **Version** : V1.1 · **Plateformes** : web:6, web:7, mobile, kit
- **Données obligatoires** : `sols.field_profile`, `agronomie.crop_params`, `agronomie.crop_cycles`
- **Données recommandées** : `sols.lab_results`, `economie.costs`
- **Données optionnelles** : `features.npk_calibration`, `satellite.field_indices`
- **Variables** : besoins de la culture ; fourniture du sol ; rendement visé ; prix des engrais ; seuils d'alerte N, P, K par culture et stade (poussés au kit)
- **Métrique** : Écart de dose vs recommandation d'un agronome (%) — seuil : <= 20 % d'écart sur 50 cas revus ; secondaires : marge brute par ha, kg N par tonne
- **Entraînement** : Barèmes révisés chaque année avec l'ISRA
- **Inférence** : batch · < 1 s · à la demande ; repli : barème régional ISRA
- **Sources amont** : 15 ●, 4 ◐, 15 ○
- **Point de vigilance** : Sans analyse de sol, iSDAsoil (30 m) ne voit pas l'historique de fumure de la parcelle

| Variante | Candidat |
|---|---|
| Compétition | Optimisation économique de la dose (QUEFTS, courbes de réponse, prix) |
| Production | Bilan de fumure : besoins − fourniture du sol (labo ou iSDAsoil), barèmes ISRA |
| Compromis | Barèmes ISRA par zone, ajustés par l'analyse de laboratoire si elle existe |

## IA-7 — Recommandations

### `reco_engine` — Moteur de recommandations

- **Nature** : rules · **Version** : MVP · **Plateformes** : web:1, web:7, mobile
- **Données obligatoires** : `agronomie.crop_cycles`, `agronomie.crop_params`, `iot.telemetry_hourly`, `meteo.forecast_asof`
- **Données recommandées** : `phyto.reference`, `utilisateurs.reco_events`
- **Données optionnelles** : `phyto.outbreaks`
- **Variables** : sorties des modèles ; urgence ; impact attendu ; confiance ; historique d'acceptation
- **Modèles amont** : `irr_water_balance`, `anomaly_rules`
- **Métrique** : Taux d'acceptation des recommandations — seuil : >= 60 % acceptées ; <= 3 recommandations par jour et par exploitation ; secondaires : exécution observée (pompe), réclamations
- **Entraînement** : Aucun au MVP ; poids révisés chaque mois
- **Inférence** : batch · < 1 min · horaire et sur événement ; repli : conseil générique de saison
- **Sources amont** : 14 ●, 5 ◐, 7 ○
- **Point de vigilance** : Mesurer l'acceptation exige un bouton « fait / pas fait » : sans lui, pas de V3

| Variante | Candidat |
|---|---|
| Compétition | Classement appris (learning-to-rank) sur les retours + contraintes de sûreté |
| Production | Règles priorisées (urgence × impact × confiance), gabarits français et wolof |
| Compromis | Règles + pondération apprise sur le taux d'acceptation |

### `reco_bandit` — Optimisation de la formulation et du moment d'envoi

- **Nature** : ml · **Version** : V3 · **Plateformes** : web:7, mobile
- **Données obligatoires** : `features.reco_bandit`
- **Données recommandées** : `utilisateurs.reco_events`
- **Variables** : contexte (culture, heure, canal) ; formulation ; historique de réponse
- **Modèles amont** : `reco_engine`
- **Métrique** : Gain d'acceptation vs règles (points) — seuil : >= 5 points, sans baisse de sûreté ; secondaires : estimation hors ligne IPS ou DR
- **Entraînement** : En continu, avec exploration plafonnée à 10 %
- **Inférence** : online · < 50 ms · à chaque envoi ; repli : reco_engine
- **Sources amont** : 16 ●, 0 ◐, 0 ○
- **Point de vigilance** : L'exploration ne doit jamais modifier une dose ou un traitement

| Variante | Candidat |
|---|---|
| Compétition | Bandit contextuel (LinUCB, Thompson) + évaluation hors ligne doublement robuste |
| Production | Thompson sampling sur la formulation et l'heure, jamais sur le contenu agronomique |
| Compromis | Tests A/B classiques |

## IA-8 — Suivi de culture et rendement

### `ndvi_gapfill` — Reconstruction des séries NDVI sous nuages

- **Nature** : statistics · **Version** : V2 · **Plateformes** : web:4, web:6
- **Données obligatoires** : `satellite.field_indices`
- **Données recommandées** : `satellite.s2_chips`
- **Variables** : NDVI, EVI, NDWI Sentinel-2 clairs ; VV, VH Sentinel-1 ; Landsat ou HLS
- **Métrique** : RMSE du NDVI reconstruit sur des pixels clairs masqués — seuil : RMSE <= 0,08 ; secondaires : biais en hivernage
- **Entraînement** : Par saison et par culture
- **Inférence** : batch · < 10 min par tuile · à chaque passage (5 j) ; repli : dernière valeur claire marquée « ancienne »
- **Sources amont** : 10 ●, 0 ◐, 0 ○
- **Point de vigilance** : En hivernage, plus de 60 % des passages Sentinel-2 sont nuageux : c'est le cœur du problème

| Variante | Candidat |
|---|---|
| Compétition | Fusion S1/S2 par réseau profond (CNN-LSTM) |
| Production | Lissage Whittaker + régression VV/VH → NDVI par culture |
| Compromis | Whittaker + HLS (Landsat + Sentinel-2) pour densifier la série |

### `phenology_stage` — Stade phénologique par parcelle

- **Nature** : statistics · **Version** : V2 · **Plateformes** : web:3, web:6
- **Données obligatoires** : `features.phenology`
- **Données recommandées** : `images.espcam_series`
- **Données optionnelles** : `images.drone_mosaics`
- **Variables** : série NDVI lissée ; degrés-jours ; date de semis déclarée
- **Modèles amont** : `ndvi_gapfill`
- **Métrique** : MAE de la date de stade (jours) — seuil : <= 7 jours pour la floraison ; secondaires : MAE floraison, MAE maturité
- **Entraînement** : Par saison ; vérité = stades déclarés et photos
- **Inférence** : batch · < 5 min · à chaque passage (5 j) ; repli : calendrier cultural FAO + date de semis
- **Sources amont** : 23 ●, 1 ◐, 3 ○
- **Point de vigilance** : Les stades déclarés sont rares et approximatifs : prévoir des relevés de conseillers

| Variante | Candidat |
|---|---|
| Compétition | Transformer temporel sur séries S1 + S2 + degrés-jours |
| Production | Lissage Whittaker du NDVI + degrés-jours, détection des transitions |
| Compromis | Degrés-jours calés sur la date de semis, NDVI en contrôle |

### `yield_forecast` — Prévision de rendement p10–p90

- **Nature** : ml · **Version** : V3 · **Plateformes** : web:9, web:11, partner
- **Données obligatoires** : `features.yield`
- **Données recommandées** : `agronomie.crop_model_params`
- **Données optionnelles** : `agronomie.yield_potential`
- **Variables** : NDVI intégré, pic et date du pic ; degrés-jours ; pluie cumulée par phase ; stress hydrique ; sol ; culture et variété ; statistiques régionales
- **Modèles amont** : `phenology_stage`, `ndvi_gapfill`
- **Programme OctOpus** : `yield_forecast`
- **Métrique** : RMSE (t/ha) sur le holdout figé — seuil : RMSE <= 20 % du rendement moyen ; couverture entre 75 et 85 % ; secondaires : couverture p10–p90 (cible 80 %), MAPE par culture, régression par région
- **Entraînement** : Annuel en fin de campagne ; GroupKFold par parcelle + validation leave-one-season-out
- **Inférence** : batch · < 10 min · décadaire en saison ; repli : statistiques régionales DAPSA ou FAOSTAT × ratio NDVI
- **Sources amont** : 45 ●, 5 ◐, 1 ○
- **Point de vigilance** : Le programme OctOpus ne découpe que par parcelle : ajouter un test par saison laissée de côté

| Variante | Candidat |
|---|---|
| Compétition | Ensemble LightGBM + hybride (sorties AquaCrop et SARRA en variables) + quantiles conformes |
| Production | LightGBM quantile (p10, p50, p90) avec prédiction conforme par culture |
| Compromis | Régression sur NDVI intégré et pluie cumulée par culture, intervalles conformes |

### `yield_crop_model` — Simulation de rendement par modèle de culture

- **Nature** : physical · **Version** : V3 · **Plateformes** : web:9, partner
- **Données obligatoires** : `agronomie.crop_model_params`, `meteo.grid_daily`, `sols.field_profile`, `agronomie.crop_cycles`
- **Données recommandées** : `iot.telemetry_hourly`, `iot.irrigation_events`
- **Données optionnelles** : `agronomie.yield_potential`
- **Variables** : météo journalière ; sol (TAW) ; date de semis ; irrigation appliquée ; variété
- **Modèles amont** : `phenology_stage`
- **Métrique** : RMSE du rendement simulé vs observé — seuil : RMSE <= 25 % ; secondaires : biais par culture
- **Entraînement** : Calage annuel des paramètres avec l'ISRA
- **Inférence** : batch · < 30 min · décadaire ; repli : yield_forecast seul
- **Sources amont** : 25 ●, 7 ◐, 1 ○
- **Point de vigilance** : Le potentiel YPYGA est non commercial : comparaison de recherche, jamais affiché aux clients

| Variante | Candidat |
|---|---|
| Compétition | Assimilation (EnKF) du LAI et de l'humidité dans AquaCrop |
| Production | SARRA-Py (céréales pluviales) et AquaCrop-OSPy (irrigué), calés localement |
| Compromis | SARRA-Py seul (GPLv3 claire), AquaCrop après lecture de sa licence |

### `crop_type_map` — Carte des cultures

- **Nature** : ml · **Version** : V3 · **Plateformes** : web:4, partner
- **Données obligatoires** : `features.crop_type`
- **Données recommandées** : `geo.open_field_boundaries`
- **Variables** : statistiques temporelles S1 et S2 par parcelle ; phénologie ; texture
- **Modèles amont** : `ndvi_gapfill`
- **Métrique** : F1 macro par culture — seuil : F1 macro >= 0,75 ; secondaires : précision par région
- **Entraînement** : Annuel ; vérité = cultures déclarées + relevés GPS ; validation spatiale par blocs
- **Inférence** : batch · < 1 h par région · 2 fois par saison ; repli : culture déclarée
- **Sources amont** : 12 ●, 1 ◐, 0 ○
- **Point de vigilance** : Les cultures associées (mil + niébé) n'ont pas de signature unique

| Variante | Candidat |
|---|---|
| Compétition | Transformer temporel (L-TAE ou Presto) sur S1 + S2 |
| Production | LightGBM sur statistiques temporelles S1 + S2 par parcelle |
| Compromis | Random forest sur NDVI décadaire |

### `field_boundary` — Détection des limites de parcelles

- **Nature** : deep_learning · **Version** : V3 · **Plateformes** : web:3, web:4, mobile
- **Données obligatoires** : `features.field_boundaries`
- **Données recommandées** : `geo.open_field_boundaries`
- **Variables** : composites S2 10 m ; PlanetScope 3 m (si contrat) ; tracés existants
- **Métrique** : IoU par parcelle — seuil : IoU >= 0,7 pour les parcelles de plus de 0,5 ha ; secondaires : erreur de surface (%)
- **Entraînement** : Local (limites rattachées à des personnes) ; annuel
- **Inférence** : batch · < 1 min par exploitation · à la demande ; repli : tracé manuel
- **Sources amont** : 9 ●, 0 ◐, 0 ○
- **Point de vigilance** : À 10 m, une parcelle de 0,25 ha fait 25 pixels : la saisie manuelle reste la référence

| Variante | Candidat |
|---|---|
| Compétition | ResUNet-a multi-tâche (étendue, limite, distance) sur S2 + PlanetScope |
| Production | Modèle ouvert affiné sur S2, proposé à l'utilisateur pour validation |
| Compromis | Tracé GPS dans l'app avec accrochage aux limites détectées |

## IA-9 — Finance et assurance

### `agri_risk_score` — Score de risque agricole pour le crédit

- **Nature** : ml · **Version** : V3 · **Plateformes** : partner
- **Données obligatoires** : `features.agri_risk`
- **Variables** : rendement prévu et variabilité ; historique de récoltes ; irrigation ; prévision saisonnière ; remboursements passés
- **Modèles amont** : `yield_forecast`
- **Métrique** : AUC du défaut — seuil : AUC >= 0,70 ; écart d'équité <= 0,05 ; secondaires : KS, écart d'AUC par genre et par région, calibration
- **Entraînement** : Annuel ; local uniquement (données financières personnelles, jamais exportées)
- **Inférence** : batch · < 1 s par dossier · à la demande du partenaire ; repli : décision humaine de l'IMF
- **Sources amont** : 49 ●, 0 ◐, 0 ○
- **Point de vigilance** : Décision automatisée sur une personne : intervention humaine et droit d'opposition obligatoires

| Variante | Candidat |
|---|---|
| Compétition | Gradient boosting + modèle de survie, contraintes d'équité |
| Production | Score logistique monotone explicable (WoE), LightGBM monotone en challenger |
| Compromis | Grille experte fondée sur des variables agronomiques |

### `index_insurance` — Indice d'assurance paramétrique

- **Nature** : statistics · **Version** : V3 · **Plateformes** : partner
- **Données obligatoires** : `features.rain_events`, `historique.regional_stats`, `satellite.regional_products`
- **Données recommandées** : `meteo.grid_daily`
- **Données optionnelles** : `meteo.seasonal_outlook`
- **Variables** : pluie par phase culturale ; ETa WaPOR ; NDVI régional ; rendements historiques DAPSA
- **Métrique** : Risque de base (mauvaises années non indemnisées) — seuil : <= 20 % de mauvaises années non indemnisées ; secondaires : corrélation indice–pertes
- **Entraînement** : Calage tous les 3 ans avec l'assureur
- **Inférence** : batch · < 10 min · décadaire ; repli : expertise sinistre CNAAS
- **Sources amont** : 17 ●, 0 ◐, 1 ○
- **Point de vigilance** : CHIRPS v2 s'arrête fin 2026 : caler l'indice directement sur la v3

| Variante | Candidat |
|---|---|
| Compétition | Indice multi-sources (pluie + ETa + NDVI) optimisé sur le risque de base |
| Production | Indice pluie CHIRPS v3 par phase culturale, seuils calés sur les rendements DAPSA |
| Compromis | Indice NDVI et pluie simple par commune |

## IA-10 — Qualité des données du kit

### `anomaly_rules` — Anomalies capteurs et pompe par règles

- **Nature** : rules · **Version** : MVP · **Plateformes** : web:1, web:10, mobile, kit
- **Données obligatoires** : `iot.telemetry_clean`, `iot.device_health`
- **Données recommandées** : `iot.irrigation_events`
- **Variables** : valeurs hors plage ; variance nulle (capteur figé) ; sauts ; pompe sans effet sur l'humidité ; drapeaux firmware
- **Métrique** : Faux positifs par kit et par mois — seuil : <= 1 faux positif par kit et par mois ; secondaires : délai de détection, incidents manqués
- **Entraînement** : Seuils révisés chaque trimestre
- **Inférence** : stream · < 1 min · à chaque message ; repli : drapeaux firmware (soil_sensor_ok, bme_ok, npk_ok, pump_fault)
- **Sources amont** : 7 ●, 0 ◐, 0 ○
- **Point de vigilance** : Sans journal des interventions terrain, impossible d'étiqueter les vrais incidents

| Variante | Candidat |
|---|---|
| Compétition | Règles + détection statistique (CUSUM, filtre de Hampel) |
| Production | Règles de plage, de gel, de saut et de cohérence pompe → humidité |
| Compromis | Règles + CUSUM sur l'humidité |

### `sm_calibration` — Étalonnage de la sonde d'humidité par type de sol

- **Nature** : statistics · **Version** : V1.1 · **Plateformes** : web:10, kit
- **Données obligatoires** : `iot.telemetry_clean`, `sols.field_profile`
- **Données recommandées** : `sols.lab_results`
- **Variables** : lecture brute de la sonde capacitive ; texture ; température du sol ; mesures gravimétriques
- **Métrique** : RMSE de la teneur en eau vs gravimétrie (points de %) — seuil : RMSE <= 3 points ; secondaires : dérive par saison
- **Entraînement** : À l'installation et chaque saison (>= 10 prélèvements par classe de texture)
- **Inférence** : batch · < 1 min · à chaque nouvel étalonnage ; repli : courbe usine marquée « non étalonnée »
- **Sources amont** : 16 ●, 0 ◐, 0 ○
- **Point de vigilance** : Tous les modèles d'irrigation héritent de l'erreur de cette sonde : à faire avant le ML. La courbe est propre à chaque kit (lectures ADC sec et eau) et stockée en NVS

| Variante | Candidat |
|---|---|
| Compétition | Étalonnage bayésien hiérarchique par sonde, corrigé de la température |
| Production | Courbe polynomiale par classe de texture, calée sur mesures gravimétriques |
| Compromis | Étalonnage usine + correction par texture SoilGrids ou iSDAsoil |

### `anomaly_ml` — Anomalies multivariées des kits

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:10, mobile
- **Données obligatoires** : `features.sensor_anomaly`
- **Données recommandées** : `meteo.forecast_asof`
- **Variables** : résidus de prévision ; corrélations entre capteurs ; tension ; historique des défauts
- **Modèles amont** : `anomaly_rules`, `soil_nowcast`
- **Métrique** : PR-AUC sur incidents étiquetés — seuil : PR-AUC >= 0,5 ; précision >= 70 % ; secondaires : précision des alertes
- **Entraînement** : Mensuel
- **Inférence** : batch · < 2 min · horaire ; repli : anomaly_rules
- **Sources amont** : 10 ●, 0 ◐, 0 ○
- **Point de vigilance** : Peu d'incidents étiquetés : commencer non supervisé, puis apprendre des retours techniciens

| Variante | Candidat |
|---|---|
| Compétition | Autoencodeur LSTM ou Transformer + isolation forest |
| Production | Isolation forest + résidu de soil_nowcast par kit |
| Compromis | Résidus de prévision seuillés (z-score robuste) |

### `pump_health` — Maintenance prédictive de la pompe

- **Nature** : ml · **Version** : V2 · **Plateformes** : web:10, mobile
- **Données obligatoires** : `features.sensor_anomaly`
- **Données recommandées** : `iot.irrigation_events`
- **Données optionnelles** : `economie.costs`
- **Variables** : courant ; débit ; durée de marche ; m³ par kWh ; démarrages par jour
- **Modèles amont** : `anomaly_rules`
- **Métrique** : Pannes détectées au moins 48 h avant (%) — seuil : >= 50 % avec <= 1 fausse alerte par pompe et par trimestre ; secondaires : fausses alertes par pompe et par trimestre
- **Entraînement** : Trimestriel
- **Inférence** : batch · < 1 min · quotidien ; repli : alerte pump_fault du firmware
- **Sources amont** : 10 ●, 0 ◐, 4 ○
- **Point de vigilance** : Exige le débitmètre et la mesure de puissance (V1.1) : sans eux, modèle impossible

| Variante | Candidat |
|---|---|
| Compétition | Modèle de survie (Weibull, DeepSurv) sur signatures électriques |
| Production | Dérive débit et courant vs courbe de la pompe (régression robuste) |
| Compromis | Seuil de rendement hydraulique (m³/kWh) |

## TRANSVERSE — Transverse

### `water_savings` — Mesure des économies d'eau et d'énergie (MRV)

- **Nature** : statistics · **Version** : V1.1 · **Plateformes** : web:1, web:11, web:13, partner
- **Données obligatoires** : `features.water_savings`
- **Variables** : volume mesuré ; besoin théorique FAO-56 ; ET0 et pluie de la campagne ; parcelles témoins
- **Modèles amont** : `irr_water_balance`
- **Métrique** : Économie d'eau (%) avec intervalle de confiance à 90 % — seuil : intervalle publié ; aucune économie annoncée sans débitmètre ; secondaires : kWh économisés, FCFA économisés
- **Entraînement** : Par campagne
- **Inférence** : batch · < 10 min · mensuel et en fin de campagne ; repli : minutes de pompage × débit nominal, marqué « estimé »
- **Sources amont** : 21 ●, 0 ◐, 0 ○
- **Point de vigilance** : Un chiffre d'économie surestimé engage la crédibilité auprès des bailleurs

| Variante | Candidat |
|---|---|
| Compétition | Contrôle synthétique ou différence de différences avec parcelles témoins |
| Production | Besoin théorique FAO-56 vs volume mesuré au débitmètre, par campagne |
| Compromis | Avant / après par parcelle, corrigé de l'ET0 |

### `price_forecast` — Prévision des prix agricoles à 4 semaines

- **Nature** : ml · **Version** : V3 · **Plateformes** : web:11, web:13, mobile
- **Données obligatoires** : `features.price_forecast`
- **Variables** : prix passés par marché et produit ; saisonnalité ; NDVI régional ; fêtes et calendrier
- **Métrique** : MAPE à 4 semaines — seuil : MAPE <= 15 % et meilleur que la saisonnalité naïve ; secondaires : gain vs saisonnalité naïve
- **Entraînement** : Mensuel
- **Inférence** : batch · < 5 min · hebdomadaire ; repli : saisonnalité naïve (même semaine N−1 × tendance)
- **Sources amont** : 10 ●, 0 ◐, 0 ○
- **Point de vigilance** : Les prix SIM et ARM sont sous convention : sans accord, pas de modèle

| Variante | Candidat |
|---|---|
| Compétition | Modèles globaux (N-BEATS, TFT) multi-marchés |
| Production | LightGBM global sur prix hebdomadaires + saisonnalité + NDVI régional |
| Compromis | SARIMA par couple marché-produit |

### `salinity_risk` — Risque de salinisation des parcelles irriguées

- **Nature** : ml · **Version** : V3 · **Plateformes** : web:4, web:6
- **Données obligatoires** : `features.salinity_risk`
- **Données recommandées** : `eau.water_quality`
- **Variables** : EC et SAR de l'eau ; profondeur de nappe ; distance au fleuve ou au Saloum ; NDVI ; texture
- **Métrique** : Accord de classe avec les mesures EC (kappa) — seuil : kappa >= 0,6 ; secondaires : rappel de la classe « élevé »
- **Entraînement** : Annuel
- **Inférence** : batch · < 10 min · saisonnier ; repli : règles FAO-29
- **Sources amont** : 29 ●, 0 ◐, 0 ○
- **Point de vigilance** : Le kit ne mesure ni EC ni salinité : sonde EC à ajouter (doc 13, manques capteurs)

| Variante | Candidat |
|---|---|
| Compétition | Krigeage avec dérive externe (EC, nappe, NDVI) |
| Production | LightGBM de classe de risque par parcelle |
| Compromis | Règles FAO-29 (EC, SAR) + carte des zones à risque (delta, Saloum) |
