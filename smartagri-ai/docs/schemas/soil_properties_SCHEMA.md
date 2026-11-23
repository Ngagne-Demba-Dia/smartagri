# `ml/data/real/soil_properties/` — Propriétés Physico-Chimiques des Sols du Sénégal

- **Sources Niveau A (immédiates)** :
  - `isdasoil` : Cloud-Optimized GeoTIFF (COG) à **30 m** de résolution sur toute l'Afrique dans le bucket AWS S3 public `s3://isdasoil/` (`us-west-2`, `--no-sign-request`, licence **CC BY 4.0**) — horizons `0–20 cm` et `20–50 cm` : argile, sable, limon, pH, carbone organique, N total, P extractible, K échangeable, CEC, densité apparente.
  - `soilgrids` : ISRIC SoilGrids 2.0 à **250 m** via WebDAV / WCS (`https://files.isric.org/soilgrids/latest/data/`, COG, licence **CC BY 4.0**).
- **Sources Niveau B (mesures terrain & laboratoire)** :
  - `soil_lab_analyses` : analyses de laboratoire des parcelles pilotes + pesées gravimétriques à l'étuve 105 °C (`sm_calibration`).
  - `soil_field_kits` : mesures de CE 1:5 et pH à l'installation des kits.
- **Sources Niveau C (partenariat)** :
  - `inp_soil_map` : cartes pédologiques fines (*dior*, *deck*, *deck-dior*, *hollaldé*, *fondé*) sous convention avec l'Institut National de Pédologie (INP).
- **Colonnes cibles normalisées (`Parquet`)** :
  `site_id`, `lat`, `lon`, `depth_cm`, `sand_pct`, `clay_pct`, `silt_pct`, `soil_class_local`, `ph_h2o`, `soc_g_kg`, `cec_cmol_kg`, `bulk_density_g_cm3`, `field_capacity_pct`, `wilting_point_pct`, `source_id`.
