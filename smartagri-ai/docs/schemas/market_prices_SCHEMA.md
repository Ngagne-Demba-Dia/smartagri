# `ml/data/real/market_prices/` — Prix Agricoles & Mercuriales du Sénégal (FCFA/kg)

- **Sources Niveau A (immédiates)** :
  - `hdx_wfp_senegal` : jeu ouvert **WFP / VAM Food Prices for Senegal** sur Humanitarian Data Exchange (`https://data.humdata.org/dataset/wfp-food-prices-for-senegal`, `wfp_food_prices_sen.csv` & `wfp_markets_sen.csv`, licence **CC BY-IGO / Open Data**), séries mensuelles/hebdomadaires en **XOF (FCFA)** par marché sénégalais (Dakar, Castors, Tilène, Thiès, Saint-Louis, Kaolack, Touba, Diourbel, Ziguinchor, Tambacounda).
  - `energy_tariffs` : grilles tarifaires publiques Senelec et arrêtés hydrocarbures.
- **Sources Niveau B (avec vérification licence ou enquête terrain)** :
  - `input_prices_survey` : relevés mensuels du prix des intrants (urée, NPK 10-10-20, semences) auprès des coopératives.
  - `fews_net` & `giews_fpma` : séries mensuelles FAO/FEWS NET (après confirmation écrite des conditions d'usage commercial).
- **Sources Niveau C (partenariat)** :
  - `sim_csa` : mercuriales hebdomadaires du Système d'Information sur les Marchés (Commissariat à la Sécurité Alimentaire).
  - `arm_prices` : prix bord champ et stocks de régulation de l'Agence de Régulation des Marchés (ARM : oignon local vs importé, pomme de terre, carotte).
- **Colonnes cibles normalisées (`Parquet`)** :
  `date`, `market`, `region`, `lat`, `lon`, `crop`, `price_type` (`retail` | `wholesale` | `farmgate`), `price_fcfa_kg`, `currency` (`XOF`), `source_id`.
