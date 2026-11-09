# 12 — Plan de développement

Confidentiel — réservé aux partenaires de travail.

Ce document répond au livrable 13. `07_feuille_de_route_budget.md` fixe les versions, les portes, l'équipe et le budget. Ce document en tire l'exécution : épopées, sprints des six premiers mois, définition de « terminé », rituels, responsabilités et premier backlog. Il se termine par la correspondance entre les 17 livrables demandés et les fichiers du dépôt (§10).

M1 correspond à novembre 2026. Les dates de sprint sont proposées et restent à ajuster quand l'équipe sera recrutée.

## 1. Organisation

| | Compétition / démo | Production | Compromis retenu |
|---|---|---|---|
| Cadence | 6 semaines, livrable par semaine (`07_feuille_de_route_budget.md` §8) | Plusieurs équipes produit, planification trimestrielle | **Une équipe, sprints de 2 semaines**, revue avec l'agronome à chaque sprint |
| Terrain | Démonstration scriptée | Équipe terrain dédiée | **Kanban terrain** en parallèle : installations, visites, tickets ; agronome et chef de produit |
| Outils | Tableau partagé | Gestion de portefeuille | Tickets GitHub Issues + Projects ; ADR dans `docs/02_architecture.md` §9 |
| Livraison | VM unique | Trains de livraison | Continue en recette, mise en production à la demande (`11_deploiement.md`) |

Capacité d'un sprint en M1–M2 : 7 ETP × 10 jours = 70 jours-personne (8 ETP dès M3 avec l'arrivée du full-stack junior, voir §6). Après les rituels, le terrain, le support et les imprévus (environ 25 %), il reste **environ 52 jours-personne de développement par sprint**. La planification se fait sur ce chiffre, pas sur 70.

## 2. Épopées

| Code | Épopée | Contenu | Références | Responsable (rôle) | Version |
|---|---|---|---|---|---|
| E1 | Firmware | v1.1 compilé et validé sur banc, puis v1.2 : historique LittleFS, horloge, `/historique`, OTA signée, jeu de paramètres poussé et événements de la page locale | Rapport d'audit, `02_architecture.md` §2, `16_architecture_octopus.md` | Ingénieur embarqué | v0.1 → v1 |
| E2 | Application mobile | Appairage, lecture locale `/data`, seuils, file d'envoi, alertes, OTA du kit | ADR 004 et 007, `10_web_ux.md` | Dév. mobile et web | v0.1 → v1 |
| E3 | API cœur | Authentification, organisations, exploitations, parcelles, kits, télémétrie par lots, seuils, alertes | `CONVENTIONS.md` §5, `05_stack_logicielle.md` §3 | Dév. backend | v0.1 → v1 |
| E4 | Données | TimescaleDB, agrégats continus, S3 brut, qualité des mesures | `04_data_mlops.md` §2–4, `db/migrations/` | Dév. backend + data scientist | v0.1 → v1 |
| E5 | Web coopérative | Modules 1, 2, 3, 4 (lecture), 5, 7 et 13 | `10_web_ux.md` §3–4, `maquettes/index.html` | Dév. mobile et web + UX | v1 |
| E6 | Recommandation d'irrigation | FAO-56 + météo (ADR 009) | `03_ia.md` §2–3 | Data scientist | v0.1 → v1 |
| E7 | Notifications | WhatsApp / SMS, préférences, quotas | `05_stack_logicielle.md` | Dév. backend | v1 |
| E8 | Assistant | Module 12 en bêta fermée, outils limités aux données de l'utilisateur | `03_ia.md` §6 et §13, ADR 006 | CTO + data scientist | v1 |
| E9 | Vision | Collecte de photos dès le MVP ; modèle serveur indicatif si le seuil est atteint | `03_ia.md` §4, `09_octopus_ml.md` | Data scientist + agronome | v1 → v2 |
| E10 | MLOps et OctOpus | Registre MLflow, porte champion/challenger, dérive, instantanés pseudonymisés | `09_octopus_ml.md`, `ml/` | Data scientist | v1 → v2 |
| E11 | Plateforme | Terraform, EKS, GitOps, observabilité, reprise après sinistre | `11_deploiement.md`, `infra/` | Dév. backend/DevOps + CTO | v0.1 → v1 |
| E12 | Sécurité et conformité | Socle `06_devsecops.md`, test d'intrusion n° 1, AIPD et déclaration CDP | `06_devsecops.md` | CTO | v1 |
| E13 | Terrain | Protocole, parcelles témoins, installation, formation, support | `07_feuille_de_route_budget.md` §4 | Agronome + chef de produit | v0.1 → v1 |

