# MISSION FRONT-RBAC-03 — Validation Fonctionnelle & Visuelle Réelle des 4 Rôles

**Date** : 22 novembre 2026  
**Outil d'exécution** : Playwright E2E (`chromium` Desktop `1280×800` & Mobile `375×800`) sur build de production Next.js (`E2E_PROD=1`)  
**Suite automatisée** : [rbac-validation.spec.ts](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/e2e/rbac-validation.spec.ts) (`4/4` tests passés en `1.2 min`, `0` erreur console, `0 px` de débordement horizontal mobile)  
**Dossier des preuves visuelles & JSON** : `plateforme/web/audit-shots/rbac/`

---

## 1. Synthèse Exécutive de la Validation

| Compte testé | Rôle affiché (En-tête) | Entrées Sidebar (Desktop & Mobile) | Dashboard dédié vérifié | Routes interdites testées en URL directe (`page.goto`) | Débordement Mobile (`375×800`) | Statut |
|---|---|:---:|---|---|:---:|:---:|
| **`agriculteur@demo.sn`** | `Rôle : Agriculteur` | **18 / 24** | `FarmerDashboard` (*Espace Agriculteur · Pilotage terrain quotidien*) | **6 / 6 bloquées** (`/fr/exploitations`, `/fr/rapports`, `/fr/kit`, `/fr/vegetation`, `/fr/previsions`, `/fr/equipements`) | `0 px` | ✅ **PASS** |
| **`cooperative@demo.sn`** | `Rôle : Gestionnaire de coopérative` | **21 / 24** | `CoopManagerDashboard` (*Espace Coopérative · Gestion mutualisée, eau & marchés*) | **3 / 3 bloquées** (`/fr/kit`, `/fr/vegetation`, `/fr/previsions`) | `0 px` | ✅ **PASS** |
| **`agronome@demo.sn`** | `Rôle : Agronome` | **23 / 24** | `AgronomistDashboard` (*Cockpit Agronome · Vigie phytosanitaire, NDVI, NPK & eau*) | **1 / 1 bloquée** (`/fr/equipements`) + lecture seule sur seuils & feedback | `0 px` | ✅ **PASS** |
| **`admin@demo.sn`** | `Rôle : Administrateur` | **24 / 24** | `AdminDashboard` (*Supervision Administrateur · Multi-organisations & Flotte IoT*) | **0 bloquée** (`24/24` écrans accessibles sur `ORG_A` + `ORG_B`) | `0 px` | ✅ **PASS** |

### Confirmations clés exigées par la mission
1. **Les dashboards sont réellement différents** : chaque rôle affiche son propre badge d'en-tête (`eyebrow`), ses propres KPIs et ses propres cartes métier (`FarmerDashboard`, `CoopManagerDashboard`, `AgronomistDashboard`, `AdminDashboard` dans [Dashboard.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/features/dashboard/Dashboard.tsx)). Le test E2E vérifie à la fois la présence des widgets du rôle actif et l'**absence stricte (`count === 0`)** des widgets des 3 autres rôles.
2. **Les menus sont réellement différents** : la barre latérale Desktop (`aside nav`) et le tiroir `<dialog>` Mobile affichent exactement **18 liens** pour l'Agriculteur, **21 liens** pour le Gestionnaire de coopérative, **23 liens** pour l'Agronome et **24 liens** pour l'Administrateur ([Sidebar.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/Sidebar.tsx) via `visibleNavItems(role)`).
3. **Les routes interdites sont bloquées en accès URL direct** : toute tentative d'ouverture directe (`page.goto("/fr/<route>")`) d'une route non autorisée est interceptée par la garde RBAC de [AppShell.tsx](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/components/AppShell.tsx), qui bloque le rendu de l'écran enfant et affiche le panneau `data-testid="rbac-forbidden"` (*« Contrôle d’accès par rôle (RBAC) — Accès réservé à un autre profil »*) avec bouton de retour vers `/fr/tableau`.
4. **Aucune route ni action sensible n'apparaît au mauvais rôle** :
   - L'**Agriculteur** (`ORG_B` — Ndiol) ne voit aucune route d'administration ou d'étalonnage (`/kit`, `/rapports`, `/exploitations`, `/equipements`, `/vegetation`, `/previsions`), et un accès direct à une parcelle d'une autre organisation (`/fr/parcelles/fld-mboro-1`) ne divulgue aucune donnée ni formulaire.
   - L'**Agronome** (`ORG_A` — Mboro & Potou) est bloqué sur `/fr/equipements`, n'a pas accès au formulaire de modification des seuils (`ThresholdForm` masqué sur `/fr/parcelles/fld-mboro-1`) et n'a pas accès aux boutons de feedback agriculteur sur `/fr/recommandations`.

