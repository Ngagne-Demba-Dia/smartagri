# `ml/data/real/iot_telemetry/` — Séries Temporelles Réelles des Kits ESP32-S3 (`telemetry.v1`)

- **Source unique** :
  - `kit_telemetry` : extraction réelle depuis l'hypertable TimescaleDB `measurements` et la vue continue `measurements_1h` (alimentées par les boîtiers ESP32-S3 physiques via `POST /v1/telemetry/batch` ou MQTT).
- **Niveau de disponibilité** :
  - **Niveau B** (nécessite la pose physique des 5 à 10 premiers kits pilotes et l'étalonnage gravimétrique `sm_calibration` sur 6 à 8 semaines).
- **Règle stricte** :
  - Le fichier `ml/data/synthetic/telemetry/telemetry.csv` ne doit **jamais** être copié dans ce dossier.
- **Colonnes cibles normalisées (`Parquet`)** :
  `device_id`, `ts`, `soil_moisture_pct`, `air_temp_c`, `air_humidity_pct`, `pressure_hpa`, `n_mgkg`, `p_mgkg`, `k_mgkg`, `pump_on`, `pump_fault`, `soil_sensor_ok`, `bme_ok`, `npk_ok`, `threshold_start_pct`, `threshold_stop_pct`.
