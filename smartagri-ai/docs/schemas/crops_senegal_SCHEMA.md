# `ml/data/real/crops_senegal/` — Cultures Maraîchères du Sénégal (Calendriers, $K_c$, Occupation du Sol)

- **Sources Niveau A (immédiates)** :
  - `fao56_tables` : paramètres culturaux FAO-56 déjà codés dans `backend/app/services/agronomy.py` (`onion`, `tomato`, `cabbage`, `potato`, `carrot`, `pepper`, `lettuce`).
  - `worldcover` : ESA WorldCover 10 m (`https://esa-worldcover.org/`, COG AWS S3 `s3://esa-worldcover/`, licence **CC BY 4.0**) pour le masque des terres cultivées (`classe 40`) des Niayes et de la Vallée.
  - `csp_pesticides` : liste réglementaire publique des produits homologués au Sahel (CSP / CILSS).
- **Sources Niveau B (préparation)** :
  - `plantdoc` : 2 598 photos de feuilles malades en plein champ (licence **CC BY 4.0**) pour le pré-entraînement de base.
  - `crop_cycles_user` : cycles culturaux déclarés par les producteurs dans PostgreSQL (`crop_cycles`).
- **Sources Niveau C (partenariat)** :
  - `isra_cdh_references` : fiches techniques et barèmes du Centre pour le Développement de l'Horticulture (ISRA/CDH Cambérène) et de l'ANCAR.
  - `dpv_alerts` : bulletins phytosanitaires de la Direction de la Protection des Végétaux (DPV).