---

## 2. Validation Détaillée Compte par Compte

### 2.1 Compte 1 — `agriculteur@demo.sn` (`AGRICULTEUR` / `farmer`)

- **Preuves générées** :
  - Rapport JSON : [farmer-report.json](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-report.json)
  - Capture Dashboard Desktop (`1280×800`) : [farmer-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-desktop-dashboard.png)
  - Capture Dashboard Mobile (`375×800`) : [farmer-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-mobile-dashboard.png)
  - Capture Tiroir Sidebar Mobile (`375×800`) : [farmer-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-mobile-sidebar.png)
  - Capture Blocage URL Directe (`/fr/exploitations`) : [farmer-blocked-exploitations.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-blocked-exploitations.png)
- **Connexion & En-tête** :
  - Authentification `/fr/login` → redirection `/fr/tableau`, badge `Rôle : Agriculteur` visible.
- **Navigation Sidebar (18 entrées visibles, 6 masquées)** :
  - *Visibles (18)* : `Alertes`, `Communauté`, `Tableau de bord`, `Parcelles`, `Carte`, `Météo`, `Cultures`, `Campagnes`, `Rendement`, `Fertilisation`, `Prix du marché`, `Recommandations`, `Maladies`, `Assistant IA`, `Irrigation`, `Risques phytosanitaires`, `Planning d’arrosage`, `Pièges à insectes`.
  - *Absentes du menu Desktop & Mobile (6)* : `/fr/exploitations`, `/fr/rapports`, `/fr/kit`, `/fr/vegetation`, `/fr/previsions`, `/fr/equipements`.
- **Dashboard (`FarmerDashboard`)** :
  - Bandeau : *« Espace Agriculteur · Pilotage terrain quotidien »*
  - KPIs vérifiés : *Parcelles sèches*, *Besoin d’eau (24 h)*, *Qualité eau d’arrosage (pH)*, *Cours Oignon (Dakar)*.
  - Cartes métier vérifiées : *Mon plan d’action du jour · Ndiol 1*, *Conseils & alertes · Ndiol 1*, *Communauté & alertes entre agriculteurs*, *Parcelles (`Ndiol 1`, `Ndiol 2`)*.
  - Widgets des autres rôles confirmés absents (`0` occurrence).
- **Accès URL direct (Routes autorisées vs Routes interdites)** :
  - `/fr/parcelles`, `/fr/irrigation`, `/fr/meteo`, `/fr/communaute`, `/fr/carte`, `/fr/parcelles/fld-ndiol-1` (avec formulaire `Démarrage (%)` / `Arrêt (%)`) : ✅ **Autorisés & fonctionnels**.
  - `/fr/exploitations`, `/fr/rapports`, `/fr/kit`, `/fr/vegetation`, `/fr/previsions`, `/fr/equipements` : 🔒 **Bloqués (`Accès réservé à un autre profil`)**.
  - `/fr/parcelles/fld-mboro-1` (parcelle hors organisation `ORG_B`) : 🔒 **Isolé (aucun formulaire ni donnée exposée)**.

---

### 2.2 Compte 2 — `cooperative@demo.sn` (`COOPERATIVE_MANAGER` / `coop_manager`)

