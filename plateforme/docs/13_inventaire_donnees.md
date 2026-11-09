# 13 — Inventaire des données (phase 1)

Confidentiel — réservé aux partenaires de travail.

Ce document répond à la phase 1 du brief IA, Data et MLOps du 27/10/2026 : recenser **toutes** les données utiles aux modèles, présents et futurs, du point de vue d'un CDO, d'un chercheur en IA agricole et d'un data scientist. Il couvre les dix domaines demandés et en ajoute cinq.

- **Source de vérité** : le catalogue `ml/catalog/` (104 sources, 110 jeux, 39 modèles), validé par `python -m agriml.catalog check`. Voir [ml/catalog/README.md](../ml/catalog/README.md).
- **Détail complet** : [A1 — Sources](annexes/A1_sources.md), [A2 — Jeux de données](annexes/A2_jeux_de_donnees.md), [A4 — Matrices](annexes/A4_matrice.md). Ces annexes sont générées ; ce document ne les recopie pas, il en tire l'analyse.
- **Suite** : modèles par fonctionnalité dans le [doc 14](14_cartographie_modeles.md), acquisition dans le [doc 15](15_acquisition_donnees.md), architecture OctOpus dans le [doc 16](16_architecture_octopus.md).

**Conventions.**

- **Obligatoire** : sans cette donnée, le modèle ne tourne pas ou n'atteint pas son seuil d'acceptation. **Recommandée** : gain mesurable attendu. **Optionnelle** : gain plausible, à démontrer.
- **[NV]** : fait non vérifié. Seules 22 sources sur 104 ont été vérifiées en ligne, le 01/11/2026. Les licences, coûts et couvertures des 82 autres sont des hypothèses de travail.
- **Volumes** : calculés pour la **cible** de 10 000 kits et 20 000 parcelles, et pour le **pilote** de 100 kits quand l'écart compte. Le calcul figure dans A2.

## 1. Ce qu'il faut retenir

1. **Les données les plus critiques sont les nôtres, pas les sources externes.** D'après la matrice A4.3, quatre sources servent de façon obligatoire à 17 modèles : contours de parcelles, consentements, registre des exploitations et comptes. Six sources du kit en servent 15, tout comme les cycles de culture et le journal des opérations. La qualité de la saisie à l'installation (UC-01) et pendant la campagne pèse davantage que le choix entre ERA5 et AgERA5.
2. **Le goulot, ce sont les étiquettes, pas les variables.**
   - Le volume d'eau réellement apporté n'est pas mesuré : le kit actuel n'a **pas de débitmètre**. Sans lui, les modèles d'irrigation apprennent sur une estimation (durée de pompage × débit nominal) au lieu d'une mesure.
   - Les rendements par parcelle et les diagnostics validés sont rares et coûteux.
   - Le § 5 chiffre ces besoins ; le doc 15 dit comment les financer.
3. **« Gratuit » ne veut pas dire « commercial ».**
   - 35 sources portent un avertissement de licence (`licence.pending`), et 14 jeux exportables vers OctOpus en héritent (`octopus.licence`).
   - Plusieurs sources réputées libres interdisent l'usage commercial : GYGA (CC BY-NC-SA), MMS et NLLB (CC BY-NC), l'API gratuite d'Open-Meteo, GADM et une partie des contenus FAO (CC BY-NC-SA 3.0 IGO).
   - Le validateur empêche déjà ces sources d'alimenter un modèle de production (règle 5).
4. **La position d'une parcelle est une donnée personnelle directe.** Un polygone GPS désigne une personne. Tout jeu qui en dérive est au moins `indirect`, donc `confidentielle`, sauf s'il est agrégé (règle 3). Seuls 13 jeux features pseudonymisés et 2 jeux publics peuvent partir vers OctOpus, et jamais leur holdout.
5. **Deux échéances datées.**
   - **CHIRPS v2 cesse d'être produit après décembre 2026** : il faut migrer vers CHIRPS v3, sous CC BY 4.0.
   - **L'API REST de SoilGrids est en pause** : il faut télécharger les fichiers.
   - Ces deux faits ont été vérifiés le 01/11/2026.

## 2. Vue d'ensemble

| Domaine | Sources | Dont internes ou saisies | Jeux raw / curated / features | Première version | Remarque |
|---|---|---|---|---|---|
| Météo et climat | 14 | 0 | 6 / 4 / 2 | MVP | Prévisions conservées avec leur heure d'émission (rejeu as-of) |
| Sols | 6 | 2 | 3 / 3 / 1 | MVP | iSDAsoil 30 m couvre le Sénégal ; analyses de laboratoire à acheter |
| Satellite | 8 | 0 | 5 / 3 / 1 | V2 | NDVI, EVI, NDWI, SAVI et rétrodiffusion SAR calculés par parcelle |
| Drone | 3 | 3 | 1 / 1 / 0 | V3 | Optionnel partout ; cadre ANACIM restrictif |
| IoT (kit) | 8 | 8 | 4 / 5 / 2 | MVP | Quatre capteurs prévus mais absents du kit v1.1 |
| Phytosanitaire | 13 | 4 | 7 / 4 / 3 | MVP | Diagnostics validés par les conseillers : la donnée la plus précieuse |
| Agronomie | 8 | 2 | 5 / 4 / 1 | MVP | Kc FAO-56, calendriers, références ISRA et CDH |
| Économie | 11 | 4 | 5 / 4 / 2 | V2 | Prix SIM/CSA et ARM sous convention |
| Géospatial | 9 | 1 | 5 / 4 / 1 | MVP | geoBoundaries à la place de GADM (non commercial) |
| **Eau et irrigation** (ajouté) | 3 | 2 | 2 / 1 / 3 | V1.1 | Qualité de l'eau d'irrigation, puits, nappes (DGPRE) |
| Historique | 5 | 1 | 3 / 2 / 1 | V1.1 | Rendements déclarés ; statistiques ANSD et DAPSA |
| **Utilisateurs et consentements** (ajouté) | 5 | 5 | 2 / 1 / 1 | MVP | Consentements par finalité, retours sur les recommandations |
| **Langue et voix** (ajouté) | 9 | 2 | 3 / 2 / 1 | MVP | Wolof et pulaar ; modèles pré-entraînés et leurs licences |
| **Connaissances (RAG)** (ajouté) | 2 | 1 | 1 / 1 / 0 | MVP | Fiches techniques sous convention, réponses d'agronomes |
| **Énergie et état du kit** (ajouté) | dans IoT | — | — | V2 | Batterie, panneau, courant de pompe : santé de la pompe et pannes |

