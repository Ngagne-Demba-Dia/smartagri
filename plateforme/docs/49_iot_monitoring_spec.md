# 49 — Spécification de Supervision IoT & Monitoring (`IA-REAL-04`)

**Date** : 16 novembre 2026  
**Statut** : Spécification opérationnelle alignée sur [`device_health.py`](../backend/app/services/device_health.py), [`alerting.py`](../backend/app/services/alerting.py) et [`metrics.py`](../backend/app/core/metrics.py).  
**Objectif** : Détecter immédiatement toute perte de connectivité, dérive capteur ou anomalie de pompage dès l'arrivée du premier kit, partout au Sénégal.

---

## 1. États de santé des 6 sous-systèmes (`GET /v1/devices/{id}/health`)

Le service `#13 device_health` ([`app/services/device_health.py`](../backend/app/services/device_health.py)) évalue en continu 6 capteurs/organes avec une provenance explicite `anomaly_rules` (`anomaly-rules-v1`) :

| Sous-système (`sensor`) | Source télémétrique | État `ok` | État `degraded` | État `fault` | État `absent` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`soil`** | `soil_sensor_ok` + alerte `soil_sensor_failure` | `soil_sensor_ok == true` et kit actif | Kit inactif ou muet (`> device_silent_hours`) | `soil_sensor_ok == false` | — |
| **`bme`** | `bme_ok` | `bme_ok == true` et kit actif | Kit inactif ou muet | `bme_ok == false` | — |
| **`npk`** | `npk_ok` | `npk_ok == true` et kit actif | Kit inactif ou muet | `npk_ok == false` | — |
| **`flow`** | Équipement pompe avec `flow_m3h` renseigné | Débitmètre déclaré et kit actif | Débitmètre déclaré mais kit muet/inactif | — | Kit v1.1 sans débitmètre |
| **`pump`** | `pump_fault` + alerte `pump_fault` | `pump_fault == false` et kit actif | Kit inactif ou muet | `pump_fault == true` | — |
| **`battery`** | `battery_mv` | `battery_mv >= 3500 mV` et kit actif | `3300 mV <= battery_mv < 3500 mV` ou kit muet | `battery_mv < 3300 mV` | — |

---

## 2. Règles d'alerte actives et seuils temporels (`alerting.py` & `config.py`)

Anti-rebond intégré : au plus **une alerte non résolue** par `(device_id, rule)` (arbitrée par l'index unique partiel PostgreSQL `uq_alerts_device_rule_active`).

| Règle (`rule`) | Condition de déclenchement exacte | Paramètre `Settings` | Résolution automatique | Action d'exploitation |
| :--- | :--- | :--- | :--- | :--- |
| **`soil_sensor_failure`** | Dernier point reçu avec `soil_sensor_ok = false` | Immédiat | **Oui** (dès `soil_sensor_ok = true`) | Vérifier câble, connecteur ou ré-enfoncer la sonde. |
| **`pump_fault`** | Dernier point reçu avec `pump_fault = true` | Immédiat | **Oui** (dès `pump_fault = false`) | Coupure de sécurité : vérifier niveau forage/bassin, relais pompe et fusible. |
| **`dry_soil_persistent`** | $\ge 3$ lectures sous `threshold_start_pct` couvrant $\ge 75\,\%$ de la fenêtre | `dry_soil_hours = 2.0 h` | **Oui** (dès remontée au-dessus du seuil) | Vérifier si la pompe a démarré ou si l'irrigation manuelle a été oubliée. |
| **`device_silent`** | Aucun point reçu depuis `device_silent_hours` (`alert_sweep.py`) | `device_silent_hours = 24.0 h` | **Oui** (au retour de télémétrie) | Vérifier couverture GSM, crédit SIM, batterie/panneau solaire (poussière). |

---

## 3. Métriques système & Observabilité d'ingestion (`metrics.py`)

Le Backend instrumente l'ingestion et le trafic via Prometheus (`/metrics`, contrôlé par `METRICS_ENABLED=true`) :
1. **Compteurs de télémétrie (`count_telemetry`)** :
   - `accepted` : points insérés dans `measurements`,
   - `duplicate` : points ignorés par idempotence `(device_id, ts)` (normal lors des reprises de tampon),
   - `rejected_point` : points rejetés entièrement (horodatage hors fenêtre `ts_plausible`),
   - `rejected_value` : champs individuels mis à `NULL` (clé inconnue, `NaN`, type invalide ou valeur hors plage physique).
2. **Indicateurs de santé du pipeline (à surveiller quotidiennement dès le Jour 1)** :
   - **Taux de complétude horaire** par kit : attendu `12 points / heure` (pas de 5 min) et **au moins `1 point / heure`** pour que l'agrégat continu `measurements_1h` alimente sans trou `soil_nowcast`. Seuil d'alerte interne : complétude `< 80 %` sur 24 h.
   - **Taux de rejet valeur** (`rejected_values / (accepted × 16)`): doit rester `< 1 %`. Un pic signale une dérive firmware ou un capteur endommagé.
   - **Latence d'ingestion** (`received_at - ts`) : médiane `< 60 s` en mode MQTT normal ; des retards $> 1\text{ h}$ indiquent un fonctionnement intermittent sur tampon réseau (`source = 'http'`/`'relay'`).
   - **Synchronisation des commandes seuils** (`device_thresholds.sync_status`) : toute commande restant à `pending` ou `sent` plus de `15 min` sans acquittement `commands/ack` doit déclencher une vérification de connectivité descendante.

---

## 4. Escalade et maintenance terrain

| Niveau | Délai de réaction | Déclencheur | Responsable |
| :--- | :--- | :--- | :--- |
| **N1 (Automatique)** | Immédiat | Alerte `dry_soil_persistent` ou batterie `degraded` | Notification producteur + conseil nettoyage panneau solaire |
| **N2 (Support Technique)** | `< 24 h` | `device_silent > 24 h` ou `rejected_values` en hausse ou `sync_status` bloqué | Vérification SIM / logs `mqtt_bridge` / contact téléphonique producteur |
| **N3 (Intervention Parcelle)** | `< 48 h` | `pump_fault` persistant, `soil_sensor_failure` ou `battery < 3300 mV` | Déplacement technicien avec sonde/boîtier de rechange et kit d'étalonnage |
