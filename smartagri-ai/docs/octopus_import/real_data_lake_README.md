# `ml/data/real/` — Référentiel des Jeux de Données Réels SmartAgri92

**Statut** : Phase IA Réelle (`IA-REAL-01`) — *Confidentiel — réservé aux partenaires de travail.*  
**Règle absolue** : Ce répertoire est **exclusivement réservé aux données réelles** (issues d'API ouvertes vérifiées, de produits satellitaires, de relevés de laboratoire/terrain ou de partenaires sous convention). **Aucune donnée synthétique (`make_synthetic.py`) ni simulée (`web/mocks/`) ne doit jamais être déposée ici.**

---

## 1. Structure de l'arborescence

```text
ml/data/real/
├── README.md                        # Présent guide de gouvernance et contrats de schémas
├── manifests/
│   └── sources_registry.json        # Registre machine des sources réelles (Niveau A / B / C, licences, URLs)
├── meteo/                           # Séries horaires & quotidiennes (NASA POWER, ERA5-Land, ECMWF/GFS, Open-Meteo)
├── rain/                            # Précipitations quotidiennes/pentadaires (CHIRPS v3, TAMSAT v3.1, GPM IMERG)
├── et0/                             # Évapotranspiration de référence & réelle (AgERA5, ERA5-Land, FAO-56, WaPOR v3)
├── soil_moisture/                   # Humidité du sol satellite/réanalyse (ERA5-Land swvl1..3, NASA POWER GWETTOP/GWETROOT, Sentinel-1)
├── soil_properties/                 # Pédologie & laboratoire (iSDAsoil 30m, ISRIC SoilGrids 250m, analyses labo & sm_calibration)
├── sentinel2_ndvi/                  # Réflectances L2A 10m & indices NDVI/EVI/NDWI/SAVI (CDSE, Digital Earth Africa STAC)
├── crops_senegal/                   # Cultures maraîchères du Sénégal (calendriers culturaux, Kc FAO-56/ISRA, WorldCover 10m)
├── yields/                          # Rendements agricoles historiques & observés (FAOSTAT Sénégal, DAPSA, ANSD, pesées terrain)
├── market_prices/                   # Mercuriales & prix agricoles en FCFA/kg (HDX WFP/VAM Sénégal, SIM/CSA, ARM, ANSD)
└── iot_telemetry/                   # Séries temporelles réelles extraites de TimescaleDB (measurements_1h des kits ESP32-S3)
```

---

## 2. Règles de dépôt et de traçabilité (Data Provenance)

Chaque jeu déposé dans un sous-dossier de `ml/data/real/<domaine>/` doit respecter les 5 règles suivantes :

1. **Format normalisé** :
   - Séries tabulaires et temporelles : **Apache Parquet** (`.parquet`, compression `snappy` ou `zstd`) ou CSV UTF-8 (`.csv`) avec horodatages ISO-8601 en **UTC** (`ts` ou `date`).
   - Produits matriciels / rasters : **Cloud-Optimized GeoTIFF** (`.tif` en `EPSG:4326` ou `EPSG:32628` — UTM Zone 28N couvrant le Sénégal) ou **NetCDF4 / Zarr**.
2. **Manifeste compagnon obligatoire (`<fichier>.manifest.json`)** :
   - Chaque fichier de données doit être accompagné d'un manifeste JSON contenant :
     - `source_id` (identifiant de `ml/catalog/sources.yaml`),
     - `owner` (propriétaire / producteur de la donnée),
     - `licence` et `commercial_use` (`open` | `contract`),
     - `fetched_at` (date et heure UTC d'acquisition),
     - `bbox_or_sites` (emprise géographique ou liste des sites : ex. Mboro, Sangalkam, Richard-Toll),
     - `sha256` (empreinte cryptographique du fichier brut),
     - `rows` et `columns` (pour les tables).
3. **Absence de fuite temporelle (*As-Of Integrity*)** :
   - Toute prévision météorologique archivée dans `meteo/` ou `rain/` doit conserver à la fois `issue_time` (date d'émission de la prévision) et `valid_time` (échéance), afin de ne jamais entraîner un modèle sur une réanalyse future déguisée en prévision.
4. **Protection des données personnelles (Loi sénégalaise 2008-12 / CDP)** :
   - Aucun nom d'exploitant, numéro de téléphone ou courriel ne doit figurer dans `ml/data/real/`.
   - Tout export vers OctOpus passe obligatoirement par `agriml.octopus.exporter` vers `data/curated/octopus/`.
5. **Références documentaires** :
   - Plan d'acquisition détaillé : [`docs/44_real_data_acquisition_plan.md`](../../../docs/44_real_data_acquisition_plan.md).
   - Inventaire initial : [`docs/41_data_inventory.md`](../../../docs/41_data_inventory.md).
   - Plan d'onboarding OctOpus : [`docs/42_octopus_onboarding_plan.md`](../../../docs/42_octopus_onboarding_plan.md).