Les colonnes de jeux comptent les jeux du domaine principal ; un jeu features combine souvent plusieurs domaines. Les effectifs exacts sont dans A2.

## 3. Inventaire par domaine

Chaque tableau donne les données essentielles et renvoie aux identifiants du catalogue. Les sources sont décrites en détail, avec leur preuve, dans A1.

### 3.1 Météo et climat

| Donnée | Sources | Collecte | Fréquence | Volume cible | Statut |
|---|---|---|---|---|---|
| Prévisions 0–10 j (T, HR, vent, Rs, pluie, ET0) | `open_meteo`, `ecmwf_open_data`, `noaa_gfs` | API et fichiers GRIB2 | 4 émissions/j | ≈ 5 Go/an | Open-Meteo : **l'API gratuite est non commerciale**, il faut l'offre payante (environ 29 à 99 $/mois, chiffres de 2023, [NV] à reconfirmer) ; ECMWF et GFS ouverts |
| Réanalyses et agroclimat (1991 et après) | `era5`, `era5_land`, `agera5`, `nasa_power` | Copernicus CDS, API POWER | Quotidien (ERA5T : ≈ 5 j de retard) | ≈ 35 Go d'historique, 1 Go/an | ERA5 CC BY vérifié ; NASA POWER [NV] |
| Pluie satellite | `chirps`, `tamsat`, `imerg` | Fichiers | Quotidien à mensuel | < 1 Go depuis 1981 | CHIRPS v2 **s'arrête fin 2026** ; TAMSAT commercial autorisé (version CC non nommée) |
| Rayonnement de surface | `cmsaf_sarah` | Fichiers, inscription | Mensuel | ≈ 20 Mo/an | Gratuit avec attribution ; **usage commercial non confirmé** |
| Stations au sol | `tahmo`, `anacim_stations` | Convention | 5 à 60 min | ≈ 0,3 Go/an | Conditions inconnues [NV] ; indispensables pour corriger le biais local |
| Prévisions saisonnières | `agrhymet_presass` | Bulletins | Annuel (mai) | < 10 Mo/an | Convention [NV] |

**Points de vigilance.**

- **Fuite de données futures.** Une prévision doit être gardée telle qu'émise (`meteo.forecast_asof`), jamais remplacée par l'observation. Sinon, les modèles apprennent avec une information qu'ils n'auront pas en production.
- **Rayonnement mesuré.** ET0 FAO-56 Penman-Monteith a besoin du rayonnement. Le kit ne le mesure pas : on prend une valeur satellite ou prévue, ou un pyranomètre sur les kits de référence (§ 6).

### 3.2 Sols

| Donnée | Sources | Collecte | Fréquence | Volume | Statut |
|---|---|---|---|---|---|
| Texture, pH, MO, N, P, K, CEC, densité | `isdasoil` (30 m), `soilgrids` (250 m), `hwsd` | Téléchargement (S3 us-west-2 pour iSDA) | À chaque version | 5 à 10 Go | iSDA et SoilGrids CC BY 4.0 vérifiés ; HWSD sans licence affichée (risque NC-SA) |
| Carte pédologique nationale | `inp_soil_map` | Convention INP | Ponctuel | < 1 Go | [NV] |
| Analyses de laboratoire | `soil_lab_analyses` | Prélèvement à l'installation, puis tous les 2 ans | Campagne | 150 à 300 échantillons au pilote, puis environ 1 000/an | Coût par échantillon : hypothèse de 15 à 40 k FCFA [NV] |
| Mesures de terrain (conductimètre, pH-mètre, tarière) | `soil_field_kits` | Animateurs | Installation | < 10 Mo | Matériel : 100 à 300 € (hypothèse) |
| Propriétés dérivées par parcelle (RU, capacité au champ, point de flétrissement) | dérivé dans `sols.field_profile` | Fonctions de pédotransfert, puis correction par le labo | À chaque analyse | 20 000 lignes | Obligatoire pour le bilan hydrique |

**Point de vigilance : la réserve utile.** Elle est calculée par pédotransfert à partir de cartes de 30 à 250 m, alors qu'une parcelle maraîchère des Niayes fait souvent moins d'un hectare. Sans analyse de laboratoire ni ajustement sur la courbe d'humidité observée, l'erreur sur la réserve utile pèse directement sur la date d'irrigation. C'est la donnée qui justifie le plus l'achat d'analyses.

### 3.3 Satellite

| Donnée | Sources | Résolution, revisite | Usage | Statut |
|---|---|---|---|---|
| Optique : bandes L2A, NDVI, EVI, NDWI, SAVI, NDRE | `sentinel2`, `landsat`, `hls` | 10–30 m ; 2 à 5 j combinés | Vigueur, phénologie, rendement, cultures | Ouvert ; quotas du Copernicus Data Space [NV] |
| Radar : VV, VH, rapport, cohérence | `sentinel1` | 10 m ; 6 à 12 j | Suivi par temps nuageux (hivernage), humidité de surface | Ouvert |
| Basse résolution : LST, NDVI MODIS et VIIRS | `modis_viirs` | 250 m–1 km ; quotidien | Assurance indicielle, contexte régional | Ouvert |
| Produits prêts à l'emploi : WOfS, couverture, NDVI anomalies | `deafrica` | 10–30 m | Contexte, masques d'eau | Ouvert [NV] |
| Évapotranspiration réelle | `wapor` | L3 20 m sur le delta du Sénégal | Validation du bilan hydrique, assurance | **Licences contradictoires** : à clarifier |
| Très haute résolution quotidienne | `planetscope` | 3 m ; quotidien | Petites parcelles | **NICFI terminé**, offre recherche non commerciale ; prix sur devis |

**Ce que le satellite ne fait pas bien ici.**

- Les parcelles maraîchères de 0,1 à 0,5 ha ne couvrent que 10 à 50 pixels Sentinel-2.
- La couverture nuageuse de juillet à septembre coupe les séries optiques. Le comblement de lacunes (`ndvi_gapfill`) et le radar ne sont donc pas des options, mais la condition pour exploiter l'optique en hivernage.

**Stockage.** On ne stocke que des découpes par zone d'intérêt :

- environ 50 Go/an sur une zone pilote de 5 000 km² ;
- les tuiles d'entraînement (`satellite.s2_chips`) font environ 30 Go/an pour la zone pilote et 240 Go/an pour toute la zone agricole nationale.

