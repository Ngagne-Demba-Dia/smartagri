# 81 — Inventaire des Écrans Mobiles (`plateforme/mobile`)

> **Statut** : Document de conception pure (MISSION MOBILE-01).  
> **Périmètre** : Inventaire exhaustif des écrans du **MVP mobile**, plus la feuille de route d'extension **V1.1 → V3** alignée sur les 24 écrans Web (`plateforme/web/app/[locale]/(app)/*`, `lib/modules.ts`, `lib/service-screens.ts`) et les 18 services de `16_architecture_octopus.md` § 9.3.  
> **Contrainte** : Aucun écran codé, aucune UI créée.

---

## 1. Synthèse chiffrée

| Périmètre | Nombre d'écrans | Détail |
|---|---|---|
| **MVP — Socle & Navigation mobile** | **4** | Connexion/Organisation, Menu principal, File de synchronisation, Paramètres & Cache hors-ligne |
| **MVP — Écrans métier & IA prioritaires** | **12** | Tableau de bord, Carte (+ table fallback), Alertes, Assistant IA, Parcelles (liste + détail), Exploitations, Météo, Irrigation, Prévisions Sol (`soil_nowcast`), Recommandations, Relais Kit ESP32-S3 |
| **Total MVP** | **16 écrans** | Couvre 100 % des services `MVP` / `MVP_V2` + les 2 capacités natives critiques (Outbox Sync & Relais Wi-Fi AP Kit) |
| **Extensions post-MVP (V1.1 → V3)** | **11 écrans** | Rapports/KPIs, Équipements, Cultures, Campagnes, Fertilisation, Risques Ravageurs, Planning d'arrosage, Diagnostic Maladies (photo), Pièges, Végétation Satellite, Rendement, Marchés (prix) |

---

## 2. Inventaire détaillé des écrans du MVP (16 écrans)

### 2.1 Socle, Authentification & Synchronisation (4 écrans)

| ID | Écran | Route GoRouter | Rôles | API / Local | Comportement hors-ligne & Sync | États & Composants clés |
|---|---|---|---|---|---|---|
| **MOB-01** | **Connexion & Choix Organisation** | `/login` | Tous | `POST /v1/auth/login`, `GET /v1/me` | Reconnexion hors-ligne autorisée si session JWT/cache valide en `SecureStorage` | Formulaire email/téléphone + mot de passe, sélecteur langue (`fr`/`wo`/`ff`), erreur `401`/`429` |
| **MOB-02** | **Menu Principal (Hub)** | `/menu` | Tous | Local + contexte `activeFarm` | 100 % hors-ligne ; affiche badges de file Outbox et mode hors-ligne | Grille des modules groupés (`Pilotage`, `Terrain`, `Cultures`, `IA`, `Matériel`), sélecteur exploitation, accès `Sync` et `Paramètres` |
| **MOB-03** | **File de Synchronisation & Conflits** | `/sync` | Tous | Drift `sync_outbox` + `telemetry_outbox` | Liste les mutations en attente, en erreur ou en conflit ; bouton « Synchroniser maintenant » | Compteur par type, statut (`pending`, `conflict`, `failed_permanent`), modale résolution conflit (`Seuils`) |
| **MOB-04** | **Paramètres & Stockage Hors-Ligne** | `/parametres` | Tous | Local (`SharedPreferences` / Drift) | 100 % hors-ligne | Choix langue (`fr`, `wo`, `ff`), thème clair/sombre WCAG AA, gestion tuiles MBTiles téléchargées (Mo utilisés / purge) |

### 2.2 Onglets principaux de la Barre du Bas (4 écrans, alignés `MOBILE_TABS`)