- **Preuves générées** :
  - Rapport JSON : [coop_manager-report.json](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-report.json)
  - Capture Dashboard Desktop (`1280×800`) : [coop_manager-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-desktop-dashboard.png)
  - Capture Dashboard Mobile (`375×800`) : [coop_manager-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-mobile-dashboard.png)
  - Capture Tiroir Sidebar Mobile (`375×800`) : [coop_manager-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-mobile-sidebar.png)
  - Capture Blocage URL Directe (`/fr/kit`) : [coop_manager-blocked-kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-blocked-kit.png)
- **Connexion & En-tête** :
  - Authentification `/fr/login` → redirection `/fr/tableau`, badge `Rôle : Gestionnaire de coopérative` visible.
- **Navigation Sidebar (21 entrées visibles, 3 masquées)** :
  - *Visibles (21)* : `Alertes`, `Communauté`, `Tableau de bord`, `Rapports`, `Exploitations`, `Parcelles`, `Carte`, `Météo`, `Cultures`, `Campagnes`, `Rendement`, `Fertilisation`, `Prix du marché`, `Recommandations`, `Maladies`, `Assistant IA`, `Irrigation`, `Risques phytosanitaires`, `Planning d’arrosage`, `Équipements`, `Pièges à insectes`.
  - *Absentes du menu Desktop & Mobile (3)* : `/fr/kit`, `/fr/vegetation`, `/fr/previsions`.
- **Dashboard (`CoopManagerDashboard`)** :
  - Bandeau : *« Espace Coopérative · Gestion mutualisée, eau & marchés »*
  - 6 KPIs vérifiés : *Surface exploitée (`3,8 ha`)*, *Parcelles sèches*, *Eau économisée (30 j)*, *Parc matériel en service*, *Campagnes*, *Cours Oignon (Dakar)*.
  - Cartes métier vérifiées : *Périmètres de la coopérative (2)* (*Périmètre de Mboro* & *Périmètre de Potou*), *Campagne, eau & marché*, *Matériel & capteurs en direct*.
- **Accès URL direct (Routes autorisées vs Routes interdites)** :
  - `/fr/exploitations`, `/fr/rapports`, `/fr/equipements`, `/fr/campagnes`, `/fr/marches` : ✅ **Autorisés & fonctionnels**.
  - `/fr/kit`, `/fr/vegetation`, `/fr/previsions` : 🔒 **Bloqués (`Accès réservé à un autre profil`)**.

---

### 2.3 Compte 3 — `agronome@demo.sn` (`AGRONOME` / `agronomist`)

- **Preuves générées** :
  - Rapport JSON : [agronomist-report.json](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-report.json)
  - Capture Dashboard Desktop (`1280×800`) : [agronomist-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-desktop-dashboard.png)
  - Capture Dashboard Mobile (`375×800`) : [agronomist-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-mobile-dashboard.png)
  - Capture Tiroir Sidebar Mobile (`375×800`) : [agronomist-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-mobile-sidebar.png)
  - Capture Blocage URL Directe (`/fr/equipements`) : [agronomist-blocked-equipements.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-blocked-equipements.png)
- **Connexion & En-tête** :
  - Authentification `/fr/login` → redirection `/fr/tableau`, badge `Rôle : Agronome` visible.
- **Navigation Sidebar (23 entrées visibles, 1 masquée)** :
  - *Visibles (23)* : toutes les entrées scientifiques, culturales, IA et étalonnage kit (`/fr/vegetation`, `/fr/previsions`, `/fr/kit`, `/fr/fertilisation`, `/fr/maladies`, `/fr/pieges`, etc.).
  - *Absente du menu Desktop & Mobile (1)* : `/fr/equipements`.
