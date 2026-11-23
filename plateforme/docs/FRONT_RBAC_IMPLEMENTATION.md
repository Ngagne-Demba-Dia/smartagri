# MISSION FRONT-RBAC-02 — Rapport d'Implémentation du RBAC Frontend

**Date** : 22 novembre 2026  
**Périmètre** : `plateforme/web` — Spécialisation des 4 Dashboards par rôle (`FarmerDashboard`, `CoopManagerDashboard`, `AgronomistDashboard`, `AdminDashboard`) + Filtrage des menus et routes (`visibleNavItems()`, `canAccessRoute()`)  
**Statut** : ✅ **IMPLÉMENTÉ & VALIDÉ (`0` nouveau service, `0` modification d'API/contrats, `31/31` suites Vitest passées)**

---

## 1. Architecture RBAC implémentée

### 1.1 Primitives de permissions ([plateforme/web/lib/roles.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/lib/roles.ts))
- **`HIDDEN_ROUTES_BY_ROLE`** : table déclarative des routes masquées par rôle conformément à [ROLE_BASED_ACCESS_AUDIT.md](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/docs/ROLE_BASED_ACCESS_AUDIT.md) :
  - `farmer` (`AGRICULTEUR`) : masque `exploitations`, `rapports`, `kit`, `vegetation`, `previsions`, `equipements`.
  - `coop_manager` (`COOPERATIVE_MANAGER`) : masque `kit`, `vegetation`, `previsions`.
  - `agronomist` (`AGRONOME`) : masque `equipements`.
  - `admin` (`ADMIN`) : aucune route masquée (`0`).
- **`canAccessRoute(role, slugOrPath)`** : vérifie si un rôle est autorisé à voir un module ou écran donné (supporte aussi bien un slug `"rapports"` qu'un chemin localisé `"/fr/rapports"`).
- **`visibleNavItems(role)`** : filtre dynamiquement les 5 groupes de navigation (`pilotage`, `terrain`, `cultures`, `ia`, `materiel`), les entrées complémentaires (`alertes`, `communaute`), les 13 modules (`MODULES`) et les 9 écrans de service (`SERVICE_SCREENS`).
- **Permissions d'actions mutantes conservées** :
  - `canEditThresholds(me, organizationId)` (`farmer`, `coop_manager`, `admin`)
  - `canGiveFeedback(me, organizationId)` (`farmer`, `coop_manager`, `admin`)
  - `canAckAlerts(me, organizationId)` (`farmer`, `coop_manager`, `agronomist`, `admin`)

### 1.2 Filtrage dynamique du Menu ([plateforme/web/components/Sidebar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Sidebar.tsx))
- `Sidebar.tsx` lit le profil courant via `useMe()`, détermine le rôle via `displayRole(me.data)` et appelle `visibleNavItems(role)` pour n'afficher que les entrées pertinentes pour le rôle connecté (sur Bureau comme dans le tiroir `<dialog>` Mobile).

---

## 2. Synthèse par Rôle : Routes visibles, Menus visibles, Dashboard visible & Permissions finales

### 2.1 `AGRICULTEUR` (`farmer` — `agriculteur@demo.sn`)
- **Routes & Menus visibles (18 entrées)** :
  - **Pilotage** : `Alertes` (`/alertes`), `Communauté` (`/communaute`), `Tableau de bord` (`/tableau`)
  - **Terrain** : `Parcelles` (`/parcelles`, `/parcelles/[id]`), `Carte` (`/carte`), `Météo` (`/meteo`)
  - **Cultures** : `Cultures` (`/cultures`), `Campagnes` (`/campagnes`), `Rendement` (`/rendement`), `Fertilisation` (`/fertilisation`), `Prix du marché` (`/marches`)
  - **IA** : `Recommandations` (`/recommandations`), `Maladies` (`/maladies`), `Assistant IA` (`/assistant`), `Irrigation` (`/irrigation`), `Risques phytosanitaires` (`/risques`), `Planning d'arrosage` (`/planning`)
  - **Matériel** : `Pièges à insectes` (`/pieges`)
- **Menus masqués (6)** : `/exploitations`, `/rapports`, `/kit`, `/vegetation`, `/previsions`, `/equipements`.
- **Dashboard visible (`FarmerDashboard` dans [Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx))** :
  - Badge d'en-tête : *« Espace Agriculteur · Pilotage terrain quotidien »*
  - **KPIs** : *Parcelles sèches*, *Besoin d’eau 24 h (mm)*, *Qualité eau d’arrosage (pH)*, *Cours Oignon Dakar (FCFA/kg)*.
  - **Widgets** :
    1. *Mon plan d’action du jour* (dose 24 h `mm` & `m³`, pluie attendue, accès direct *Pilotage irrigation* & *Planning d’arrosage*).
    2. *Conseils & alertes de ma parcelle* (recommandations IA en direct + raccourcis *Conseil IA* & *Cours des marchés*).
    3. *Communauté & alertes vocales entre agriculteurs* (maladies, insectes, oiseaux).
    4. *Grille de mes parcelles (`FieldLiveCard`)* avec télémétrie capteurs et pH de l'eau.
- **Permissions finales** :
  - Périmètre données : `ORG_B` (*Périmètre de Ndiol*).
  - Modification des seuils d'arrosage (`ThresholdForm`) : ✅ Autorisé.
  - Retour sur les recommandations IA (`canGiveFeedback`) : ✅ Autorisé.
  - Acquittement des alertes (`canAckAlerts`) : ✅ Autorisé.

---

### 2.2 `COOPERATIVE_MANAGER` (`coop_manager` — `cooperative@demo.sn`)
- **Routes & Menus visibles (21 entrées)** :
  - **Pilotage** : `Alertes` (`/alertes`), `Communauté` (`/communaute`), `Tableau de bord` (`/tableau`), `Rapports` (`/rapports`)
  - **Terrain** : `Exploitations` (`/exploitations`), `Parcelles` (`/parcelles`, `/parcelles/[id]`), `Carte` (`/carte`), `Météo` (`/meteo`)
  - **Cultures** : `Cultures` (`/cultures`), `Campagnes` (`/campagnes`), `Rendement` (`/rendement`), `Fertilisation` (`/fertilisation`), `Prix du marché` (`/marches`)
  - **IA** : `Recommandations` (`/recommandations`), `Maladies` (`/maladies`), `Assistant IA` (`/assistant`), `Irrigation` (`/irrigation`), `Risques phytosanitaires` (`/risques`), `Planning d'arrosage` (`/planning`)
  - **Matériel** : `Équipements` (`/equipements`), `Pièges à insectes` (`/pieges`)
- **Menus masqués (3)** : `/kit`, `/vegetation`, `/previsions`.
- **Dashboard visible (`CoopManagerDashboard` dans [Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx))** :
  - Badge d'en-tête : *« Espace Coopérative · Gestion mutualisée, eau & marchés »*
  - **6 KPIs** : *Surface exploitée (`ha`)*, *Parcelles sèches*, *Eau économisée 30 j (`m³`)*, *Parc matériel en service (`OK / total`)*, *Campagne active (`%`)*, *Cours Oignon Dakar (`FCFA/kg`)*.
  - **Widgets** :
    1. *Périmètres de la coopérative* (comparatif *Périmètre de Mboro* vs *Périmètre de Potou* : nombre de parcelles, parcelles à arroser, pH de l'eau).
    2. *Campagne, eau & marché* (économie d'eau 30 j, disponibilité des kits & heures de pompage, prix observé et prévu à +1 sem., liens *Planning*, *Rapports*, *Marchés*).
    3. *Parc matériel & flotte des kits (`HardwareSection`)* (pompes solaires avec débit `m³/h`, réservoirs, panneaux solaires, capteurs).
    4. *Communauté & Parcelles de la coopérative (`FieldLiveCard`)*.
- **Permissions finales** :
  - Périmètre données : `ORG_A` (*Coopérative des Niayes : Mboro & Potou*).
  - Modification des seuils d'arrosage : ✅ Autorisé.
  - Retour sur les recommandations IA : ✅ Autorisé.
  - Acquittement des alertes : ✅ Autorisé.
  - Export CSV des rapports KPI : ✅ Autorisé.

---

### 2.3 `AGRONOME` (`agronomist` — `agronome@demo.sn`)
- **Routes & Menus visibles (23 entrées)** :
  - **Pilotage** : `Alertes` (`/alertes`), `Communauté` (`/communaute`), `Tableau de bord` (`/tableau`), `Rapports` (`/rapports`)
  - **Terrain** : `Exploitations` (`/exploitations`), `Parcelles` (`/parcelles`, `/parcelles/[id]`), `Carte` (`/carte`), `Météo` (`/meteo`)
  - **Cultures** : `Cultures` (`/cultures`), `Campagnes` (`/campagnes`), `Rendement` (`/rendement`), `Fertilisation` (`/fertilisation`), `Végétation` (`/vegetation`), `Prix du marché` (`/marches`)
  - **IA** : `Recommandations` (`/recommandations`), `Maladies` (`/maladies`), `Assistant IA` (`/assistant`), `Irrigation` (`/irrigation`), `Risques phytosanitaires` (`/risques`), `Humidité prévue` (`/previsions`), `Planning d'arrosage` (`/planning`)
  - **Matériel** : `Paramètres du kit` (`/kit`), `Pièges à insectes` (`/pieges`)
- **Menu masqué (1)** : `/equipements` *(maintenance mécanique)*.
- **Dashboard visible (`AgronomistDashboard` dans [Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx))** :
  - Badge d'en-tête : *« Cockpit Agronome · Vigie phytosanitaire, NDVI, NPK & eau »*
  - **KPIs** : *Parcelles suivies*, *Parcelles sèches*, *Adoption des conseils IA (`%`)*, *Diagnostics foliaires (30 j)*.
  - **Widgets** :
    1. *Matrice de diagnostic agronomique par parcelle* : tableau croisant pour chaque parcelle `Parcelle & culture`, `Humidité & verdict`, `Eau (pH / Salinité CE en dS/m)` et boutons d'analyse directe (`NPK`, `Phyto`, `Fertilisation NPK`, `Végétation NDVI`, `Prévision sol 72 h`).
    2. *Santé des 6 capteurs & flotte des kits (`HardwareSection` sans maintenance mécanique)*.
    3. *Veille communautaire & Parcelles (`FieldLiveCard`)*.
- **Permissions finales** :
  - Périmètre données : `ORG_A` (*Coopérative des Niayes*).
  - Modification des seuils matériels (`ThresholdForm`) : 🔒 **Masqué & refusé (`canEditThresholds = false`)**.
  - Boutons de feedback agriculteur (`RecommendationsList`) : 🔒 **Masqué & refusé (`canGiveFeedback = false`)**.
  - Acquittement des alertes (`canAckAlerts`) : ✅ Autorisé.

---

### 2.4 `ADMIN` (`admin` — `admin@demo.sn`)
- **Routes & Menus visibles (24 / 24 entrées — Accès complet)** :
  - Tous les menus et toutes les routes sans restriction.
- **Dashboard visible (`AdminDashboard` dans [Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx))** :
  - Badge d'en-tête : *« Supervision Administrateur · Multi-organisations & Flotte IoT »*
  - **KPIs** : *Exploitations supervisées (Multi-Org)*, *Disponibilité flotte kits (`Uptime %`)*, *Mesures reçues (30 j)*, plus les 4 KPIs globaux du bandeau (*Parcelles suivies*, *Parcelles sèches*, *Kits silencieux*, *Alertes ouvertes*).
  - **Widgets** :
    1. *Supervision multi-organisations & règles d'alertes* : état consolidé des 3 périmètres (*Mboro*, *Potou*, *Ndiol*) + répartition des alertes par règle (`soil_dry`, `device_offline`, `pump_fault`, `sensor_fault`, `fertilizer_low`).
    2. *Centre de contrôle matériel & flotte des 5 kits ESP32-S3 (`HardwareSection` complète)*.
    3. *Communauté, Grille complète des 7 parcelles (`FieldLiveCard`) & Sources de provenance multi-exploitations*.
- **Permissions finales** :
  - Périmètre données : **Toutes les organisations (`ORG_A` + `ORG_B`)**.
  - Toutes les actions (`canEditThresholds`, `canGiveFeedback`, `canAckAlerts`) : ✅ Autorisées.
