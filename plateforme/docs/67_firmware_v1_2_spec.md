# 67 — Spécification Technique Firmware ESP32-S3 v1.2 (`SMARTAGRI-FW-01`)

**Date** : 16 novembre 2026  
**Statut** : Spécification d'architecture et de contrat firmware — *Confidentiel — réservé aux partenaires de travail.*  
**Documents sources** :
- [`66_kit_platform_gap_analysis.md`](./66_kit_platform_gap_analysis.md) (`SMARTAGRI-COHERENCE-01`)
- [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf) (Adafruit Feather ESP32-S3 No PSRAM, TFT ILI9488 480×320, SEN0500, sonde sol capacitive, SEN0605 NPK RS485 + Shield V1.0, relais 5V + pompe 12V, LEDs + buzzer)
- [`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) (Firmware V7 actuel — socle local TFT + capteurs)
- [`CONVENTIONS.md`](../CONVENTIONS.md) (§3 `telemetry.v1`, §4 MQTT, §5 API REST) & [`mqtt_bridge.py`](../backend/app/ingestion/mqtt_bridge.py)

> [!IMPORTANT]
> **Contrainte de périmètre** : Ce document est une **spécification pure** (aucun code firmware ni backend n'a été écrit ou modifié). Il définit l'évolution du firmware V7 vers **v1.2** en distinguant ce qui est **immédiatement compatible** avec la plateforme actuelle (`telemetry.v1`) et ce qui relève d'une **extension coordonnée (`telemetry.v2`)**.

---

## 1. Architecture cible du Firmware v1.2

Le firmware v1.2 conserve intégralement le socle d'acquisition et d'affichage TFT ILI9488 du firmware V7 (refraîchissement différentiel, I2C SEN0500 sur `GPIO3/4`, RS485 Modbus MANU sur `GPIO17/18/12`, ADC sol sur `GPIO8`, relais `GPIO11`, LEDs `GPIO13/15`, buzzer `GPIO14`), et y ajoute :
- **La couche réseau & synchronisation horaire** : Wi-Fi (STA vers routeur/point d'accès + mode AP local de secours pour le relais mobile), SNTP (UTC ISO 8601) et persistance NVS (`Preferences`) pour `device_id` (`SA92-XXXXXX`), `device_key`, seuils, étalonnage et compteur `seq`.
- **La double voie d'ingestion** : MQTT TLS (voie nominale connectée) + HTTP `POST /v1/telemetry/batch` / `GET /data` (voie directe ou relais mobile hors-ligne).
- **La sûreté de fonctionnement terrain** : hystérésis d'arrosage, garde-fou pompe (`10 min` / `30 min`), détection de défaut sonde sol (`capteurSolOk`).

---

## 2. Spécification détaillée des 10 chantiers

### 2.1 MQTT (`P0` — Voie nominale connectée)

Conforme à [`CONVENTIONS.md`](../CONVENTIONS.md) §4 et [`mqtt_bridge.py`](../backend/app/ingestion/mqtt_bridge.py) (l. 42-46, 82-155) :

| Paramètre | Spécification Firmware v1.2 |
|---|---|
| **Transport & Sécurité** | MQTTS sur port **8883** (TLS 1.2+, vérification certificat serveur) ; repli `mqtt://1883` uniquement en build `dev/local`. |
| **Authentification** | `username = device_id` (`SA92-XXXXXX`), `password = device_key` (secret fourni à l'enregistrement `POST /v1/devices`). |
| **QoS & Taille max** | **QoS 1** sur tous les sujets ; payload JSON strictement **$\le 16\text{ Kio}$** (`MAX_PAYLOAD_BYTES = 16384`). |
| **Publication Télémétrie** | Sujet : `agri92/v1/devices/{device_id}/telemetry` — cadence nominale **5 min** (et publication immédiate sur changement d'état pompe ou défaut). |
| **Publication Événements** | Sujet : `agri92/v1/devices/{device_id}/events` — payload `{"type": "<event_name>"}` (`<= 64` car.), ex. `boot`, `pump_lockout`, `sensor_fault`. |
| **Souscription Commandes** | Sujet : `agri92/v1/devices/{device_id}/commands` — réception de `{"cmd": "set_thresholds", "id": "<uuid>", "start": int, "stop": int}`. |
| **Publication Acquittement** | Sujet : `agri92/v1/devices/{device_id}/commands/ack` — payload `{"id": "<uuid>", "ok": true|false}` après validation des bornes et écriture NVS. |
| **Reconnexion** | Backoff exponentiel borné (`1 s` → `120 s`), sans bloquer la boucle locale d'acquisition/sécurité (`loop()`). |

---

### 2.2 HTTP `telemetry.v1` (`P0` — Voie directe & relais mobile)

Deux rôles HTTP sont supportés pour garantir la compatibilité totale avec la plateforme et l'application mobile relais :

1. **Client HTTP vers l'API plateforme** (si Wi-Fi Internet disponible sans broker MQTT) :
   - **Route** : `POST /v1/telemetry/batch` ([`telemetry.py`](../backend/app/api/v1/telemetry.py) l. 51-69).
   - **En-tête** : `X-Device-Key: <device_key>`, `Content-Type: application/json`.
   - **Corps (`TelemetryBatch`)** : `{"points": [ <TelemetryPoint>, ... ]}` (1 à 1000 points, tampon circulaire en RAM/NVS en cas de coupure).
2. **Serveur HTTP local sur le kit** (mode AP Wi-Fi pour relais mobile hors-ligne, [`16_architecture_octopus.md`](./16_architecture_octopus.md) §6.2) :
   - **`GET /data`** : expose le dernier point au format brut kit (`sol`, `temp`, `hum`, `pres`, `n`, `p`, `k`, `pompe`, `defautPompe`, `capteurSolOk`, `bmeOk`, `npkOk`, `alerteEngrais`, `alertePlante`, `seuilStart`, `seuilStop`) + métadonnées (`fw`, `seq`, `param_version`, `heure_ok`).
   - **`POST /parametres`** : reçoit les blocs `seuils`, `npk`, `etalonnage`, `agro` (et jeton local), contrôle les bornes, persiste en NVS et met à jour `param_version`.

**Format canonique `TelemetryPoint` (`telemetry.v1`) émis par le firmware** :
```json
{
  "schema": "telemetry.v1",
  "device_id": "SA92-000123",
  "fw": "1.2.0",
  "seq": 42,
  "ts": "2026-11-16T12:00:00Z",
  "source": "mqtt",
  "m": {
    "soil_moisture_pct": 42.0,
    "air_temp_c": 31.5,
    "air_humidity_pct": 55.0,
    "pressure_hpa": 1009.2,
    "n_mgkg": 24,
    "p_mgkg": 14,
    "k_mgkg": 110,
    "pump_on": false,
    "pump_fault": false,
    "soil_sensor_ok": true,
    "bme_ok": true,
    "npk_ok": true,
    "alert_fertilizer": false,
    "alert_plant": false,
    "threshold_start_pct": 30,
    "threshold_stop_pct": 60
  }
}
```
> [!NOTE]
> `ts` est synchronisé par SNTP au démarrage puis toutes les 6 h. Si l'horloge n'est pas encore synchronisée (`heure_ok == false`), le kit émet sur `GET /data` (horodatage par le relais mobile) ou omet `schema` sur MQTT afin que `mqtt_bridge._telemetry_point` horodate à réception.

---

### 2.3 Hystérésis d'irrigation (`P0` — Suppression du battement relais)

Remplace le seuil unique `SEUIL_SOL_SEC = 30` du firmware V7 ([`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) l. 83, 1298-1300) par une machine à états à hystérésis conforme à `device_thresholds` ([`001_init.sql`](../db/migrations/001_init.sql) l. 208-209) et [`devices.py`](../backend/app/services/devices.py) :

- **Paramètres stockés en NVS** : `seuilStart` (défaut `30`), `seuilStop` (défaut `60`).
- **Validation stricte à toute mise à jour (MQTT / HTTP)** : entiers, `0 <= seuilStart`, `seuilStart + 5 <= seuilStop <= 100`. Tout jeu hors bornes est rejeté (`ok: false`).
- **Loi de commande** (uniquement si `capteurSolOk == true` et hors verrouillage pompe) :
  - Si `pump_on == false` et `humiditeSol < seuilStart` → passage à `pump_on = true` (`relaisOn()`).
  - Si `pump_on == true` et `humiditeSol >= seuilStop` → passage à `pump_on = false` (`relaisOff()`).
  - Entre `seuilStart` et `seuilStop` → maintien de l'état courant.
- **Anti-bruit ADC** : appliquer une moyenne glissante (ex. 10 lectures espacées de 100 ms) avant comparaison aux seuils.

---

### 2.4 Sécurité pompe (`P0` — Garde-fou 10 min / 30 min)

Aligne le firmware sur le contrat affiché dans [`PumpState.tsx`](../web/features/fields/PumpState.tsx) (l. 8-10) et [`53_kit_data_model_mapping.md`](./53_kit_data_model_mapping.md) :

- **Durée maximale de marche continue (`PUMP_MAX_RUN_MS`)** : **`10 min` (`600 000 ms`)**. Dès que la pompe atteint 10 min en continu, le firmware force `relaisOff()` (`pump_on = false`) et entre en **verrouillage de repos (`PUMP_LOCK_MS`)** pendant **`30 min` (`1 800 000 ms`)**.
- **Comportement pendant le verrouillage** :
  - Aucun redémarrage automatique possible tant que les 30 min ne sont pas écoulées.
  - Affichage TFT dédié sur la carte état (`VERROU POMPE 30m` ou décompte restant) + émission de l'événement MQTT `pump_lockout`.
- **Détection `pump_fault` sans débitmètre (V1.2)** :
  - Si après un cycle complet de `10 min` d'arrosage, l'humidité du sol n'a pas augmenté d'au moins `+2 %` (`delta_sol < 2`), lever `pump_fault = true` (présomption de marche à sec, pompe désamorcée ou fuite conduite) et maintenir l'alerte jusqu'à reprise d'une hausse d'humidité ou acquittement/reset local.
  - Si la sonde sol passe en défaut (`capteurSolOk == false`) → arrêt immédiat de la pompe (`relaisOff()`).

---

### 2.5 Détection défaut sonde sol `capteurSolOk` (`P0` — Intégrité ADC)

Corrige la faille critique de `lireHumiditeSol()` dans le firmware V7 ([`code-kitsmartagri92.ino`](../../code-kitsmartagri92.ino) l. 979-996), où une sonde débranchée renvoyant `0` ou `4095` provoque respectivement `100 %` ou `0 %` (arrosage permanent) :

- **Plage ADC brute valide (12 bits `0..4095`)** :
  - `ADC_MIN_VALID = 400` (en dessous : court-circuit à la masse ou sonde absente selon câblage).
  - `ADC_MAX_VALID = 3900` (au-dessus : circuit ouvert / sonde débranchée).
- **Anti-rebond** : `capteurSolOk` passe à `false` après **3 lectures consécutives** hors `[400, 3900]` (soit 6 s à cadence 2 s) et repasse à `true` après **3 lectures consécutives** valides.
- **Conséquences** :
  - Lorsque `capteurSolOk == false` : la pompe est **immédiatement coupée**, `soil_moisture_pct` est émis à `null` dans `telemetry.v1`, l'écran TFT affiche `-- %` + `SONDE SOL HS`, et le backend lève automatiquement l'alerte `soil_sensor_failure` ([`alerting.py`](../backend/app/services/alerting.py) l. 176-179).

---

### 2.6 & 2.7 Exposition UV et Luminosité (`P1` — Canaux SEN0500 déjà mesurés)

Le capteur DFRobot SEN0500 produit déjà `indiceUV` et `lumiere` (lux) dans le firmware V7, mais le contrat plateforme actuel **`telemetry.v1` rejette toute clé inconnue** (`clean_metrics()` dans [`telemetry.py`](../backend/app/services/telemetry.py) l. 128-130).

| Aspect | Spécification Firmware v1.2 |
|---|---|
| **Acquisition firmware** | Conservée à 2 s (moyennée sur 5 min pour l'envoi). Plages physiques : `uv_index ∈ [0.0, 16.0]`, `luminosity_lux ∈ [0.0, 120000.0]`. Si `!capteurOK` ou `!isfinite` → `null`. |
| **Compatibilité plateforme actuelle (`telemetry.v1`)** | **Ne pas injecter `uv` / `lux` dans `m` tant que la plateforme est en `telemetry.v1`** (sinon `rejected_values` incrémenté à chaque point). |
| **Exposition immédiate (locale)** | Exposer `"uv"` et `"lux"` sur la route locale `GET /data` (ignorés par le pont s'il filtre, utiles pour l'app mobile). |
| **Cible `telemetry.v2` (coordonnée avec Backend/DB)** | Activer l'envoi de `uv_index` (`uv`) et `luminosity_lux` (`lux`) dans `telemetry.v2` dès que la migration SQL `004` et `KIT_KEY_MAP` les accepteront. |

---

### 2.8 Correction `battery_mv` (`P1` — Suppression du faux positif `"ok"`)

D'après [`Liste_materiel_Kit_Smart_Agri92.pdf`](../../Liste_materiel_Kit_Smart_Agri92.pdf), le kit v1.1/v1.2 de base **ne comporte aucun capteur de tension batterie** (`INA219` ou pont diviseur).
- **Côté Firmware v1.2** :
  - Ne **jamais** fabriquer ou simuler une valeur `battery_mv` constante.
  - Prévoir un drapeau de compilation `#define HAS_BATTERY_MONITOR 0` : si `0`, ne pas émettre de clé `battery_mv` ; si `1` (révision matérielle avec pont diviseur calibré sur broche ADC libre ou INA219 I2C `0x40`), lire la tension en `mV` (`[0, 16000]`) et l'émettre dans `telemetry.v2`.
- **Côté Plateforme (prérequis coordonné)** : corriger [`device_health.py`](../backend/app/services/device_health.py) (l. 88-97) pour retourner `"absent"` (comme `"flow"`) lorsque `battery_mv is None`, au lieu de `"ok"`.

---

### 2.9 Alignement NPK (`P0` — Cohérence kit ↔ plateforme)

Résout la divergence identifiée entre firmware V7 (`K_FAIBLE=100, K_BON=200`), [`agronomy.py`](../backend/app/services/agronomy.py) (`K=(80, 150)`) et [`kit_parameters.py`](../backend/app/services/kit_parameters.py) (`K<80`) :

- **Valeurs par défaut unifiées (usine)** dans le firmware v1.2 :
  - `N_FAIBLE = 20`, `N_BON = 40` (`mg/kg`)
  - `P_FAIBLE = 10`, `P_BON = 25` (`mg/kg`)
  - `K_FAIBLE = 80`, `K_BON = 150` (`mg/kg`)
- **Paramétrage dynamique** : ces 3 seuils d'alerte (`npk.n`, `npk.p`, `npk.k`) deviennent modifiables via `POST /parametres` et persistés en NVS (`0..2000 mg/kg`).
- **Garde-fou mesure** : si `humiditeSol < 10 %` ou `!capteurSolOk`, la sonde conductimétrique SEN0605 est aveugle : conserver l'envoi des valeurs brutes si `npkOK == true`, mais ne pas déclencher d'alerte visuelle rouge trompeuse sans mention.

---

### 2.10 Alignement ADC sol (`P0` — Étalonnage cohérent)

Résout la divergence entre firmware V7 (`SOIL_DRY = 3000`, `SOIL_WET = 1300`) et [`kit_parameters.py`](../backend/app/services/kit_parameters.py) (`FACTORY_CALIBRATION = {"adc_sec": 3200, "adc_eau": 1350}`) :

- **Valeurs d'usine alignées** dans le firmware v1.2 :
  - `SOIL_DRY = 3200` (`adc_sec`)
  - `SOIL_WET = 1350` (`adc_eau`)
- **Étalonnage dynamique NVS** : le bloc `etalonnage` (`adc_sec`, `adc_eau`) reçu via `POST /parametres` remplace les valeurs d'usine après vérification stricte `0 <= adc_eau < adc_sec <= 4095`.
- **Fallback usine** : bouton ou commande permettant de restaurer `3200 / 1350`.

---

## 3. Priorisation et Feuille de Route Firmware v1.2

| Priorité | Chantier | Compatibilité plateforme actuelle | Dépendance / Prérequis |
|---|---|---|---|
| **P0** | **2.3 Hystérésis irrigation (`start`/`stop`)** | 100 % compatible (`device_thresholds`, `telemetry.v1`) | Aucun |
| **P0** | **2.4 Sécurité pompe (`10 min` / `30 min` + `pump_fault`)** | 100 % compatible (`PumpState.tsx`, `alerting.py`) | Aucun |
| **P0** | **2.5 Détection défaut sonde sol (`capteurSolOk`)** | 100 % compatible (`soil_sensor_failure`, `FieldDetail.tsx`) | Aucun |
| **P0** | **2.9 & 2.10 Alignement seuils NPK & ADC usine** | 100 % compatible (`agronomy.py`, `kit_parameters.py`) | Aucun |
| **P0** | **2.1 & 2.2 Connectivité MQTT TLS + HTTP `telemetry.v1` (`/data`, `/parametres`)** | 100 % compatible (`mqtt_bridge.py`, `POST /v1/telemetry/batch`) | Provisioning `device_id` + `device_key` |
| **P1** | **2.6 & 2.7 Exposition UV & Luminosité** | `GET /data` immédiat ; **Backend/DB requiert `telemetry.v2`** | Migration SQL `004` + `KIT_KEY_MAP` |
| **P1** | **2.8 Correction `battery_mv`** | Côté firmware : ne rien inventer (`HAS_BATTERY_MONITOR=0`) | Correctif `device_health.py` (`"absent"`) puis ajout INA219 en v1.3 |
| **P2** | **Tampon carte SD (écran TFT 3.5")** | Compatible via rejeu `POST /v1/telemetry/batch` (max 1000 pts/lot) | Activation SPI SD sur broche CS dédiée |
| **P2** | **Renommage sémantique `bme_ok` → `sen0500_ok` & OTA HTTPS** | Requiert `telemetry.v2` et route `GET /v1/firmware/latest` | Phase V1.2+ (`CONVENTIONS.md` §5.2) |

---

## 4. Jalons d'exécution recommandés (compatibles plateforme actuelle)

1. **Jalon FW-1.2-Alpha (Sûreté & Alignement local — 0 dépendance réseau)** :
   - Intégrer hystérésis `30/60`, timer pompe `10/30 min`, `capteurSolOk` (`[400, 3900]`), et constantes alignées (`NPK 20/40, 10/25, 80/150` ; `ADC 3200/1350`) + persistance NVS.
   - Validation sur banc physique (test sonde débranchée, test battement autour du seuil, test coupure à 10 min).
2. **Jalon FW-1.2-Beta (Connectivité `telemetry.v1` — Plateforme actuelle prête)** :
   - Ajouter Wi-Fi STA/AP, SNTP, client MQTTS (`agri92/v1/devices/{id}/telemetry|events|commands|commands/ack`), client `POST /v1/telemetry/batch`, et serveur local `GET /data` + `POST /parametres`.
   - Validation bout-en-bout contre `mqtt_bridge.py` et FastAPI (`pytest` / stack locale) sans aucune modification du backend ni du frontend.
3. **Jalon FW-1.2-Prod (Pré-série terrain)** :
   - Qualification complète des 5 chantiers P0, puis ouverture coordonnée de `telemetry.v2` (P1 : `uv_index`, `luminosity_lux`, `battery_mv`) et du tampon SD (P2).