### 3.4 Drones

| Donnée | Source | Collecte | Volume | Statut |
|---|---|---|---|---|
| Orthomosaïques RGB (comptage, levée, contours) | `drone_rgb` | Prestataire ou drone propre, 2 à 4 vols par saison et par site | 2 à 5 Go par vol de 50 ha, environ 320 Go/an pour 20 sites | Prestation : 5 à 15 k FCFA/ha (hypothèse) |
| Multispectral (NDVI fin, NDRE) | `drone_multispectral` | Idem | Idem | Capteur : 4 à 8 k€ (hypothèse) |
| Thermique (stress hydrique) | `drone_thermal` | Vol à midi solaire | Idem | Capteur : 3 à 6 k€ (hypothèse) |

**Décision : le drone est optionnel dans tous les modèles** (A4.1). Trois raisons :

- un coût par hectare élevé pour des parcelles minuscules ;
- un cadre réglementaire contraignant (§ 8.4) ;
- l'ESP32-CAM et Sentinel-2 couvrent déjà l'essentiel.

Le drone sert à **étiqueter** (contours de parcelles, types de culture, vérité terrain pour le satellite) sur quelques sites de référence. Il ne sert pas à produire.

### 3.5 IoT : le kit SmartAgri92

| Donnée | Source | État | Fréquence | Volume cible | Rôle |
|---|---|---|---|---|---|
| Humidité du sol, T, HR, pression, N/P/K, état de la pompe, seuils, version des paramètres appliqués (`param_version`, à ajouter) | `kit_telemetry` (`telemetry.v1`) | **En place** (firmware v1.1 ni compilé ni testé sur le matériel) | 5 min | 2,9 M lignes/j, soit 20 à 40 Go/an | Entrée de presque tous les modèles |
| Événements : pompe, défauts, redémarrages, acquittements ; actions faites depuis la page locale ou l'application | `kit_events` | En place pour la pompe et les défauts ; **actions de l'utilisateur absentes** | À l'occurrence | 1 à 2 Go/an | Sessions d'irrigation, pannes |
| Registre : firmware, profondeur de sonde, étalonnage, débit nominal, cuve, panneau | `kit_config` | En place, **mais incomplet tant que l'installation ne l'impose pas** | Au changement | < 100 Mo | Contexte obligatoire |
| Images ESP32-CAM | `kit_espcam` | Optionnel | 4 photos/j conseillées | 75 Go/an pour 500 kits | Canopée, phénologie, pièges |
| **Débit et volume (débitmètre)** | `kit_flowmeter` | **Absent, prévu en v1.2** | 5 min | Inclus dans la télémétrie | **Vérité terrain de l'eau** |
| **Énergie : batterie, panneau, courant de pompe** | `kit_power` | **Absent** (INA219 prévu) | 5 min | Idem | Santé de la pompe, autonomie, anomalies |
| **Sol étendu : CE (salinité), température, 2e profondeur** | `kit_soil_extended` | **Absent**, sauf si la sonde 7-en-1 expose déjà CE et T | 5 min | Idem | Salinité, drainage, calibration |
| **Microclimat de référence** : pluviomètre, humectation foliaire, pyranomètre, anémomètre | `kit_microclimate` | **Absent** ; 1 kit sur 20 | 5 min | Idem | ET0 complète, biais local, risque fongique |

Le § 6 détaille ce que coûtent ces manques et dans quel ordre les combler.

**Exigences de la page locale.** Le prototype « Tableau de bord du champ » sert de référence pour la page que le kit affichera sur son propre Wi-Fi (doc 10 § 1.5 ; carte des modèles au doc 14 § 4.2.1). Il impose cinq exigences de données au kit :

1. **Journaliser les actions de l'utilisateur.** Chaque action est un événement de `kit_events` : seuil modifié, bascule entre mode automatique et manuel, commande manuelle de la pompe, alerte acquittée, analyse lancée, jeu de paramètres appliqué. Il porte le déclencheur (`auto`, `manuel`, `utilisateur`, `planificateur`), l'origine (page locale, application, serveur) et `param_version`. Les forçages manuels sont l'étiquette la moins chère pour `irr_need_24h` : l'agriculteur qui arrose contre l'avis du kit dit que le seuil était faux.
2. **Dater juste.** Sans horloge fiable, ni la courbe ni l'événement n'ont de valeur. Ordre de priorité de la source d'heure : le téléphone connecté à la page, puis SNTP, puis une RTC. `/data` expose `heure_ok`, et toute mesure prise sans heure fiable est marquée comme telle, jamais datée au hasard (doc 00 L1).
3. **Garder un historique embarqué.** Les courbes Jour, Semaine, Mois et Année du prototype exigent :
   - 30 jours au pas de 5 min, soit 8 640 enregistrements (doc 02) ;
   - un an d'agrégats journaliers (min, moyenne, max) pour 8 variables, soit 365 × 8 × 3 × 2 octets ≈ 18 Ko (hypothèse : 2 octets par valeur). Ça tient dans LittleFS.
4. **Étalonner par kit.** `ADC_SEC` et `ADC_EAU` sont aujourd'hui fixés à la compilation. `sm_calibration` fournit une courbe par kit, enregistrée en NVS et poussée par le même chemin que les seuils (doc 16). Le registre `kit_config` garde la date et la méthode d'étalonnage.
5. **Recevoir des seuils NPK par culture et par stade.** Les seuils N < 20, P < 10 et K < 80 sont codés en dur dans le firmware, sans NVS ni route pour les changer. `fert_reco` les produit par culture et par stade. Ils arrivent dans le jeu de paramètres, et le kit renvoie la version appliquée.

### 3.6 Phytosanitaire

| Donnée | Sources | Collecte | Volume | Statut |
|---|---|---|---|---|
| Diagnostics validés (classe, gravité, certitude) | `advisor_diagnoses` | File de validation du module 8 | ≥ 5 000 à la V2 | **Donnée la plus précieuse du projet** |
| Photos des producteurs | `farmer_photos` | App mobile, avec consentement | 50 k à 200 k/an, soit 50 à 500 Go/an | Personnelles (visages, lieux) : floutage |
| Relevés de piégeage et d'observation | `scouting_reports` | Animateurs, pièges à phéromones | Environ 100 k relevés/an | Protocole à écrire |
| Traitements appliqués | `treatments_log` | Saisie | Faible | Sert à la fois de cible et de variable confondante |
| Alertes officielles | `dpv_alerts`, `famews`, `fao_locust` | Convention DPV, FAO | Hebdomadaire | [NV] |
| Produits homologués | `csp_pesticides` | Liste du Comité sahélien des pesticides | Semestriel | **L'assistant ne recommande que ces produits** |
| Biologie des ravageurs (seuils thermiques, degrés-jours) | `pest_biology_reference` | Littérature | Ponctuel | Paramètres de `pest_phenology` |
| Images publiques | `plantvillage`, `plantdoc`, `gbif` | Téléchargement | Environ 56 k images | PlantVillage : **aucune licence d'origine**, chaîne de droits du dérivé CC0 non établie ; PlantDoc CC BY 4.0 ; GBIF à filtrer sur CC0 et CC BY |
| Modèles pré-entraînés de vision | `vision_backbones` | Hub de modèles | — | Licence à vérifier modèle par modèle |

