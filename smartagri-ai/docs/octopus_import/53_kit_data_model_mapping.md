# 53 — Cartographie Matériel Kit Smart-Agri92 ↔ Données ↔ Modèles IA (`IA-REAL-05`)

**Date** : 16 novembre 2026  
**Statut** : Référentiel matériel & capacité IA — *Confidentiel — réservé aux partenaires de travail.*  
**Sources analysées** :
- [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf) (inventaire matériel réel du Kit Smart-Agri92),
- [`41_data_inventory.md`](./41_data_inventory.md), [`45_real_data_lake_ready.md`](./45_real_data_lake_ready.md) (`IA-REAL-03`, Data Lake national `14/14` régions), [`46_real_data_enrichment.md`](./46_real_data_enrichment.md),
- Contrats Backend [`services/telemetry.py`](../backend/app/services/telemetry.py) (`telemetry.v1`) & [`services/device_health.py`](../backend/app/services/device_health.py).

**Contraintes respectées** : Aucun modèle entraîné ; aucune donnée synthétique ; aucune modification du Frontend ni du Backend ; approche nationale (généralisation à tout kit installé n'importe où au Sénégal).

---

## 1. Inventaire Matériel Réel & Spécifications par Capteur

D'après [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf), le Kit Smart-Agri92 (v1.1) repose sur un microcontrôleur **Adafruit Feather ESP32-S3 (No PSRAM)**, un écran TFT SPI 3.5" 480×320 (tactile et lecteur SD physiquement présents mais non utilisés dans le code final), un **Shield RS485 DFRobot V1.0 (mode MANU)**, un relais 5 V pilotant une pompe 12 V sur batterie 12 V, une alimentation 12 V dédiée au capteur NPK (ex. MT3608), 3 indicateurs locaux (LED rouge, LED verte, Buzzer) et **3 blocs capteurs** :

| Capteur / Organe (BOM réelle) | Grandeur mesurée (`telemetry.v1`) | Fréquence d'acquisition recommandée | Unité | Plage physique valide (`telemetry.py` / datasheet) | Règles de qualité & vigilance terrain |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Capteur d'humidité du sol capacitif (analogique)** | `soil_moisture_pct` (`sol`) + `soil_sensor_ok` (`capteurSolOk`) | Lecture interne **1 min** (moyenne glissante), envoi plateforme **5 min** → agrégation **`1 h`** (`measurements_1h`) | `%` (relatif ADC `3200→1400`, puis `%` étalonné) | `[0.0, 100.0] %` | - Masquer à `NaN` si `soil_sensor_ok = false`.<br>- Rejeter *flatline* ($\sigma = 0$ sur $\ge 6\text{ h}$) et *spike* ($|\Delta| > 35\,\%$ en 5 min sans pompe/pluie).<br>- **Étalonnage gravimétrique (`sm_calibration`) indispensable** selon la texture locale (`iSDAsoil` 30 m) ; éviter les poches d'air à la pose (`-20 cm`). |
| **DFRobot SEN0500 — Température air** | `air_temp_c` (`temp`) + `bme_ok` (`bmeOk`) | **5 min** → agrégation **`1 h`** | `°C` | `[-10.0, 60.0] °C` | - Masquer à `NaN` si `bme_ok = false`.<br>- Exige un **abri ventilé blanc** à `1,5 m` : en plein soleil au Sénégal, la mesure dérive de `+5` à `+12 °C`. |
| **DFRobot SEN0500 — Humidité relative air** | `air_humidity_pct` (`hum`) + `bme_ok` | **5 min** → agrégation **`1 h`** | `% HR` | `[0.0, 100.0] %` | - Masquer si `bme_ok = false`.<br>- Surveiller dérive/saturation pendant l'hivernage (`> 95 %` prolongé) ou poussière d'harmattan sur la membrane. |
| **DFRobot SEN0500 — Pression atmosphérique** | `pressure_hpa` (`pres`) + `bme_ok` | **5 min** → agrégation **`1 h`** | `hPa` | `[800.0, 1100.0] hPa` | - Plage attendue au Sénégal (basse altitude) : `1000–1022 hPa`. Toute valeur hors `[980, 1035]` hors erreur capteur signale un défaut `bme_ok`. |
| **DFRobot SEN0500 — Indice UV & Luminosité** | *Non mappé dans `telemetry.v1` v1.1* | **5 min** (recommandé en v1.2 pour proxy $R_s$) | `UV index` (`0–15`) & `lux` (`0–65535`) | `UV ∈ [0, 16]`, `Lux ∈ [0, 120000]` | - **Capacité matérielle déjà présente sur le SEN0500** mais non transmise par le firmware v1.1.<br>- Nettoyer la fenêtre optique chaque semaine (poussière) ; utile comme proxy local d'ensoleillement pour $ET_0$. |
| **DFRobot SEN0605 — Capteur NPK RS485** *(via Shield RS485 V1.0 + MT3608 12 V)* | `n_mgkg`, `p_mgkg`, `k_mgkg` (`n`, `p`, `k`) + `npk_ok` (`npkOk`) | **15 min à 1 h** (inutile à 5 min : inertie chimique lente + économie batterie 12 V) | `mg/kg` | `[0, 1999] mg/kg` | - Masquer si `npk_ok = false` ou si `soil_moisture_pct < 10 %` (sonde conductimétrique aveugle en sol très sec).<br>- **Valeur indicative uniquement** (`agronomy.py`) : ne jamais recommander de dose chiffrée d'engrais sans analyse labo. |
| **Relais 5 V + Pompe 12 V** | `pump_on` (`pompe`), `pump_fault` (`defautPompe`), `threshold_start_pct`, `threshold_stop_pct` | **À chaque changement d'état** + battement **5 min** | `bool` / `%` | `start ∈ [0, 95]`, `stop ∈ [5, 100]`, `start + 5 ≤ stop` | - Sécurité firmware : `10 min` marche max / `30 min` repos.<br>- Sans débitmètre, `pump_on` donne uniquement la **durée d'activation**, pas le volume réel pompé ($\text{m}^3$). |

> [!IMPORTANT]
> **Écarts détectés entre la BOM réelle et le Backend existant** :
> 1. `device_health.py` vérifie `battery_mv` (`< 3500 mV` dégradé, `< 3300 mV` défaut), mais **aucun capteur de tension/courant batterie** ne figure dans `Liste_materiel_Kit_Smart_Agri92.pdf` ni dans `KIT_KEY_MAP` (`services/telemetry.py`).
> 2. Le lecteur **SD** de l'écran TFT 3.5" existe physiquement mais n'est pas activé dans le code final, et **aucun modem cellulaire (GSM/LTE) ni LoRaWAN** n'est dans la BOM de base (Wi-Fi ESP32-S3 uniquement).

---

## 2. Cartographie par Modèle IA : Variables Disponibles, Manquantes et Impact

Grâce au **Data Lake National (`IA-REAL-03`, `14/14` régions)**, tout kit géolocalisé `(lat, lon)` reçoit automatiquement les variables satellitaires et climatiques de sa cellule (`cell_id` `0,05°`, `power_cell_id`), compensant une partie des capteurs absents du kit :

| Modèle / Service IA | Variables fournies par le Kit v1.1 | Variables fournies par le Data Lake National (`IA-REAL-03`) | Variables encore manquantes | Impact sur le modèle |
| :--- | :--- | :--- | :--- | :--- |
| **`soil_nowcast`** (`#2 soil_forecast`) | `soil_moisture_pct`, `air_temp_c`, `air_humidity_pct`, `pressure_hpa`, `pump_on`, `threshold_start/stop_pct`, `soil_sensor_ok` | Texture/pH/SOC/FC/WP (`iSDAsoil`), pluie `CHIRPS`, $ET_0$ FAO-56, `WorldCover` | Historique réel `measurements_1h` (6–8 sem.) + `sm_calibration` (étuve 105 °C) + prévisions *as-of* ECMWF/GFS | **Impact faible à moyen** : 100 % auto-supervisé ; premier modèle ML faisable après 6 semaines de collecte multi-kits. |
| **`anomaly_ml`** (`#13 device_health`) | `soil_moisture_pct`, `air_temp_c`, `air_humidity_pct`, `pressure_hpa`, `pump_on`, `pump_fault`, drapeaux `*_ok` | Contexte pluie/météo pour distinguer arrosage, pluie et panne capteur | Résidus de `soil_nowcast` + `battery_mv` (tension) + journal d'incidents réels | **Impact moyen** : la détection par règles (`anomaly_rules`) tourne dès le Jour 1 ; le ML sur résidus suit `soil_nowcast`. |
| **`wx_rain_prob`** (`rain_events`) | *(Optionnel : `pressure_hpa` local)* | **100 % disponible** (`CHIRPS` + `NASA POWER` 2015–2026 sur 14 régions) | Archivage *as-of* GRIB2 ECMWF/GFS (Niveau B) pour la calibration NWP | **Impact nul sur le kit** : modélisable indépendamment du matériel grâce au Data Lake national. |
| **`wx_local_bias`** (`#1 weather` MOS) | `air_temp_c`, `air_humidity_pct`, `pressure_hpa` | Grilles météo nationales (`NASA POWER`, future `ERA5-Land`) | Séries appariées `(prévision as-of, mesure kit)` + stations `ANACIM` | **Impact moyen** : exige l'abri ventilé SEN0500 (sinon biais solaire) et 2–3 mois d'historique apparié. |
| **`irr_need_24h`** (`#3 irrigation_need` ML) & **`water_savings`** (`#14`) | `soil_moisture_pct`, `pump_on` (durée), `threshold_*` | $ET_0$ FAO-56, courbes $K_c$, réserve utile `iSDAsoil`, pluie `CHIRPS` | **Débitmètre réel** (`flow_l_min`, volume cumulé en $\text{m}^3$) + pression/courant pompe | **Impact BLOQUANT pour le ML** : sans débitmètre, la cible « mm réellement apportés » est inconnue. Le moteur physique `irr_water_balance` reste actif en production. |
| **`irr_scheduler`** (`#4 irrigation_plan`) | `pump_on`, `threshold_start/stop_pct` | $ET_0$, pluie prévue | Débit réel vérifié + `soil_nowcast` + `irr_need_24h` + capacité électrique pompe/batterie | **Impact BLOQUANT** : dépend de `irr_need_24h` et du débitmètre. |
| **`fert_reco`** (`#6 fertilization`) | `n_mgkg`, `p_mgkg`, `k_mgkg` (indicatifs) | `iSDAsoil` (N, P, K, pH, CEC, SOC à `0-20` & `20-50 cm`) | **Analyses sol labo (`npk_calibration`)** + barèmes signés `ISRA/CDH` | **Impact fort** : le capteur NPK RS485 seul est trop sensible à l'humidité/CE ; `rules` possibles dès validation ISRA, calibration ML après essais labo. |
| **`pest_risk`** (`#9 pest_risk`) | `air_temp_c`, `air_humidity_pct` | Pluie `CHIRPS`, météo nationale, listes `CSP` | **Humectation foliaire** (absente du kit) + bulletins `DPV` + comptages pièges | **Impact moyen** : règles hygrométriques/degrés-jours possibles avec SEN0500 + DPV ; ML bloqué sans relevés terrain. |
| **`ndvi_gapfill` / `phenology_stage`** (`#11 vegetation`) | *(Aucune variable kit requise)* | **Catalogue Sentinel-2 national** (`20 722` scènes), composites 2025, `WorldCover` | Polygones parcelles saisis + série Sentinel-2 complète 2024–2026 + `Sentinel-1` SAR | **Impact nul sur le kit** : dépend uniquement du géoréférencement parcelle et du pipeline satellite. |
| **`yield_forecast`** (`#12`) & **`price_forecast`** (`#15`) | `soil_moisture_pct`, `air_temp_c`, `air_humidity_pct` (stress local) | `FAOSTAT` (1961–2024), `WFP/VAM` (79 marchés), `iSDAsoil`, `CHIRPS`, Sentinel-2 | **$\ge 4$ campagnes de pesées parcellaires** / conventions `DAPSA` & `SIM/CSA` | **Impact temporel fort** : bloqué à court terme par la durée des campagnes agricoles (`>= 6–24 mois`). |
| **`vis_disease`** (`#8`) & **`vis_pest_count`** (`#10`) | *Aucune caméra dans le kit v1.1* | — | **Caméra (ESP32-CAM ou smartphone)** + $\ge 500$ photos terrain doublement annotées | **Impact BLOQUANT côté kit** (dépend des photos smartphone agriculteur/conseiller). |
| **`asst_asr`** (`#17 assistant_transcribe`) | *Aucun microphone dans le kit v1.1* | Lexiques `fr`/`wo`/`ff` | **Audio smartphone/API** + 20–50 h de corpus vocal agricole consenti | **Impact nul sur le kit** (service applicatif mobile/web). |

---

## 3. Classement Opérationnel des Modèles (Horizons Réalistes)

| Palier temporel | Modèles & Services IA | Condition exacte de mise en œuvre |
| :--- | :--- | :--- |
| **1. Faisable dès les premiers kits (Jour 1 / Immédiat)** | - **Moteurs déterministes Backend** : `irr_water_balance` (`#3`), `irr_et0`, `reco_engine` (`#5`), `anomaly_rules` (`#13`), `asst_retrieval` (`#16`)<br>- **`wx_rain_prob`** (`rain_events`, données publiques nationales `CHIRPS` + `NASA POWER`)<br>- **Qualification technique OctOpus** sur proxy national (`soil_nowcast_proxy_national`) | Aucune attente d'historique capteur : le kit fournit l'état instantané (`telemetry.v1`) et le Data Lake national fournit le contexte climatique et pédologique sur tout le Sénégal. |
| **2. Faisable après 6 semaines** *(de télémétrie continue multi-kits)* | - **`soil_nowcast` (`#2 soil_forecast`, `soil_moisture_nowcast`)** — *1er modèle ML production*<br>- **`anomaly_ml`** (détection d'anomalies sur résidus de `soil_nowcast`)<br>- **`ndvi_gapfill` & `phenology_stage`** (`#11`, sur contours GPS enregistrés)<br>- **`fert_reco` & `risk_rules`** en mode `rules` (si barèmes ISRA/CDH/DPV signés) | $\ge 5$ à $10$ kits répartis dans plusieurs zones du Sénégal + **6 à 8 semaines** continues dans `measurements_1h` ($\ge 5\,000$–$13\,000$ points horaires) + étalonnage `sm_calibration` + pièces conformité OctOpus (C1–C4). |
| **3. Faisable après 6 mois** *(1 à 4 campagnes complètes)* | - **`wx_local_bias`** (`#1`, correction biais température/HR locale)<br>- **`npk_calibration`** (calibration sonde SEN0605 vs analyses labo)<br>- **`yield_forecast` (`#12`)** (amorçage après plusieurs campagnes ; cible robuste à 4 campagnes)<br>- **`price_forecast` (`#15`)** & **`asst_asr` (`#17`)** en wolof/pulaar | Accumulation saisonnière (saison sèche + hivernage), campagnes de pesées terrain / analyses sol labo, collecte vocale consentie et conventions `SIM/CSA` / `ANACIM` / `DAPSA`. |
| **4. Bloqué par le matériel actuel (Kit v1.1)** | - **`irr_need_24h` (`#3` en ML supervisé)**<br>- **`water_savings` (`#14` certifié MRV)**<br>- **`irr_scheduler` (`#4` optimiseur MPC)**<br>- **`pump_health` (`#13` prédiction panne pompe 48 h)**<br>- **`vis_disease` / `vis_pest_count` automatisés boîtier** *(sans smartphone)* | **Absence physique** de **débitmètre** sur conduite, de capteur **courant/tension pompe & batterie**, d'**ESP32-CAM** et de **pluviomètre/humectation foliaire**. |

---

## 4. Recommandations Matérielles Futures (Révisions v1.2 & v2)

Pour lever les blocages ci-dessus tout en maintenant un coût compatible avec l'agriculture maraîchère au Sénégal et une couverture nationale hors-ligne :

| Priorité | Ajout / Évolution matérielle | Ce qu'il débloque immédiatement | Coût / Impact firmware |
| :-: | :--- | :--- | :--- |
| **P1 (Critique)** | **Débitmètre à impulsions (effet Hall)** sur la conduite de sortie pompe | Débloque **`irr_need_24h` (ML)**, **`water_savings` certifié (MRV)** et l'optimiseur **`irr_scheduler`**. Mesure le volume réel en $\text{L/min}$ et détecte les fuites/pompage à sec. | Faible (`kit_flowmeter` prévu en `telemetry.v2`, 1 entrée interruption GPIO ESP32-S3). |
| **P2 (Critique)** | **Capteur tension/courant I2C (ex. INA219 / pont diviseur calibré)** sur batterie 12 V et pompe | Alimente `battery_mv` attendu par **`device_health.py`** (suppression des faux états `ok`/`degraded`) et débloque **`pump_health` (prédiction panne pompe 48 h)** via signature de courant. | Très faible (~2–5 k FCFA, bus I2C partagé avec le SEN0500). |
| **P3 (Critique)** | **Activation du lecteur carte SD déjà présent sur l'écran TFT 3.5" + connectivité GSM/LTE-M ou LoRaWAN** | Évite toute perte de données en zone rurale sans Wi-Fi (tampon SD local rejoué via `POST /v1/telemetry/batch` dès reconnexion). | Nul pour la SD (déjà dans la BOM) ; modem GSM/LTE-M indispensable hors zone Wi-Fi. |
| **P4 (Forte valeur)** | **Exposition logicielle des canaux UV & Luminosité du SEN0500** | Le capteur SEN0500 mesure déjà l'UV et la luminosité : les ajouter à `telemetry.v2` fournit un proxy local gratuit de rayonnement solaire $R_s$ pour **$ET_0$ locale** et détection de couverture nuageuse. | **0 € matériel** (simple mise à jour firmware + schéma `telemetry.v2`). |
| **P5 (Référence)** | **Pluviomètre à augets basculants + 2e sonde sol (profondeur `-40 cm` & CE salinité)** sur 1 kit sur 10 | Vérité terrain pluie locale (calibres `CHIRPS` et `wx_rain_prob`), suivi du front d'humectation racinaire et surveillance de la **salinisation** (`salinity_risk` dans les Niayes et le Delta). | Moyen (réservé aux kits de référence multi-zones). |
| **P6 (V2 Phyto)** | **Capteur d'humectation foliaire** + **ESP32-CAM** (4 photos/jour max) | Débloque **`pest_risk` ML** (durée d'humectation pour mildiou/alternariose) et **`vis_pest_count`** automatique sur pièges chromatiques/phéromones. | Moyen (nécessite passage sur ESP32-S3 avec **PSRAM** pour la capture JPEG). |
