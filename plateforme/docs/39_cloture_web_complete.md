# 39 — Clôture Complète du Produit Web SmartAgri92 (Phase E6)

**Date** : 14 novembre 2026  
**Périmètre** : Produit Web SmartAgri92 (`plateforme/web`) intégré au Backend FastAPI (`plateforme/backend`)  
**Statut global du produit Web** : **PRODUCT READY (Prêt pour utilisation réelle)**

---

## 1. Ce qui est terminé

### 1.1 Produit Web (`plateforme/web`) — 100 % achevé, audité et durci
- **Couverture fonctionnelle intégrale** :
  - **24 écrans** fonctionnels et revus humainement ([`34_revue_humaine.md`](./34_revue_humaine.md)) : Connexion (`/fr/login`), Tableau de bord (`/fr/tableau`), Exploitations (`/fr/exploitations`), Parcelles (`/fr/parcelles`), Détail Parcelle à 4 onglets (`/fr/parcelles/[id]`), Carte interactive Leaflet (`/fr/carte`), Météo & ET0 (`/fr/meteo`), Irrigation (`/fr/irrigation`), Humidité prévue (`/fr/previsions`), Planning d'arrosage (`/fr/planning`), Fertilisation NPK (`/fr/fertilisation`), Risques phytosanitaires (`/fr/risques`), Pièges à insectes (`/fr/pieges`), Recommandations (`/fr/recommandations`), Assistant IA (`/fr/assistant`), Diagnostic Maladies (`/fr/maladies`), État du kit (`/fr/kit`), Alertes (`/fr/alertes`), Rapports (`/fr/rapports`), Équipements (`/fr/equipements`), Cultures (`/fr/cultures`), Campagnes (`/fr/campagnes`), Rendement (`/fr/rendement`), Végétation NDVI (`/fr/vegetation`), Prix du marché (`/fr/marches`).
  - **18/18 services** de [`16_architecture_octopus.md`](./16_architecture_octopus.md) § 9.3 disposent de leur écran, de leur contrat Zod (`lib/contracts/*.ts`) et de leur gestion explicite de la provenance (`model_name`, `model_version`, `source`, `confidence`, `fallback_step`, `computed_at`, `stale`).
- **Sécurité BFF & résilience réseau** :
  - Authentification par cookies `httpOnly` (`sa_at`, `sa_rt`), protection CSRF (`X-Requested-With: smartagri-web`), en-têtes CSP à nonce par requête, aucun jeton dans `localStorage`.
  - Bandeau hors-ligne (`OfflineBanner`), bandeau de données anciennes (`StaleBanner`), indicateurs de fraîcheur (`FreshnessBadge`), états vides et erreurs traduits par code stable.
- **Validation multi-navigateur ([`35_validation_navigateurs.md`](./35_validation_navigateurs.md))** :
  - Validé par tests E2E automatisés sur **Chromium (Blink)**, **Firefox 157 (Gecko)** et **WebKit 27.2 (Safari)** : Leaflet SVG, upload image + réduction Canvas, microphone (`MediaRecorder` multi-codec), `localStorage`, cookies, thème sombre, responsive `375 px → 1920 px`, et animations (`prefers-reduced-motion`).
- **Accessibilité WCAG 2.1 AA ([`36_accessibilite_finale.md`](./36_accessibilite_finale.md))** :
  - **14/14 paires de contraste** conformes en thème clair et en thème sombre (`npm run contrast`).
  - Navigation clavier intégrale, indicateur `:focus-visible` sur tous les contrôles, sémantique ARIA (`role="log"`, `role="status"`, `role="alert"`, `role="radiogroup"`, `<dialog>` natif mobile), cibles tactiles `>= 44×44 px`.
- **Durcissement UX ([`37_ux_hardening.md`](./37_ux_hardening.md))** :
  - Suppression des micro-frictions : normalisation de `-0 %` en `0 %`, libellés métier francisés pour les saisons (`Saison sèche (contre-saison)`, `Saison des pluies (hivernage)`), les règles d'alerte (`Défaut de pompe (pump_fault)`, `Sol sec (soil_dry)`), et les pompes d'irrigation (`Pompe solaire Ndiol` avec créneaux réalistes `06 h 00 – 12 h 00`), repère terrain d'équivalence hydrique (`1 mm = 1 L/m² = 10 m³/ha`), conseil de prise de vue photo sur Maladies, et 3 boutons de questions rapides d'onboarding dans l'Assistant.

