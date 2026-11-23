# `ml/data/real/yields/` — Rendements Agricoles Réels au Sénégal

- **Sources Niveau A (immédiates, échelle nationale)** :
  - `faostat` : base `QCL` (Crops and livestock products — Sénégal `area_code=195`, 1961–présent, licence **CC BY 4.0**), fournissant surfaces récoltées (ha), rendements (kg/ha → t/ha) et productions (tonnes) pour oignon, tomate, pomme de terre, chou, carotte, piment/poivron, riz, maïs, mil, sorgho, arachide.
- **Sources Niveau B (préparation / saisie terrain)** :
  - `farmer_harvests` : pesées réelles en fin de cycle (`crop_cycles.yield_kg` / `area_ha`) sur les parcelles pilotes.
  - `sarra` : simulations de référence du modèle agro-climatique SARRA-Py (CIRAD, GPLv3).
- **Sources Niveau C (partenariat)** :
  - `dapsa_surveys` : Enquête Agricole Annuelle (EAA) de la DAPSA par département (Thiès, Tivaouane, Louga, Dagana, Podor, Dakar).
  - `ansd_stats` : bulletins agricoles régionaux ANSD.
  - `research_trials` : essais variétaux ISRA/CDH et AfricaRice.
- **Colonnes cibles normalisées (`Parquet`)** :
  `region_or_field_id`, `campaign_id`, `year`, `season`, `crop`, `area_ha`, `yield_t_ha`, `production_t`, `scale` (`national` | `department` | `field`), `source_id`.
