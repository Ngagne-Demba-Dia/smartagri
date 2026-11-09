# Annexe A1 — Sources de données

> Confidentiel - réservé aux partenaires de travail.
> Fichier généré par `python -m agriml.catalog render` depuis `ml/catalog/*.yaml` — ne pas modifier à la main.

104 sources sur 14 domaines. « Usage commercial » : ouvert = permis ; contrat = accord ou abonnement à signer ; non commercial = recherche seulement ; à vérifier = licence non confirmée. « Vérifiée » = date de lecture de la licence sur une page publique (URL dans `sources.yaml`, champ `evidence`).

## Synthèse

| Domaine | Sources | ouvert | contrat | non commercial | à vérifier | Licence vérifiée |
|---|---|---|---|---|---|---|
| Météo et climat | 14 | 9 | 4 | 0 | 1 | 5 |
| Sols | 6 | 4 | 1 | 0 | 1 | 3 |
| Satellite | 8 | 6 | 1 | 0 | 1 | 1 |
| Drone | 3 | 3 | 0 | 0 | 0 | 0 |
| IoT (kit) | 8 | 8 | 0 | 0 | 0 | 0 |
| Phytosanitaire | 13 | 7 | 3 | 0 | 3 | 3 |
| Agronomie | 8 | 4 | 1 | 1 | 2 | 3 |
| Économie | 11 | 5 | 4 | 0 | 2 | 0 |
| Géospatial | 9 | 6 | 2 | 0 | 1 | 4 |
| Eau et irrigation | 3 | 2 | 1 | 0 | 0 | 0 |
| Historique | 5 | 2 | 2 | 0 | 1 | 0 |
| Utilisateurs et consentements | 5 | 5 | 0 | 0 | 0 | 0 |
| Langue et voix | 9 | 4 | 1 | 2 | 2 | 3 |
| Connaissances (RAG) | 2 | 1 | 1 | 0 | 0 | 0 |
| **Total** | 104 | 66 | 21 | 3 | 14 | 22 |

## Météo et climat

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `open_meteo` | Open-Meteo (prévision, archive, ensembles) | API publique | Données CC BY 4.0 ; API gratuite réservée au non commercial (abonnement ou publicité = commercial) | contrat | — | complète | Standard ~29 $/mois, Professional ~99 $/mois (blog 2023, à reconfirmer) ; Professional requis pour historique, ensembles, rayonnement ; ou auto-hébergement (AGPLv3) | API REST JSON | 2026-11-01 |
| `ecmwf_open_data` | ECMWF Open Data (IFS, AIFS) | Open data | CC BY 4.0 | ouvert | — | complète | Gratuit | GRIB2 par HTTP et miroirs cloud | non |
| `noaa_gfs` | NOAA GFS | Open data | Domaine public (NOAA) | ouvert | — | complète | Gratuit | GRIB2 (NOMADS, AWS Open Data) | non |
| `era5` | ERA5 (réanalyse ECMWF) | Open data | CC BY (C3S/ECMWF), compte CDS | ouvert | — | complète | Gratuit | Copernicus CDS (cdsapi), ARCO Zarr | 2026-11-01 |
| `era5_land` | ERA5-Land | Open data | Licence Copernicus (libre, attribution) | ouvert | — | complète | Gratuit | Copernicus CDS | non |
| `agera5` | AgERA5 (indicateurs agrométéo) | Open data | Licence Copernicus (libre, attribution) | ouvert | — | complète | Gratuit | Copernicus CDS | non |
| `nasa_power` | NASA POWER (agroclimatologie) | API publique | Données NASA, libres avec citation | ouvert | — | complète | Gratuit | API REST (point, région), JSON/CSV | non |
| `chirps` | CHIRPS v3 (pluie satellite + stations) | Open data | v2 domaine public ; v3 CC BY 4.0 (attribution) | ouvert | — | complète | Gratuit | GeoTIFF, NetCDF, COG (HTTP), GEE | 2026-11-01 |
| `tamsat` | TAMSAT v3.1 (pluie Afrique) | Open data | Creative Commons (version non nommée) ; usage opérationnel, recherche et commercial déclaré | ouvert | — | complète | Gratuit | NetCDF (HTTP), sous-ensembles CSV ; pas d'API | 2026-11-01 |
| `imerg` | NASA GPM IMERG | Open data | Données NASA, libres | ouvert | — | complète | Gratuit (compte Earthdata) | GES DISC (HTTP, OPeNDAP) | non |
| `cmsaf_sarah` | CM SAF SARAH-3 (rayonnement MSG) | Open data | CM SAF products licence rev. 1 : gratuit, © EUMETSAT ; usage commercial non explicite | à vérifier | — | complète | Gratuit (inscription) | Portail CM SAF | 2026-11-01 |
| `tahmo` | TAHMO (stations automatiques) | Partenaire | Accord de données TAHMO | contrat | — | partielle | Non publié (Data Policy non lue) ; hypothèse : gratuit recherche, devis en commercial | Portail après formulaire ; API non documentée publiquement | non |
| `anacim_stations` | ANACIM (stations synoptiques et climatologiques) | Partenaire | Convention ANACIM | contrat | — | partielle | Sur convention | Fichiers fournis par l'ANACIM | non |
| `agrhymet_presass` | AGRHYMET / PRESASS (prévision saisonnière) | Partenaire | Bulletins publics ; données sur convention | contrat | — | complète | Gratuit (bulletins) | Bulletins PDF, cartes | non |