- **Dashboard (`AgronomistDashboard`)** :
  - Bandeau : *« Cockpit Agronome · Vigie phytosanitaire, NDVI, NPK & eau »*
  - KPIs vérifiés : *Parcelles suivies*, *Parcelles sèches*, *Adoption des conseils IA (`%`)*, *Diagnostics foliaires (30 j)*.
  - Cartes métier vérifiées : *Matrice de diagnostic agronomique par parcelle* (colonnes `Parcelle & culture`, `Humidité & verdict`, `Eau (pH / CE)`, `Analyse dédiée` avec accès direct `NPK` et `Phyto`, raccourcis `Fertilisation NPK`, `Végétation NDVI`, `Prévision sol 72 h`).
- **Accès URL direct & Restrictions d'écriture fines** :
  - `/fr/vegetation`, `/fr/previsions`, `/fr/kit`, `/fr/fertilisation`, `/fr/maladies` : ✅ **Autorisés & fonctionnels**.
  - `/fr/equipements` : 🔒 **Bloqué (`Accès réservé à un autre profil`)**.
  - `/fr/parcelles/fld-mboro-1` : 🔒 **Formulaire de seuils (`Démarrage (%)` / `Arrêt (%)`) masqué** (`canEditThresholds = false`).
  - `/fr/recommandations` : 🔒 **Boutons de retour producteur (*Avez-vous suivi cette recommandation ?*) masqués** (`canGiveFeedback = false`).

---

### 2.4 Compte 4 — `admin@demo.sn` (`ADMIN` / `admin`)

- **Preuves générées** :
  - Rapport JSON : [admin-report.json](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-report.json)
  - Capture Dashboard Desktop (`1280×800`) : [admin-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-desktop-dashboard.png)
  - Capture Dashboard Mobile (`375×800`) : [admin-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-mobile-dashboard.png)
  - Capture Tiroir Sidebar Mobile (`375×800`) : [admin-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-mobile-sidebar.png)
- **Connexion & En-tête** :
  - Authentification `/fr/login` → redirection `/fr/tableau`, badge `Rôle : Administrateur` visible.
- **Navigation Sidebar (24 / 24 entrées visibles)** :
  - Accès complet aux 5 groupes (`Pilotage`, `Terrain`, `Cultures`, `IA`, `Matériel`) sur Desktop et Mobile.
- **Dashboard (`AdminDashboard`)** :
  - Bandeau : *« Supervision Administrateur · Multi-organisations & Flotte IoT »*
  - KPIs vérifiés : *Exploitations supervisées (`3` : Mboro, Potou, Ndiol)*, *Disponibilité flotte kits (`99,2 %`)*, *Mesures reçues (30 j)*, *Parcelles suivies (`7`)*, *Parcelles sèches*, *Kits silencieux*, *Alertes ouvertes*.
  - Cartes métier vérifiées : *Supervision multi-organisations & règles d’alertes*, *Répartition des alertes par règle*, *Matériel & capteurs en direct (5 kits actifs)*, *Grille multi-organisations des 7 parcelles*.
- **Accès URL direct** :
  - Toutes les routes (`/fr/exploitations`, `/fr/rapports`, `/fr/kit`, `/fr/vegetation`, `/fr/previsions`, `/fr/equipements`, etc.) : ✅ **24 / 24 accessibles sans restriction**.

---

## 3. Matrice Finale de Validation Page par Page (Accès URL Direct & Menu)