### 1.2 Backend FastAPI & Intégration Hybride (`plateforme/backend`, `plateforme/db`) — 100 % achevé
- **Migrations SQL** (`001_initial_schema.sql`, `002_row_level_security.sql`, `003_device_parameter_sets.sql`) avec isolation multi-organisation PostgreSQL RLS.
- **Moteur de provenance et chaîne de repli à 3 paliers** (`ml` → `rules` → `last`) opérationnels.
- **Mode hybride par service** (`AGRI_MOCK` + `AGRI_SERVICES`) aligné entre BFF Next.js et Backend FastAPI, avec correspondance déterministe entre les slugs de démonstration (`fld-mboro-1`, `dev-0001`, `farm-mboro`) et les UUID v4 de la base.
- **5 services activables immédiatement en mode `real` (`source="rules"`)** : `weather`, `irrigation_need`, `recommendations`, `kit_parameters`, `device_health` (+ routes v1 `yield_forecast`, `water_savings`, `assistant_chat`, `map_layers` GeoJSON).
- **4 services techniquement implémentés et testés côté Backend** prêts à basculer en `real` dès levée de leur prérequis externe : `fertilization`, `pest_risk`, `diagnosis_analyze`, `assistant_transcribe`.

---

## 2. Ce qui reste réellement (hors périmètre Web RC)

Rien ne reste à développer dans l'application Web (`plateforme/web`) pour sa mise en service initiale en mode hybride. Les travaux restants concernent exclusivement les phases ultérieures du programme global :

1. **Phase IA / MLOps (`agriml` & OctOpus)** : entraînement des modèles ML, export des bundles ONNX/LightGBM dans `ml/artifacts/`, et activation du palier 1 (`source="ml"`, `fallback_step=1`).
2. **Validation linguistique humaine Wolof / Pulaar** : relecture par des locuteurs natifs des fichiers CSV `plateforme/web/messages/traduction/wo.csv` et `ff.csv` puis compilation vers `messages/wo.json` et `messages/ff.json`.
3. **Alimentation des référentiels agronomiques et marchés** : saisie des tables officielles ISRA/CDH/DPV et flux SIM/CSA.
4. **Application mobile terrain hors-ligne prolongé** : chantier mobile dédié (distinct du Web responsive déjà opérationnel sur smartphone).

---

## 3. Points bloquants externes

Ces points ne bloquent **pas** le déploiement du produit Web en mode hybride (`rules` + `mock`), mais conditionnent le passage de certains services spécifiques en mode `real` complet :

| Service / Domaine | Point bloquant externe | Responsable / Source externe | Comportement actuel mis en place |
|---|---|---|---|
| **Fertilisation (`#6`)** | Tables d'exportation N-P-K par culture × stade × texture de sol | Agronomes ISRA / CDH | Route backend implémentée ; renvoie `dose_kg_ha=0` + avertissement explicite sans inventer de dose ; Web servi en `mock` explicite |
| **Risques ravageurs (`#9`)** | Seuils degrés-jours et grilles hygrométriques par ravageur (noctuelle, thrips, mildiou) | Agronomes ISRA / DPV | Route backend implémentée avec vigilance prudente ; Web servi en `mock` explicite |
| **Transcription vocale (`#17`)** | Clé API et choix contractuel du fournisseur ASR cloud ou serveur GPU local | Direction technique / Ops | Protocole `Transcriber` prêt ; comparatif Whisper / Azure / Google Cloud STT v2 livré ([`31_rapport_D6.md`](./31_rapport_D6.md)) ; renvoie `503 MODEL_UNAVAILABLE` si appelé en `real` sans clé |
| **Traductions `wo` / `ff`** | Validation terminologique agricole par traducteurs natifs | Équipe linguistique / Coopératives | Clés présentes à 100 % (`npm run i18n:check` vert) avec repli français propre |

---

## 4. Ce qui dépend maintenant de l'IA (Phase ultérieure)