## Sols

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `soilgrids` | ISRIC SoilGrids 2.0 | Open data | CC BY 4.0 | ouvert | — | complète | Gratuit | WCS, WebDAV (COG) ; API REST « temporarily paused » sans calendrier | 2026-11-01 |
| `isdasoil` | iSDAsoil (Afrique) | Open data | CC BY 4.0 | ouvert | — | complète | Gratuit | S3 public isdasoil (us-west-2), COG ; API iSDA (état non vérifié) | 2026-11-01 |
| `hwsd` | FAO HWSD v2 | Open data | Aucune licence affichée par la FAO ; mentions secondaires CC BY-NC-SA (risque NC) | à vérifier | — | complète | Gratuit | Raster + base de profils | 2026-11-01 |
| `inp_soil_map` | Institut national de pédologie (cartes, études) | Partenaire | Convention INP | contrat | — | partielle | Sur convention | Cartes et rapports | non |
| `soil_lab_analyses` | Analyses de sol en laboratoire | Partenaire | Prestation : résultats propriété du projet | ouvert | indirecte | partielle | Hypothèse 15–40 k FCFA par échantillon | Fichiers du laboratoire, saisie | non |
| `soil_field_kits` | Mesures de terrain (conductimètre, pH-mètre) | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 100–300 € par appareil | Saisie mobile du technicien | non |

## Satellite

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `sentinel2` | Sentinel-2 L2A | Open data | Licence Copernicus (libre) | ouvert | — | complète | Gratuit (quotas CDSE) | Copernicus Data Space : STAC, openEO, Sentinel Hub | non |
| `sentinel1` | Sentinel-1 GRD | Open data | Licence Copernicus (libre) | ouvert | — | complète | Gratuit (quotas CDSE) | Copernicus Data Space | non |
| `landsat` | Landsat 8/9 Collection 2 | Open data | Domaine public (USGS) | ouvert | — | complète | Gratuit | USGS M2M, STAC, AWS (paiement du demandeur) | non |
| `hls` | NASA HLS (Landsat + Sentinel-2 harmonisés) | Open data | Données NASA, libres | ouvert | — | complète | Gratuit (Earthdata) | LP DAAC, STAC CMR | non |
| `modis_viirs` | MODIS / VIIRS (indices de végétation) | Open data | Données NASA, libres | ouvert | — | complète | Gratuit | LP DAAC, AppEEARS | non |
| `planetscope` | PlanetScope | Commercial | Licence Planet (usage et diffusion restreints) | contrat | — | complète | Sur devis (non publié) ; NICFI terminé le 23/01/2025 ; offre Éducation et recherche non commerciale | API Planet | non |
| `deafrica` | Digital Earth Africa | Open data | CC BY 4.0 (à confirmer par produit) | ouvert | — | complète | Gratuit | AWS af-south-1 (COG), STAC | non |
| `wapor` | FAO WaPOR v3 | Open data | Contradictoire : FAO Open Data, CC BY-SA 4.0 ou CC BY-NC-SA 4.0 selon la page | à vérifier | — | complète | Gratuit | Portail et API WaPOR, GEE, DE Africa | 2026-11-01 |

