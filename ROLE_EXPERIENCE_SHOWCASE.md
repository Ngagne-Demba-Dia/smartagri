# MISSION FRONT-RBAC-04 — Rapport Visuel Exécutif des Expériences par Rôle (`ROLE_EXPERIENCE_SHOWCASE.md`)

**Plateforme** : SmartAgri92 — Pilotage Hydro-Agricole, IoT & IA pour le Sénégal (Niayes, Vallée du Fleuve, Bassin Arachidier, Casamance)  
**Date** : 22 novembre 2026  
**Document complet** : [plateforme/docs/ROLE_EXPERIENCE_SHOWCASE.md](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/docs/ROLE_EXPERIENCE_SHOWCASE.md)

---

## 1. Synthèse Exécutive Jury

| Rôle Métier | Compte de Démonstration | Périmètre de Données (RLS) | Menus Visibles | Menus Masqués & Bloqués (URL directe) | Philosophie du Dashboard |
|---|---|---|:---:|:---:|---|
| **1. `AGRICULTEUR`** (`farmer`) | `agriculteur@demo.sn` *(mdp : `demo`)* | **Exploitation de Ndiol** (`ORG_B` — Vallée du Fleuve, `2 parcelles`, `1,6 ha`) | **18 / 24** | **6 bloqués** (`/exploitations`, `/rapports`, `/kit`, `/vegetation`, `/previsions`, `/equipements`) | **Action terrain immédiate** : dose d'eau du jour, pH de l'eau, météo, prix du marché et alertes vocales communautaires |
| **2. `COOPERATIVE_MANAGER`** (`coop_manager`) | `cooperative@demo.sn` *(mdp : `demo`)* | **Coopérative des Niayes** (`ORG_A` — Mboro & Potou, `5 parcelles`, `3,8 ha`) | **21 / 24** | **3 bloqués** (`/kit`, `/vegetation`, `/previsions`) | **Gestion mutualisée** : comparaison des périmètres, économies d'eau 30 j, parc pompes solaires, campagnes et vente groupée |
| **3. `AGRONOME`** (`agronomist`) | `agronome@demo.sn` *(mdp : `demo`)* | **Coopérative des Niayes** (`ORG_A` — Mboro & Potou, `5 parcelles`) | **23 / 24** | **1 bloqué** (`/equipements`) + **Seuils & Feedback en lecture seule** | **Vigie scientifique & IA** : matrice par parcelle (humidité, pH/CE, NPK, NDVI, ravageurs), diagnostics foliaires et adoption IA |
| **4. `ADMIN`** (`admin`) | `admin@demo.sn` *(mdp : `demo`)* | **Multi-Organisations** (`ORG_A + ORG_B` — `3 exploitations`, `7 parcelles`, `5,4 ha`) | **24 / 24** | **0 bloqué** (Accès total) | **Supervision système & flotte IoT** : disponibilité des 5 kits ESP32-S3, 33 408 mesures 30 j, santé des 6 capteurs et alertes par règle |

---

## 2. Index des Captures Visuelles Générées (`plateforme/web/audit-shots/rbac/`)

- **1. `AGRICULTEUR` (`agriculteur@demo.sn`)** :
  - Dashboard Desktop : [farmer-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-desktop-dashboard.png)
  - Sidebar Filtrée (18 menus) : [farmer-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-mobile-sidebar.png)
  - Vue Mobile (`375×800`) : [farmer-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-mobile-dashboard.png)
  - Blocage URL Directe (`/fr/exploitations`) : [farmer-blocked-exploitations.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/farmer-blocked-exploitations.png)
- **2. `COOPERATIVE_MANAGER` (`cooperative@demo.sn`)** :
  - Dashboard Desktop : [coop_manager-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-desktop-dashboard.png)
  - Sidebar Filtrée (21 menus) : [coop_manager-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-mobile-sidebar.png)
  - Vue Mobile (`375×800`) : [coop_manager-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-mobile-dashboard.png)
  - Blocage URL Directe (`/fr/kit`) : [coop_manager-blocked-kit.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/coop_manager-blocked-kit.png)
- **3. `AGRONOME` (`agronome@demo.sn`)** :
  - Dashboard Desktop : [agronomist-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-desktop-dashboard.png)
  - Sidebar Filtrée (23 menus) : [agronomist-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-mobile-sidebar.png)
  - Vue Mobile (`375×800`) : [agronomist-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-mobile-dashboard.png)
  - Blocage URL Directe (`/fr/equipements`) : [agronomist-blocked-equipements.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/agronomist-blocked-equipements.png)
- **4. `ADMIN` (`admin@demo.sn`)** :
  - Dashboard Desktop : [admin-desktop-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-desktop-dashboard.png)
  - Sidebar Complète (24/24 menus) : [admin-mobile-sidebar.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-mobile-sidebar.png)
  - Vue Mobile (`375×800`) : [admin-mobile-dashboard.png](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/web/audit-shots/rbac/admin-mobile-dashboard.png)

Consulter [plateforme/docs/ROLE_EXPERIENCE_SHOWCASE.md](file:///c:/Users/ngdia/Documents/projet_agri/plateforme/docs/ROLE_EXPERIENCE_SHOWCASE.md) pour le dossier complet illustré rôle par rôle.