| ID | Écran | Route GoRouter | Module / Service | Rôles | API consommée | Hors-ligne & Sync | États & Composants clés |
|---|---|---|---|---|---|---|---|
| **MOB-05** | **Tableau de bord (Accueil)** | `/tableau` | Module 1 (`dashboard`) · Services #1, #2, #5, #13 | Tous | Agrégat `fields`, `alerts`, `weather`, `recommendations`, `soil_forecast` | **Stale-While-Revalidate** ; affiche bandeau « Hors-ligne / Âge des données » | KPIs exploitation, alertes critiques, résumé météo, prochain arrosage conseillé, accès rapide Assistant & Relais Kit |
| **MOB-06** | **Carte Interactive & Liste** | `/carte` | Module 4 (`map`) · Service #18 (`map_layers`) | Tous | `GET /v1/farms/{farm_id}/map?layers=...` | Tuiles **MBTiles** en cache + GeoJSON en Drift ; bouton téléchargement emprise ; bascule « Vue Tableau » | Modes `moisture`, `ndvi`, `salinity`, `crop_type` ; toggles Kits & Contours ; fiche parcelle en BottomSheet |
| **MOB-07** | **Alertes** | `/alertes` | Module 10 · Service #13 (`device_health`) | Tous (ack: `ALERT_ACKERS`) | `GET /v1/alerts`, `POST /v1/alerts/{id}/ack` | Lecture en cache ; **acquittement mis en file Outbox** si hors-ligne | Filtres gravité (`critical`, `warning`, `info`) et statut (`open`, `acknowledged`, `resolved`), `ProvenanceBadge`, action acquitter |
| **MOB-08** | **Assistant IA** | `/assistant` | Module 12 · Services #16 (`assistant_chat`) & #17 (`assistant_transcribe`) | Tous | `POST /v1/assistant/chat`, `POST /v1/assistant/transcribe` | Historique local consultable hors-ligne ; envoi bloqué avec message clair si hors-ligne | 3 suggestions rapides, bulles texte brut (`SelectableText`), `citations`, bandeaux `fallback`/`refusal`/`truncated`, micro `≤60s` éditable, bouton TTS (`asst_tts`) |

### 2.3 Écrans Terrain, Décision IA & Relais Kit (8 écrans)

| ID | Écran | Route GoRouter | Module / Service | Rôles | API consommée | Hors-ligne & Sync | États & Composants clés |
|---|---|---|---|---|---|---|---|
| **MOB-09** | **Exploitations** | `/exploitations` | Module 2 (`farms`) | Tous | `GET /v1/farms` | **Cache-First** (24 h) | Liste des exploitations, surface totale, nombre de parcelles/kits, sélection exploitation active |
| **MOB-10** | **Liste des Parcelles** | `/parcelles` | Module 3 (`fields`) | Tous | `GET /v1/farms/{farm_id}/fields` | **Cache-First** (24 h) | Recherche/filtre, culture en cours, dernière humidité, badge alerte |
| **MOB-11** | **Détail d'une Parcelle** | `/parcelles/:id` | Module 3 (`fields`) · Hub parcelle | Tous | `GET /v1/fields/{id}` + résumés #1, #2, #3, #5 | **Stale-While-Revalidate** | Identité parcelle, cycle actif, liens directs vers Météo, Irrigation, Prévisions Sol, Recommandations |
| **MOB-12** | **Météo Parcelle** | `/meteo` (ou `/:fieldId`) | Module 5 (`weather`) · Service #1 | Tous | `GET /v1/fields/{id}/weather?days=7` | **Stale-While-Revalidate** (`staleMs = 1 h`) | Températures min/max, pluie (mm + proba si dispo), $ET_0$ Hargreaves, `ProvenanceBadge` (`provider`/`cache`/`stale_cache`) |
| **MOB-13** | **Irrigation (Besoin 24 h)** | `/irrigation` | Service #3 (`irrigation_need`) | Tous | `GET /v1/fields/{id}/irrigation-need` | **Stale-While-Revalidate** (`staleMs = 6 h`) | Besoin en mm et m³, report conseillé si pluie prévue (`defer_reason`), repère terrain `1 mm = 1 L/m² = 10 m³/ha`, `ProvenanceBadge` |
| **MOB-14** | **Prévisions Sol (`soil_nowcast`)** | `/previsions` | Service #2 (`soil_forecast`) | Tous | `GET /v1/fields/{id}/soil-forecast?horizons=24,48,72` | **Stale-While-Revalidate** (`staleMs = 15 min`) | Courbe/bandes d'humidité `p10`–`p50`–`p90` à 24/48/72 h, seuils `start_pct`/`stop_pct`, `ConfidenceView` (`interval`), `ProvenanceBadge` |
| **MOB-15** | **Recommandations & Retour** | `/recommandations` | Module 7 · Service #5 (`recommendations`) | Tous (feedback: `FEEDBACK_WRITERS`) | `GET /v1/fields/{id}/recommendations`, `POST /v1/recommendations/{id}/feedback` | Lecture cache (`15 min`) ; **feedback mis en file Outbox** si hors-ligne | Liste priorisée (`high`/`medium`/`low`), justification, `valid_until`, boutons retour (`followed`, `partially_followed`, `ignored`, `not_applicable`) |
| **MOB-16** | **Kit Terrain & Relais Wi-Fi AP** | `/kit` | Service #7 (`kit_parameters`) + #13 (`device_health`) + Firmware v1.2 | Tous (seuils: `THRESHOLD_WRITERS`) | Cloud : `GET /parameters`, `POST /parameters/ack`, `PUT /thresholds`, `GET /health`, `POST /v1/telemetry/batch`<br/>Local Kit AP : `GET /data`, `POST /parametres` | **Pivot terrain hors-ligne** : lit le cache des paramètres, pousse vers le kit en Wi-Fi AP, collecte `/data`, met `ack` et `telemetry/batch` en Outbox | État des 6 capteurs (`soil`, `bme`, `npk`, `flow`, `pump`, `battery`), bloc seuils/NPK/étalonnage/agro avec validité (`7j`/`30j`/`180j`), assistant connexion Wi-Fi AP Kit |

