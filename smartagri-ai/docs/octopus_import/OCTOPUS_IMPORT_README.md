# Package d'Import OctOpus — SmartAgri92 (`OCTOPUS-PACK-01`)

**Date de génération** : 2026-11-16 10:28 UTC  
**Périmètre** : Data Lake Réel National du Sénégal (`14/14` régions, grille `0,05°`, `0` donnée synthétique, `0` modèle entraîné).

---

## 1. Contenu du Package (`octopus_import/`)

- **`datasets/`** : **25 fichiers Parquet réels** issus exclusivement des sources Niveau A téléchargées et vérifiées (**30,073,395 lignes**, **162.64 Mo**).
- **`manifests/`** : empreintes SHA-256 par fichier, rapport d'audit (`lake_audit_report.json`), contrôles croisés (`cross_checks.json`) et infos grille (`grid_info.json`).
- **`schemas/`** : contrats de colonnes par domaine (`*_SCHEMA.md`) et catalogue MLOps complet (`catalog/sources.yaml`, `datasets.yaml`, `models.yaml`).
- **`documentation/`** : documents `41`, `42`, `44`, `45`, `46`, `53` + gouvernance `real_data_lake_README.md`.
- **`uploads/`** : instantané prêt à téléverser `soil_nowcast_proxy_national/v=20261114-natl01/` (`train.parquet` `258 440` lignes / `9.7 Mo` + `test.parquet` `25 915` lignes sans cible, `power_cell_id` pseudonymisé HMAC-SHA256, `holdout_sent: false`).
- **`octopus_datasets_inventory.csv`** : inventaire tabulaire complet avec SHA-256, lignes, tailles et vagues d'import.
- **`octopus_upload_order.md`** : procédure d'import en **4 vagues**.

---

## 2. Licences & Conformité Commerciale

Toutes les données incluses dans `datasets/` sont sous **licence ouverte compatible usage commercial (`commercial_use: open`)** :
- **NASA POWER** : NASA Open Data Policy (attribution requise).
- **CHIRPS** : CC BY 4.0 (UCSB CHC / DE Africa S3).
- **iSDAsoil & SoilGrids 2.0** : CC BY 4.0.
- **ESA WorldCover 10 m & Digital Earth Africa Sentinel-2 L2A** : CC BY 4.0 / Licence Copernicus libre.
- **FAOSTAT** : CC BY 4.0.
- **WFP / VAM Senegal Food Prices (HDX)** : CC BY-IGO 3.0 / Open Data.
- **geoBoundaries ADM1 Sénégal** : CC BY 3.0 IGO (OCHA ROWCA).

---

## 3. Dépendances & Clés de Jointure

- **Clé spatiale fine (`0,05°`, ≈ 5,5 km)** : `cell_id` (`0..6944` sur les 14 régions, définie dans `datasets/geo/senegal_grid_0p05.parquet`).
- **Clé spatiale météo (`0,5° × 0,625°`)** : `power_cell_id` (`76` mailles, table de correspondance incluse dans `senegal_grid_0p05.parquet`).
- **Zones de validation spatiale** : la colonne `validation_zone` (`mboro`, `potou`, `richard_toll`) doit rester **exclue de l'entraînement** pour mesurer la généralisation spatiale à tout nouveau kit au Sénégal.
- **Holdouts souverains** : strictement exclus de ce package (`holdout_sent: false`), conservés localement dans `plateforme/ml/data/curated/holdout/`.

---

## 4. Ordre Recommandé d'Import

Suivre les 4 vagues décrites dans `octopus_upload_order.md` :
1. **Vague 1** : `geo` → `weather` (`meteo`) → `rain` → `ET0` → `soil_wetness` (`soil_moisture`)
2. **Vague 2** : `soils` (`soil_properties`) → `worldcover` & `fao56` (`crops_senegal`)
3. **Vague 3** : `sentinel2` & `ndvi` (`sentinel2_ndvi`)
4. **Vague 4** : `prices` (`market_prices`) → `yields`
