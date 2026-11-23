# `ml/data/real/sentinel2_ndvi/` — Séries Sentinel-2 L2A & Indices de Végétation (NDVI, EVI, NDWI, SAVI)

- **Sources Niveau A (immédiates, sans authentification)** :
  - `deafrica` (Digital Earth Africa) : catalogue STAC public `https://explorer.digitalearth.africa/stac` (collection `s2_l2a`, COG sur `s3.af-south-1.amazonaws.com` en accès `aws_unsigned=True`, licence **CC BY 4.0**), résolution **10 m** (bandes `B02`, `B03`, `B04`, `B08` + masque nuageux `SCL` 20 m), revisite 5 jours sur tout le Sénégal.
- **Sources Niveau B (avec compte CDSE / Earthdata & post-traitement)** :
  - `sentinel2` : Copernicus Data Space Ecosystem (`https://catalogue.dataspace.copernicus.eu/stac`).
  - `hls` : NASA Harmonized Landsat Sentinel-2 (30 m, 2–3 jours).
  - Lissage de Whittaker (`ndvi_gapfill`) sur les pixels clairs (`SCL in {4, 5}`).
- **Colonnes cibles normalisées (`Parquet` par parcelle / polygone)** :
  `field_id`, `date`, `scene_id`, `cloud_pct`, `ndvi_mean`, `ndvi_p10`, `ndvi_p90`, `evi_mean`, `ndwi_mean`, `savi_mean`, `gapfilled`, `source_id`.