**Biais à surveiller.**

- PlantVillage est photographié en laboratoire, sur fond uni. Un modèle entraîné dessus s'effondre sur des photos de terrain. Ces images servent au pré-entraînement, jamais à l'évaluation.
- Les cultures locales sont peu représentées, voire absentes : oignon, gombo, bissap, piment, aubergine africaine.

### 3.7 Agronomie

| Donnée | Sources | Collecte | Statut |
|---|---|---|---|
| Cycles de culture (semis, variété, stades, récolte) | `crop_cycles_user` | Saisie (module 6), relances SMS et WhatsApp | **Obligatoire pour 15 modèles** ; qualité de saisie à mesurer |
| Journal des opérations (irrigation manuelle, fertilisation, traitements) | `operations_log` | Saisie | Idem |
| Kc, profondeur racinaire, fraction p | `fao56_tables` | FAO-56 | Ouvert |
| Calendriers culturaux | `fao_crop_calendar` | FAO | Licence [NV] |
| Références locales : variétés, densités, fumure | `isra_cdh_references` | Convention ISRA et CDH | [NV] ; indispensable pour adapter FAO-56 |
| Modèles de culture | `sarra`, `aquacrop` | Paramétrage local avec l'ISRA | SARRA-Py GPLv3, SARRA-O CeCILL-C ; AquaCrop [NV] |
| Rendements potentiels | `gyga` | Téléchargement | **CC BY-NC-SA : non commercial**, couverture du Sénégal non vérifiée |

### 3.8 Économie

| Donnée | Sources | Collecte | Statut |
|---|---|---|---|
| Prix de marché (légumes, céréales) | `sim_csa`, `arm_prices`, `fews_net`, `giews_fpma` | Convention ou téléchargement | 50 marchés × 20 produits × 52 semaines, soit 52 k lignes/an ; licences [NV] |
| Prix des intrants, coûts logistiques | `input_prices_survey`, `logistics_costs` | Enquête mensuelle des animateurs | Interne |
| Tarifs de l'énergie (électricité, gasoil) | `energy_tariffs` | Barèmes publics | Coût de pompage |
| Comptabilité d'exploitation | `farm_accounts` | Saisie | **Directement personnelle** |
| Paiements d'abonnement | `payments` | Mobile money | Directement personnelle ; sert au risque de crédit |
| Contrats d'assurance et sinistres | `cnaas_insurance` | Convention CNAAS | [NV] |
| Remboursements de crédit | `mfi_credit_outcomes` | Convention avec une IMF, consentement explicite | Directement personnelle ; V3 |

### 3.9 Géospatial

| Donnée | Sources | Statut |
|---|---|---|
| **Contours des parcelles** | `user_field_boundaries` | Dessinés dans l'app ou levés au GPS. **Donnée personnelle directe**. Obligatoire pour 17 modèles |
| Limites administratives | `geoboundaries`, `ansd_admin` | geoBoundaries ouvert ; **GADM exclu (non commercial)** ; ANSD sur demande |
| Relief | `copernicus_dem` | GLO-30, ouvert |
| Occupation du sol | `worldcover` | CC BY 4.0, 10 m, millésimes 2020 et 2021 (vérifié) |
| Eaux de surface | `jrc_gsw` | Libre avec attribution, 1984–2024 (vérifié) |
| Hydrographie | `hydrosheds` | Usage commercial autorisé (vérifié) |
| Routes, marchés, localités | `osm` | **ODbL : partage à l'identique** des bases dérivées ; usage en interne sans difficulté |
| Contours de parcelles ouverts | `field_boundaries_open` | Fields of The World, etc. : licence et couverture [NV] |

### 3.10 Eau et irrigation (domaine ajouté)

Le brief range l'eau sous « IoT ». Pourtant, la ressource conditionne la recommandation : on ne conseille pas d'irriguer avec une eau trop salée ou un puits à sec.

| Donnée | Source | Collecte | Usage |
|---|---|---|---|
| Qualité de l'eau d'irrigation : CE, pH, et SAR si possible | `irrigation_water_quality` | Conductimètre à l'installation, puis à chaque saison sèche (environ 2 000 prélèvements/an) | `salinity_risk`, `irr_scheduler` (fraction de lessivage) |
| Inventaire des puits et forages (profondeur, débit, type de pompe) | `well_inventory` | Installation (UC-01) | Contraintes de débit, coût de pompage |
| Niveaux de nappe | `dgpre_groundwater` | Convention DGPRE [NV] | Risque de pénurie, intrusion saline dans les Niayes |

### 3.11 Historique

| Donnée | Sources | Statut |
|---|---|---|
| Rendements déclarés par parcelle | `farmer_harvests` | Saisie en fin de campagne (40 k lignes/an à la cible). **Cible du modèle de rendement** |
| Statistiques agricoles nationales et régionales | `ansd_stats`, `dapsa_surveys`, `faostat` | ANSD : licence ouverte dont le nom n'est pas vérifié ; DAPSA sur convention ; FAOSTAT ouvert |
| Essais agronomiques | `research_trials` | ISRA, CGIAR : gratuit ou sur convention [NV] |

### 3.12 Utilisateurs et consentements (domaine ajouté)

| Donnée | Source | Pourquoi elle compte pour l'IA |
|---|---|---|
| Comptes (téléphone, langue, rôle) | `user_accounts` | Langue de l'assistant, segmentation ; **directement personnelle** |
| Registre des exploitations | `farm_registry` | Lien entre parcelles, kits et membres |
| **Consentements par finalité** : service, amélioration des modèles, partage avec des partenaires, voix, photos | `consents` | **Filtre d'entrée de chaque jeu d'entraînement**. Une donnée sans consentement pour la finalité « amélioration des modèles » n'entre pas dans les features |
| Retours sur les recommandations (accepter, refuser, plus tard) | `reco_feedback` | Récompense du bandit (`reco_bandit`), mesure d'adoption |
| Usage de l'application | `app_usage` | Contexte du bandit, détection d'abandon |

