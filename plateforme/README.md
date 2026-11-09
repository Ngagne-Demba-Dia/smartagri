# SmartAgri92 — plateforme

Confidentiel — réservé aux partenaires de travail. Ne pas publier ce dépôt ni ces documents.

Ce dossier contient l'étude complète et le code de départ de la plateforme SmartAgri92 : kit d'irrigation intelligent (ESP32-S3), application mobile, plateforme web et cloud, IA agronomique et cadre de modèles pour les compétitions.

L'expérimentation, l'entraînement et le suivi des modèles se font sur **OctOpus ML** (https://octopus.ml/app). La base PostgreSQL et S3 restent la source de vérité, MLflow le registre de référence ; seuls des instantanés pseudonymisés partent vers OctOpus, jamais le jeu de test final. Le cadre complet est dans `docs/09_octopus_ml.md`.

## Comment lire les recommandations

Chaque choix important est présenté en trois variantes :

| Variante | Sens pour un modèle d'IA | Sens pour le logiciel et l'infrastructure |
|---|---|---|
| **Compétition** | Meilleur score sur la métrique officielle (ensembles, gros modèles, validation croisée poussée) | Meilleure démonstration en un temps limité |
| **Production** | Fiable, explicable, peu coûteux à faire tourner, surveillé | Cible à 10 000 kits, sécurité et exploitation complètes |
| **Compromis** | Ce que l'on construit maintenant sans se fermer la route vers la production | idem |

## Documents

| Fichier | Contenu |
|---|---|
| [CONVENTIONS.md](CONVENTIONS.md) | Contrats communs : arborescence, schéma de télémétrie, MQTT, API, base, variables d'environnement |
| [docs/00_lecture_critique.md](docs/00_lecture_critique.md) | Lecture critique du dossier projet et du firmware : forces, 20 lacunes, priorités |
| [docs/01_analyse_metier.md](docs/01_analyse_metier.md) | Synthèse, contexte, personas, cas d'usage, parcours utilisateurs, indicateurs, modèle économique |
| [docs/02_architecture.md](docs/02_architecture.md) | Architectures terrain, applicative, microservices, cloud, données, sécurité ; décisions (ADR) |
| [docs/03_ia.md](docs/03_ia.md) | Les 10 cas d'usage IA, modèles, gouvernance, ingénierie des prompts |
| [docs/04_data_mlops.md](docs/04_data_mlops.md) | Data lake, ingestion, ETL, gouvernance, MLOps, dérive, réentraînement, observabilité IA |
| [docs/05_stack_logicielle.md](docs/05_stack_logicielle.md) | Choix technologiques, API REST v1, API locale du kit, schéma de base |
| [docs/06_devsecops.md](docs/06_devsecops.md) | CI/CD, chaîne d'approvisionnement, OWASP API et LLM, IoT, cloud, secrets, supervision, tests, conformité |
| [docs/07_feuille_de_route_budget.md](docs/07_feuille_de_route_budget.md) | Versions, Gantt 24 mois, MVP, portes de passage, équipe, BOM du kit, budget en trois scénarios, risques |
| [docs/08_competition_ia.md](docs/08_competition_ia.md) | Méthode de compétition : analyse du règlement, validation, features, ensembles, plan d'amélioration du score |
| [docs/09_octopus_ml.md](docs/09_octopus_ml.md) | OctOpus ML comme hub IA : flux de données, pseudonymisation, registre, repli, coûts, risques, questions au fournisseur |
| [docs/10_web_ux.md](docs/10_web_ux.md) | Analyse du prototype « Tableau de bord du champ », 13 modules web, parcours, maquettes, accessibilité, i18n |
| [docs/11_deploiement.md](docs/11_deploiement.md) | Environnements, GitOps, migrations, sauvegardes, retour arrière, exploitation |
| [docs/12_plan_developpement.md](docs/12_plan_developpement.md) | Épopées, sprints M1–M6, définition de « terminé », équipe (RACI), correspondance des 17 livrables |
| [docs/13_inventaire_donnees.md](docs/13_inventaire_donnees.md) | Inventaire des données : sources, jeux par zone du lac, classification, données personnelles, AIPD |
| [docs/14_cartographie_modeles.md](docs/14_cartographie_modeles.md) | Cartographie des 39 modèles : usages, données, métriques, plateformes, replis, page locale du kit |
| [docs/15_acquisition_donnees.md](docs/15_acquisition_donnees.md) | Stratégie d'acquisition : licences, vagues, étiquetage, clauses partenaires, coûts, contrôles de conformité |
| [docs/16_architecture_octopus.md](docs/16_architecture_octopus.md) | Référence IA, Data et MLOps (baseline v1) : export vers OctOpus, programmes, orchestration, mise en production, kit, écarts, 18 services pour la phase web |
| [docs/17_frontend_v0_1.md](docs/17_frontend_v0_1.md) | Frontend v0.1 : écrans, 18 services simulés avec provenance et confiance, scénarios, retrait d'une simulation, passage à l'API réelle |
| [docs/18_ecrans_services_ia.md](docs/18_ecrans_services_ia.md) | Écrans des services 3, 7, 6 et 9 (sprint A), candidats de révision v1.x du doc 16, ordre des sprints B à D |

## Les 17 livrables

| N° | Livrable | Où le trouver |
|---|---|---|
| 1 | Analyse complète du projet | `docs/00`, `docs/01`, `docs/10` §1 |
| 2 | Architecture fonctionnelle | `docs/10` §2–3, `docs/01` §4–5 |
| 3 | Architecture technique | `docs/02` §1–4, `CONVENTIONS.md` |
| 4 | Architecture IA | `docs/03`, `docs/09` |
| 5 | Architecture data | `docs/04` §1–5, `docs/02` §6 |
| 6 | Architecture MLOps | `docs/04` §6–8, `docs/09` §5–9 |
| 7 | Architecture cloud | `docs/02` §5, `infra/` |
| 8 | Base de données | `docs/05` §5, `CONVENTIONS.md` §6, `db/migrations/` |
| 9 | APIs | `docs/05` §3–4, `CONVENTIONS.md` §3–5 |
| 10 | Maquettes UX/UI | `docs/10` §4–7, `maquettes/index.html` |
| 11 | Microservices | `docs/02` §3, ADR 001 |
| 12 | Roadmap MVP | `docs/07` §1–4 |
| 13 | Plan de développement | `docs/12` |
| 14 | Structure du code | `CONVENTIONS.md` §1, section « Code » ci-dessous |
| 15 | Recommandations technologiques | `docs/05` §1–2 |
| 16 | Plan de déploiement | `docs/11` |
| 17 | Plan de sécurité | `docs/06`, rapport d'audit du firmware |

Le détail (code et fichiers associés à chaque livrable) est dans `docs/12_plan_developpement.md` §10.

## Code

| Dossier | Contenu |
|---|---|
| `backend/` | API FastAPI (monolithe modulaire) : authentification, organisations, exploitations et parcelles, kits, télémétrie, séries, seuils, alertes, recommandations, campagnes, équipements et maintenance, météo, prévision de rendement, rapports, assistant ; inférence avec repli (`app/services/inference/`) |
| `db/migrations/` | Schéma PostgreSQL 16 + TimescaleDB + PostGIS (hypertable, agrégats continus, RLS), appliqué par `python -m app.db.migrate` |
| `ml/` | Package `agriml` : validation croisée sans fuite, features agronomiques, ensembles, optimisation, suivi, vision, dérive ; client OctOpus (`octopus/`) et MLOps (`mlops/` : registre, promotion, réentraînement) |
| `web/` | Plateforme web Next.js (BFF, 13 modules) |
| `mobile/` | Application Flutter (lecture locale du kit, file hors ligne, relais vers le cloud) |
| `maquettes/` | Maquette HTML cliquable des écrans web, thèmes clair et sombre (locale, non publiée) |
| `infra/` | Terraform (AWS), Kubernetes (Kustomize, ArgoCD), observabilité, scripts GitOps |
| `.github/workflows/` | CI et CD |
| `docker-compose.yml`, `Makefile` | Environnement local complet ; `make help` liste les commandes |

## Démarrage rapide

```bash
# Environnement local (API, base, MQTT, stockage objets, MLflow)
cp .env.example .env          # puis renseigner les secrets
make mqtt-passwd
make up                       # ou : docker compose up -d ; le service migrate applique db/migrations avant l'API
make migrate                  # réapplique les migrations en attente (sans effet si tout est appliqué)

# Tests
make test-backend             # cd backend && python -m pytest -q
make test-ml                  # cd ml && python -m pytest -q
make smoke-ml                 # entraînement de fumée sur données synthétiques

# Entraîner une expérience
cd ml && python -m agriml.train --config configs/<experience>.yaml
```

Ne jamais installer le paquet PyPI `octopus-ml` : il n'a aucun lien avec OctOpus ML. Le client utilisé ici est écrit avec `httpx` (`ml/src/agriml/octopus/client.py`).

## État de vérification

À compléter avec les résultats réels.

## En attente

Ces éléments n'ont pas encore été fournis ; le travail a été conçu pour les intégrer sans refonte :

1. **Le second document du projet.** Ont été analysés : le dossier projet (PDF), le firmware et le prototype web « Tableau de bord du champ ».
2. **Le règlement et les données de la compétition.** Le cadre `agriml` est indépendant de la métrique : il suffit d'écrire un fichier de configuration (métrique, cible, schéma de validation, groupes) pour lancer une première référence.

## Points d'attention

- **Le firmware v1.1 n'a été ni compilé ni testé sur le matériel.** Toute la plateforme en dépend : sa validation sur banc est la première tâche (porte G0).
- **Aucune opération irréversible** (chiffrement flash, Secure Boot, eFuses) n'a été appliquée. Elle est planifiée pour l'industrialisation.
- Les montants, les effectifs et les indicateurs sont des **hypothèses à valider**.
- **OctOpus ML** : l'API exacte, la localisation des données, le format des modèles exportés et les prix sont à confirmer avec le fournisseur (`docs/09_octopus_ml.md` §11). Aucune donnée du projet n'y a été envoyée pendant cette étude.
- Les traductions en wolof et en pulaar devront être relues par des locuteurs natifs.
