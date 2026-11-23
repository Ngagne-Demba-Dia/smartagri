# `ml/data/real/et0/` — Évapotranspiration de Référence ($ET_0$) et Réelle ($ET_a$)

- **Sources Niveau A (immédiates)** :
  - Calcul déterministe FAO-56 (`agronomy.extraterrestrial_radiation` + `agronomy.hargreaves_et0` ou Penman-Monteith complet) alimenté par les séries réelles `nasa_power` (`T2M_MAX`, `T2M_MIN`, `ALLSKY_SFC_SW_DWN`, `WS2M`, `RH2M`).
- **Sources Niveau B (avec préparation / clarification licence)** :
  - `agera5` & `era5_land` : `potential_evaporation` / indicateurs agrométéo C3S (0,1°).
  - `wapor` (FAO WaPOR v3) : $ET_a$ et biomasse décadaire à **20 m (L3)** sur la Vallée du Fleuve Sénégal et **100 m (L2)** sur tout le Sénégal (licence à confirmer par écrit pour l'export commercial).
- **Colonnes cibles normalisées (`Parquet`)** :
  `site_id`, `lat`, `lon`, `date`, `ra_mj_m2`, `et0_hargreaves_mm`, `et0_pm_mm`, `eta_wapor_mm`, `source_id`.