### 3.13 Langue et voix (domaine ajouté)

| Donnée | Sources | Statut |
|---|---|---|
| Conversations de l'assistant | `assistant_logs` | Directement personnelles ; environ 2,5 Go/an ; évaluation et garde-fous |
| Corpus vocal consenti (wolof, pulaar) | `speech_consented` | Collecte sous contrat : 100 à 300 h, soit 12 à 35 Go ; 3 à 8 k FCFA par heure transcrite (hypothèse) |
| Corpus vocaux publics | `common_voice`, `open_wolof_speech` | Common Voice ouvert ; corpus wolof publics : 10 à 40 h, licences [NV] (ALFFA, Kallaama non recherchés) |
| Modèles de base | `claude_api`, `embedding_models`, `xlsr_models` | XLS-R sous Apache 2.0 : utilisable commercialement après affinage (vérifié) |
| Modèles non commerciaux | `mms_models`, `nllb_models` | **CC BY-NC 4.0** : recherche uniquement ; le pulaar est absent de MMS (vérifié) |

### 3.14 Connaissances pour le RAG (domaine ajouté)

| Donnée | Source | Statut |
|---|---|---|
| Fiches techniques : ISRA, ANCAR, ONG, FAO | `technical_sheets` | 500 à 2 000 documents. **La FAO est souvent sous CC BY-NC-SA 3.0 IGO** : citer est possible, mais l'intégration dans un service commercial doit être vérifiée document par document |
| Questions et réponses validées par des agronomes | `agronomist_qa` | Interne ; sert à la fois au corpus et au jeu d'évaluation |

## 4. Besoins par cas d'usage

Ce tableau se lit **au niveau des jeux**, et non des sources. La matrice A4.1 suit la lignée jusqu'aux sources : elle est plus large, car un jeu brut regroupe plusieurs sources. Par exemple, `raw.iot.telemetry` réunit les quatre futurs capteurs du kit. Les jeux exacts de chaque modèle sont dans A3.

### IA-1 — Irrigation (`irr_et0`, `irr_water_balance`, `soil_nowcast`, `irr_need_24h`, `irr_scheduler`)

- **Obligatoires**
  - Télémétrie horaire et sessions d'irrigation.
  - Prévisions as-of et grille météo quotidienne.
  - Profil de sol de la parcelle : réserve utile.
  - Cycle de culture, stade, Kc.
  - Coûts de l'énergie, pour le planificateur V3.
- **Recommandées**
  - Correction du biais météo local.
  - Épisodes de pluie.
  - Analyses de laboratoire.
  - État des équipements.
- **Optionnelles** : indices satellite, qualité de l'eau.
- **Cible** : le besoin en eau à 24 h, reconstitué a posteriori par bilan hydrique (`target_need_mm_24h`).
- **Manque critique** : le **volume apporté**. Sans débitmètre, on l'estime par durée de pompage × débit nominal (`kit_config`). L'erreur est inconnue tant qu'aucune mesure ne la quantifie ; la campagne de mesure du § 5 sert à cela.

### IA-2 — Météo locale (`wx_blend`, `wx_local_bias`, `wx_rain_prob`)

- **Obligatoires** : prévisions as-of de plusieurs fournisseurs ; observations locales (BME280 du kit), qui servent à la fois de variable et de cible du biais.
- **Recommandées** : stations TAHMO et ANACIM ; grille quotidienne.
- **Optionnelles** : prévisions saisonnières, contexte de la parcelle (relief, distance à la mer).
- **Manque critique**
  - **La pluie mesurée** : il n'y a aucun pluviomètre sur le kit. La probabilité de pluie s'étalonne donc sur CHIRPS et IMERG, à 5–10 km, et non sur la parcelle.
  - Le pluviomètre à augets du kit de référence (1 sur 20) corrige en partie ce manque.

### IA-3 — Vision (`vis_quality`, `vis_disease`, `vis_pest_count`, `vis_canopy`)

- **Obligatoires** : photos étiquetées et validées (au moins 5 000 à la V2), un modèle pré-entraîné, environ 3 000 images de pièges annotées et, pour la canopée, les séries ESP32-CAM.
- **Recommandées** : référentiel phytosanitaire (classes et conseils) ; indices satellite pour la canopée.
- **Optionnelles** : images publiques, mosaïques de drone, risque météo comme a priori.
- **Métadonnées obligatoires sur chaque photo** : culture, stade, région, date et appareil. Elles permettent de stratifier l'évaluation et de détecter les biais.

### IA-4 — Risques phytosanitaires (`risk_rules`, `pest_phenology`, `pest_risk_ml`)

- **Obligatoires** : grille météo et prévisions ; cycles de culture ; référentiel des ravageurs (seuils, degrés-jours).
- **Recommandées** : foyers observés (relevés et diagnostics), biais local, épisodes de pluie.
- **Optionnelles** : images de pièges.
- **Manques critiques**
  - **L'humectation foliaire**, qui pilote les maladies fongiques. Elle n'est mesurée que sur les kits de référence.
  - **Les absences confirmées.** Sans relevés négatifs, le modèle confond « pas de maladie » et « pas d'observation ». Le protocole de piégeage doit enregistrer les zéros.

### IA-5 — Assistant (`asst_llm`, `asst_retrieval`, `asst_guard`, `asst_asr`, `asst_tts`)

- **Obligatoires** :
  - le corpus RAG découpé ;
  - la liste CSP des produits autorisés ;
  - un jeu d'évaluation noté par des agronomes (environ 5 000 échanges par an) ;
  - un corpus vocal pour la V2.
- **Recommandées** : contexte de la parcelle (cycle, prévisions).
- **Optionnelles** : épisodes de pluie récents.
- **Hors production** : les modèles MMS et NLLB servent **en recherche seulement** (CC BY-NC).
- **Manque critique**
  - **Le pulaar** : aucun corpus ouvert n'a été identifié. La collecte consentie est la seule voie.
  - **Le wolof** : les corpus publics sont faibles, de l'ordre de 10 à 40 h [NV].

### IA-6 — Fertilisation (`fert_reco`, `npk_calibration`)