## Drone

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `drone_rgb` | Drone RGB (orthomosaïques, MNS) | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 5–15 k FCFA/ha en prestation | Missions planifiées, photogrammétrie | non |
| `drone_multispectral` | Drone multispectral | Interne | Interne | ouvert | indirecte | partielle | Capteur 5–10 bandes (hypothèse 4–8 k€) | Missions planifiées, panneau de calibration | non |
| `drone_thermal` | Drone thermique | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 3–6 k€ le capteur | Vols en milieu de journée | non |

## IoT (kit)

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `kit_telemetry` | Télémétrie du kit (telemetry.v1) | Interne | Interne | ouvert | indirecte | partielle | Inclus dans le kit | MQTT, relais mobile, POST /v1/telemetry/batch | non |
| `kit_events` | Événements du kit | Interne | Interne | ouvert | indirecte | partielle | Inclus | MQTT, API | non |
| `kit_config` | Registre et configuration des kits | Interne | Interne | ouvert | indirecte | partielle | Inclus | API devices, installation (UC-01) | non |
| `kit_espcam` | Images ESP32-CAM | Interne | Interne | ouvert | indirecte | partielle | Module caméra (hypothèse 5–8 k FCFA) | Téléversement S3 présigné | non |
| `kit_flowmeter` | Débitmètre (prévu, firmware v1.2) | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 3–10 k FCFA (effet Hall) | telemetry.v2 (à définir) | non |
| `kit_power` | Énergie (prévu) : batterie, panneau, courant pompe | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 2–5 k FCFA (INA219) | telemetry.v2 (à définir) | non |
| `kit_soil_extended` | Sol étendu (prévu) : CE, température, 2e profondeur | Interne | Interne | ouvert | indirecte | partielle | 0 si la sonde 7-en-1 expose CE/T ; sinon seconde sonde | telemetry.v2 (à définir) | non |
| `kit_microclimate` | Microclimat (prévu, kits de référence) | Interne | Interne | ouvert | indirecte | partielle | Hypothèse 60–150 k FCFA par kit de référence | telemetry.v2 (à définir) | non |

