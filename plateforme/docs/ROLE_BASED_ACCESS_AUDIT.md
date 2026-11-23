# MISSION FRONT-RBAC-01 — Audit Complet du Système de Rôles & Architecture des Dashboards par Rôle

**Date** : 22 novembre 2026  
**Périmètre** : `plateforme/web` (Frontend Next.js 15 + BFF) & `plateforme/backend` (API FastAPI + RLS)  
**Rôles audités** :
1. **`AGRICULTEUR`** (`farmer` — `agriculteur@demo.sn`)
2. **`COOPERATIVE_MANAGER`** (`coop_manager` — `cooperative@demo.sn`)
3. **`AGRONOME`** (`agronomist` — `agronome@demo.sn`)
4. **`ADMIN`** (`admin` — `admin@demo.sn`)

> **Contrainte respectée** : Aucun écran n'a été modifié. Ce document constitue l'audit exhaustif de l'existant et le cahier des charges de spécialisation RBAC des menus, routes et tableaux de bord.

---

## 1. Inventaire de toutes les Pages Web (`25` pages)

Toutes les pages résident sous `plateforme/web/app/[locale]/` (locales : `fr`, `wo`, `ff`). Actuellement, le middleware ([middleware.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/middleware.ts)) vérifie uniquement la présence d'un cookie de session (`sa_at` ou `sa_rt`), ce qui rend les **24 pages connectées accessibles en URL directe aux 4 rôles**, le filtrage des données se faisant par organisation (`organization_id`) côté API/mocks.

| # | URL (`/[locale]/...`) | Fichier Page (`app/[locale]/...`) | Composant Vue (`features/...`) | Groupe Menu | Filtrage actuel par rôle |
|---:|---|---|---|---|---|
| 0 | `/fr/login` | `login/page.tsx` | `features/auth/LoginForm.tsx` | Public | Public (redirige vers `/tableau` si connecté) |
| 1 | `/fr/tableau` | `(app)/tableau/page.tsx` | `features/dashboard/Dashboard.tsx` | `pilotage` | Données filtrées par `orgIds` ; **même layout pour les 4 rôles** |
| 2 | `/fr/alertes` | `(app)/alertes/page.tsx` | `features/alerts/AlertsLog.tsx` | `pilotage` | Données filtrées par `orgIds` ; bouton *Acquitter* contrôlé par `canAckAlerts()` |
| 3 | `/fr/communaute` | `(app)/communaute/page.tsx` | `features/community/CommunityView.tsx` | `pilotage` | Accessible aux 4 rôles (publication écrite & vocale) |
| 4 | `/fr/rapports` | `(app)/rapports/page.tsx` | `features/reports/ReportsView.tsx` | `pilotage` | Données filtrées par `orgIds` + export CSV |
| 5 | `/fr/exploitations` | `(app)/exploitations/page.tsx` | `features/farms/FarmsList.tsx` | `terrain` | `farmer` voit sa ferme (`Ndiol`) ; `coop`/`agronome` voient la coopérative (`Mboro`, `Potou`) ; `admin` voit tout |
| 6 | `/fr/parcelles` | `(app)/parcelles/page.tsx` | `features/fields/FieldsList.tsx` | `terrain` | Parcelles filtrées par `orgIds` |
| 7 | `/fr/parcelles/[id]` | `(app)/parcelles/[id]/page.tsx` | `features/fields/FieldDetail.tsx` | `terrain` | `404` hors `orgIds` ; formulaire de seuils (`ThresholdForm`) contrôlé par `canEditThresholds()` |
| 8 | `/fr/carte` | `(app)/carte/page.tsx` | `features/map/FieldMap.tsx` | `terrain` | Carte nationale du Sénégal (6 zones) + zoom périmètre filtré par `orgIds` |
| 9 | `/fr/meteo` | `(app)/meteo/page.tsx` | `features/weather/WeatherView.tsx` | `terrain` | Parcelles filtrées par `orgIds` |
| 10 | `/fr/cultures` | `(app)/cultures/page.tsx` | `features/crops/CropsView.tsx` | `cultures` | Cycles culturaux filtrés par `orgIds` (lecture seule côté UI) |
| 11 | `/fr/campagnes` | `(app)/campagnes/page.tsx` | `features/campaigns/CampaignsView.tsx` | `cultures` | Campagnes filtrées par `orgIds` (lecture seule côté UI) |
| 12 | `/fr/rendement` | `(app)/rendement/page.tsx` | `features/yield/YieldView.tsx` | `cultures` | Prévisions filtrées par `orgIds` |
| 13 | `/fr/fertilisation` | `(app)/fertilisation/page.tsx` | `features/fertilization/FertilizationView.tsx` | `cultures` | Doses NPK indicatives filtrées par `orgIds` |
| 14 | `/fr/vegetation` | `(app)/vegetation/page.tsx` | `features/vegetation/VegetationView.tsx` | `cultures` | Séries NDVI/EVI filtrées par `orgIds` |
| 15 | `/fr/marches` | `(app)/marches/page.tsx` | `features/markets/MarketsView.tsx` | `cultures` | Prix de gros nationaux (Dakar, Thiès, Saint-Louis, Touba, Kaolack) — communs aux 4 rôles |
| 16 | `/fr/recommandations` | `(app)/recommandations/page.tsx` | `features/recommendations/RecommendationsList.tsx` | `ia` | Filtrées par `orgIds` ; boutons de retour (*Suivi / Ignoré*) contrôlés par `canGiveFeedback()` |
| 17 | `/fr/maladies` | `(app)/maladies/page.tsx` | `features/diagnosis/DiagnosisView.tsx` | `ia` | Upload photo & analyse foliaire autorisés aux 4 rôles (`DIAGNOSIS_WRITERS`) |
| 18 | `/fr/assistant` | `(app)/assistant/page.tsx` | `features/assistant/AssistantChat.tsx` | `ia` | Chat écrit & vocal accessible aux 4 rôles |
| 19 | `/fr/irrigation` | `(app)/irrigation/page.tsx` | `features/irrigation/IrrigationView.tsx` | `ia` | Besoin 24 h + Capteur pH & qualité de l'eau + Demande 7 j filtrés par `orgIds` |
| 20 | `/fr/risques` | `(app)/risques/page.tsx` | `features/pest-risk/PestRiskView.tsx` | `ia` | Risques ravageurs filtrés par `orgIds` |
| 21 | `/fr/previsions` | `(app)/previsions/page.tsx` | `features/soil-forecast/SoilForecastView.tsx` | `ia` | Prévisions d'humidité 24/48/72 h filtrées par `orgIds` |
| 22 | `/fr/planning` | `(app)/planning/page.tsx` | `features/irrigation-plan/IrrigationPlanView.tsx` | `ia` | Créneaux d'arrosage par pompe et par exploitation filtrés par `orgIds` |
| 23 | `/fr/equipements` | `(app)/equipements/page.tsx` | `features/equipment/EquipmentView.tsx` | `materiel` | Parc matériel + santé des kits filtrés par `orgIds` |
| 24 | `/fr/kit` | `(app)/kit/page.tsx` | `features/kit/KitView.tsx` | `materiel` | Santé des 6 capteurs + paramètres conseillés filtrés par `orgIds` |
| 25 | `/fr/pieges` | `(app)/pieges/page.tsx` | `features/traps/TrapsView.tsx` | `materiel` | Comptages des pièges englués filtrés par `orgIds` |