L'interface Web affiche déjà toutes les métadonnées IA (provenance, confiance, explications `why`, paliers de repli, abstention). Le passage du palier 2 (`rules`) ou du mode `mock` au palier 1 (`ml`) dépend uniquement de la livraison des artefacts par le pipeline `agriml` ([`33_readiness_ia_reelle.md`](./33_readiness_ia_reelle.md)) :

1. **Modèles tabulaires LightGBM / Ridge (`V1` / `V1.1`)** :
   - `soil_nowcast` (`#2 Humidité prévue 24 h`),
   - `irr_need_24h` (`#3 Besoin d'irrigation 24 h`),
   - `fert_npk` (`#6 Fertilisation NPK`),
   - `pest_risk` (`#9 Risques phytosanitaires`),
   - `anomaly_ml` (`#13 Détection d'anomalies capteurs`).
2. **Modèles de vision ONNX int8 (`V2`)** :
   - `vis_disease` (`#8 Diagnostic photo des maladies` — le chargeur `OnnxVisionAnalyzer` et la règle d'abstention `confidence < 0.7` sont déjà codés et testés dans `app/services/diagnosis.py`),
   - `vis_pest_trap` (`#10 Comptage d'insectes sur pièges`).
3. **Modèles avancés et RAG (`V2` / `V3`)** :
   - `irr_mpc` (`#4 Planning d'irrigation sous contrainte`),
   - `ndvi_Clean` (`#11 Végétation satellite Sentinel-2`),
   - `yield_Fcst` (`#12 Prévision de rendement`),
   - `price_Fcst` (`#15 Prévision des prix du marché`),
   - `rag_Agronomy` (`#16 Assistant IA` — enrichissement vectoriel pgvector sur fiches ISRA/CDH).

---

## 5. Ce qui dépend des données

1. **Historique télémétrique terrain des kits ESP32-S3 (`telemetry_readings`)** :
   - Le service `irrigation_need` et le moteur `recommendations` exigent au moins 6 relevés horaires récents (< 48 h) pour calculer le déficit hydrique à partir de la sonde capacitative (sinon ils basculent proprement sur le repli météo `ET0`).
   - L'entraînement des modèles `soil_nowcast` et `irr_need_24h` requiert l'accumulation des séries temporelles réelles en base TimescaleDB.
2. **Corpus photographique terrain annoté (Zone des Niayes & Vallée du Fleuve)** :
   - Nécessaire pour entraîner et calibrer `vis_disease` et `vis_pest_trap` sur les variétés locales (oignon Violet de Galmi, tomate, chou, pomme de terre) et les conditions d'éclairage réelles.
3. **Séries historiques de rendements et de prix de marché (SIM / CSA / ANSD)** :
   - Nécessaires pour alimenter `yield_forecast` (au-delà des moyennes historiques par culture) et `price_forecast` (marchés de Dakar, Thiès, Saint-Louis, Touba, Kaolack).
4. **Flux satellite Sentinel-2 (Copernicus)** :
   - Nécessaire pour alimenter `vegetation` (`ndvi_Clean`) et les tuiles raster NDVI de la carte (`map_layers`).

---

## 6. Ce qui dépend du mobile

1. **Usage smartphone via navigateur Web (Déjà opérationnel à 100 %)** :
   - Le produit Web SmartAgri92 est intégralement **responsive dès `375 px`** (barre de navigation basse à 4 onglets + tiroir `<dialog>`, cibles tactiles `44×44 px`, capture photo directe via `capture="environment"` sur `/fr/maladies`, dictée vocale via `MediaRecorder` sur `/fr/assistant`, réduction des photos à `<= 256 Ko` sur appareil avant envoi pour réseaux 2G/3G).
2. **Fonctionnalités spécifiques à une future application mobile native / PWA hors-ligne prolongé** :
   - File d'attente de synchronisation différée en écriture (*offline-first mutation queue*) pour saisir des observations de terrain ou stocker des photos pendant plusieurs heures en zone blanche totale avant retour de la connectivité.
   - Notifications *push* natives (OS mobile) en complément des canaux SMS / WhatsApp / Voix gérés par le backend d'alertes.
   - Appairage Bluetooth Low Energy (BLE) / Wi-Fi local direct avec le boîtier ESP32-S3 pour le diagnostic matériel sur site sans réseau cellulaire.