## Phytosanitaire

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `advisor_diagnoses` | Validations des conseillers | Interne | Interne | ouvert | indirecte | partielle | Temps des conseillers | File de validation (module 8) | non |
| `farmer_photos` | Photos des producteurs | Saisie utilisateur | Consentement de l'utilisateur | ouvert | directe | partielle | — | Application mobile, web (POST /v1/images) | non |
| `scouting_reports` | Observations et piégeage | Saisie utilisateur | Interne | ouvert | indirecte | partielle | Pièges à phéromones (hypothèse) | Saisie mobile | non |
| `treatments_log` | Journal des traitements | Saisie utilisateur | Interne | ouvert | indirecte | partielle | — | Saisie mobile | non |
| `dpv_alerts` | Direction de la protection des végétaux (alertes) | Partenaire | Convention DPV | contrat | — | partielle | Sur convention | Bulletins, échanges | non |
| `famews` | FAO FAMEWS (chenille légionnaire) | Partenaire | Plateforme « freely accessible » ; ni licence, ni export, ni API trouvés (page FAO en 404) | à vérifier | — | partielle | Gratuit | Plateforme FAMEWS (accord à demander à la FAO) | non |
| `fao_locust` | FAO Desert Locust Watch / Locust Hub | Open data | Réutilisation encouragée avec crédit FAO ; licence exacte non trouvée | à vérifier | — | complète | Gratuit | Locust Hub ; jeu complet sur demande de compte, pas de temps réel | non |
| `csp_pesticides` | Liste des pesticides autorisés (CSP / CILSS) | Référence | Liste réglementaire publique | ouvert | — | complète | Gratuit | Liste publiée par le CSP | non |
| `pest_biology_reference` | Biologie des ravageurs (littérature) | Référence | Faits publiés, citation | ouvert | — | complète | — | Revue bibliographique | non |
| `plantvillage` | PlantVillage | Open data | Original sans licence (citation demandée) ; dérivé Mendeley CC0, chaîne de droits non établie | à vérifier | — | aucune | Gratuit | Dépôts publics | 2026-11-01 |
| `plantdoc` | PlantDoc | Open data | CC BY 4.0 (LICENSE.txt) | ouvert | — | aucune | Gratuit | Dépôt public | 2026-11-01 |
| `gbif` | GBIF (occurrences d'espèces) | Open data | CC0, CC BY 4.0 ou CC BY-NC 4.0 par jeu ; un téléchargement prend la plus restrictive | contrat | — | partielle | Gratuit | API GBIF avec filtre de licence (CC0, CC BY) | 2026-11-01 |
| `vision_backbones` | Réseaux de vision pré-entraînés (timm, torchvision) | Pré-entraîné | Variable selon le modèle | contrat | — | complète | Gratuit | Poids publics | non |

## Agronomie

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `crop_cycles_user` | Cycles culturaux déclarés | Saisie utilisateur | Interne | ouvert | indirecte | partielle | — | API fields, campagnes | non |
| `operations_log` | Journal des opérations | Saisie utilisateur | Interne | ouvert | indirecte | partielle | — | Saisie mobile | non |
| `fao56_tables` | FAO-56 (coefficients culturaux) | Référence | Coefficients publiés, citation | ouvert | — | complète | — | Publication FAO 56 | non |
| `fao_crop_calendar` | FAO Crop Calendar | Open data | Aucune licence trouvée (hypothèse : CC BY-NC-SA 3.0 IGO de la FAO) | à vérifier | — | complète | Gratuit | Outil en ligne | non |
| `isra_cdh_references` | Références ISRA, CDH, ANCAR | Partenaire | Convention de partenariat | contrat | — | complète | Sur convention | Fiches, catalogues, rapports | non |
| `aquacrop` | AquaCrop (FAO) / AquaCrop-OSPy | Référence | Logiciel gratuit ; cœur Fortran open source (LICENSE non lu) ; manuels FAO non commerciaux | à vérifier | — | complète | Gratuit | Logiciel, bibliothèque Python | 2026-11-01 |
| `sarra` | SARRA-Py / SARRA-O (famille SARRA, CIRAD) | Référence | SARRA-Py GPLv3 ; SARRA-O CeCILL-C (à confirmer) ; SARRA-H non publié (contact CIRAD) | ouvert | — | complète | Gratuit (paramétrage local avec l'ISRA conseillé) | Dépôts GitHub (Python) | 2026-11-01 |
| `gyga` | Yield Potential and Yield Gap Atlas (YPYGA, ex-GYGA) | Open data | CC BY-NC-SA 4.0 ; usage commercial sur accord | non commercial | — | ? | Gratuit (non commercial) | Atlas en ligne, téléchargement | 2026-11-01 |

## Économie

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `sim_csa` | SIM du Commissariat à la sécurité alimentaire | Partenaire | Convention CSA | contrat | — | partielle | Sur convention | Bulletins, fichiers | non |
| `arm_prices` | Agence de régulation des marchés (ARM) | Partenaire | Convention ARM | contrat | — | partielle | Sur convention | Bulletins, fichiers | non |
| `fews_net` | FEWS NET (prix de marché) | Open data | À confirmer | à vérifier | — | partielle | Gratuit | Portail, API | non |
| `giews_fpma` | FAO GIEWS FPMA | Open data | Licence non indiquée ; couverture Sénégal non vérifiée | à vérifier | — | partielle | Gratuit | Outil FPMA | non |
| `input_prices_survey` | Relevé des prix des intrants | Interne | Interne | ouvert | — | partielle | Temps des animateurs | Enquête mensuelle (coopératives, fournisseurs) | non |
| `energy_tariffs` | Tarifs de l'électricité et des carburants | Référence | Textes publics | ouvert | — | complète | — | Arrêtés et grilles tarifaires | non |
| `logistics_costs` | Coûts logistiques | Interne | Interne | ouvert | — | partielle | Temps des animateurs | Enquête | non |
| `farm_accounts` | Comptes d'exploitation déclarés | Saisie utilisateur | Consentement de l'utilisateur | ouvert | directe | partielle | — | Saisie mobile (V2) | non |
| `payments` | Paiements mobiles (Wave, Orange Money) | Interne | Interne | ouvert | directe | partielle | Frais de transaction | Webhooks des opérateurs | non |
| `cnaas_insurance` | CNAAS (assurance agricole) | Partenaire | Convention CNAAS | contrat | indirecte | partielle | Sur convention | Fichiers | non |
| `mfi_credit_outcomes` | Remboursements de crédit (institutions de microfinance) | Partenaire | Convention + consentement | contrat | directe | partielle | Sur convention | Fichiers | non |

## Géospatial

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `user_field_boundaries` | Contours des parcelles | Saisie utilisateur | Consentement de l'utilisateur | ouvert | directe | partielle | — | Dessin web (module 4), relevé GPS mobile | non |
| `geoboundaries` | geoBoundaries (limites administratives) | Open data | CC BY 4.0 (à confirmer) | ouvert | — | complète | Gratuit | API, GeoJSON | non |
| `ansd_admin` | ANSD (limites officielles, recensement) | Partenaire | « Licence ouverte » annoncée par l'ANSD (2024), conditions non lues | contrat | — | complète | Sur demande | Fichiers | non |
| `copernicus_dem` | Copernicus DEM GLO-30 | Open data | Licence Copernicus DEM (libre, conditions) | ouvert | — | complète | Gratuit | AWS Open Data, CDSE | non |
| `worldcover` | ESA WorldCover | Open data | CC BY 4.0 | ouvert | — | complète | Gratuit | COG (AWS, Zenodo) | 2026-11-01 |
| `jrc_gsw` | JRC Global Surface Water v1.5 | Open data | Copernicus : gratuit, sans restriction ; crédit EC JRC/Google | ouvert | — | complète | Gratuit | GEE, téléchargement | 2026-11-01 |
| `hydrosheds` | HydroSHEDS / HydroRIVERS | Open data | Licence HydroSHEDS : usage scientifique, éducatif et commercial, attribution | ouvert | — | complète | Gratuit | Téléchargement | 2026-11-01 |
| `osm` | OpenStreetMap | Open data | ODbL 1.0 : attribution et partage à l'identique des bases dérivées diffusées | contrat | — | complète | Gratuit (tuiles et API OSM non utilisables en production : auto-héberger) | Extraits Geofabrik, Overpass | 2026-11-01 |
| `field_boundaries_open` | Contours de parcelles ouverts (Fields of The World…) | Open data | À confirmer | à vérifier | — | ? | Gratuit | Téléchargement | non |

## Eau et irrigation

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `dgpre_groundwater` | DGPRE (nappes, piézométrie, qualité) | Partenaire | Convention DGPRE | contrat | — | partielle | Sur convention | Fichiers | non |
| `irrigation_water_quality` | Qualité de l'eau d'irrigation | Interne | Interne | ouvert | indirecte | partielle | Conductimètre (voir sols) | Saisie mobile du technicien | non |
| `well_inventory` | Inventaire des ouvrages d'irrigation | Saisie utilisateur | Interne | ouvert | indirecte | partielle | — | Installation du kit (UC-01) | non |

## Historique

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `faostat` | FAOSTAT | Open data | CC BY 4.0 (à confirmer) | ouvert | — | complète | Gratuit | API, CSV | non |
| `dapsa_surveys` | DAPSA (enquête agricole annuelle) | Partenaire | Convention | contrat | — | complète | Sur convention | Rapports, tableaux | non |
| `ansd_stats` | ANSD (statistiques) | Partenaire | « Licence ouverte » annoncée (2024), mentions légales non lues (TLS) | à vérifier | — | complète | Gratuit | Publications | non |
| `farmer_harvests` | Récoltes déclarées | Saisie utilisateur | Interne | ouvert | indirecte | partielle | — | Saisie mobile, campagnes (module 11) | non |
| `research_trials` | Essais agronomiques (ISRA, AfricaRice, CIRAD) | Partenaire | Variable selon le jeu | contrat | — | partielle | Gratuit à sur convention | Dataverse, conventions | non |

## Utilisateurs et consentements

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `user_accounts` | Comptes | Interne | Interne | ouvert | directe | partielle | — | API auth, me | non |
| `farm_registry` | Exploitations et membres | Interne | Interne | ouvert | directe | partielle | — | API farms | non |
| `consents` | Consentements | Interne | Interne | ouvert | directe | partielle | — | API (à créer) | non |
| `reco_feedback` | Retours sur les recommandations | Interne | Interne | ouvert | indirecte | partielle | — | API recommendations feedback | non |
| `app_usage` | Journal d'usage de l'application | Interne | Interne | ouvert | indirecte | partielle | — | Journaux applicatifs | non |

## Langue et voix

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `assistant_logs` | Conversations de l'assistant | Interne | Interne | ouvert | directe | partielle | — | API assistant/chat | non |
| `speech_consented` | Enregistrements vocaux consentis | Saisie utilisateur | Consentement explicite | ouvert | directe (identifiante) | partielle | Hypothèse 3–8 k FCFA par heure transcrite | Campagne de collecte (V2) | non |
| `common_voice` | Mozilla Common Voice | Open data | CC0 | ouvert | — | ? | Gratuit | Téléchargement | non |
| `open_wolof_speech` | Corpus vocaux wolof publics | Open data | Variable, à vérifier jeu par jeu | à vérifier | — | partielle | Gratuit | Dépôts publics | non |
| `claude_api` | Anthropic Claude (claude-opus-5-5, claude-haiku-5-5) | Pré-entraîné | Conditions commerciales Anthropic | contrat | — | complète | Paiement à l'usage (jetons) | API Messages | non |
| `embedding_models` | Embeddings multilingues ouverts (multilingual-e5, BGE-M3) | Pré-entraîné | MIT annoncé, non vérifié modèle par modèle | à vérifier | — | partielle | Gratuit (auto-hébergé) | Poids publics | non |
| `mms_models` | Meta MMS (ASR, TTS, identification de langue) | Pré-entraîné | CC BY-NC 4.0 | non commercial | — | partielle | Gratuit (non commercial) | Poids publics | 2026-11-01 |
| `xlsr_models` | wav2vec 2.0 XLS-R (300M à 2B) | Pré-entraîné | Apache-2.0 | ouvert | — | complète | Gratuit | Poids publics | 2026-11-01 |
| `nllb_models` | Meta NLLB-200 (traduction) | Pré-entraîné | CC BY-NC 4.0 | non commercial | — | partielle | Gratuit (non commercial) | Poids publics | 2026-11-01 |

## Connaissances (RAG)

| Id | Source | Type | Licence | Usage commercial | Perso. | Couverture SN | Coût | Accès | Vérifiée |
|---|---|---|---|---|---|---|---|---|---|
| `technical_sheets` | Fiches techniques (ANCAR, ISRA, CDH, FAO) | Référence | Droits de reproduction à obtenir | contrat | — | complète | Sur convention | PDF, documents | non |
| `agronomist_qa` | Questions-réponses validées | Interne | Interne | ouvert | — | complète | Temps des agronomes | Outil de relecture | non |