---

## 2. Inventaire de toutes les Routes (BFF Next.js & API FastAPI `/v1`)

### 2.1 Routes BFF Next.js (`plateforme/web/app/api/`)

| Méthode & Route BFF | Fichier | Rôle & Sécurité |
|---|---|---|
| `POST /api/auth/login` | `app/api/auth/login/route.ts` | Authentifie via `/v1/auth/token`, pose les cookies `httpOnly` `sa_at` et `sa_rt`, vérifie CSRF (`X-Requested-With`) |
| `POST /api/auth/logout` | `app/api/auth/logout/route.ts` | Révoque le jeton via `/v1/auth/logout` et efface les cookies `sa_at` / `sa_rt` |
| `POST /api/auth/refresh` | `app/api/auth/refresh/route.ts` | Rotation du refresh token via `/v1/auth/refresh` |
| `GET, POST /api/dev/mock` | `app/api/dev/mock/route.ts` | Inspection et changement des scénarios de simulation (`AGRI_MOCK=1` uniquement, `404` sinon) |
| `GET /api/health` | `app/api/health/route.ts` | Sonde de santé du serveur Frontend (`200 OK`) |
| `ALL /api/v1/[...path]` | `app/api/v1/[...path]/route.ts` | Proxy BFF vers FastAPI ou `mocks/` selon [lib/service-mode.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/service-mode.ts). Bloque `/v1/auth/*` et `/v1/telemetry/*` |

### 2.2 Routes API Métier & IA (`/v1/...`) et Matrice d'Autorisation Backend

Source : [plateforme/backend/app/core/constants.py](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/backend/app/core/constants.py) et routeurs `plateforme/backend/app/api/v1/*.py`.