| Route (`/fr/...`) | `agriculteur@demo.sn` (`farmer`) | `cooperative@demo.sn` (`coop_manager`) | `agronome@demo.sn` (`agronomist`) | `admin@demo.sn` (`admin`) |
|---|:---:|:---:|:---:|:---:|
| `/fr/tableau` | ✅ Menu + `FarmerDashboard` | ✅ Menu + `CoopManagerDashboard` | ✅ Menu + `AgronomistDashboard` | ✅ Menu + `AdminDashboard` |
| `/fr/alertes` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/communaute` | ✅ Menu + Accès (Écrit & Vocal) | ✅ Menu + Accès (Écrit & Vocal) | ✅ Menu + Accès (Écrit & Vocal) | ✅ Menu + Accès (Écrit & Vocal) |
| `/fr/rapports` | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Accès + Export CSV | ✅ Menu + Accès + Export CSV | ✅ Menu + Accès + Export CSV |
| `/fr/exploitations` | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Accès (`Mboro`, `Potou`) | ✅ Menu + Accès (`Mboro`, `Potou`) | ✅ Menu + Accès (`Mboro`, `Potou`, `Ndiol`) |
| `/fr/parcelles` | ✅ Menu + Accès (`Ndiol 1..2`) | ✅ Menu + Accès (`Mboro 1..3`, `Potou 1..2`) | ✅ Menu + Accès (`Mboro 1..3`, `Potou 1..2`) | ✅ Menu + Accès (`7 parcelles`) |
| `/fr/parcelles/[id]` | ✅ Seuils éditables (`ORG_B` seul) | ✅ Seuils éditables (`ORG_A` seul) | 🔒 **Lecture seule** (`ThresholdForm` masqué) | ✅ Seuils éditables (`ORG_A+B`) |
| `/fr/carte` | ✅ Menu + Carte Sénégal (`ORG_B`) | ✅ Menu + Carte Sénégal (`ORG_A`) | ✅ Menu + Carte Sénégal (`ORG_A`) | ✅ Menu + Carte Sénégal (`ORG_A+B`) |
| `/fr/meteo` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/cultures` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/campagnes` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/rendement` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/fertilisation` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/vegetation` | ⛔ **Masqué & URL Bloquée** | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Accès (NDVI / EVI) | ✅ Menu + Accès (NDVI / EVI) |
| `/fr/marches` | ✅ Menu + Accès (Cours nationaux) | ✅ Menu + Accès (Cours nationaux) | ✅ Menu + Accès (Cours nationaux) | ✅ Menu + Accès (Cours nationaux) |
| `/fr/recommandations` | ✅ Menu + Feedback activé | ✅ Menu + Feedback activé | 🔒 **Menu + Lecture seule** (Feedback masqué) | ✅ Menu + Feedback activé |
| `/fr/maladies` | ✅ Menu + Analyse photo | ✅ Menu + Analyse photo | ✅ Menu + Analyse photo | ✅ Menu + Analyse photo |
| `/fr/assistant` | ✅ Menu + Chat écrit & vocal | ✅ Menu + Chat écrit & vocal | ✅ Menu + Chat écrit & vocal | ✅ Menu + Chat écrit & vocal |
| `/fr/irrigation` | ✅ Menu + Besoin 24h & Sonde pH | ✅ Menu + Besoin 24h & Sonde pH | ✅ Menu + Besoin 24h & Sonde pH | ✅ Menu + Besoin 24h & Sonde pH |
| `/fr/risques` | ✅ Menu + Accès (`ORG_B`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A`) | ✅ Menu + Accès (`ORG_A+B`) |
| `/fr/previsions` | ⛔ **Masqué & URL Bloquée** | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Courbes p10–p90 72h | ✅ Menu + Courbes p10–p90 72h |
| `/fr/planning` | ✅ Menu + Créneaux pompe (`ORG_B`) | ✅ Menu + Créneaux pompe (`ORG_A`) | ✅ Menu + Créneaux pompe (`ORG_A`) | ✅ Menu + Créneaux pompe (`ORG_A+B`) |
| `/fr/equipements` | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Parc matériel (`ORG_A`) | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Parc matériel (`ORG_A+B`) |
| `/fr/kit` | ⛔ **Masqué & URL Bloquée** | ⛔ **Masqué & URL Bloquée** | ✅ Menu + Étalonnage ADC & Kc | ✅ Menu + Étalonnage ADC & Kc |
| `/fr/pieges` | ✅ Menu + Pièges (`ORG_B`) | ✅ Menu + Pièges (`ORG_A`) | ✅ Menu + Pièges (`ORG_A`) | ✅ Menu + Pièges (`ORG_A+B`) |
