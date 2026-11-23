# 66 — Audit de Cohérence Matériel / Firmware / Plateforme (`SMARTAGRI-COHERENCE-01`)

**Date** : 16 novembre 2026  
**Statut** : Audit de cohérence en lecture seule — *Confidentiel — réservé aux partenaires de travail.*  
**Périmètre** :
- Firmware ESP32-S3 ([`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino), V7)
- Inventaire matériel ([`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf))
- Contrats & Documentation ([`CONVENTIONS.md`](../CONVENTIONS.md), [`16_architecture_octopus.md`](./16_architecture_octopus.md), [`PASSATION.md`](../web/PASSATION.md))
- Base de données PostgreSQL / TimescaleDB ([`001_init.sql`](../db/migrations/001_init.sql))
- Backend FastAPI ([`plateforme/backend/app/`](../backend/app/))
- Frontend Next.js ([`plateforme/web/`](../web/))
- Consommation ML existante (`soil_nowcast` dans [`soil_moisture.py`](../ml/src/agriml/forecast/soil_moisture.py) & [`soil_moisture_forecast.yaml`](../ml/configs/soil_moisture_forecast.yaml))

> [!NOTE]
> **Respect des contraintes** : Aucun code, contrat, schéma ou document existant n'a été modifié. Aucun modèle IA, RAG, SoilNowcast ou Rain Intelligence n'a été développé ou modifié.

---

## SECTION 1 — Inventaire complet des variables du kit

D'après [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf) et le firmware V7 ([`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino)), le kit SmartAgri92 produit **13 variables** (9 mesures capteurs + 4 états d'actionneurs/indicateurs).

| # | Variable | Source matérielle (BOM) | Symbole firmware V7 (`code-kitsmartagri92.ino`) | Unité / Type | Fréquence d'acquisition firmware | Clé `telemetry.v1` attendue (`CONVENTIONS.md` §3 / `KIT_KEY_MAP`) |
|---|---|---|---|---|---|---|
| 1 | **`temperature`** | DFRobot SEN0500 (I2C `0x22`, `SDA=3`, `SCL=4`) | `temperature` (`environnement.getTemperature(TEMP_C)`) | `°C` (`float`) | 2 s | `temp` → `air_temp_c` |
| 2 | **`humidity`** | DFRobot SEN0500 (I2C `0x22`) | `humiditeAir` (`environnement.getHumidity()`) | `%` (`float`) | 2 s | `hum` → `air_humidity_pct` |
| 3 | **`pressure`** | DFRobot SEN0500 (I2C `0x22`) | `pression` (`environnement.getAtmospherePressure(HPA)`) | `hPa` (`float`) | 2 s | `pres` → `pressure_hpa` |
| 4 | **`uv`** | DFRobot SEN0500 (I2C `0x22`) | `indiceUV` (`environnement.getUltravioletIntensity()`) | Indice UV (`float`) | 2 s | **Non prévue** |
| 5 | **`luminosity`** | DFRobot SEN0500 (I2C `0x22`) | `lumiere` (`environnement.getLuminousIntensity()`) | `lux` (`float`) | 2 s | **Non prévue** |
| 6 | **`soil moisture`** | Sonde capacitive analogique (`SOIL_PIN = GPIO8`, ADC 12 bits) | `humiditeSol` (`map(brut, 3000, 1300, 0, 100)`, borné `0..100`) | `%` (`int`) | 2 s | `sol` → `soil_moisture_pct` |
| 7 | **`N`** | Capteur NPK RS485 DFRobot SEN0605 (Modbus `0x01`, reg `0x1E`) | `valeurN` (`npk.getResponseBuffer(0)`) | `mg/kg` (`int`) | 4 s (10 s si erreur) | `n` → `n_mgkg` |
| 8 | **`P`** | Capteur NPK RS485 DFRobot SEN0605 (Modbus `0x01`, reg `0x1E+1`) | `valeurP` (`npk.getResponseBuffer(1)`) | `mg/kg` (`int`) | 4 s (10 s si erreur) | `p` → `p_mgkg` |
| 9 | **`K`** | Capteur NPK RS485 DFRobot SEN0605 (Modbus `0x01`, reg `0x1E+2`) | `valeurK` (`npk.getResponseBuffer(2)`) | `mg/kg` (`int`) | 4 s (10 s si erreur) | `k` → `k_mgkg` |
| 10 | **`relay state`** | Relais 5V (`RELAY_PIN = GPIO11`, actif bas `LOW`) | `relaisOn()` / `relaisOff()` (piloté par `solSec`) | État GPIO (`OUTPUT/LOW` vs `INPUT`) | À chaque boucle (`loop`) | **Non prévue** (fusionnée avec `pompe`) |
| 11 | **`pump state`** | Pompe d'arrosage 12V (alimentée via relais 5V + batterie 12V) | Déduit de `solSec` (`humiditeSol < 30`) via `relaisOn()`/`relaisOff()` (pas de variable booléenne dédiée) | ON/OFF implicite | À chaque boucle (`loop`) | `pompe` → `pump_on` |
| 12 | **`led state`** | LED rouge alerte (`LED_PIN = GPIO13`) + LED verte OK (`LED_OK_PIN = GPIO15`) | `etatLED` (clignotement 300 ms sur `solSec`), `LED_OK_PIN` (`HIGH` si `!solSec`) | `bool` / `HIGH`/`LOW` | 300 ms / boucle | **Non prévue** (partiellement reflétée par `alertePlante`/`alerteEngrais`) |
| 13 | **`buzzer state`** | Buzzer actif (`BUZZER_PIN = GPIO14`, `BUZZER_ON = LOW`) | Piloté en phase avec `etatLED` quand `solSec` est vrai | `LOW`/`HIGH` | 300 ms / boucle | **Non prévue** |