| Domaine / Service | Méthode & Route `/v1/...` | `AGRICULTEUR` (`farmer`) | `COOP_MANAGER` (`coop_manager`) | `AGRONOME` (`agronomist`) | `ADMIN` (`admin`) | Constante Backend / Règle |
|---|---|:---:|:---:|:---:|:---:|---|
| **Session** | `GET /v1/me` | ✅ | ✅ | ✅ | ✅ | Tout utilisateur authentifié |
| **Exploitations** | `GET /v1/farms` | ✅ *(sa ferme)* | ✅ *(sa coop)* | ✅ *(sa coop)* | ✅ *(toutes)* | Scope `principal.org_ids` (RLS) |
| **Exploitations** | `POST /v1/farms` | ✅ | ✅ | ❌ (`403`) | ✅ | `FARM_WRITERS` *(Non exposé dans l'UI Web)* |
| **Carte** | `GET /v1/farms/{farm_id}/map` | ✅ | ✅ | ✅ | ✅ | Service `#18 map_layers` |
| **Planning eau** | `GET /v1/farms/{farm_id}/irrigation-plan` | ✅ | ✅ | ✅ | ✅ | Service `#4 irrigation_plan` |
| **Parcelles** | `GET /v1/farms/{farm_id}/fields` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Parcelles** | `POST /v1/farms/{farm_id}/fields` | ✅ | ✅ | ❌ (`403`) | ✅ | `FARM_WRITERS` *(Non exposé dans l'UI Web)* |
| **Parcelle** | `GET /v1/fields/{field_id}` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Météo** | `GET /v1/fields/{field_id}/weather` | ✅ | ✅ | ✅ | ✅ | Service `#1 weather` |
| **Prévision sol** | `GET /v1/fields/{field_id}/soil-forecast` | ✅ | ✅ | ✅ | ✅ | Service `#2 soil_forecast` |
| **Irrigation 24h** | `GET /v1/fields/{field_id}/irrigation-need` | ✅ | ✅ | ✅ | ✅ | Service `#3 irrigation_need` |
| **Conseils IA** | `GET /v1/fields/{field_id}/recommendations` | ✅ | ✅ | ✅ | ✅ | Service `#5 recommendations` |
| **Feedback IA** | `POST /v1/recommendations/{id}/feedback` | ✅ | ✅ | ❌ (`403`) | ✅ | `FEEDBACK_WRITERS` + `canGiveFeedback()` |
| **Fertilisation** | `GET /v1/fields/{field_id}/fertilization` | ✅ | ✅ | ✅ | ✅ | Service `#6 fertilization` |
| **Risques ravageurs** | `GET /v1/fields/{field_id}/pest-risk` | ✅ | ✅ | ✅ | ✅ | Service `#9 pest_risk` |
| **Végétation NDVI** | `GET /v1/fields/{field_id}/vegetation` | ✅ | ✅ | ✅ | ✅ | Service `#11 vegetation` |
| **Rendement** | `GET /v1/fields/{field_id}/yield-forecast` | ✅ | ✅ | ✅ | ✅ | Service `#12 yield_forecast` |
| **Cycles cultures** | `GET /v1/fields/{field_id}/crop-cycles` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Cycles cultures** | `POST, PATCH /v1/fields/{id}/crop-cycles` | ✅ | ✅ | ✅ | ✅ | `CROP_CYCLE_WRITERS` *(Non exposé dans l'UI Web)* |
| **Kits IoT** | `GET /v1/devices`, `GET /v1/devices/{id}` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Kits IoT** | `POST, PATCH /v1/devices` | ❌ (`403`) | ✅ | ❌ (`403`) | ✅ | `DEVICE_WRITERS` *(Non exposé dans l'UI Web)* |
| **Mesures** | `GET /v1/devices/{id}/measurements` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Seuils kit** | `GET /v1/devices/{id}/thresholds` | ✅ | ✅ | ✅ | ✅ | Service `#7 kit_parameters` |
| **Seuils kit** | `PUT /v1/devices/{id}/thresholds` | ✅ | ✅ | ❌ (`403`) | ✅ | `THRESHOLD_WRITERS` + `canEditThresholds()` |
| **Paramètres kit** | `GET /v1/devices/{id}/parameters` | ✅ | ✅ | ✅ | ✅ | Service `#7 kit_parameters` |
| **Santé du kit** | `GET /v1/devices/{id}/health` | ✅ | ✅ | ✅ | ✅ | Service `#13 device_health` |
| **Pièges insectes** | `GET /v1/devices/{id}/trap-counts` | ✅ | ✅ | ✅ | ✅ | Service `#10 trap_counts` |
| **Alertes** | `GET /v1/alerts` | ✅ | ✅ | ✅ | ✅ | Service `#13 device_health` |
| **Acquitter alerte** | `POST /v1/alerts/{id}/ack` | ✅ | ✅ | ✅ | ✅ | `ALERT_ACKERS` + `canAckAlerts()` |
| **Maladies photo** | `POST /v1/diagnoses/analyze`, `POST /v1/diagnoses` | ✅ | ✅ | ✅ | ✅ | Service `#8 disease_diagnosis` (`DIAGNOSIS_WRITERS`) |
| **Campagnes** | `GET /v1/campaigns` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Campagnes** | `POST, PATCH /v1/campaigns` | ❌ (`403`) | ✅ | ❌ (`403`) | ✅ | `CAMPAIGN_WRITERS` *(Non exposé dans l'UI Web)* |
| **Équipements** | `GET /v1/equipment` | ✅ | ✅ | ✅ | ✅ | Scope `principal.org_ids` |
| **Équipements** | `POST, PATCH /v1/equipment` | ✅ | ✅ | ❌ (`403`) | ✅ | `EQUIPMENT_WRITERS` *(Non exposé dans l'UI Web)* |
| **Rapports KPIs** | `GET /v1/reports/kpis`, `GET /v1/reports/export.csv` | ✅ | ✅ | ✅ | ✅ | Service `#14 water_savings` |
| **Marchés** | `GET /v1/markets/prices` | ✅ | ✅ | ✅ | ✅ | Service `#15 price_forecast` |
| **Assistant IA** | `POST /v1/assistant/chat`, `POST /v1/assistant/transcribe` | ✅ | ✅ | ✅ | ✅ | Services `#16` & `#17` |

---

## 3. Inventaire de tous les Menus

### 3.1 Barre latérale Bureau & Tiroir Mobile ([components/Sidebar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Sidebar.tsx))
Actuellement organisée en **5 groupes statiques**, affichant **24 entrées** à tous les rôles sans distinction :
1. **PILOTAGE (`pilotage`)** :
   - `Alertes` (`/alertes`)
   - `Communauté` (`/communaute`)
   - `Tableau de bord` (`/tableau`)
   - `Rapports` (`/rapports`)
2. **TERRAIN (`terrain`)** :
   - `Exploitations` (`/exploitations`)
   - `Parcelles` (`/parcelles`)
   - `Carte` (`/carte`)
   - `Météo` (`/meteo`)
3. **CULTURES (`cultures`)** :
   - `Cultures` (`/cultures`)
   - `Campagnes` (`/campagnes`)
   - `Rendement` (`/rendement`)
   - `Fertilisation` (`/fertilisation`)
   - `Végétation` (`/vegetation`)
   - `Prix du marché` (`/marches`)
4. **IA (`ia`)** :
   - `Recommandations` (`/recommandations`)
   - `Maladies` (`/maladies`)
   - `Assistant IA` (`/assistant`)
   - `Irrigation` (`/irrigation`)
   - `Risques phytosanitaires` (`/risques`)
   - `Humidité prévue` (`/previsions`)
   - `Planning d’arrosage` (`/planning`)
5. **MATÉRIEL (`materiel`)** :
   - `Équipements` (`/equipements`)
   - `Paramètres du kit` (`/kit`)
   - `Pièges à insectes` (`/pieges`)

### 3.2 Barre inférieure Mobile ([components/BottomBar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/BottomBar.tsx))
4 onglets fixes (`MOBILE_TABS` dans [lib/modules.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/modules.ts)) + bouton `Menu` :
1. `Accueil` (`/tableau`)
2. `Carte` (`/carte`)
3. `Alertes` (`/alertes`)
4. `Assistant` (`/assistant`)
5. `Menu` (ouvre le `<dialog>` contenant `Sidebar`)

### 3.3 Barre supérieure ([components/AppShell.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/AppShell.tsx))
- Badge de rôle : `Connecté : Agriculteur | Gestionnaire de coopérative | Agronome | Administrateur` (via `displayRole(me.data)`).
- Bascule de thème clair/sombre (`ThemeToggle`).
- Sélecteur de langue `Français / Wolof / Pulaar` (`LocaleSwitcher`).
- Bouton `Se déconnecter`.

---

## 4. Inventaire des Permissions (`lib/roles.ts` vs `backend/app/core/constants.py`)

### 4.1 Ce qui est implémenté dans [plateforme/web/lib/roles.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/roles.ts)
Seulement **3 prédicats d'écriture** et **1 sélecteur d'affichage** existent côté Frontend :
1. `canEditThresholds(me, organizationId)` → `farmer`, `coop_manager`, `admin` (masque le formulaire `PUT /v1/devices/{id}/thresholds` dans [ThresholdForm.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/fields/ThresholdForm.tsx) pour l'**Agronome**).
2. `canGiveFeedback(me, organizationId)` → `farmer`, `coop_manager`, `admin` (masque les boutons *Suivi / Partiellement suivi / Ignoré / Non applicable* dans [RecommendationsList.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/recommendations/RecommendationsList.tsx) pour l'**Agronome**).
3. `canAckAlerts(me, organizationId)` → `farmer`, `coop_manager`, `agronomist`, `admin` (utilisé dans [AlertsLog.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/alerts/AlertsLog.tsx)).
4. `displayRole(me)` → renvoie `me?.memberships[0]?.role ?? null` (utilisé uniquement pour afficher le badge texte dans l'en-tête de `AppShell.tsx`).

### 4.2 Écarts constatés entre les rôles métier et l'interface actuelle
1. **Le Tableau de bord (`Dashboard.tsx`) est 100 % identique dans sa structure pour les 4 rôles** :
   - Un **Agriculteur** voit des widgets de gestion multi-exploitations ou des paramètres d'étalonnage ADC (`adc_sec` / `adc_eau`) qui relèvent du support technique.
   - Un **Gestionnaire de coopérative** n'a pas de vue consolidée multi-exploitations (comparaison Mboro vs Potou, répartition de l'eau entre membres, suivi des campagnes et stocks/marchés de la coopérative).
   - Un **Agronome** n'a pas de cockpit de diagnostic agronomique priorisé (stress hydrique multi-parcelles, anomalies NDVI, alertes maladies/pièges à insectes, qualité pH/salinité de l'eau, taux de suivi des recommandations).
   - Un **Administrateur** n'a pas de vue de supervision système & flotte IoT (état des organisations `ORG_A` + `ORG_B`, santé de tous les kits ESP32-S3, versions firmware, disponibilité télémétrique, étalonnage ADC, audit des alertes critiques).
2. **Aucun filtrage des menus ni des routes par rôle** :
   - Les 24 entrées de `Sidebar.tsx` sont toutes affichées à l'Agriculteur, ce qui alourdit la navigation sur smartphone (ex. `/rapports` d'organisation, `/kit` étalonnage ADC, `/campagnes` administratives).

---

## 5. Proposition des 4 Dashboards et Périmètres par Rôle

### 5.1 Rôle 1 — `AGRICULTEUR` (`farmer`)
**Objectif métier** : *« Que dois-je faire aujourd'hui sur mes parcelles ? Faut-il arroser, ma pompe marche-t-elle, quel est le risque météo/maladie et à quel prix vendre ma récolte ? »*

- **Routes autorisées (16 routes opérationnelles terrain)** :
  - `/tableau`, `/parcelles`, `/parcelles/[id]`, `/irrigation`, `/meteo`, `/recommandations`, `/maladies`, `/assistant`, `/alertes`, `/communaute`, `/marches`, `/cultures`, `/fertilisation`, `/risques`, `/planning`, `/carte` (centrée par défaut sur son périmètre).
- **Routes & menus à masquer pour `AGRICULTEUR`** :
  - `/exploitations` *(inutile quand l'agriculteur n'a qu'une seule exploitation ; ses parcelles suffisent)*
  - `/kit` *(paramètres bas niveau d'étalonnage ADC `adc_sec` / `adc_eau` réservés aux techniciens/admin ; l'agriculteur règle déjà ses seuils `start/stop %` sur `/parcelles/[id]`)*
  - `/rapports` *(rapports KPI d'organisation / export CSV comptable réservés à la coopérative et à l'admin)*
  - `/vegetation` *(séries brutes NDVI/EVI satellite : trop théorique, déjà résumé dans ses recommandations)*
- **Menus visibles (`Sidebar`)** :
  - **Mon Quotidien** : `Tableau de bord`, `Mes Parcelles`, `Irrigation & pH eau`, `Météo`, `Planning d'arrosage`
  - **Conseils & Santé** : `Recommandations IA`, `Diagnostic Maladies (photo)`, `Risques ravageurs`, `Assistant vocal IA`
  - **Entraide & Vente** : `Communauté (vocaux)`, `Prix du marché`, `Mes Cultures`, `Fertilisation`, `Alertes`, `Carte`
- **KPIs visibles sur le Dashboard Agriculteur (4 KPIs simples)** :
  1. **Parcelles à arroser aujourd'hui** (`counts.dry` + volume en `m³` / heures de pompage)
  2. **État Pompe & Eau** (`Pompe en marche / à l'arrêt` + `pH de l'eau`)
  3. **Météo & Pluie 24 h** (`Temp. max/min °C` + `Pluie attendue mm`)
  4. **Cours du jour (FCFA/kg)** (prix de sa culture active au marché le plus proche)
- **Widgets visibles sur le Dashboard Agriculteur** :
  1. **Bandeau d'action du jour (Synthèse IA + Bouton Vocal)** : *« Arroser Ndiol 1 (5,5 mm · 55 m³) ce matin avant 10 h »*.
  2. **Cartes « Mes Parcelles en direct » (`FieldLiveCard`)** : humidité du sol `%`, air `°C / %`, pompe `ON/OFF`, `pH eau`, seuils démarrage/arrêt et bouton *Irrigation*.
  3. **Météo 3 jours de la parcelle** (`WeatherPanel`).
  4. **Dernières alertes de la Communauté (Maladies, Insectes, Oiseaux)** avec lecture vocale en 1 clic.

---

### 5.2 Rôle 2 — `COOPERATIVE_MANAGER` (`coop_manager`)
**Objectif métier** : *« Comment se portent les périmètres de la coopérative (Mboro, Potou) ? Quelle est la consommation d'eau totale, l'état du parc de pompes solaires, l'avancement de la campagne et les cours de vente groupée ? »*

- **Routes autorisées (22 routes de gestion collective)** :
  - `/tableau`, `/exploitations`, `/parcelles`, `/parcelles/[id]`, `/carte` (vue nationale & périmètres coopérative), `/campagnes`, `/cultures`, `/rendement`, `/marches`, `/rapports` (avec export CSV), `/planning`, `/irrigation`, `/equipements`, `/alertes`, `/communaute`, `/recommandations`, `/meteo`, `/fertilisation`, `/risques`, `/assistant`.
- **Routes & menus à masquer pour `COOPERATIVE_MANAGER`** :
  - `/kit` *(étalonnage électronique ADC sonde : réservé à l'agronome/admin technique)*
  - `/vegetation` *(analyse fine NDVI/EVI réservée à l'agronome)*
  - `/previsions` *(courbes probabilistes `p10–p90` d'humidité du sol réservées à l'agronome)*
- **Menus visibles (`Sidebar`)** :
  - **Pilotage Coopérative** : `Tableau de bord Coopérative`, `Exploitations & Périmètres`, `Carte du Sénégal & Zones`, `Campagnes agricoles`, `Rapports & Export CSV`
  - **Production & Marchés** : `Parcelles`, `Cultures`, `Prévision de rendement (t/ha)`, `Prix du marché (FCFA/kg)`, `Communauté des producteurs`
  - **Eau & Matériel collectif** : `Planning d'arrosage mutualisé`, `Irrigation & pH`, `Parc Équipements (pompes, bassins, solaire)`, `Alertes`, `Météo`
  - **Assistance** : `Recommandations`, `Assistant IA`
- **KPIs visibles sur le Dashboard Coopérative (6 KPIs de gestion)** :
  1. **Exploitations & Surface active** (`2 périmètres · 3,8 ha`)
  2. **Parcelles en stress hydrique** (`counts.dry` sur l'ensemble de la coopérative)
  3. **Eau consommée & Économisée (30 j)** (`water_m3` m³ + `water_savings.saved_m3` m³ / `%`)
  4. **Parc Matériel (Pompes & Solaire)** (`ok / total` + équipements en maintenance)
  5. **Avancement Campagne active** (`Contre-saison froide : X % · Jours restants`)
  6. **Cours de gros Oignon / Tomate (Dakar & Thiès)** (`FCFA/kg` + tendance à +1/+4 semaines)
- **Widgets visibles sur le Dashboard Coopérative** :
  1. **Tableau comparatif des Périmètres de la Coopérative** (*Périmètre de Mboro* vs *Périmètre de Potou* : surface, humidité moyenne, parcelles sèches, état de la pompe solaire, débit `m³/h`, alertes ouvertes).
  2. **Planning de pompage mutualisé du jour** (créneaux par pompe solaire et volume total `m³`).
  3. **Suivi de Campagne, Rendements attendus & Cours des Marchés** (projection de récolte en tonnes + cours FCFA/kg).
  4. **État du Parc Matériel & Alertes critiques** (pompes, réservoirs, champs solaires).
  5. **Veille Communautaire de la Coopérative** (annonces et alertes terrain des membres).

---

### 5.3 Rôle 3 — `AGRONOME` (`agronomist`)
**Objectif métier** : *« Quelles parcelles présentent un stress hydrique, une anomalie de vigueur NDVI, une carence NPK, un pH d'eau inadapté ou un risque épidémique (mildiou, thrips, noctuelles), et mes recommandations sont-elles suivies ? »*

- **Routes autorisées (23 routes scientifiques & conseil)** :
  - Toutes les routes d'analyse agronomique, phytosanitaire, pédologique et satellitaire : `/tableau`, `/carte`, `/parcelles`, `/parcelles/[id]` *(lecture seule sur les seuils matériels)*, `/irrigation` *(avec capteur pH/CE)*, `/previsions` *(p10–p90 humidité 24–72 h)*, `/fertilisation` *(NPK)*, `/vegetation` *(NDVI/EVI & stade BBCH)*, `/rendement`, `/cultures`, `/campagnes`, `/risques`, `/maladies`, `/pieges`, `/recommandations` *(mode superviseur : voit les conseils sans les boutons de feedback agriculteur)*, `/meteo`, `/alertes`, `/communaute`, `/assistant`, `/kit` *(lecture de l'étalonnage et du coefficient cultural `Kc`)*.
- **Routes & menus à masquer ou restreindre pour `AGRONOME`** :
  - `/equipements` *(gestion de maintenance mécanique des pompes/réservoirs réservée au gestionnaire de coopérative et à l'admin)*
  - Sur `/parcelles/[id]` : **masquer le formulaire de modification des seuils (`ThresholdForm`)** ➡️ *Déjà implémenté via `canEditThresholds()`*.
  - Sur `/recommandations` : **masquer les boutons de feedback producteur** ➡️ *Déjà implémenté via `canGiveFeedback()`*.
- **Menus visibles (`Sidebar`)** :
  - **Diagnostic & Vigie** : `Tableau de bord Agronome`, `Carte agro-écologique & NDVI`, `Alertes agronomiques`, `Communauté & Signalements terrain`
  - **Eau, Sol & Fertilité** : `Irrigation & Qualité eau (pH / CE)`, `Humidité prévue (24–72 h)`, `Fertilisation & Sondes NPK`, `Météo & ET0 FAO-56`, `Paramètres agro & Kc (/kit)`
  - **Santé Végétale & Ravageurs** : `Risques phytosanitaires`, `Diagnostic Maladies (Vision)`, `Pièges à insectes`, `Végétation satellite (NDVI / EVI)`
  - **Suivi Cultural** : `Parcelles`, `Cycles culturaux & BBCH`, `Prévision de rendement`, `Recommandations IA`, `Assistant agronomique`
- **KPIs visibles sur le Dashboard Agronome (6 KPIs scientifiques)** :
  1. **Indice NDVI moyen & Parcelles en baisse de vigueur** (`NDVI` + delta)
  2. **Déficit hydrique & ET0 FAO-56 du jour** (`ET0 mm` vs `Besoin net mm`)
  3. **Qualité de l'eau & Sol (pH / Salinité / Classe NPK)** (`pH 6,4–7,6` · classe NPK `bas / moyen / élevé`)
  4. **Pression Phytosanitaire & Pièges** (niveau de risque max `Thrips / Mildiou / Noctuelle` + captures pièges/jour)
  5. **Diagnostics Foliaires (Maladies)** (répartition `Sain / Suspect / Malade`)
  6. **Taux d'adoption des Recommandations** (`recommendations_followed_pct %` issu de `/v1/reports/kpis`)
- **Widgets visibles sur le Dashboard Agronome** :
  1. **Matrice de Santé Agronomique des Parcelles** : tableau/cartes croisant pour chaque parcelle `Culture & Stade BBCH`, `Humidité sol %`, `Besoin 24 h (mm)`, `NDVI`, `N-P-K (mg/kg)`, `pH de l'eau` et `Risque ravageur`.
  2. **Vigie Phytosanitaire & Captures des Pièges Chromantiques** (alertes maladies, insectes, oiseaux + accès direct à `/risques`, `/pieges` et `/maladies`).
  3. **Bilan Hydrique & Qualité de l'Eau par Périmètre** (comparaison pH, conductivité CE `dS/m` et risque d'entartrage Mboro vs Potou vs Ndiol).
  4. **Suivi d'impact des Recommandations IA** (part des conseils suivis, partiellement suivis ou ignorés par les agriculteurs).

---

### 5.4 Rôle 4 — `ADMIN` (`admin`)
**Objectif métier** : *« Toutes les organisations (Coopérative des Niayes, Exploitation de Ndiol), la flotte de kits ESP32-S3, les capteurs, les synchronisations relais et les services IA/Backend fonctionnent-ils nominalement ? »*

- **Routes autorisées (25 / 25 — Accès total)** :
  - Toutes les routes sans aucune restriction, sur l'ensemble des organisations (`ORG_A` + `ORG_B`).
- **Menus visibles (`Sidebar`)** :
  - Tous les groupes (`Pilotage`, `Terrain`, `Cultures`, `IA`, `Matériel`) avec un bandeau/groupe de tête **Supervision & Flotte IoT**.
- **KPIs visibles sur le Dashboard Administrateur (6 KPIs système & multi-organisations)** :
  1. **Organisations & Exploitations supervisées** (`2 organisations · 3 exploitations · 7 parcelles · 5,4 ha`)
  2. **Disponibilité Flotte Kits IoT (`Uptime %`)** (`kit_uptime_pct : 99,2 %` + kits en ligne vs silencieux)
  3. **Volume de Mesures Télémétriques (30 j)** (`measurements` reçues + événements d'irrigation)
  4. **Capteurs en Défaut / Dégradés** (nombre de sondes `soil`, `bme`, `npk`, `flow`, `pump`, `battery` hors état `ok`)
  5. **Synchronisation des Seuils Relais** (kits `applied` vs `pending` / `failed`)
  6. **Alertes Critiques Ouvertes (Multi-Org)** (`critical` + répartition par règle `device_offline`, `pump_fault`, `sensor_fault`, `soil_dry`)
- **Widgets visibles sur le Dashboard Administrateur** :
  1. **Supervision Multi-Organisations & Exploitations** (vue consolidée `Coopérative des Niayes` + `Exploitation de Ndiol` avec statut de chaque site).
  2. **Centre de Contrôle de la Flotte IoT (`5 kits ESP32-S3`) & Santé des 6 Capteurs** : tableau complet de tous les kits (`SA92-0001` à `SA92-0101`), firmware `v1.1.0`, dernier contact, état de synchro des seuils, et état des 6 organes matériels.
  3. **Journal des Alertes Système & Matériel par Règle** (`alerts_by_rule` : `device_offline`, `pump_fault`, `sensor_fault`, `soil_dry`, `fertilizer_low`).
  4. **Provenance & État des Services IA / Moteurs de Règles** (fraîcheur des calculs, sources `rules` / `agriml`, latence et cache météo).

---

## 6. Synthèse des Écarts : Déjà implémenté vs Ce qui manque vs Ce qui doit être masqué

### 6.1 Ce qui est DÉJÀ implémenté ✅
1. **Authentification & Session par rôle** :
   - 4 comptes de démonstration fonctionnels dans [mocks/auth.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/mocks/auth.ts) (`agriculteur@demo.sn`, `cooperative@demo.sn`, `agronome@demo.sn`, `admin@demo.sn`) et support hybride dans [live_stack.py](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/backend/scripts/live_stack.py).
   - Affichage du rôle actif dans l'en-tête ([AppShell.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/AppShell.tsx) via `displayRole()`).
2. **Isolation des données par organisation (Multi-tenancy / RLS)** :
   - `AGRICULTEUR` ne voit que `ORG_B` (`Périmètre de Ndiol`).
   - `COOPERATIVE_MANAGER` et `AGRONOME` ne voient que `ORG_A` (`Périmètre de Mboro` + `Périmètre de Potou`).
   - `ADMIN` voit `ORG_A` + `ORG_B`.
3. **Contrôle des actions mutantes sur 3 écrans** ([lib/roles.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/roles.ts)) :
   - `canEditThresholds()` masque l'édition des seuils pour `AGRONOME` sur `/parcelles/[id]`.
   - `canGiveFeedback()` masque les boutons de feedback pour `AGRONOME` sur `/recommandations`.
   - `canAckAlerts()` autorise l'acquittement des alertes sur `/alertes`.

### 6.2 Ce qui MANQUE à développer ❌
1. **Table de permissions de navigation par rôle dans [lib/roles.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/roles.ts)** :
   - Ajouter `canAccessRoute(role: Role | null, slug: string): boolean` et `visibleNavItems(role: Role | null)` pour filtrer dynamiquement la barre latérale ([Sidebar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Sidebar.tsx)) et la barre mobile ([BottomBar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/BottomBar.tsx)).
2. **Protection des routes non autorisées au rôle** :
   - Afficher un bandeau ou rediriger proprement vers `/tableau` si un rôle tente d'ouvrir manuellement une route hors de son périmètre fonctionnel (ex. `AGRICULTEUR` sur `/kit` ou `/rapports`).
3. **4 variantes spécialisées du Dashboard dans [features/dashboard/Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx)** :
   - `FarmerDashboard` (orienté action du jour, arrosage, pompe, pH eau, météo, prix du marché, communauté vocale).
   - `CoopManagerDashboard` (orienté comparaison des périmètres Mboro/Potou, économie d'eau, planning de pompage mutualisé, parc équipements, campagne et marchés).
   - `AgronomistDashboard` (orienté matrice agronomique NDVI/NPK/pH/ET0, vigie phytosanitaire & pièges, diagnostics maladies et taux de suivi des conseils).
   - `AdminDashboard` (orienté supervision multi-organisations, santé complète de la flotte des 5 kits ESP32-S3, synchro relais, répartition des alertes par règle et provenance des services).

### 6.3 Récapitulatif de ce qui doit être MASQUÉ par rôle 🔒

| Élément / Route / Action | `AGRICULTEUR` (`farmer`) | `COOP_MANAGER` (`coop_manager`) | `AGRONOME` (`agronomist`) | `ADMIN` (`admin`) |
|---|:---:|:---:|:---:|:---:|
| Menu & Page `/exploitations` | 🔒 **Masqué** *(1 seule ferme)* | ✅ Visible | ✅ Visible | ✅ Visible |
| Menu & Page `/rapports` (KPI Org & CSV) | 🔒 **Masqué** | ✅ Visible | ✅ Visible | ✅ Visible |
| Menu & Page `/kit` (Étalonnage ADC & Kc) | 🔒 **Masqué** | 🔒 **Masqué** | ✅ Visible *(lecture)* | ✅ Visible |
| Menu & Page `/vegetation` (Séries NDVI/EVI) | 🔒 **Masqué** | 🔒 **Masqué** | ✅ Visible | ✅ Visible |
| Menu & Page `/previsions` (Courbes p10–p90) | 🔒 **Masqué** | 🔒 **Masqué** | ✅ Visible | ✅ Visible |
| Menu & Page `/equipements` (Parc mécanique) | 🔒 **Masqué** | ✅ Visible | 🔒 **Masqué** | ✅ Visible |
| Formulaire `ThresholdForm` (`PUT /thresholds`) | ✅ Visible | ✅ Visible | 🔒 **Masqué** *(Déjà fait)* | ✅ Visible |
| Boutons Feedback IA (`POST /feedback`) | ✅ Visible | ✅ Visible | 🔒 **Masqué** *(Déjà fait)* | ✅ Visible |
| Sélecteur multi-organisations / Vue Flotte globale | 🔒 **Masqué** | 🔒 **Masqué** | 🔒 **Masqué** | ✅ Visible |