- **Obligatoires** : profil de sol, paramètres de culture, cycles. Pour la calibration du capteur NPK, des **paires capteur-laboratoire** : 150 à 1 000 par an.
- **Recommandées** : analyses de laboratoire et coûts des intrants.
- **Optionnelles** : indices satellite.
- **Défi** : les capteurs NPK à bas coût mesurent en réalité une conductivité. Ils ne donnent pas les teneurs en N, P et K. Si les paires montrent une corrélation faible (R² < 0,5, à vérifier), il faut afficher l'indicateur comme une « tendance » et fonder la recommandation sur le laboratoire et le bilan, pas sur le capteur.

### IA-7 — Recommandations (`reco_engine`, `reco_bandit`)

- **Obligatoires** : cycles, paramètres de culture, télémétrie, prévisions.
- **Recommandées** : référentiel phytosanitaire ; retours sur les recommandations.
- **Optionnelles** : foyers observés.
- **Cible du bandit** : l'acceptation, puis l'effet mesuré (eau économisée, rendement). Il faut journaliser la **probabilité de proposition** de chaque recommandation, sinon l'évaluation hors ligne est impossible.

### IA-8 — Suivi de culture et rendement (`ndvi_gapfill`, `phenology_stage`, `yield_forecast`, `yield_crop_model`, `crop_type_map`, `field_boundary`)

- **Obligatoires** : indices satellite par parcelle ; stades phénologiques ; rendements déclarés ; paramètres des modèles de culture ; grille météo ; sol ; cycles ; contours.
- **Recommandées**
  - Tuiles Sentinel-2.
  - Séries ESP32-CAM.
  - Contours ouverts.
  - Télémétrie et irrigation, pour le modèle de culture.
- **Optionnelles** : rendement potentiel (GYGA, non commercial) ; mosaïques de drone.
- **Manque critique** : **des rendements mesurés**. Les rendements déclarés sont bruités. Prévoir des **carrés de rendement** (pesée sur une placette de 10 m²) sur un échantillon de parcelles par campagne.
- **Volume** : il faut au moins trois campagnes avant un modèle de rendement crédible. C'est pourquoi `yield_forecast` est en V3.

### IA-9 — Finance et assurance (`agri_risk_score`, `index_insurance`)

- **Obligatoires** : historique des rendements et des statistiques régionales ; épisodes de pluie ; produits satellite régionaux ; remboursements de crédit et sinistres, sous convention.
- **Recommandées** : grille météo.
- **Défi** : un score de crédit est une **décision à fort impact sur des personnes**. Il exige un consentement explicite, l'explicabilité, un contrôle d'équité entre régions et genres, et un recours humain. Sans base juridique validée, ce cas d'usage reste en V3 et sur des données agrégées.

### IA-10 — Qualité des données du kit (`anomaly_rules`, `sm_calibration`, `anomaly_ml`, `pump_health`)

- **Obligatoires** : télémétrie nettoyée, santé des appareils, profil de sol. Pour l'étalonnage de l'humidité, des **mesures gravimétriques** de référence.
- **Recommandées** : sessions d'irrigation, prévisions (pour expliquer une hausse d'humidité par la pluie).
- **Optionnelles** : coûts.
- **Manque critique** : **le courant de la pompe** (`kit_power`). Sans lui, `pump_health` ne voit qu'un relais commandé, pas une pompe qui tourne à vide.

### Transverse (`water_savings`, `price_forecast`, `salinity_risk`)

- **Mesure des économies d'eau (MRV)** : volumes apportés, comparés au besoin FAO-56 et à une pratique de référence. **Sans débitmètre, la mesure n'est pas opposable** à un bailleur.
- **Salinité** : CE de l'eau et du sol (absente du kit), nappes, satellite.
- **Prix** : séries SIM/CSA et ARM, sous convention.

## 5. Étiquettes et vérité terrain

