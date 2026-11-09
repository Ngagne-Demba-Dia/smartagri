# Annexe A2 — Jeux de données

> Confidentiel - réservé aux partenaires de travail.
> Fichier généré par `python -m agriml.catalog render` depuis `ml/catalog/*.yaml` — ne pas modifier à la main.

110 jeux du lac `s3://agri-<zone>/<domaine>/<table>/date=AAAA-MM-JJ/`. La donnée personnelle n'est pas déclarée : elle est calculée depuis les sources amont (abaissée par la minimisation ou l'agrégation k-anonyme). Seuls les jeux features `public` ou `pseudonymised` peuvent partir vers OctOpus, en instantané, sans leur holdout.

## Synthèse

| Zone | Jeux |
|---|---|
| raw | 52 |
| curated | 39 |
| features | 19 |

| Politique OctOpus | Jeux |
|---|---|
| forbidden | 95 |
| pseudonymised | 13 |
| public | 2 |

## Zone raw (immuable, jamais exportée)

### Météo et climat

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.meteo.forecasts` | Prévisions brutes avec heure d'émission (GRIB2 / JSON) | MVP | interne | — | open_meteo, ecmwf_open_data, noaa_gfs | émission × échéance × maille ou point · 4 émissions/j | IFS 0,25° Sénégal 450 mailles × 4 émissions × 61 échéances × 15 var. ≈ 2,4 Go/an ; + GFS et points ≈ 5 Go/an | 5 ans (rejeu as-of) | interdit | — |
| `raw.meteo.reanalysis` | Réanalyses et agroclimat (températures, Rs, vent, HR, ET) | MVP | publique | — | era5, era5_land, agera5, nasa_power | maille × heure ou jour · quotidien (latence ERA5 ~5 j) | ERA5-Land 0,1° : 2 772 mailles × 8 760 h × 10 var. × 4 o ≈ 1 Go/an ; historique 1991+ ≈ 35 Go | illimitée | interdit | — |
| `raw.meteo.rain_satellite` | Pluie estimée par satellite (journalier, pentadaire) | V1.1 | publique | — | chirps, tamsat, imerg | maille × jour · quotidien (IMERG early) à mensuel (CHIRPS final) | CHIRPS 0,05° : 11 k mailles × 365 j ≈ 16 Mo/an ; 1981+ < 1 Go | illimitée | interdit | — |
| `raw.meteo.radiation` | Rayonnement solaire de surface satellitaire | V2 | publique | — | cmsaf_sarah | maille × jour · mensuel | 0,05° journalier ≈ 20 Mo/an | illimitée | interdit | — |
| `raw.meteo.stations` | Observations de stations partenaires (sous convention) | V2 | confidentielle | — | tahmo, anacim_stations | station × 5–60 min · horaire à quotidien | 100 stations × 288 obs/j ≈ 10 M lignes/an ≈ 0,3 Go/an | selon convention (défaut 5 ans) | interdit | — |
| `raw.meteo.seasonal` | Prévisions saisonnières (terciles pluie, dates de démarrage, séquences sèches) | V3 | confidentielle | — | agrhymet_presass | zone × saison · annuel (mai) + mises à jour | < 10 Mo/an | illimitée | interdit | — |

### Sols

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.sols.grids` | Cartes de sols mondiales/africaines (texture, pH, MO, N, P, K, CEC) | MVP | publique | — | soilgrids, isdasoil, hwsd | pixel 30–250 m × profondeur · à chaque nouvelle version (≈ annuelle) | iSDAsoil 30 m Sénégal ≈ 5–10 Go ; SoilGrids 250 m ≈ 0,4 Go ; HWSD < 1 Go | illimitée | interdit | — |
| `raw.sols.national` | Carte pédologique et profils nationaux (sous convention) | V2 | confidentielle | — | inp_soil_map | polygone / profil · ponctuel | < 1 Go | selon convention | interdit | — |
| `raw.sols.lab` | Analyses de laboratoire et kits terrain géoréférencés | V1.1 | confidentielle | indirecte | soil_lab_analyses, soil_field_kits | échantillon × profondeur · campagne | 150–300 échantillons au pilote, puis ≈ 1 000/an ; < 10 Mo | illimitée (référence d'étalonnage) | interdit | — |

### Satellite

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.satellite.optical` | Scènes L2A optiques (références STAC, découpes COG sur les AOI) | V2 | publique | — | sentinel2, landsat, hls | scène × bande · à chaque passage (2–5 j) | AOI pilote 5 000 km² ≈ 50 Go/an de découpes ; pas de copie des tuiles complètes | découpes AOI 3 ans (re-téléchargeables) | interdit | — |
| `raw.satellite.sar` | Sentinel-1 GRD/RTC (VV, VH), insensible aux nuages | V2 | publique | — | sentinel1 | scène · 6–12 j | AOI pilote ≈ 30 Go/an | découpes AOI 3 ans | interdit | — |
| `raw.satellite.coarse` | Produits basse résolution (NDVI 250 m, ETa, biomasse) | V2 | publique | — | modis_viirs, wapor | pixel × 8–16 j · 8–16 j | Sénégal ≈ 2 Go/an | illimitée | interdit | — |
| `raw.satellite.deafrica` | Produits Digital Earth Africa (géomédianes, eau, masques cultures) | V2 | publique | — | deafrica | pixel × produit · trimestriel à annuel | ≈ 5 Go/an sur les AOI | illimitée | interdit | — |
| `raw.satellite.planet` | PlanetScope 3 m (sous licence, zones à forte valeur seulement) | V3 | confidentielle | — | planetscope | scène · quotidien | 500 km² × 100 dates × 30 Mo/km²/100 ≈ 15 Go/an | selon licence | interdit | — |

### Drone

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.images.drone` | Images de vol brutes RGB, multispectrales, thermiques | V3 | confidentielle | indirecte | drone_rgb, drone_multispectral, drone_thermal | vol × image · campagne (2–4 vols/saison/site) | 2–5 Go par vol de 50 ha ⇒ 20 sites × 4 vols × 4 Go ≈ 320 Go/an | 2 ans, orthomosaïques conservées | interdit | — |

### IoT (kit)

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.iot.telemetry` | Messages telemetry.v1 tels que reçus (MQTT → ingestor), y compris capteurs ajoutés en V1.1+ | MVP | confidentielle | indirecte | kit_telemetry, kit_flowmeter, kit_power, kit_soil_extended, kit_microclimate | kit × 5 min · flux continu | 10 000 kits × 288 msg/j = 2,9 M lignes/j ≈ 1,05 G lignes/an ≈ 20–40 Go/an ; pilote 100 kits = 29 k lignes/j | 3 ans, puis agrégats horaires seulement | interdit | — |
| `raw.iot.events` | Événements du kit : démarrage/arrêt pompe, défauts, redémarrages, OTA ; actions depuis la page locale ou l'app (seuils modifiés, mode auto/manuel, commande manuelle, alerte acquittée, analyse lancée, jeu de paramètres appliqué), avec déclencheur, origine et param_version | MVP | confidentielle | indirecte | kit_events | événement · flux continu | ≈ 20 évén./kit/j, dont 2–5 actions ⇒ 73 M lignes/an à 10 000 kits ≈ 1–2 Go/an | 3 ans | interdit | — |
| `raw.iot.devices` | Inventaire et configuration : firmware, seuils, étalonnages, rattachement parcelle | MVP | confidentielle | indirecte | kit_config | kit × version de configuration · à chaque changement | 10 000 kits × ~20 versions ≈ 200 k lignes, < 100 Mo | durée de vie du kit + 1 an | interdit | — |
| `raw.images.espcam` | Photos ESP32-CAM du couvert ou du piège (politique de volume : 4/j, pas horaire) | V2 | confidentielle | indirecte | kit_espcam | photo · 4 photos/j/kit équipé | 500 kits × 4 photos/j × 100 Ko ≈ 75 Go/an ; horaire sur 10 000 kits = 8,8 To/an (à proscrire) | 1 an, sauf images étiquetées (5 ans) | interdit | — |

### Phytosanitaire

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.images.field_photos` | Photos téléphone (symptômes, couvert) avec EXIF et GPS d'origine | MVP | personnelle | directe | farmer_photos | photo · à la demande (app mobile) | 50 k–200 k photos/an × 1–2,5 Mo ≈ 50–500 Go/an | 5 ans avec consentement, sinon 90 j | interdit | — |
| `raw.phyto.labels` | Diagnostics des conseillers (étiquettes d'images et d'observations) | MVP | confidentielle | indirecte | advisor_diagnoses | diagnostic · à la demande | objectif ≥ 5 000 diagnostics validés à V2 | illimitée (vérité terrain) | interdit | — |
| `raw.phyto.field_reports` | Relevés de piégeage, observations, traitements appliqués | V1.1 | confidentielle | indirecte | scouting_reports, treatments_log | relevé · hebdomadaire en saison | ≈ 100 k relevés/an | illimitée | interdit | — |
| `raw.phyto.external_alerts` | Alertes officielles et réseaux de surveillance (chenille, criquet) | V2 | confidentielle | — | dpv_alerts, famews, fao_locust | alerte × zone · hebdomadaire | < 50 Mo/an | illimitée | interdit | — |
| `raw.phyto.reference` | Liste CSP des produits homologués, biologie des ravageurs | MVP | interne | — | csp_pesticides, pest_biology_reference | produit / espèce · à chaque publication CSP (≈ semestriel) | < 10 Mo | toutes versions | interdit | — |
| `raw.phyto.public_images` | Jeux d'images publics (pré-entraînement, hors conditions sénégalaises) | V2 | publique | — | plantvillage, plantdoc | image · ponctuel | PlantVillage ≈ 54 k images ≈ 1–2 Go ; PlantDoc ≈ 2,6 k | illimitée | interdit | — |
| `raw.phyto.gbif` | Occurrences géoréférencées d'espèces nuisibles (licence par jeu) | V3 | publique | — | gbif | occurrence · trimestriel | < 100 Mo | illimitée | interdit | — |

### Agronomie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.agronomie.cycles` | Déclarations : culture, variété, semis, opérations, irrigation manuelle | MVP | confidentielle | indirecte | crop_cycles_user, operations_log | parcelle × campagne / opération · à la saisie | 20 000 parcelles × 2 campagnes × 30 opérations ≈ 1,2 M lignes/an | illimitée (historique parcelle) | interdit | — |
| `raw.agronomie.reference` | Kc, durées de stades, profondeur racinaire, calendriers | MVP | publique | — | fao56_tables, fao_crop_calendar | culture × stade × zone · ponctuel | < 5 Mo | toutes versions | interdit | — |
| `raw.agronomie.partner_reference` | Références locales ISRA/CDH : variétés, doses, rendements potentiels | V1.1 | confidentielle | — | isra_cdh_references | culture × variété × zone · annuel | < 10 Mo | selon convention | interdit | — |
| `raw.agronomie.crop_models` | Paramètres et sorties de modèles de culture (AquaCrop, SARRA-Py/O) | V3 | confidentielle | — | aquacrop, sarra | culture × site × scénario · annuel | < 1 Go | illimitée | interdit | — |
| `raw.agronomie.yield_gap` | Rendements potentiels et écarts YPYGA (CC BY-NC-SA) : étalonnage et comparaison uniquement | V3 | interne | — | gyga | culture × zone climatique · ponctuel | < 50 Mo | durée du projet de recherche | interdit | recherche seule |

### Économie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.economie.market_prices` | Prix de gros et de détail par marché et produit | V2 | confidentielle | — | sim_csa, arm_prices, fews_net, giews_fpma | marché × produit × semaine · hebdomadaire | 50 marchés × 20 produits × 52 sem. = 52 k lignes/an | illimitée | interdit | — |
| `raw.economie.inputs_costs` | Prix des intrants, tarifs énergie, coûts de transport | V2 | interne | — | input_prices_survey, energy_tariffs, logistics_costs | intrant × zone × mois · mensuel | < 10 Mo/an | illimitée | interdit | — |
| `raw.economie.farm_accounts` | Comptes d'exploitation saisis : dépenses, ventes, main-d'œuvre | V2 | personnelle | directe | farm_accounts | exploitation × écriture · à la saisie | 5 000 exploitations × 200 écritures/an = 1 M lignes/an | 10 ans (pièces comptables) ou retrait du consentement | interdit | — |
| `raw.economie.payments` | Abonnements et paiements mobile money (statut, montant, échéance) | V2 | personnelle | directe | payments | transaction · flux continu | 10 000 abonnés × 12 paiements/an = 120 k lignes/an | 10 ans (obligation comptable) | interdit | — |
| `raw.economie.finance_partners` | Sinistres d'assurance et remboursements de crédit (avec consentement) | V3 | personnelle | directe | cnaas_insurance, mfi_credit_outcomes | contrat × campagne · campagne | ≈ 5–20 k contrats/an | durée du contrat + 5 ans | interdit | — |

### Géospatial

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.geo.fields` | Polygones de parcelles saisis ou dessinés, rattachés à l'exploitant | MVP | personnelle | directe | user_field_boundaries | parcelle × version · à la saisie | 20 000 polygones × 2 Ko ≈ 40 Mo | durée du compte + 1 an | interdit | — |
| `raw.geo.reference` | Limites administratives, MNT 30 m, occupation du sol 10 m, eaux de surface, bassins | MVP | publique | — | geoboundaries, copernicus_dem, worldcover, jrc_gsw, hydrosheds | raster / vecteur · à chaque version | MNT GLO-30 ≈ 0,9 Go ; WorldCover ≈ 0,5–2 Go ; GSW ≈ 1 Go ; HydroSHEDS < 1 Go | toutes versions | interdit | — |
| `raw.geo.official` | Découpage administratif officiel ANSD (communes, villages) | V1.1 | confidentielle | — | ansd_admin | polygone · à chaque recensement | < 500 Mo | toutes versions | interdit | — |
| `raw.geo.osm` | Routes, marchés, points d'eau OSM (ODbL, partage à l'identique) | V2 | publique | — | osm | objet · mensuel | Sénégal ≈ 200 Mo (PBF) | dernière version + 1 | interdit | — |
| `raw.geo.open_field_boundaries` | Limites de parcelles ouvertes (jeux de référence, entraînement) | V3 | publique | — | field_boundaries_open | polygone · ponctuel | < 1 Go | illimitée | interdit | — |

### Eau et irrigation

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.eau.groundwater` | Piézométrie et qualité des nappes (DGPRE, sous convention) | V3 | confidentielle | — | dgpre_groundwater | piézomètre × mois · mensuel à annuel | < 50 Mo | illimitée | interdit | — |
| `raw.eau.water_quality` | CE, pH, SAR des eaux d'irrigation ; inventaire des puits | V1.1 | confidentielle | indirecte | irrigation_water_quality, well_inventory | point d'eau × prélèvement · campagne | ≈ 2 000 prélèvements/an, < 5 Mo | illimitée | interdit | — |

### Historique

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.historique.statistics` | Statistiques agricoles nationales et régionales | V1.1 | interne | — | faostat, dapsa_surveys, ansd_stats | zone × culture × année · annuel | < 50 Mo | illimitée | interdit | — |
| `raw.historique.harvests` | Récoltes déclarées ou pesées (poids, surface récoltée, qualité) | V1.1 | confidentielle | indirecte | farmer_harvests | parcelle × campagne · fin de campagne | 20 000 parcelles × 2 campagnes = 40 k lignes/an | illimitée | interdit | — |
| `raw.historique.trials` | Essais agronomiques (doses, variétés, rendements mesurés) | V3 | confidentielle | — | research_trials | parcelle d'essai · annuel | < 100 Mo | selon convention | interdit | — |

### Utilisateurs et consentements

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.utilisateurs.accounts` | Comptes, exploitations, rôles, consentements horodatés | MVP | personnelle | directe | user_accounts, farm_registry, consents | compte / exploitation / consentement · flux continu | 10 000 comptes, < 100 Mo | durée du compte + 1 an ; preuves de consentement 5 ans | interdit | — |
| `raw.utilisateurs.feedback` | Retour sur les recommandations (suivie, ignorée, note) et usage | MVP | confidentielle | indirecte | reco_feedback, app_usage | événement · flux continu | 10 000 utilisateurs × 5 évén./j ≈ 18 M lignes/an | 2 ans | interdit | — |

### Langue et voix

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.langue.assistant` | Conversations de l'assistant (texte libre, pièces jointes) | MVP | personnelle | directe | assistant_logs | message · flux continu | 5 000 utilisateurs actifs × 100 conversations/an × 5 Ko ≈ 2,5 Go/an | 90 j bruts, puis extraits minimisés | interdit | — |
| `raw.langue.speech` | Enregistrements vocaux (wolof, pulaar, sérère) avec consentement explicite | V2 | personnelle | directe | speech_consented | enregistrement · campagnes de collecte | 16 kHz mono 16 bits = 115 Mo/h ; 100 h ≈ 12 Go | jusqu'au retrait du consentement, max 5 ans | interdit | — |
| `raw.langue.public_speech` | Corpus vocaux publics | V2 | publique | — | common_voice, open_wolof_speech | enregistrement · à chaque version | wolof public ≈ 10–40 h ≈ 1–5 Go | illimitée | interdit | — |

### Connaissances (RAG)

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `raw.connaissances.corpus` | Fiches techniques et questions-réponses validées par agronomes | MVP | interne | — | technical_sheets, agronomist_qa | document · à chaque ajout | 500–2 000 documents, < 2 Go | toutes versions | interdit | — |

## Zone curated (nettoyée, conforme)

### Météo et climat

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `meteo.forecast_asof` | Prévisions indexées par (heure d'émission, échéance) : on n'utilise que ce qui était connu à t (pas de fuite) | MVP | interne | — | raw.meteo.forecasts | émission × échéance × maille · 4×/j | ≈ 5 Go/an | 5 ans | interdit | — |
| `meteo.grid_daily` | Météo journalière observée par maille : Tmin/Tmax, HR, vent 2 m, Rs, pluie fusionnée, ET0 FAO-56 | MVP | publique | — | raw.meteo.reanalysis, raw.meteo.rain_satellite, raw.meteo.radiation | maille 0,1° × jour · quotidien | 2 772 × 365 ≈ 1 M lignes/an | illimitée | interdit | — |
| `meteo.stations_clean` | Observations de stations contrôlées (QC, homogénéisation) | V2 | confidentielle | — | raw.meteo.stations | station × heure · horaire | ≈ 1 M lignes/an | selon convention | interdit | — |
| `meteo.seasonal_outlook` | Prévision saisonnière normalisée par zone (terciles, démarrage, fin) | V3 | confidentielle | — | raw.meteo.seasonal | zone × saison · annuel | < 1 Mo/an | illimitée | interdit | — |

### Sols

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `sols.soil_grid` | Propriétés harmonisées : texture, pH, MO, N, P, K, CEC, CC/PF par pédotransfert, incertitude | MVP | publique | — | raw.sols.grids, raw.sols.national | pixel 30 m × 2 profondeurs · à chaque version source | ≈ 10 Go | toutes versions | interdit | — |
| `sols.lab_results` | Analyses rattachées à une parcelle pseudonymisée, méthode et laboratoire normalisés | V1.1 | confidentielle | indirecte | raw.sols.lab, geo.fields | échantillon · campagne | ≈ 1 000 lignes/an | illimitée | interdit | minimisé |
| `sols.field_profile` | Profil de sol par parcelle : RU (TAW), CC, PF, pH, MO, CE ; source = labo sinon grille (avec incertitude) | MVP | confidentielle | indirecte | sols.lab_results, sols.soil_grid, geo.fields | parcelle · à chaque analyse | 20 000 lignes | illimitée | interdit | minimisé |

### Satellite

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `satellite.field_indices` | Statistiques zonales par parcelle et date : NDVI, EVI, NDWI, SAVI, NDRE, MSAVI, VV, VH, part nuageuse | V2 | confidentielle | indirecte | raw.satellite.optical, raw.satellite.sar, raw.satellite.deafrica, raw.satellite.planet, geo.fields | parcelle × date d'acquisition · à chaque passage | 20 000 parcelles × 70–150 dates/an ⇒ 1,5–3 M lignes/an, < 1 Go | illimitée | interdit | minimisé |
| `satellite.regional_products` | Anomalies NDVI, ETa, biomasse et masques cultures agrégés par commune | V2 | publique | — | raw.satellite.coarse, raw.satellite.deafrica | commune × décade · décadaire | 550 communes × 36 décades ≈ 20 k lignes/an | illimitée | interdit | — |
| `satellite.s2_chips` | Tuiles 256×256 multi-dates (10 bandes S2 + VV/VH), masque nuages, pour l'apprentissage profond | V2 | publique | — | raw.satellite.optical, raw.satellite.sar | tuile × date · mensuel | AOI 5 000 km² ≈ 760 tuiles × 30 dates × 1,3 Mo ≈ 30 Go/an ; zone agricole nationale ≈ 240 Go/an | 3 ans | interdit | — |

### Drone

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `images.drone_mosaics` | Orthomosaïques géoréférencées, MNS, cartes NDVI/NDRE et température de couvert | V3 | confidentielle | indirecte | raw.images.drone, geo.fields | vol × raster · après chaque vol | ≈ 10 % du brut ⇒ 30 Go/an | 5 ans | interdit | minimisé |

### IoT (kit)

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `iot.telemetry_clean` | Dédoublonné, UTC, unités SI, plages physiques, drapeaux qualité, étalonnage par kit appliqué | MVP | confidentielle | indirecte | raw.iot.telemetry, raw.iot.devices | kit × 5 min · micro-lots 5 min | ≈ raw (~1 G lignes/an à cible) | 3 ans | interdit | — |
| `iot.telemetry_hourly` | Agrégats horaires (moyenne, min, max, taux de complétude) par kit | MVP | confidentielle | indirecte | iot.telemetry_clean | kit × heure · horaire | 10 000 × 24 × 365 = 87,6 M lignes/an ≈ 2–4 Go/an | illimitée | interdit | — |
| `iot.irrigation_events` | Sessions d'irrigation : début, fin, durée, volume (débitmètre ou débit nominal), déclencheur (auto, manuel, utilisateur, planificateur), mode, seuils et param_version appliqués ; changements de seuils et de mode (les forçages servent de signal d'étiquette) | MVP | confidentielle | indirecte | raw.iot.events, iot.telemetry_clean | session · horaire | ≈ 2 sessions/kit/j ⇒ 7 M lignes/an | illimitée | interdit | — |
| `iot.device_health` | État quotidien du kit : complétude, défauts capteurs, batterie, courant pompe, firmware | MVP | confidentielle | indirecte | raw.iot.events, raw.iot.devices, iot.telemetry_clean | kit × jour · quotidien | 3,65 M lignes/an | illimitée | interdit | — |
| `images.espcam_series` | Séries temporelles d'images du kit, normalisées, contrôle qualité | V2 | confidentielle | indirecte | raw.images.espcam | kit × image · quotidien | ≈ 75 Go/an | 1 an (5 ans si étiquetée) | interdit | minimisé |

### Phytosanitaire

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `images.labelled` | Photos floutées (visages, plaques), sans EXIF, GPS arrondi, étiquette conseiller et niveau de confiance | MVP | confidentielle | indirecte | raw.images.field_photos, raw.phyto.labels | image · quotidien | ≈ 30 % des photos brutes, recadrées 1 Mpx | 5 ans | interdit | minimisé |
| `images.public_reference` | Images publiques ré-étiquetées vers la taxonomie SmartAgri92 | V2 | publique | — | raw.phyto.public_images | image · ponctuel | ≈ 2 Go | illimitée | interdit | — |
| `phyto.outbreaks` | Événements de présence / absence de bioagresseurs datés et localisés (parcelle ou commune) | V1.1 | confidentielle | indirecte | raw.phyto.labels, raw.phyto.field_reports, raw.phyto.external_alerts, raw.phyto.gbif | événement · quotidien | ≈ 100 k lignes/an | illimitée | interdit | — |
| `phyto.reference` | Produits homologués (matière active, dose, DAR, cultures), seuils biologiques | MVP | interne | — | raw.phyto.reference | produit × culture · à chaque publication CSP | < 5 Mo | toutes versions | interdit | — |

### Agronomie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `agronomie.crop_cycles` | Cycle normalisé par parcelle : culture, variété, semis, stades déclarés, opérations | MVP | confidentielle | indirecte | raw.agronomie.cycles | parcelle × campagne · à la saisie | 40 k cycles/an | illimitée | interdit | — |
| `agronomie.crop_params` | Paramètres par culture et zone : Kc, durées de stades, Zr, p, Ky, besoins NPK, seuils de rendement | MVP | interne | — | raw.agronomie.reference, raw.agronomie.partner_reference | culture × variété × zone · annuel | < 5 Mo | toutes versions | interdit | — |
| `agronomie.crop_model_params` | Paramètres calés AquaCrop / SARRA (cultures, sols, variétés locales) | V3 | confidentielle | — | raw.agronomie.crop_models, agronomie.crop_params | culture × site · annuel | < 100 Mo | illimitée | interdit | — |
| `agronomie.yield_potential` | Potentiels de rendement par zone (YPYGA) : référence de recherche, jamais servie en production | V3 | interne | — | raw.agronomie.yield_gap | culture × zone · ponctuel | < 10 Mo | durée du projet | interdit | recherche seule |

### Économie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `economie.prices_weekly` | Prix hebdomadaires harmonisés (FCFA/kg), marché, produit, qualité | V2 | interne | — | raw.economie.market_prices | marché × produit × semaine · hebdomadaire | 52 k lignes/an | illimitée | interdit | — |
| `economie.costs` | Coûts de production de référence par culture et zone (k ≥ 10 exploitations par cellule) | V2 | interne | — | raw.economie.inputs_costs, raw.economie.farm_accounts | culture × zone × campagne · mensuel | < 1 Mo/an | illimitée | interdit | agrégé |
| `economie.farm_economics` | Marge brute par exploitation et campagne, historique de paiement | V2 | personnelle | directe | raw.economie.farm_accounts, raw.economie.payments | exploitation × campagne · mensuel | 10 k lignes/an | 10 ans | interdit | — |
| `economie.credit_outcomes` | Résultat crédit / assurance par exploitation (remboursé, retard, sinistre indemnisé) | V3 | personnelle | directe | raw.economie.finance_partners, economie.farm_economics | contrat · campagne | 5–20 k lignes/an | durée du contrat + 5 ans | interdit | — |

### Géospatial

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `geo.fields` | Parcelles valides (géométrie réparée, surface, centroïde) filtrées par consentement actif | MVP | personnelle | directe | raw.geo.fields, raw.utilisateurs.accounts | parcelle · à la saisie | 20 000 lignes | durée du compte + 1 an | interdit | — |
| `geo.reference_layers` | Couches de contexte normalisées (EPSG:4326 / 32628) : admin, pente, occupation du sol, eau, routes | MVP | publique | — | raw.geo.reference, raw.geo.official, raw.geo.osm | raster / vecteur · à chaque version | ≈ 5 Go | toutes versions | interdit | — |
| `geo.field_context` | Contexte statique par parcelle pseudonymisée : surface, altitude, pente, commune, distance à l'eau et au marché | MVP | confidentielle | indirecte | geo.fields, geo.reference_layers | parcelle · à la saisie | 20 000 lignes | illimitée | interdit | minimisé |
| `geo.open_field_boundaries` | Limites ouvertes harmonisées (masques d'entraînement) | V3 | publique | — | raw.geo.open_field_boundaries | polygone · ponctuel | < 1 Go | illimitée | interdit | — |

### Eau et irrigation

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `eau.water_quality` | CE, SAR, pH par point d'eau rattaché aux parcelles ; contexte piézométrique | V1.1 | confidentielle | indirecte | raw.eau.water_quality, raw.eau.groundwater | point d'eau × date · campagne | < 10 Mo | illimitée | interdit | — |

### Historique

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `historique.yields` | Rendement (t/ha) par parcelle et campagne avec méthode (pesée, déclaration, essai) et fiabilité | V1.1 | confidentielle | indirecte | raw.historique.harvests, raw.historique.trials, agronomie.crop_cycles | parcelle × campagne · fin de campagne | 40 k lignes/an | illimitée | interdit | — |
| `historique.regional_stats` | Rendements, surfaces, productions par région et culture (séries 1990+) | V1.1 | interne | — | raw.historique.statistics | région × culture × année · annuel | < 1 Mo | illimitée | interdit | — |

### Utilisateurs et consentements

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `utilisateurs.reco_events` | Recommandation émise → vue → suivie / ignorée → résultat mesuré (humidité, rendement) ; alertes acquittées (page locale du kit, app) | MVP | confidentielle | indirecte | raw.utilisateurs.feedback, raw.iot.events | recommandation · horaire | 10 000 × 1 reco/j ≈ 3,7 M lignes/an | illimitée | interdit | minimisé |

### Langue et voix

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `langue.assistant_eval` | Questions anonymisées (PII retirées), réponses, sources citées, notes agronome (jeu d'évaluation) | MVP | confidentielle | indirecte | raw.langue.assistant | échange · hebdomadaire | ≈ 5 k échanges notés/an | illimitée | interdit | minimisé |
| `langue.speech_corpus` | Segments audio transcrits (wolof, pulaar, sérère, français), locuteur pseudonymisé ; la voix reste identifiante | V2 | personnelle | directe | raw.langue.speech, raw.langue.public_speech | segment · campagne | 100–300 h ≈ 12–35 Go | jusqu'au retrait du consentement | interdit | — |

### Connaissances (RAG)

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `connaissances.rag_chunks` | Passages de 300–800 jetons avec métadonnées (culture, zone, licence, date) et embeddings | MVP | interne | — | raw.connaissances.corpus, phyto.reference, agronomie.crop_params | passage · à chaque ajout | ≈ 20–80 k passages, < 1 Go | toutes versions | interdit | — |

## Zone features (prête pour l'entraînement)

### Météo et climat

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.local_weather_bias` | Écart prévision as-of / mesure kit ou station ; cible : erreur T, HR, pluie par échéance | V2 | confidentielle | indirecte | iot.telemetry_hourly, meteo.forecast_asof, meteo.stations_clean | kit × émission × échéance · quotidien | ≈ 50 M lignes/an à cible | versions DVC | pseudonymised `local_weather_bias` (licence à confirmer) | minimisé, holdout |
| `features.rain_events` | Prévisions as-of et pluie observée par maille ; cible : pluie ≥ 1 / 10 / 20 mm à J+1…J+5 | V2 | interne | — | meteo.grid_daily, meteo.forecast_asof | maille × émission × échéance · quotidien | ≈ 20 M lignes (1991+) | versions DVC | public `rain_events` (licence à confirmer) | — |

### Sols

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.npk_calibration` | Lecture NPK du kit (RS485), humidité, température, CE ; cible : N, P, K de laboratoire | V2 | confidentielle | indirecte | iot.telemetry_clean, sols.lab_results, eau.water_quality | échantillon · campagne | 150–1 000 paires/an (petit jeu) | versions DVC | pseudonymised `npk_calibration` (licence à confirmer) | minimisé, holdout |

### Satellite

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.crop_type` | Séries temporelles S1/S2 par parcelle ; cible : culture déclarée et vérifiée | V3 | confidentielle | indirecte | satellite.field_indices, satellite.s2_chips, agronomie.crop_cycles | parcelle × campagne · campagne | ≈ 40 k séries/an | versions DVC | pseudonymised `crop_type` (licence à confirmer) | minimisé, holdout |

### IoT (kit)

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.soil_nowcast` | Fenêtres horaires d'humidité, irrigation, météo as-of ; cible : soil_moisture_pct à t+1…t+72 h | MVP | confidentielle | indirecte | iot.telemetry_hourly, iot.irrigation_events, meteo.forecast_asof, meteo.grid_daily, sols.field_profile | kit × heure · quotidien | pilote 876 k lignes/an ; cible 87,6 M | versions DVC | pseudonymised `soil_nowcast` (licence à confirmer) | minimisé, holdout |
| `features.sensor_anomaly` | Résidus capteur / attendu, dérives, courant pompe ; cible : défaut confirmé par intervention | V2 | confidentielle | indirecte | iot.telemetry_clean, iot.device_health, iot.irrigation_events, meteo.forecast_asof | kit × heure · quotidien | ≈ 87 M lignes/an à cible | versions DVC | pseudonymised `sensor_anomaly` (licence à confirmer) | minimisé, holdout |

### Phytosanitaire

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.disease_images` | Images 384 px + métadonnées (culture, stade, région) ; cible : label (maladie, ravageur, sain, carence) | V2 | confidentielle | indirecte | images.labelled, images.public_reference, images.espcam_series | image · hebdomadaire | ≥ 5 000 images validées (V2) ≈ 2 Go | versions DVC | pseudonymised `disease_images` (licence à confirmer) | minimisé, holdout |
| `features.pest_trap_images` | Images de pièges avec boîtes annotées ; cible : nombre d'individus par espèce | V3 | confidentielle | indirecte | images.espcam_series, images.labelled | image · hebdomadaire | ≈ 3 000 images annotées, < 1 Go | versions DVC | pseudonymised `pest_trap_images` (licence à confirmer) | minimisé, holdout |
| `features.pest_risk` | Degrés-jours, humectation, stade, voisinage des foyers ; cible : présence sous 7 / 14 j | V2 | confidentielle | indirecte | phyto.outbreaks, phyto.reference, meteo.grid_daily, meteo.forecast_asof, satellite.field_indices, agronomie.crop_cycles, geo.field_context | parcelle × semaine · hebdomadaire | 20 000 × 52 ≈ 1 M lignes/an | versions DVC | pseudonymised `pest_risk` (licence à confirmer) | minimisé, holdout |

### Agronomie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.phenology` | Séries NDVI lissées, GDD depuis semis ; cible : stade BBCH observé | V2 | confidentielle | indirecte | satellite.field_indices, agronomie.crop_cycles, agronomie.crop_params, meteo.grid_daily | parcelle × date · à chaque passage | ≈ 3 M lignes/an | versions DVC | pseudonymised `phenology` (licence à confirmer) | minimisé, holdout |

### Économie

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.price_forecast` | Prix retardés, saisonnalité, anomalies de végétation régionales ; cible : prix à 4 / 8 / 12 semaines | V3 | interne | — | economie.prices_weekly, historique.regional_stats, satellite.regional_products | marché × produit × semaine · hebdomadaire | ≈ 500 k lignes (2010+) | versions DVC | public `price_forecast` (licence à confirmer) | — |
| `features.agri_risk` | Historique de rendement, marge, paiements, exposition climatique ; cible : défaut ou sinistre | V3 | personnelle | directe | economie.credit_outcomes, economie.farm_economics, historique.yields, meteo.seasonal_outlook, features.yield | exploitation × campagne · campagne | 5–20 k lignes/an | durée du contrat + 5 ans | interdit | — |

### Géospatial

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.field_boundaries` | Tuiles S2 + masques de limites ; les polygones exacts identifient l'exploitant : entraînement local seulement | V3 | personnelle | directe | satellite.s2_chips, geo.fields, geo.open_field_boundaries | tuile · campagne | ≈ 30 Go | versions DVC | interdit | — |

### Eau et irrigation

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.irrigation_need` | État hydrique, stade, ETc prévue ; cible : target_need_mm_24h (bilan hydrique a posteriori) | V2 | confidentielle | indirecte | iot.telemetry_hourly, iot.irrigation_events, meteo.forecast_asof, meteo.grid_daily, sols.field_profile, agronomie.crop_cycles, agronomie.crop_params, geo.field_context, satellite.field_indices | parcelle × jour · quotidien | 20 000 × 365 = 7,3 M lignes/an | versions DVC | pseudonymised `irrigation_need` (licence à confirmer) | minimisé, holdout |
| `features.salinity_risk` | CE eau et sol, fraction de lessivage, distance à la mer / au fleuve ; cible : CE sol en fin de saison | V3 | confidentielle | indirecte | eau.water_quality, sols.field_profile, iot.telemetry_hourly, geo.field_context, satellite.regional_products | parcelle × saison · campagne | < 100 k lignes | versions DVC | pseudonymised `salinity_risk` (licence à confirmer) | minimisé, holdout |
| `features.water_savings` | Volume appliqué vs besoin FAO-56 et vs pratique de référence ; économie d'eau et d'énergie (MRV) | V1.1 | confidentielle | indirecte | iot.irrigation_events, iot.telemetry_hourly, agronomie.crop_cycles, meteo.grid_daily, economie.costs | parcelle × semaine · hebdomadaire | ≈ 1 M lignes/an | illimitée | interdit | — |

### Historique

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.yield` | Agrégats saisonniers (NDVI intégré, stress hydrique, pluie, GDD) ; cible : yield_t_ha | V3 | confidentielle | indirecte | historique.yields, satellite.field_indices, meteo.grid_daily, meteo.seasonal_outlook, iot.telemetry_hourly, sols.field_profile, agronomie.crop_cycles, geo.field_context, historique.regional_stats | parcelle × campagne · décadaire en saison | ≈ 40 k lignes/an | versions DVC | pseudonymised `yield` (licence à confirmer) | minimisé, holdout |

### Utilisateurs et consentements

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.reco_bandit` | Contexte, action recommandée, propension, récompense (adoption, gain mesuré) | V3 | confidentielle | indirecte | utilisateurs.reco_events, agronomie.crop_cycles, geo.field_context | recommandation · quotidien | ≈ 3,7 M lignes/an | versions DVC | pseudonymised `reco_bandit` (licence à confirmer) | minimisé, holdout |

### Langue et voix

| Id | Contenu | Dispo | Classification | Perso. calculée | Entrées | Grain · rafraîchissement | Volume | Rétention | OctOpus | Drapeaux |
|---|---|---|---|---|---|---|---|---|---|---|
| `features.asr_speech` | Segments audio 16 kHz + transcriptions normalisées ; la voix reste identifiante | V2 | personnelle | directe | langue.speech_corpus | segment · campagne | ≈ 12–35 Go | jusqu'au retrait du consentement | interdit | — |
