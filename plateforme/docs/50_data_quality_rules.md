# 50 — Règles de Qualité et d'Hygiène des Données IoT (`IA-REAL-04`)

**Date** : 16 novembre 2026  
**Statut** : Référentiel normatif d'admission vers le Data Lake Réel (`ml/data/real/iot_telemetry/`) — *Confidentiel — réservé aux partenaires de travail.*  
**Objectif** : Empêcher toute pollution du Data Lake réel dès le premier paquet envoyé par le premier kit physique.

---

## 1. Barrière 1 — Validation stricte à l'ingestion (`services/telemetry.py`)

Toute donnée entrant par MQTT ou `POST /v1/telemetry/batch` subit automatiquement les contrôles suivants **avant** écriture en base :

1. **Idempotence temporelle** : clé primaire `(device_id, ts)` avec `INSERT ... ON CONFLICT DO NOTHING`. Aucun doublon possible même en cas de réémission réseau.
2. **Fenêtre temporelle UTC (`ts_plausible`)** :
   - Horodatage obligatoirement normalisé en **UTC**.
   - Rejet complet du point (`rejected_points += 1`) si `ts < 2024-01-01T00:00:00Z` (`MIN_TS`) ou si `ts > now + 10 min` (`MAX_FUTURE`), protégeant contre les horloges RTC non initialisées (`1970-01-01` ou `2099`).
3. **Plages physiques admissibles (`FLOAT_RANGES` & `INT_RANGES`)** :
   - Une valeur `NaN`, booléenne sur champ numérique, de mauvais type ou hors plage est **remplacée par `NULL`** (jamais imputée à l'ingestion) et comptabilisée dans `rejected_values` :
     - `soil_moisture_pct` $\in [0.0, 100.0]\,\%$
     - `air_temp_c` $\in [-10.0, 60.0]\,^\circ\text{C}$
     - `air_humidity_pct` $\in [0.0, 100.0]\,\%$
     - `pressure_hpa` $\in [800.0, 1100.0]\,\text{hPa}$
     - `n_mgkg`, `p_mgkg`, `k_mgkg` $\in [0, 1999]\,\text{mg/kg}$
     - `threshold_start_pct` $\in [0, 95]$ et `threshold_stop_pct` $\in [5, 100]$ (avec règle firmware `start + 5 <= stop` vérifiée par `agronomy.validate_thresholds`).
4. **Rejet des clés inconnues** : `extra="forbid"` sur `TelemetryPoint` et filtrage strict sur `METRIC_KEYS` dans `clean_metrics()`.

---

## 2. Barrière 2 — Nettoyage et qualification pour le Data Lake (`iot.telemetry_clean` → `ml/data/real/iot_telemetry/`)

Avant qu'une série horaire issue de `measurements_1h` ne soit publiée en Parquet dans `ml/data/real/iot_telemetry/`, les règles suivantes s'appliquent :

| Règle | Condition de détection d'anomalie | Action appliquée |
| :--- | :--- | :--- |
| **Q1 — Masquage par drapeau matériel** | `soil_sensor_ok = false` (ou `bme_ok = false`, `npk_ok = false`) | Mettre la mesure correspondante à `NaN` même si le chiffre brut est dans `[0, 100]`. |
| **Q2 — Détection de capteur figé (*flatline*)** | Écart-type $= 0$ sur **$\ge 6$ heures consécutives** de `soil_moisture_pct` ou `air_temp_c` | Marquer la plage en `quality_flag = "flatline"` et exclure de la cible d'entraînement `soil_nowcast`. |
| **Q3 — Saut physique impossible (*spike*)** | Variation $|\Delta \text{soil\_moisture\_pct}| > 35\,\%$ en 5 min **sans** événement `pump_on` ni pluie `> 5 mm` | Marquer en `quality_flag = "spike"` (probable arrachement ou ré-insertion de sonde). |
| **Q4 — Interpolation bornée** | Trou dans la série horaire `measurements_1h` | Interpolation linéaire autorisée **uniquement si la coupure est $\le 3\text{ h}$** (conforme à `soil_moisture_nowcast.yaml`) ; au-delà, conserver `NaN`. |
| **Q5 — Cohérence pompe / humidité** | `pump_on = true` prolongé ($> 2\text{ h}$) sans aucune hausse d'humidité du sol ni alerte | Signaler pour contrôle terrain (fuite tuyau, goutteur bouché ou sonde placée hors bulbe). |
| **Q6 — Étalonnage gravimétrique** | Présence ou absence de courbe `sm_calibration` pour le sol de la parcelle | Conserver le booléen `calibrated` (`true` / `false`) afin de ne jamais mélanger mesures brutes et mesures étalonnées sans contrôle. |

---

## 3. Barrière 3 — Gouvernance, Zéro Synthétique et Confidentialité OctOpus

1. **Séparation absolue réel / synthétique** :
   - Le dossier [`ml/data/real/iot_telemetry/`](../ml/data/real/iot_telemetry/SCHEMA.md) ne doit **jamais** contenir `ml/data/synthetic/telemetry/telemetry.csv` ni aucune donnée simulée.
   - Tout fichier déposé doit posséder son manifeste `.parquet.manifest.json` avec `synthetic_data: false`, empreinte `sha256` et métriques de complétude.
2. **Généralisation nationale (zéro dépendance site pilote)** :
   - Chaque ligne extraite est rattachée à sa cellule nationale `(cell_id, power_cell_id)` via les coordonnées de la parcelle (`senegal_grid_0p05.parquet`), quelle que soit la région du Sénégal.
   - Les kits situés dans les zones de validation (`mboro`, `potou`, `richard_toll`) conservent leur marqueur `validation_zone` pour les tests de généralisation spatiale.
3. **Protection des données personnelles avant export OctOpus (`agriml.octopus.exporter`)** :
   - Suppression des colonnes identifiantes (`owner_name`, `phone`, `email`),
   - Pseudonymisation irréversible de `device_id` et `field_key` par **HMAC-SHA256** (`AGRIML_PSEUDO_SALT` local),
   - Arrondi des coordonnées GPS à $0,01^\circ$ ($\approx 1,1\text{ km}$, `lat_r`, `lon_r`),
   - Isolation physique du Holdout chez SmartAgri92 (`holdout_sent: false`).