## 3. Sprints M1–M6

### 3.1 Pilote v0.1 (M1–M2) et porte G0

**Contrainte de calendrier.** La porte G0 exige 10 kits en service au moins 90 % du temps sur 4 semaines. Pour une revue la semaine du 4 janvier 2027, les kits doivent donc être posés **au plus tard le 4 décembre 2026**. Il reste un mois pour valider le firmware sur banc, au lieu des 30 jours prévus dans le Gantt. Le banc est concentré sur les tests de sécurité du rapport d'audit (S1–S2), et l'installation se fait en deux vagues de 5 kits.

| Sprint | Dates | Objectif | Contenu principal | Démo de fin de sprint |
|---|---|---|---|---|
| S1 | 02/11 – 13/11/2026 | Tout compile, tout démarre | E1 : compilation de v1.1 pour ESP32-S3, banc monté. E3/E4 : `make up`, migration `001_init.sql`, jeu de démonstration. E11 : dépôt, protections de branche, CI verte. E2 : squelette Flutter, lecture de `/data`. E13 : protocole, choix des 10 parcelles et des parcelles témoins, consentements | Un kit sur banc dont la mesure apparaît dans l'application |
| S2 | 16/11 – 27/11 | Kit sûr, relais de bout en bout | E1 : tests de sécurité du rapport (401, 405, 400, capteur débranché, CRC faux, verrouillage pompe). E2 : seuils et file d'envoi. E3 : `POST /v1/telemetry/batch`, kits, seuils. E6 : ET0 et besoin en eau FAO-56. E13 : installation des 5 premiers kits | Mesures de terrain dans la base, via le téléphone |
| S3 | 30/11 – 11/12 | Pilote complet | E13 : 5 kits de plus, pose terminée le 4/12. E3 : alertes. E5 : tableau de bord minimal (courbes, alertes). E6 : recommandation affichée dans l'application. E11 : Terraform validé, recette amorcée | Un exploitant pilote reçoit une recommandation |
| S4 | 14/12 – 25/12 (capacité réduite) | Fiabilité | Taux de mesures reçues (objectif ≥ 95 %), correction des pertes de la file, bilan énergie (E1), premiers tableaux de suivi G0 | Indicateurs G0 à jour |
| S5 | 28/12/2026 – 08/01/2027 | Revue G0 | Stabilisation et rapport G0 ; préparation du MVP (affinage du backlog, ADR) | Revue G0 avec le comité de pilotage |

### 3.2 MVP v1 (M3–M6) et porte G1