| Cible | Modèles | Provenance | Volume visé | Comment l'obtenir | Coût indicatif |
|---|---|---|---|---|---|
| Volume d'eau apporté (L) | `irr_need_24h`, `water_savings`, `pump_health` | `kit_flowmeter` | Tous les kits, à partir de la v1.2 | Débitmètre à effet Hall ; **au pilote, 20 kits équipés** pour mesurer l'erreur de l'estimation durée × débit | 3 à 10 k FCFA par kit (hypothèse) |
| Humidité future | `soil_nowcast` | Télémétrie (auto-étiquetée) | Toute la flotte | Décalage temporel ; exclure les capteurs en défaut (`anomaly_rules`) | Nul |
| Humidité gravimétrique | `sm_calibration` | Prélèvements | 3 profondeurs × 5 dates × 30 parcelles | Animateurs, étuve du laboratoire partenaire | Inclus dans le budget du laboratoire |
| Paires capteur NPK-laboratoire | `npk_calibration` | `soil_lab_analyses` | 150 à 1 000/an | Prélèvement au pied de la sonde, le même jour | 15 à 40 k FCFA par échantillon [NV] |
| Diagnostics validés | `vis_disease` | `advisor_diagnoses` | ≥ 5 000 à la V2, 300 par classe et plus | File de validation, apprentissage actif (les cas incertains d'abord) | Temps des conseillers |
| Comptage de ravageurs | `vis_pest_count` | Images de pièges annotées | Environ 3 000 images | Annotation par boîtes, double annotation sur 10 % | Prestataire ou animateurs |
| Foyers et absences | `pest_risk_ml` | `scouting_reports` | Environ 100 k relevés/an | Protocole hebdomadaire **avec les zéros** | Temps des animateurs, pièges |
| Rendement | `yield_forecast` | `farmer_harvests`, carrés de rendement | 40 k déclarations par an et 300 carrés par campagne | Déclaration à la récolte, carrés sur un échantillon stratifié | Pesons, temps des animateurs |
| Type de culture | `crop_type_map` | Cycles saisis, relevés au bord des champs | 2 000 points par campagne | Relevés géolocalisés par les animateurs | Temps des animateurs |
| Contours de parcelles | `field_boundary` | `user_field_boundaries`, drone | 5 000 polygones | Extraits des parcelles consenties, vérifiés sur image | Inclus |
| Acceptation et effet d'une recommandation | `reco_bandit` | `reco_feedback` | Toute la flotte | Journal avec la probabilité de proposition | Nul |
| Qualité des réponses de l'assistant | `asst_*` | `agronomist_qa`, notation | Environ 5 000 échanges/an | Grille de notation (exactitude, sécurité, utilité) | Temps des agronomes |
| Transcriptions vocales | `asst_asr` | `speech_consented` | 100 à 300 h | Collecte guidée, transcription double sur 10 % | 3 à 8 k FCFA par heure transcrite (hypothèse) |
| Remboursements | `agri_risk_score` | `mfi_credit_outcomes` | 5 à 20 k contrats/an | Convention IMF, consentement explicite | Convention |

**Règles d'étiquetage.**

1. **Étiqueter là où l'on sert.** Le module 8 sert aussi d'outil d'annotation, et l'acceptation d'une recommandation est elle-même une étiquette. On évite ainsi un outil séparé que personne n'ouvre.
2. **Provenance.** Chaque étiquette garde son auteur, son rôle, sa date, sa certitude et sa méthode. Une étiquette de producteur n'a pas le même poids qu'une étiquette de conseiller.
3. **Accord inter-annotateurs.** On mesure le kappa de Cohen sur 10 % en double annotation, avec un seuil de 0,7 par classe (hypothèse à ajuster). Une classe sous le seuil est fusionnée ou redéfinie.
4. **Jeu de référence figé.** Pour chaque modèle, un holdout stratifié par saison, région et culture. Il n'est **jamais exporté** vers OctOpus ni utilisé pour régler les hyperparamètres.
5. **Découpage temporel.**
   - On valide toujours sur une saison postérieure, jamais au hasard.
   - Pour le rendement, on ajoute un découpage qui laisse de côté une saison entière (leave-one-season-out). Le catalogue le prévoit déjà pour `yield_forecast`, mais le programme OctOpus du même nom ne découpe que par parcelle (GroupKFold) : il faut l'aligner (voir doc 14).
6. **Apprentissage actif.** La file des conseillers est triée par incertitude du modèle et par rareté de la classe.

## 6. Manques du kit et données à créer

| Manque | Conséquence aujourd'hui | Ajout proposé | Coût (hypothèse) | Priorité |
|---|---|---|---|---|
| **Débitmètre** | Ni vérité terrain de l'eau ni mesure des économies opposable | Capteur à effet Hall sur le refoulement, `telemetry.v2` | 3 à 10 k FCFA | **1 : avant la V2** |
| **Courant de la pompe, batterie, panneau** | Pannes vues trop tard, désamorçage invisible | INA219 ou équivalent | 2 à 5 k FCFA | 2 |
| **CE et température du sol** | Ni salinité ni correction thermique de l'humidité | Lire CE et T si la sonde 7-en-1 les expose, sinon seconde sonde | 0 à la sonde | 2 : **vérifier d'abord le registre Modbus de la sonde** |
| **Seconde profondeur (30–40 cm)** | Drainage et profondeur racinaire non observés | Seconde sonde capacitive | Prix d'une sonde | 3 |
| **Microclimat de référence** (1 kit sur 20) | ET0 incomplète, aucune pluie locale, aucune humectation | Pluviomètre à augets, capteur d'humectation, pyranomètre, anémomètre | 60 à 150 k FCFA par kit de référence | 2 |
| **Métadonnées d'installation** | Profondeur de sonde, sol, débit nominal manquants | Champs obligatoires dans l'assistant d'installation (UC-01) | Nul | **1** |
| **Politique ESP32-CAM** | Prise horaire sur 10 000 kits : 8,8 To/an | 4 photos/j, aux heures fixes, sur 500 kits volontaires | Module : 5 à 8 k FCFA | 3 |

**Avertissement.** Aucun de ces ajouts n'existe dans le firmware v1.1, qui n'est ni compilé ni testé sur le matériel. `telemetry.v2` reste à spécifier :

- les nouveaux champs sont optionnels ;
- les anciens kits continuent d'émettre en v1 ;
- le contrat de données est versionné.

## 7. Volumes et stockage

| Flux | Pilote (100 kits) | Cible (10 000 kits) | Remarque |
|---|---|---|---|
| Télémétrie et événements | < 1 Go/an | 22 à 42 Go/an | 1 G lignes/an : partitionnement par jour, compression Parquet |
| Photos des producteurs | 1 à 5 Go/an | 50 à 500 Go/an | Recadrage à 1 Mpx dans la zone curated (environ 30 % conservé) |
| ESP32-CAM | 15 Go/an (20 kits) | 75 Go/an (500 kits) | **Ne pas généraliser à l'horaire** |
| Drone | 0 | Environ 320 Go/an (V3, 20 sites) | Le brut passe en stockage froid après mosaïquage |
| Satellite (découpes et tuiles) | Environ 80 Go/an | 100 à 330 Go/an | Selon la zone couverte |
| Météo, sols, géo | Environ 50 Go une fois, puis 6 Go/an | Idem | Peu dépendant de la flotte |
| Voix | 0 | 12 à 35 Go (corpus) | Une fois, puis enrichissements |
| Assistant | < 0,1 Go/an | Environ 2,5 Go/an | Rétention courte (§ 8) |
| **Total** | **Environ 0,1 To/an** | **Environ 0,6 à 1,3 To/an** | **Les images (photos, ESP32-CAM, drone) en représentent environ 70 %** |

**Coût du stockage.** À la cible, le volume se compte en téraoctets, ce qui reste modeste. La surface S3 Standard en eu-west-3 coûte de l'ordre de 0,024 $ par Go et par mois [NV]. Un téraoctet représente donc environ 25 $ par mois, avant passage en accès peu fréquent ou en Glacier.

**Le vrai coût est ailleurs** :

- le **calcul satellite** : la constitution des tuiles et l'extraction par parcelle ;
- l'**étiquetage** : temps des conseillers et des animateurs ;
- les **analyses de laboratoire**.

Le doc 15 les chiffre.

## 8. Réglementation

Les points ci-dessous sont **à valider par un juriste au Sénégal**. Ils complètent les docs [04](04_data_mlops.md) (§ 5) et [06](06_devsecops.md) sans les répéter.

### 8.1 Données personnelles (loi n° 2008-12, CDP)

- **Texte applicable.** La loi 2008-12 semble toujours en vigueur ; aucune réforme adoptée n'a été trouvée (recherche du 01/11/2026, confiance moyenne).
- **Ce qui est personnel.** La personnalisation est calculée par le catalogue (règle 3) à partir de ce que déclarent les sources : `direct` ou `indirect`, avec une marque `identifying` pour ce qui identifie.
  - **Directement personnelles** :
    - téléphone et compte ;
    - **contours GPS des parcelles** ;
    - photos (visages, maisons) ;
    - voix ;
    - comptabilité, paiements, crédit ;
    - conversations.
  - **Indirectement personnelles** : tout ce qui est rattaché à une parcelle ou à un kit, c'est-à-dire la télémétrie, les cycles et les diagnostics.
- **Formalités.**
  - Déclaration, ou demande d'autorisation, auprès de la CDP **avant toute donnée réelle hors du pilote**.
  - La déclaration couvre l'hébergement à Paris (transfert hors du Sénégal) **et** les sous-traitants : OctOpus et ses hébergeurs, le fournisseur du LLM.
  - Les délais de traitement de la CDP ne sont pas connus : les anticiper (risque R8 du doc 07).
- **AIPD obligatoires** dans six cas :
  - l'assistant (conversations) ;
  - les photos ;
  - la voix ;
  - le partage avec des partenaires (assureur, IMF) ;
  - le score de risque (IA-9) ;
  - les exports vers OctOpus.
- **Consentement par finalité** (`consents`). Le service, l'amélioration des modèles, le partage avec des partenaires, la voix et les photos sont des **cases distinctes**. Un retrait de consentement retire la donnée du prochain instantané d'entraînement. Il ne retire pas un modèle déjà entraîné ; il faut l'indiquer dans la notice.
- **Minimisation pour l'IA.** Les jeux features exportables sont `minimised` :
  - identifiants pseudonymisés par HMAC ;
  - coordonnées arrondies ou remplacées par la commune ;
  - dates relatives au semis quand l'information suffit.

### 8.2 Voix

La voix est une donnée personnelle. Elle devient biométrique si elle sert à identifier. **SmartAgri92 ne fait pas d'identification par la voix**, et le contrat de collecte doit l'écrire.

- **Collecte** : consentement écrit ou enregistré, rémunération déclarée, droit de retrait.
- **Stockage** : séparé, sans le numéro de téléphone.
- **Publication** : aucune publication du corpus sans un second consentement.

### 8.3 Images

- **Floutage** automatique des visages avant la zone curated.
- Les **métadonnées EXIF GPS sont retirées** de l'image et la position est stockée à part, rattachée à la parcelle.
- L'ESP32-CAM ne vise que la culture. Le cadrage est vérifié à l'installation : pas d'habitation ni de voie publique dans le champ.

### 8.4 Drones (ANACIM)

- **Règles d'exploitation.** Elles relèvent du RAS 06, annexe 5 de l'ANACIM.
- **Loisir.** Une circulaire du 27/01/2026 interdirait les drones de loisir [NV, confiance basse].
- **Usage professionnel.** Il passerait par une **autorisation préalable** et une **assurance de responsabilité civile** [NV].
- **Épandage.** **Aucune règle trouvée** : il est **hors du périmètre**.
- **En pratique.** Recourir à des prestataires autorisés, avec l'autorisation et l'attestation d'assurance archivées pour chaque vol.

### 8.5 Licences des données et des modèles

- **Règle portée par le validateur.** Une source `restricted` (non commerciale) ne peut alimenter qu'un usage de recherche (`research_only`), jamais un jeu obligatoire ou recommandé d'un modèle de production. Une source `contract` ou `unknown` déclenche un avertissement jusqu'à ce que la licence soit levée (`licence_cleared`).
- **Sources concernées.**
  - Trois sources sont non commerciales : `gyga`, `mms_models` et `nllb_models`.
  - Vingt et une sont sous contrat, quatorze de licence inconnue.
- **Ordre de levée.** L'ordre de traitement et les clauses à négocier sont dans le doc 15.
- **OSM (ODbL).** Une base dérivée **diffusée** doit rester sous ODbL. Un usage interne ou des variables agrégées ne posent pas de difficulté. Ne jamais mélanger OSM dans un jeu publié sous une autre licence.

### 8.6 Produits phytosanitaires

L'assistant et le moteur de recommandations ne citent que des produits **homologués par le CSP**, avec la dose et le délai avant récolte de l'étiquette. Le garde-fou `asst_guard` bloque tout autre produit. C'est une exigence de sécurité des personnes, pas une préférence.

## 9. Qualité des données

| Contrôle | Où | Exemple de règle | Effet si la règle échoue |
|---|---|---|---|
| Plausibilité physique | `iot.telemetry_clean` | Humidité entre 0 et 100 %, T de l'air entre 5 et 50 °C, saut de plus de 30 points en 5 min sans irrigation | Valeur marquée, exclue des features |
| Capteur figé ou dérivant | `anomaly_rules`, `anomaly_ml` | Variance nulle sur 6 h, dérive par rapport aux voisins | Alerte de maintenance, kit exclu de l'entraînement |
| Fraîcheur | Tous les flux | Télémétrie de plus de 2 h, prévision de plus de 12 h | Repli de l'inférence (A3) |
| Discipline as-of | `meteo.forecast_asof` | Une prévision n'est jamais plus récente que l'heure de décision | Test bloquant de la chaîne de features |
| Géométrie | `geo.fields` | Polygone valide, surface entre 0,01 et 50 ha, dans le Sénégal | Saisie refusée |
| Complétude des métadonnées | `kit_config`, `crop_cycles_user` | Profondeur de sonde, culture, date de semis | Recommandation en mode dégradé, relance |
| Qualité d'image | `vis_quality` | Flou, sous-exposition, absence de feuille | Nouvelle prise demandée tout de suite |
| Accord des étiquettes | `advisor_diagnoses` | Kappa ≥ 0,7 par classe | Classe révisée |
| Consentement | Toutes les features | Finalité « amélioration des modèles » | Ligne exclue |

## 10. Limites de cet inventaire

- **82 sources sur 104 ne sont pas vérifiées.** La liste des recherches restantes est dans le doc 15, § 7. Elle comprend notamment NASA POWER, ERA5-Land, AgERA5, Copernicus Data Space, Digital Earth Africa, FAOSTAT, FEWS NET, SIM/CSA, les corpus vocaux wolof et les textes réglementaires complets.
- **Les volumes sont des ordres de grandeur.** Le pilote les mesurera ; il faut ensuite mettre à jour `volume` dans le catalogue et régénérer A2.
- **La nécessité d'une donnée est une hypothèse de modélisation.** Une donnée « recommandée » doit prouver son gain par une ablation avant d'entraîner un coût d'acquisition (doc 14).
- **Le catalogue décrit ce qui doit exister.** Il ne garantit pas que les flux soient en place : seuls la télémétrie v1, les comptes, les parcelles et les prévisions sont branchés dans le code actuel.