### Variables complémentaires associées (drapeaux & contexte firmware ↔ plateforme)
- **Produits par le firmware V7 mais non listés comme capteurs physiques** : `capteurOK` (SEN0500 présent), `npkOK` (Modbus NPK OK), `solSec` (`humiditeSol < SEUIL_SOL_SEC`), `etatEngrais` (`ENGRAIS_PAUVRE` / `CORRECT` / `RICHE`).
- **Attendus par `telemetry.v1` mais absents du firmware V7** : `defautPompe` (`pump_fault`), `capteurSolOk` (`soil_sensor_ok`), `alertePlante` (`alert_plant`), `seuilStart` (`threshold_start_pct`), `seuilStop` (`threshold_stop_pct`), et `bmeOk` (`bme_ok`, nommé pour un BME280 alors que le kit utilise un SEN0500).

---

## SECTION 2 — Matrice complète : Firmware → API → Base → Backend → Frontend → IA

> [!IMPORTANT]
> **Constat structurel préalable sur le Firmware V7** : [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) est actuellement un **firmware local autonome** (affichage TFT ILI9488 + logs `Serial`). Il ne possède **ni pile Wi-Fi, ni client MQTT, ni serveur HTTP (`/data`, `/parametres`), ni sérialisation `telemetry.v1`**. La colonne « Firmware » ci-dessous indique donc si la donnée est **mesurée/calculée en mémoire** par le firmware V7, et la colonne « `telemetry.v1` » indique si le contrat d'ingestion plateforme la prévoit.