---

## 3. Écrans différés Post-MVP (V1.1 → V3, alignés sur le Web)

Ces écrans ne font **pas** partie du MVP mobile (ils restent accessibles via le Web responsive `375 px` en attendant leur intégration native) :

| Version | ID | Écran | Route | Service / Module | Spécificité mobile future |
|---|---|---|---|---|---|
| **V1.1** | **EXT-01** | Rapports & Économies d'eau | `/rapports` | Module 13 · Service #14 (`water_savings`) | Export PDF/partage natif |
| **V1.1** | **EXT-02** | Équipements | `/equipements` | Module 10 (`equipment`) | Inventaire pompes/vannes/capteurs |
| **V1.1** | **EXT-03** | Cultures | `/cultures` | Module 6 (`crops`) | Fiches cultures et stades |
| **V1.1** | **EXT-04** | Campagnes | `/campagnes` | Module 11 (`campaigns`) | Suivi de saison agricole |
| **V1.1** | **EXT-05** | Fertilisation | `/fertilisation` | Service #6 (`fertilization`) | Doses N-P-K (mention « indicatif ») |
| **V1.1** | **EXT-06** | Risques Ravageurs | `/risques` | Service #9 (`pest_risk`) | Alertes foyers à 7 et 14 jours |
| **V1.1** | **EXT-07** | Planning d'arrosage | `/planning` | Service #4 (`irrigation_plan`) | Créneaux par pompe et parcelle |
| **V2** | **EXT-08** | Diagnostic Maladies (Photo) | `/maladies` | Module 8 · Service #8 (`disease_diagnosis`) | Caméra + `vis_quality` TFLite + compression `≤ 256 Kio` + abstention `< 0.7` |
| **V2** | **EXT-09** | Pièges à insectes | `/pieges` | Service #10 (`trap_counts`) | Séries de comptage caméra piège |
| **V2** | **EXT-10** | Végétation Satellite | `/vegetation` | Service #11 (`vegetation`) | Séries NDVI/EVI (`gapfilled`) & stade BBCH |
| **V3** | **EXT-11** | Rendement & Marchés | `/rendement`, `/marches` | Module 9 · Services #12 (`yield_forecast`) & #15 (`price_forecast`) | Prévisions campagne (`p10`–`p90`) et prix FCFA/kg |

---

## 4. Critères d'acceptation de conception (Avant démarrage dev Mobile)

1. Aucune route ni champ JSON inventé : 100 % des DTOs Flutter correspondent aux contrats de `plateforme/web/lib/contracts/*.ts` et `16_architecture_octopus.md` § 9.
2. Chaque écran MVP respecte les 5 invariants transverses décrits dans [`80_mobile_architecture.md`](./80_mobile_architecture.md) § 4 (`QueryStateView`, `ProvenanceWidget`, `SyncBanner`, `RoleGate`, WCAG 2.1 AA).
3. Le mode hors-ligne et la boucle de relais Kit (`MOB-16` ↔ `MOB-03`) sont testables de bout en bout sans connexion Internet active.