| Sprint | Dates | Objectif | Contenu principal |
|---|---|---|---|
| S6 | 11/01 – 22/01/2027 | Comptes et organisations | E3 : rôles, organisations, filtrage (404 en cas d'accès à une autre organisation). E5 : squelette Next.js + BFF, modules 2 et 3. E11 : production amorcée, première mise en production à blanc |
| S7 | 25/01 – 05/02 | Le web devient utile | E5 : module 1 (tableau de bord). E6/E5 : module 7 (recommandations). E1 : OTA signée sur banc (v1.2). E9 : protocole de collecte des photos (consentement, floutage, EXIF retiré) |
| S8 | 08/02 – 19/02 | Météo et alertes | E5 : module 5. E7 : WhatsApp / SMS. E4 : agrégats continus `1h`/`1d`/`1w`/`1mo`. E2 : alertes poussées |
| S9 | 22/02 – 05/03 | Carte et historique | E5 : module 4 (lecture). E1 : historique et horloge v1.2. E2 : OTA par l'application (vague 0 sur banc) |
| S10 | 08/03 – 19/03 | Assistant en bêta fermée | E8 : module 12, outils et plafonds, jeu d'évaluation hors ligne. E10 : MLflow et porte champion/challenger branchés sur la recommandation |
| S11 | 22/03 – 02/04 | Rapports et vision indicative | E5 : module 13 (KPI, export CSV). E9 : modèle serveur, derrière un drapeau de fonctionnalité, s'il dépasse le seuil défini avec l'agronome. E12 : test d'intrusion n° 1 |
| S12 | 05/04 – 16/04 | Correctifs du test d'intrusion | E12 : correction de tous les constats critiques et élevés. E13 : 40 kits de plus posés (50 au total). E1 : vagues OTA 1 et 2 |
| S13 | 19/04 – 30/04 | Revue G1 | Gel de 5 jours, exercice de restauration (`11_deploiement.md` §9), mesure de l'économie d'eau face aux parcelles témoins, rapport G1 |

**Ramadan et Korité.** En 2027, le Ramadan devrait couvrir environ du 8 février au 9 mars (dates à confirmer), donc les sprints S8 et S9. La capacité de ces sprints sera estimée avec l'équipe ; aucune journée terrain ne sera imposée en fin de journée.

**Pose des 40 kits du MVP.** La planification ci-dessus les pose en S12, ce qui laisse peu de recul avant G1. Si le fonds de roulement des kits (R11) est disponible plus tôt, les kits doivent être posés à partir de S8, pour que l'économie d'eau soit mesurée sur une plus grande partie du cycle.

### 3.3 Après le MVP

- **V1.1** (M7–M8) : modules 6 (analyse des cultures), 10 (équipements) et 11 (campagnes), connexion OTP (`/v1/auth/otp/*`), tests E2E Playwright, tests de fumée après synchronisation.
- **V2** (M7–M12) : module 8 complet (diagnostic sur le téléphone, hors ligne), wolof, MQTT, *shadow* et canari des modèles, Argo Rollouts.
- **V3** (M13–M18) : module 9 (prévision de rendement), NDVI, pulaar.

Les sprints de ces versions seront planifiés à la revue G1.

## 4. Définition de « prêt » et de « terminé »

**Une histoire est prête** quand :

- elle a des critères d'acceptation vérifiables ;
- la maquette existe si elle a une interface ;
- son impact sur `CONVENTIONS.md` (route, table, variable) est identifié ;
- elle tient dans un sprint.

**Une histoire est terminée** quand tous les points qui la concernent sont cochés.

Commun

- [ ] Code relu par une personne, par deux pour l'authentification, les droits, la pompe, l'OTA et les paiements.
- [ ] CI verte : tests, couverture ≥ 80 % sur le code modifié, lint, aucun constat critique ni élevé (gitleaks, Semgrep, Trivy, pip-audit ou `npm audit`).
- [ ] `CONVENTIONS.md` et la documentation concernée sont à jour ; une ADR est ajoutée si une décision d'architecture change.
- [ ] Le code est déployé en recette et la démonstration a été faite au chef de produit (et à l'agronome si l'histoire touche au conseil).
- [ ] Journaux structurés sans donnée personnelle ; métrique ou alerte ajoutée si l'histoire crée un nouveau mode de panne.

Web et mobile

- [ ] Fonctionne en clair et en sombre, à 360 px de large, et au clavier ; contrastes AA ; libellés en français, clés prêtes pour le wolof.
- [ ] Testé sur un Android d'entrée de gamme (2 Go de RAM) et en réseau lent (3G simulée).
- [ ] Mobile : fonctionne 7 jours hors ligne, et la file d'envoi survit à une mise à jour de l'application.

Firmware

- [ ] Compile pour la cible (`esp32:esp32`, ESP32-S3), et les cas du plan de tests concernés passent sur banc.
- [ ] La pompe reste au niveau sûr dans tous les chemins d'erreur, et le chien de garde est actif.
- [ ] Aucune opération sur les eFuses.

ML et IA

- [ ] Jeu de données versionné (DVC, manifeste), modèle enregistré dans MLflow, fiche de modèle remplie.
- [ ] Évaluation sur le jeu réservé, qui n'a jamais été envoyé à OctOpus ; la porte champion/challenger est passée.
- [ ] Seules des données pseudonymisées ont quitté la plateforme (`09_octopus_ml.md`).
- [ ] Assistant : le jeu d'évaluation hors ligne passe et aucune fuite entre organisations n'est observée.

## 5. Rituels

| Rituel | Fréquence | Durée | Participants | Résultat |
|---|---|---|---|---|
| Point quotidien | Chaque jour | 15 min | Équipe | Blocages levés |
| Planification | Début de sprint | 2 h | Équipe | Objectif et engagement du sprint |
| Affinage | Chaque semaine | 1 h | Chef de produit, CTO, un développeur à tour de rôle | Histoires prêtes |
| Revue et démo | Fin de sprint | 1 h | Équipe, agronome, si possible un représentant de coopérative | Retours, backlog ajusté |
| Rétrospective | Fin de sprint | 1 h | Équipe | 1 à 3 actions d'amélioration |
| Journée terrain | Chaque mois, pour chaque développeur | 1 jour | Un développeur + l'agronome | Observations d'usage, tickets |
| Revue d'architecture | Toutes les 2 semaines | 45 min | CTO + développeurs concernés | ADR |
| Revue de sécurité | Chaque mois | 1 h | CTO + backend/DevOps | Suivi des constats, rotation des secrets |
| Revue des modèles | Chaque mois, à partir de S10 | 1 h | Data scientist, agronome, CTO | Promotion ou rejet, suivi de la dérive |
| Analyse d'incident | Après chaque incident | 1 h | Personnes concernées | Analyse sans recherche de coupable, actions |
| Comité de pilotage | À chaque porte (G0, G1…) | 2 h | Direction, partenaires, CTO, chef de produit | Décision : passage, prolongation ou correction |

## 6. Équipe et responsabilités

R : réalise ; A : rend compte ; C : consulté.

| Épopée | CTO | Backend/DevOps | Mobile et web | Embarqué | Data/ML | Agronome | UX (0,5) | Chef de produit (0,5) |
|---|---|---|---|---|---|---|---|---|
| E1 Firmware | A | | C | R | | C | | |
| E2 Mobile | C | C | R | C | | C | R | A |
| E3 API | A | R | C | | | | | C |
| E4 Données | A | R | | | R | | | |
| E5 Web | C | R (BFF) | R | | | C | R | A |
| E6 Irrigation | C | C | | | R | R | | A |
| E7 Notifications | | R | C | | | C | | A |
| E8 Assistant | R | C | C | | R | C | | A |
| E9 Vision | C | | C | | R | R | | A |
| E10 MLOps | A | C | | | R | | | |
| E11 Plateforme | A | R | | | C | | | |
| E12 Sécurité | R | R | C | C | C | | | |
| E13 Terrain | | | | C | | R | C | A |

**Le risque principal se lit dans la colonne « Mobile et web ».** Une seule personne porte l'application Flutter et le web Next.js pendant tout le MVP. Trois mesures sont recommandées :

1. Avancer le développeur full-stack junior de M7 à **M3**. Le coût est de 4 × 400 000 FCFA, soit 1,6 M FCFA sur le budget M1–M6 (intégré au scénario standard de `07_feuille_de_route_budget.md` §7).
2. Faire construire le BFF par la personne backend.
3. Limiter le web du MVP aux 8 modules retenus, sans ajouter de fonction.

Sans ces mesures, il faudra choisir entre le module 13 et le module 4.

## 7. Modules et versions

| Module | Version | Épopée | Sprint visé |
|---|---|---|---|
| 1 Tableau de bord | MVP | E5 | S3 (minimal), S7 |
| 2 Exploitations | MVP | E5 | S6 |
| 3 Parcelles | MVP | E5 | S6 |
| 4 Carte SIG | MVP en lecture ; dessin et NDVI en V2 | E5 | S9 |
| 5 Météo | MVP | E5, E6 | S8 |
| 6 Analyse des cultures | V1.1 | E5 | M7–M8 |
| 7 Recommandations | MVP (FAO-56) | E5, E6 | S7 |
| 8 Détection de maladies | Collecte de photos au MVP ; modèle indicatif derrière un drapeau en S11 ; complet en V2 | E9 | S7, S11 |
| 9 Prévision de rendement | V3, visible avant avec l'étiquette « expérimental » | E10 | M13+ |
| 10 Équipements | V1.1 | E5 | M7–M8 |
| 11 Campagnes | V1.1 | E5 | M7–M8 |
| 12 Assistant | MVP, bêta fermée | E8 | S10 |
| 13 Rapports et KPI | MVP (écran + CSV) ; PDF en V2 | E5 | S11 |

Les maquettes des 13 modules existent dès maintenant (`maquettes/index.html`) : les modules hors MVP servent aux tests d'usage, pas au développement.

## 8. Backlog du sprint 1

| ID | Histoire | Critères d'acceptation |
|---|---|---|
| FW-1 | En tant que responsable embarqué, je compile le firmware v1.1 pour l'ESP32-S3 | Compilation sans erreur avec le core `esp32:esp32` 3.x, bibliothèques et `User_Setup.h` de TFT_eSPI figés ; job de compilation ajouté à la CI |
| FW-2 | Je monte un banc avec pompe sur bac, capteur de sol, BME280 et sonde NPK | Banc photographié et documenté ; procédure de flashage écrite |
| FW-3 | Je vérifie les protections de l'API locale | `POST /seuils` sans `X-Agri-Token` → 401 ; GET → 405 ; `start=50&stop=52` → 400 ; un jeton valide est accepté |
| API-1 | En tant que développeur, je démarre la plateforme en une commande | `make up` démarre db, mqtt, minio, api, ingestor, mlflow ; le service `migrate` applique `db/migrations` et les inscrit dans `schema_migrations` ; `make seed` charge le jeu de démonstration ; `/healthz` répond |
| API-2 | En tant que relais mobile, j'envoie un lot de mesures | `POST /v1/telemetry/batch` accepte jusqu'à 1 000 points `telemetry.v1` ; les doublons sont ignorés ; un point hors plage est rejeté et compté |
| MOB-1 | En tant qu'exploitant, je vois les mesures de mon kit sans Internet | Connexion au Wi-Fi du kit, lecture de `/data` toutes les 5 s, verdict « sol sec » ou « humidité correcte » |
| WEB-0 | En tant qu'équipe, nous partageons les jetons de design | Jetons de couleur des maquettes (clair et sombre, palette des graphiques validée) repris dans le paquet web |
| ML-1 | En tant qu'agronome, j'obtiens le besoin en eau d'une parcelle | ET0 FAO-56 calculé depuis Open-Meteo, Kc par culture et stade, résultat comparé à un calcul de référence (écart < 5 %) |
| OPS-1 | En tant qu'équipe, notre dépôt est protégé | Branche `main` protégée, CI obligatoire, Dependabot actif, environnements `ecr-push` et `production` créés |
| TER-1 | En tant qu'agronome, je fixe le protocole du pilote | 10 parcelles et autant de témoins choisies, formulaire de consentement validé, calendrier des visites |

## 9. Risques d'exécution

| Risque | Signal d'alerte | Réponse |
|---|---|---|
| Firmware non validé à temps (R1) | Tests de sécurité du banc non verts à la fin de S2 | La pose glisse ; G0 est décalé plutôt que de poser un kit non sûr |
| Surcharge du profil mobile et web | Vélocité de E2 + E5 inférieure à 60 % du prévu deux sprints de suite | Mesures du §6 ; module 13 reporté en V1.1 |
| Pertes de mesures dans le relais | Moins de 95 % de points reçus en S4 | Journal de la file sur le téléphone, accusés de réception par lot, test 7 jours hors ligne |
| Dépendance à OctOpus | Pas de réponse aux questions de `09_octopus_ml.md` §11 avant S10 | Entraînement local (même code `agriml`), OctOpus reste facultatif |
| Données de vision insuffisantes (R9) | Moins de 300 images confirmées par classe en S10 | Modèle non publié ; collecte prolongée pendant l'hivernage |
| Retard de la déclaration CDP (R8) | Pas de récépissé avant S10 | Pas de données réelles en dehors du pilote ; option d'hébergement souverain étudiée |

Le registre complet est au §9 de `07_feuille_de_route_budget.md`.

## 10. Correspondance des 17 livrables

| N° | Livrable demandé | Document principal | Code et fichiers associés |
|---|---|---|---|
| 1 | Analyse complète du projet | `00_lecture_critique.md`, `01_analyse_metier.md`, `10_web_ux.md` §1 (prototype) | Rapport d'audit du firmware (PDF) |
| 2 | Architecture fonctionnelle | `10_web_ux.md` §2–3, `01_analyse_metier.md` §4–5 | `maquettes/index.html` |
| 3 | Architecture technique | `02_architecture.md` §1–4 | `backend/`, `CONVENTIONS.md` |
| 4 | Architecture IA | `03_ia.md`, `09_octopus_ml.md` | `ml/`, `backend/app/services/assistant/` |
| 5 | Architecture data | `04_data_mlops.md` §1–5, `02_architecture.md` §6 | `db/migrations/`, `infra/terraform/modules/datalake` |
| 6 | Architecture MLOps | `04_data_mlops.md` §6–8, `09_octopus_ml.md` §5–9 | `ml/`, `infra/k8s/base/ml` |
| 7 | Architecture cloud | `02_architecture.md` §5 | `infra/terraform/`, `infra/k8s/` |
| 8 | Base de données | `05_stack_logicielle.md` §5, `CONVENTIONS.md` §6 | `db/migrations/001_init.sql`, `002_extensions.sql` |
| 9 | APIs | `05_stack_logicielle.md` §3–4, `CONVENTIONS.md` §3–5 | `backend/app/` |
| 10 | Maquettes UX/UI | `10_web_ux.md` §4–7 | `maquettes/index.html` |
| 11 | Microservices | `02_architecture.md` §3 (monolithe modulaire, cible §3.3), ADR 001 | `infra/k8s/base/app` |
| 12 | Roadmap MVP | `07_feuille_de_route_budget.md` §1–4 | — |
| 13 | Plan de développement | Ce document | — |
| 14 | Structure du code | `CONVENTIONS.md` §1, `README.md` | Arborescence du dépôt |
| 15 | Recommandations technologiques | `05_stack_logicielle.md` §1–2 | — |
| 16 | Plan de déploiement | `11_deploiement.md` | `.github/workflows/`, `infra/` |
| 17 | Plan de sécurité | `06_devsecops.md` | Rapport d'audit du firmware, `infra/k8s/base/app/networkpolicies.yaml` |