| Variable | 1. Produite Firmware (V7) | 2. Prévue `telemetry.v1` (`CONVENTIONS.md` / `telemetry.py`) | 3. Stockée PostgreSQL / Timescale (`001_init.sql`) | 4. Exposée Backend (`measurements.py` / API v1) | 5. Visible Frontend (`plateforme/web/`) | 6a. Rules Engine (`alerting.py`) | 6b. Recommendations (`recommendations.py` / `agronomy.py`) | 6c. SoilNowcast (`soil_moisture.py`) | 6d. Assistant (`tools.py`) | 6e. Device Health (`device_health.py`) | 7. Ignorée ? | 8. Valeur métier | 9. Priorité |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **`temperature`** | **Oui** (`temperature`, °C) | **Oui** (`temp` → `air_temp_c`, `[-10, 60]`) | **Oui** (`measurements.air_temp_c`, agrégats `1h`/`1d` avg/min/max) | **Oui** (`raw` + `1h`/`1d`/`1w`/`1mo`, `latest_measurement`) | **Oui** (`FieldDetail.tsx` `LatestReading` + `AssistantChat`) | **Non** | **Oui** (calcul $ET_0$ Hargreaves sur 24h si $\ge 6$ points) | **Oui** (`exog`: `air_temp_c`) | **Oui** (`get_latest_measurements` + `HISTORY_KEYS` min/max) | **Non** (seul `bme_ok` est vérifié) | Non | **Très haute** ($ET_0$ locale, stress thermique, SoilNowcast) | **P0** |
| **`humidity`** | **Oui** (`humiditeAir`, %) | **Oui** (`hum` → `air_humidity_pct`, `[0, 100]`) | **Oui** (`measurements.air_humidity_pct`, agrégat `avg`) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Oui** (`FieldDetail.tsx` `LatestReading`) | **Non** | **Non** (non utilisée dans `agronomy.py` / `irrigation_need.py`) | **Oui** (`exog`: `air_humidity_pct`) | **Oui** (`get_latest_measurements` + `HISTORY_KEYS` avg) | **Non** | Non | **Haute** (risque fongique / `pest_risk`, bilan évaporatif, SoilNowcast) | **P1** |
| **`pressure`** | **Oui** (`pression`, hPa) | **Oui** (`pres` → `pressure_hpa`, `[800, 1100]`) | **Oui** (`measurements.pressure_hpa`, agrégat `avg`) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Non** (jamais affichée dans les écrans Next.js) | **Non** | **Non** | **Non** | **Partiel** (`get_latest_measurements` oui ; absent de `HISTORY_KEYS`) | **Non** | **Oui** (côté Frontend & IA/Règles) | **Moyenne** (tendance barométrique locale, proxy biais météo) | **P2** |
| **`uv`** | **Oui** (`indiceUV`, UV) | **Non** (rejetée par `clean_metrics` si envoyée) | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Oui (100 % perdue)** | **Moyenne à haute** (proxy rayonnement solaire $R_s$ pour $ET_0$ locale & risque brûlure) | **P1** |
| **`luminosity`** | **Oui** (`lumiere`, lux) | **Non** (rejetée par `clean_metrics` si envoyée) | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Oui (100 % perdue)** | **Haute** (proxy $R_s$ / nébulosité pour $ET_0$ & photosynthèse, capteur déjà câblé) | **P1** |
| **`soil moisture`** | **Oui** (`humiditeSol`, %) | **Oui** (`sol` → `soil_moisture_pct`, `[0, 100]`) | **Oui** (`measurements.soil_moisture_pct`, agrégats avg/min/max) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Oui** (`FieldDetail.tsx`, `MoistureChart.tsx`, `RampSwatch`) | **Oui** (`dry_soil_persistent`) | **Oui** (`recommend_irrigation` FAO-56) | **Oui** (`target`: `soil_moisture_pct`) | **Oui** (`get_latest_measurements` + `HISTORY_KEYS` avg/min) | **Partiel** (via `soil_sensor_ok`) | Non | **Critique** (pilotage irrigation, déclenchement pompe, cœur métier) | **P0** |
| **`N`** | **Oui** (`valeurN`, mg/kg) | **Oui** (`n` → `n_mgkg`, `[0, 1999]`) | **Oui** (`measurements.n_mgkg`, agrégat `avg`) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Partiel** (`RecommendationCards.tsx` via `/recommendations`, absent de `FieldDetail`) | **Non** (`alert_fertilizer` ignoré par `alerting.py`) | **Oui** (`fertility_status` + `fertilization.py` classes indicatives) | **Non** | **Oui** (`get_latest_measurements` uniquement) | **Partiel** (via `npk_ok`) | Non | **Haute** (suivi carence azotée indicatif, future calibration `npk_calibration`) | **P1** |
| **`P`** | **Oui** (`valeurP`, mg/kg) | **Oui** (`p` → `p_mgkg`, `[0, 1999]`) | **Oui** (`measurements.p_mgkg`, agrégat `avg`) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Partiel** (`RecommendationCards.tsx` via `/recommendations`, absent de `FieldDetail`) | **Non** | **Oui** (`fertility_status` + `fertilization.py`) | **Non** | **Oui** (`get_latest_measurements` uniquement) | **Partiel** (via `npk_ok`) | Non | **Haute** (suivi phosphore indicatif) | **P1** |
| **`K`** | **Oui** (`valeurK`, mg/kg) | **Oui** (`k` → `k_mgkg`, `[0, 1999]`) | **Oui** (`measurements.k_mgkg`, agrégat `avg`) | **Oui** (`raw` + agrégats, `latest_measurement`) | **Partiel** (`RecommendationCards.tsx` via `/recommendations`, absent de `FieldDetail`) | **Non** | **Oui** (`fertility_status` + `fertilization.py`) | **Non** | **Oui** (`get_latest_measurements` uniquement) | **Partiel** (via `npk_ok`) | Non | **Haute** (suivi potassium indicatif) | **P1** |
| **`relay state`** | **Oui** (`relaisOn()`/`relaisOff()`, GPIO11) | **Non** (assimilé à `pompe` / `pump_on`) | **Non** (pas de colonne distincte) | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Oui** (fusionné avec `pump_on`) | **Faible** (redondant avec `pump_on` sauf diagnostic électrique relais vs pompe) | **P2** |
| **`pump state`** | **Implicite** (piloté par `solSec` sans variable booléenne) | **Oui** (`pompe` → `pump_on`, `bool`) | **Oui** (`measurements.pump_on`, agrégat `pump_on_ratio`) | **Oui** (`raw` + `pump_on_ratio`, `latest_measurement`) | **Oui** (`PumpState.tsx`) | **Non** (seul `pump_fault` déclenche une alerte) | **Non** | **Oui** (`exog`: `pump_on`) | **Oui** (`get_latest_measurements` + `pump_on_ratio`) | **Partiel** (`pump_fault` vérifié, pas `pump_on`) | Non | **Critique** (preuve d'arrosage, calcul `pump_on_ratio`, SoilNowcast) | **P0** |
| **`led state`** | **Oui** (`LED_PIN` rouge, `LED_OK_PIN` verte) | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Oui (100 % locale)** | **Faible** (indicateur visuel terrain uniquement ; les états métier sont déjà portés par les alertes/statuts) | **P2** |
| **`buzzer state`** | **Oui** (`BUZZER_PIN`, actif sur `solSec`) | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Non** | **Oui (100 % locale)** | **Faible** (alarme sonore locale uniquement ; pas d'intérêt à remonter en télémétrie) | **P2** |

---

## SECTION 3 — Données perdues ou non exploitées

### 3.1 Données produites par le firmware mais 100 % perdues à la frontière d'ingestion
1. **`uv` (`indiceUV`) et `luminosity` (`lumiere` en lux)** :
   - Le capteur **DFRobot SEN0500** les mesure toutes les 2 secondes dans [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) (l. 1070-1074).
   - Elles ne figurent **ni dans [`CONVENTIONS.md`](../CONVENTIONS.md) §3**, **ni dans `KIT_KEY_MAP` / `METRIC_KEYS`** ([`telemetry.py`](../backend/app/services/telemetry.py) l. 28-60), **ni dans la table `measurements`** ([`001_init.sql`](../db/migrations/001_init.sql) l. 222-248).
   - Conséquence : si un firmware les envoie dans `telemetry.v1`, `clean_metrics()` les rejette et incrémente `rejected_values`. On perd gratuitement un proxy local de rayonnement solaire ($R_s$) utile pour l'$ET_0$ et le diagnostic de couverture nuageuse.

### 3.2 Données stockées en base mais non exploitées (ou sous-exploitées)
1. **`pressure_hpa`** :
   - Ingérée, stockée dans `measurements`, agrégée dans `measurements_1h` et `measurements_1d`, exposée par `GET /v1/devices/{id}/measurements` et `GET /v1/devices/{id}`.
   - **Jamais affichée sur le Frontend Next.js** (absente de [`FieldDetail.tsx`](../web/features/fields/FieldDetail.tsx)), **jamais utilisée** par `alerting.py`, `recommendations.py`, `agronomy.py`, `device_health.py` ni `soil_nowcast`.
2. **`alert_fertilizer` et `alert_plant`** :
   - Prévues dans `telemetry.v1` (`alerteEngrais`, `alertePlante`), stockées dans `measurements`, exposées dans `RAW_COLUMNS`.
   - **Jamais lues par [`alerting.py`](../backend/app/services/alerting.py)** (seuls `soil_sensor_ok`, `pump_fault`, `soil_moisture_pct` et `threshold_start_pct` déclenchent des alertes), et **jamais affichées** sur le Frontend.
3. **`n_mgkg`, `p_mgkg`, `k_mgkg` sur l'écran parcelle** :
   - Exploitées par `recommendations.py` et `fertilization.py`, et affichées dans [`RecommendationCards.tsx`](../web/features/recommendations/RecommendationCards.tsx), mais **absentes de la carte « Dernière mesure »** ([`FieldDetail.tsx`](../web/features/fields/FieldDetail.tsx) `LatestReading`) et **absentes de l'historique conversationnel** de l'Assistant (`HISTORY_KEYS` dans [`tools.py`](../backend/app/services/assistant/tools.py) l. 37-38).
4. **`relay state`, `led state`, `buzzer state`** :
   - Non transmises et non stockées. Pour `led` et `buzzer`, c'est **normal et souhaitable** (actionneurs d'interface locale). Pour `relay`, son état est confondu avec `pump_on`.

---

## SECTION 4 — Incohérences techniques critiques

L'audit croisé entre le code firmware V7, la BOM PDF, la base de données, le backend et le frontend révèle **9 incohérences techniques majeures** :

1. **Absence totale de connectivité et de contrat `telemetry.v1` dans le firmware V7** (🔴 **BLOQUANT**)
   - Le firmware [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) (V7) ne contient **aucun code Wi-Fi, HTTP ou MQTT**. Il n'expose ni `GET /data`, ni `POST /parametres` (pourtant requis par [`CONVENTIONS.md`](../CONVENTIONS.md) §3 et [`16_architecture_octopus.md`](./16_architecture_octopus.md) §6.2), ni l'horodatage, ni le `device_id` (`SA92-XXXXXX`).
   - En l'état, **aucun kit flashé avec ce firmware ne peut communiquer** ni avec l'application mobile relais, ni avec le backend FastAPI (`POST /v1/telemetry/batch`), ni avec le broker Mosquitto.

2. **Absence d'hystérésis sur les seuils d'arrosage dans le firmware V7** (🔴 **BLOQUANT**)
   - Firmware V7 (l. 83, 1298-1300) : seuil unique `SEUIL_SOL_SEC = 30` (`solSec = humiditeSol < 30`). Dès que l'humidité oscille autour de 30 %, le relais/pompe et le buzzer battent toutes les 2 secondes (**pompage erratique / usure prématurée du relais et de la pompe**).
   - Plateforme (`CONVENTIONS.md` §3, `001_init.sql` l. 208-209, `devices.py`, `agronomy.py`, `kit_parameters.py`) : exige une **paire à hystérésis** (`start` et `stop` avec `0 ≤ start` et `start + 5 ≤ stop ≤ 100`).

3. **Sécurité pompe « 10 min max / 30 min repos » affichée mais non codée** (🔴 **BLOQUANT**)
   - Le Frontend ([`PumpState.tsx`](../web/features/fields/PumpState.tsx) l. 8-10) affiche explicitement à l'agriculteur : *« Durées imposées par le firmware v1.1 : 10 min marche max / 30 min repos »*.
   - Or, [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) n'implémente **aucun timer de marche maximale ni de verrouillage de repos**. Si le capteur sol reste sous `30 %` (ou est débranché/hors sol), la pompe tourne **en continu jusqu'à destruction ou vidange complète de la batterie 12V**.

4. **Absence de détection de défaut sonde sol (`soil_sensor_ok`) et défaut pompe (`pump_fault`)** (🔴 **BLOQUANT**)
   - Le Backend ([`alerting.py`](../backend/app/services/alerting.py) l. 176-182) et le Frontend ([`FieldDetail.tsx`](../web/features/fields/FieldDetail.tsx) l. 73, [`PumpState.tsx`](../web/features/fields/PumpState.tsx) l. 19) reposent sur `soil_sensor_ok` et `pump_fault`.
   - Dans le firmware V7, `lireHumiditeSol()` (l. 979-996) lit `analogRead(SOIL_PIN)` sans vérifier si la sonde est débranchée (`brut == 0` ou `4095`), et aucune détection `pump_fault` n'existe. Pire : une sonde débranchée renvoyant `0` donne `map(0, 3000, 1300, 0, 100)` → `constrain(..., 0, 100) = 100 %` (ou si `4095` → `0 %` → **déclenchement permanent de la pompe** !).

5. **Désalignement des seuils NPK entre Firmware, Agronomy et KitParameters** (🟠 **MAJEUR**)
   - Firmware V7 (l. 86-92) : `N < 20` (bon `≥ 40`), `P < 10` (bon `≥ 20`), `K < 100` (bon `≥ 200`).
   - Backend [`agronomy.py`](../backend/app/services/agronomy.py) (l. 217) : `N: (20, 40)`, `P: (10, 25)`, `K: (80, 150)`.
   - Backend [`kit_parameters.py`](../backend/app/services/kit_parameters.py) (l. 27) & [`16_architecture_octopus.md`](./16_architecture_octopus.md) (l. 470) : `N < 20, P < 10, K < 80`.
   - Résultat : le kit local et la plateforme web peuvent afficher des diagnostics NPK contradictoires pour une même mesure.

6. **Désalignement de l'étalonnage ADC usine de la sonde d'humidité du sol** (🟠 **MAJEUR**)
   - Firmware V7 (l. 80-81) : `SOIL_DRY = 3000`, `SOIL_WET = 1300`.
   - Backend [`kit_parameters.py`](../backend/app/services/kit_parameters.py) (l. 28) : `FACTORY_CALIBRATION = {"adc_sec": 3200, "adc_eau": 1350}`.
   - Écart de ~5-10 % d'humidité calculée entre la valeur par défaut du kit et la valeur par défaut affichée dans l'écran `/kit` (`KitView.tsx`).

7. **Métrique fantôme `battery_mv` dans `device_health.py`** (🟠 **MAJEUR**)
   - [`device_health.py`](../backend/app/services/device_health.py) (l. 88-97) vérifie `getattr(latest, "battery_mv", None)` pour calculer la santé de la batterie (`"battery"` dans `DeviceHealthSchema`).
   - Or, **aucun capteur de tension batterie** n'existe dans [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf), **aucune clé `battery_mv`** n'existe dans `telemetry.v1` ni dans la table `measurements`. `battery_mv` vaut donc toujours `None` et le capteur `"battery"` affiche `"ok"` par défaut tant que le kit est actif, masquant toute décharge réelle de la batterie 12V.

8. **Incohérence de nommage capteur `bme_ok` / `"bme"` vs `SEN0500`** (🟡 **MINEUR**)
   - Le matériel réel et le firmware V7 utilisent un **DFRobot SEN0500** (`capteurOK`), mais toute la chaîne plateforme (`telemetry.v1`, `measurements.bme_ok`, `device_health.py`, `DeviceHealthSchema` `"bme"`) parle de **BME** (BME280).

9. **Lecteur SD et écran tactile présents dans la BOM mais inutilisés** (🟡 **MINEUR**)
   - L'écran TFT 3.5" inclut un lecteur SD et un contrôleur tactile non exploités dans le firmware V7. En zone rurale sans Wi-Fi continu, l'absence de tampon SD expose à une perte de mesures entre deux passages du relais mobile.

---

## SECTION 5 — Actions recommandées

1. **[A1 — Firmware V8 / v1.1 réseau]** Implémenter dans le firmware ESP32-S3 :
   - Le serveur HTTP local (`GET /data`, `POST /parametres` avec jeton) et/ou le client MQTT TLS (`agri92/v1/devices/{device_id}/telemetry`, `commands`, `commands/ack`) selon [`CONVENTIONS.md`](../CONVENTIONS.md) §3-4.
   - La persistance NVS des paramètres (`seuils`, `npk`, `etalonnage`) et l'émission du payload `telemetry.v1` complet (`sol`, `temp`, `hum`, `pres`, `n`, `p`, `k`, `pompe`, `defautPompe`, `capteurSolOk`, `bmeOk`, `npkOk`, `alerteEngrais`, `seuilStart`, `seuilStop`).
2. **[A2 — Firmware sécurité pompe & hystérésis]** Implémenter immédiatement :
   - La logique d'hystérésis `start` / `stop` (`start + 5 <= stop`) au lieu du seuil unique `SEUIL_SOL_SEC = 30`.
   - Le minuteur matériel de sécurité pompe (`10 min` marche max / `30 min` repos forcé) promis par l'UI (`PumpState.tsx`).
   - La détection de sonde sol débranchée/court-circuitée (`brut < 400 || brut > 3900` → `capteurSolOk = false`, arrêt pompe).
3. **[A3 — Alignement constantes NPK & étalonnage]** Unifier sur une seule vérité partagée (ex. aligner le firmware et `agronomy.py` sur `K_FAIBLE=80`, `adc_sec=3200`, `adc_eau=1350`, ou mettre à jour `kit_parameters.py` selon la mesure terrain réelle sur la sonde capacitive retenue).
4. **[A4 — Extension `telemetry.v2` pour UV & Luminosité]** Ajouter `uv_index` (`uv`) et `luminosity_lux` (`lux`) à `telemetry.v1`→`v2`, à la table `measurements` (migration `004_...sql`) et à `measurements_1h`/`1d` pour exploiter les deux canaux déjà lus par le SEN0500.
5. **[A5 — Correction `device_health.py` & matériel batterie]** Soit ajouter un pont diviseur / INA219 sur la batterie 12V et exposer `battery_mv` dans `telemetry.v2`, soit afficher honnêtement `"absent"` (comme `"flow"`) dans `device_health.py` tant qu'aucun capteur de tension n'est câblé.
6. **[A6 — Exploitation Frontend & Rules Engine]**
   - Afficher `n_mgkg`, `p_mgkg`, `k_mgkg` et `pressure_hpa` dans la fiche détail kit/parcelle ([`FieldDetail.tsx`](../web/features/fields/FieldDetail.tsx)).
   - Brancher `alert_fertilizer` (ou calcul équivalent côté serveur) dans [`alerting.py`](../backend/app/services/alerting.py) et ajouter `n_mgkg_avg`, `p_mgkg_avg`, `k_mgkg_avg` à `HISTORY_KEYS` de l'Assistant (`tools.py`).

---

## SECTION 6 — Quick wins

Actions à faible coût technique et fort gain immédiat :

1. **Afficher `"absent"` pour `"battery"` dans `device_health.py` quand `battery_mv is None`** (10 min, backend) : évite de renvoyer un faux statut `"ok"` pour la batterie 12V alors qu'aucun capteur de tension n'existe dans le kit.
2. **Alimenter les seuils NPK & ADC usine de manière cohérente** (15 min, firmware/backend) : aligner `K_FAIBLE` (`80` vs `100`) et `SOIL_DRY`/`SOIL_WET` (`3000/1300` vs `3200/1350`) entre [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino), [`agronomy.py`](../backend/app/services/agronomy.py) et [`kit_parameters.py`](../backend/app/services/kit_parameters.py).
3. **Ajouter le contrôle de sonde sol débranchée (`soil_sensor_ok`) + hystérésis + timer 10/30 min dans le firmware** (~2 h, firmware) : sécurise le matériel avant tout test terrain.
4. **Exposer `n_mgkg_avg`, `p_mgkg_avg`, `k_mgkg_avg` dans `HISTORY_KEYS` de l'Assistant** ([`tools.py`](../backend/app/services/assistant/tools.py) l. 37, 5 min) : permet à l'assistant agronomique de répondre sur l'évolution NPK sur 7/30 jours sans aucune migration DB.
5. **Afficher `pressure_hpa` et `n/p/k` dans `LatestReading`** ([`FieldDetail.tsx`](../web/features/fields/FieldDetail.tsx), ~30 min) : valorise des données déjà ingérées, stockées et renvoyées par `/v1/devices/{id}`.

---

## Synthèse décisionnelle : Classement des recommandations

| Rang | Action | 1. Valeur métier | 2. Difficulté | 3. Impact sur SmartAgri | Priorité |
|---|---|---|---|---|---|
| 1 | **A1 — Connectivité Wi-Fi/HTTP/MQTT + contrat `telemetry.v1` dans le firmware** | **Critique** (sans elle, zéro donnée réelle en plateforme) | Élevée (dev firmware + tests terrain) | **Débloque toute la plateforme** (ingestion, dashboard, alertes, ML) | **P0** |
| 2 | **A2 — Hystérésis `start/stop`, timer pompe 10/30 min & détection `soil_sensor_ok`** | **Critique** (protège pompe, relais, batterie et cultures) | Faible à moyenne (logique C++ pure) | **Évite la casse matériel** et aligne le kit sur les promesses de l'UI | **P0** |
| 3 | **A3 — Alignement des seuils NPK & étalonnage ADC usine** | **Haute** (cohérence des diagnostics locaux vs web) | Très faible (constantes) | **Élimine les contradictions** entre écran TFT du kit et dashboard Web | **P0** |
| 4 | **A5 — Honnêteté `battery` (`"absent"` si non mesuré) ou ajout capteur tension** | **Haute** (fiabilité de `device_health`) | Très faible (logique) / Faible (INA219) | **Supprime un faux positif `"ok"`** sur la santé batterie | **P1** |
| 5 | **A4 — Ajout `uv` et `luminosity` (`SEN0500`) dans `telemetry.v2` & DB** | **Haute** (proxy $R_s$ gratuit pour $ET_0$) | Moyenne (migration SQL + contrat + firmware) | **Améliore $ET_0$ locale** et les futurs modèles IA sans coût matériel | **P1** |
| 6 | **A6 — Affichage `pressure_hpa` & NPK dans `FieldDetail` + `HISTORY_KEYS` Assistant** | **Moyenne** (meilleure exploitation des données existantes) | Faible | **Complète l'UX** et les réponses de l'Assistant | **P2** |

---

## 🚨 Ce qui doit impérativement être corrigé avant la mise en production des premiers kits

Avant de déployer les premiers kits SmartAgri92 sur le terrain, **4 points non négociables (P0)** doivent impérativement être corrigés dans le firmware et vérifiés en intégration bout-en-bout :

1. **Implémenter le pont de communication `telemetry.v1` sur l'ESP32-S3** (Wi-Fi AP/STA + `GET /data` + `POST /parametres` et/ou client MQTT TLS + horodatage), car le firmware V7 actuel est 100 % hors-ligne et ne produit aucun JSON `telemetry.v1`.
2. **Implémenter l'hystérésis (`seuilStart` / `seuilStop`) et la sécurité pompe (`10 min` max de marche / `30 min` de repos)** dans le firmware, pour éviter le battement du relais et le pompage à sec ou continu.
3. **Implémenter le contrôle d'intégrité de la sonde sol (`capteurSolOk` / `soil_sensor_ok`)** dans `lireHumiditeSol()` pour bloquer la pompe et lever l'alerte `soil_sensor_failure` si la sonde est débranchée ou hors plage ADC.
4. **Aligner les constantes par défaut (seuils NPK et étalonnage ADC `SOIL_DRY` / `SOIL_WET`)** entre le firmware, [`agronomy.py`](../backend/app/services/agronomy.py) et [`kit_parameters.py`](../backend/app/services/kit_parameters.py), et corriger l'état `"battery"` dans [`device_health.py`](../backend/app/services/device_health.py) afin de ne pas afficher `"ok"` en l'absence de capteur de tension.
