# 23 — Plan d'intégration : retirer les simulations dans l'ordre

> Sprint D, phase 4. Document de travail interne, confidentiel (partenaires uniquement).
> Date : 2026-11-09. Complète `22_backend_gap_analysis.md` (inventaire et écarts) et prépare `24_backend_readiness_report.md`.

## 1. Principes

1. **Contrats inchangés.** Le Doc 16 (baseline v1), les 18 contrats et le schéma Zod du Frontend ne bougent pas. Si une route ne peut pas respecter un contrat, on propose une révision **v1.x** au Doc 16 ; on n'invente aucun champ.
2. **Le backend s'aligne sur le Zod**, pas l'inverse. Les seules modifications Frontend admises sont celles que la consigne autorise : correction de bug, de régression, ou adaptation imposée par FastAPI. Aucune fonctionnalité ni refonte visuelle ; toute idée nouvelle va au backlog v1.1.
3. **Règles d'abord, ML ensuite.** Chaque service est livré d'abord avec ses règles (`source: rules`, `fallback_step: 2`, `confidence.kind: none`), ce qui est conforme au Doc 16 § 5.5. Un modèle ne remplace les règles qu'après avoir passé les critères de promotion du Doc 16 § 5.3 (voir doc 24).
4. **Un service à la fois, réversible par réglage.** Une simulation disparaît quand sa route réelle est livrée (règle posée par le doc 17 § 3). Le retour arrière ne doit jamais demander de revert de code.

## 2. Mécanique actuelle des simulations (fait vérifié)

| Élément | Constat |
|---|---|
| Bascule | `AGRI_MOCK=1` (`web/lib/mock-config.ts`) : le BFF sert **toutes** les routes depuis MSW (`mocks/`), hôte réservé `api.mock.invalid`. Sinon : `API_BASE_URL` (obligatoire). |
| Route non simulée | 404 `NOT_FOUND`, sans appel réseau (`mocks/index.ts`) |
| Granularité | Aucune : pas de mode « ce service réel, les autres simulés » |
| Validation | `parseContract` (Zod) côté BFF ; réponse non conforme = `BAD_RESPONSE` 502 |
| Blocages BFF | `auth` et `telemetry` non proxifiés par `/api/v1/[...path]` ; corps limité à 256 Kio |

Conséquence : tant que `AGRI_MOCK=1`, aucune route réelle n'est exercée par l'interface ; et dès `AGRI_MOCK` retiré, les 10 services sans route répondent par une erreur. Il faut donc un **mode hybride** (étape D0).

## 3. D0 — Préparation (avant tout retrait de simulation)

**Objectif :** rendre l'intégration possible et mesurable. Aucun service IA n'est encore branché.

| Livrable | Détail | Type de changement | Estimation |
|---|---|---|---|
| Hybride par route | Variable `AGRI_REAL_ROUTES` (liste de préfixes). En mode simulé, les URI listées sont envoyées à `API_BASE_URL`, les autres à MSW. Changement limité à `lib/server/upstream.ts` et `mocks/index.ts` | Frontend, **adaptation imposée** par FastAPI (aucun écran touché) | 1 j |
| Bloc de provenance | Module backend unique `services/provenance.py` produisant `{model_name, model_version, source, fallback_step, computed_at, data_as_of, stale, confidence}` (Doc 16 § 9.2) ; helper `rules_provenance(...)` | Backend | 1 j |
| Chaîne de repli minimale | Étendre `predict_or_503` : bundle → règles → 503, avec `fallback_step` renvoyé (R12, partie locale seulement ; le lot OctOpus attend la confirmation de son contrat) | Backend | 2 j |
| Bug E1 | `payload.crop` : l'API renvoie un objet, le Zod attend une chaîne. **Décision à prendre avec le chef de projet** : corriger l'API (renvoyer le nom de la culture) ou le Zod (accepter l'objet). Le Doc 16 ne fixe pas la forme de `payload` pour `recommendations` ; la correction côté API évite de toucher au Frontend | Backend (recommandé) | 0,5 j |
| Pluie annoncée (E2) | Renseigner `rain_forecast_mm` depuis `weather.forecast_with_cache` dans `recommendations.irrigation_payload` | Backend | 1 j |
| Test de contrat « live » | Un test qui lance l'API avec le jeu de démonstration (`seed.py`) et valide chaque réponse par le schéma Zod correspondant (Vitest côté web, serveur FastAPI de test). Sans lui, `BAD_RESPONSE` 502 n'apparaît qu'en production | Tests | 2 j |
| Gabarit de test d'inférence | Fixtures `pytest` : bundle présent, absent, empreinte SHA-256 fausse, colonne `PERSONAL_COLUMNS` | Tests | 1 j |

**Prérequis :** accord sur le point E1 ; environnement de test avec PostgreSQL ou SQLite selon `tests/conftest.py` (à confirmer).
**Risques :** le test de contrat live révèle d'autres écarts de forme (probable : c'est son rôle) ; l'hybride introduit un second chemin de code dans le BFF.
**Retour arrière :** laisser `AGRI_REAL_ROUTES` vide : comportement identique à aujourd'hui. Le bloc de provenance est additif (champ nouveau, `OptionalProvenance` accepte `null` et un objet).
**Critère de sortie :** les 5 routes existantes (météo, recommandations, rendement, rapports, assistant) passent le test de contrat live ; E1 et E2 clos.

## 4. D1 — `irrigation_need` (premier service réel)

| Rubrique | Détail |
|---|---|
| Route | `GET /v1/fields/{field_id}/irrigation-need` |
| Moteur | Règles FAO-56 existantes (`agronomy.recommend_irrigation`) + pluie annoncée à 24 h ; `defer = true` si pluie ≥ `RAIN_SKIP_MM` ; `volume_m3 = need_mm × surface` |
| Provenance | `model_name: irr_water_balance`, `source: rules`, `fallback_step: 2`, `confidence.kind: none`, `data_as_of` = dernière mesure, `stale` si la mesure dépasse la validité |
| Prérequis | D0 terminé ; surface de la parcelle renseignée (sinon `volume_m3: null`, autorisé par le Zod) ; cycle actif (sinon 404 `NO_ACTIVE_CYCLE`) |
| Risques | (1) météo indisponible : `WEATHER_UNAVAILABLE` 503, l'écran doit afficher l'état d'erreur déjà prévu ; (2) humidité manquante ou capteur défaillant : l'action `verifier_capteur` existe déjà, `need_mm` doit rester ≥ 0 et la provenance marquer `stale` ; (3) incohérence avec la carte « recommandation d'irrigation » (même moteur, deux écrans) : les deux doivent lire la même fonction |
| Tests | pytest : nominal, pluie annoncée (`defer`), pas de cycle (404), hors organisation (404), météo en échec (503), mesure périmée (`stale`), forme de provenance ; contrat live Zod ; Playwright existant relancé avec `AGRI_REAL_ROUTES=/v1/fields/*/irrigation-need` |
| Retrait de simulation | Handler `irrigation-need` de `mocks/handlers/ai.ts` désactivé (le fichier reste, pour les scénarios `stale`/`fallback`) |
| Retour arrière | Retirer le préfixe de `AGRI_REAL_ROUTES` et redémarrer le BFF : l'écran revient à la simulation. Rien à revert. |
| Estimation | 3 à 4 j (voir doc 22 § 5) |

## 5. D2 — `kit_parameters` + `device_health`

| Rubrique | `kit_parameters` | `device_health` |
|---|---|---|
| Route | `GET /v1/devices/{device_id}/parameters` ; accusé `POST …/parameters/ack` (proposé Doc 16 § 6.2) | `GET /v1/devices/{device_id}/health` |
| Moteur | Seuils depuis la table existante ; seuils NPK et étalonnage : valeurs d'usine du firmware (N < 20, P < 10, K < 80 ; étalonnage fixé à la compilation) ; `agro` depuis le cycle actif | États des capteurs depuis les drapeaux de la dernière mesure et les alertes ouvertes ; `pump_failure_48h: null` (règles) |
| Provenance | Un bloc par rubrique (`seuils`, `npk`, `etalonnage`, `agro`), `source: rules`, `confidence none` | `source: rules`, `fallback_step: 2` |
| Prérequis | Migration : table `device_parameter_sets` (version strictement croissante, `emis_a`) ; D0 | D0 ; mesures récentes en base |
| Risques | (1) **Le kit n'applique pas encore `agro`** (backlog firmware E1, doc 12) : l'API peut l'émettre, rien ne l'utilise ; ne pas annoncer l'inverse à l'utilisateur ; (2) bornes des blocs : le Zod les vérifie, un jeu hors bornes donne `BAD_RESPONSE` ; (3) l'accusé de réception réclame une écriture d'état : à limiter à `DEVICE_WRITERS` ou à la clé d'appareil ; (4) migration de schéma en production | (1) faux « panne » si la télémétrie est simplement en retard : séparer `unknown` de `fault` ; (2) coût d'une requête par kit : s'appuyer sur la dernière mesure, pas sur un balayage |
| Tests | pytest : version croissante, bornes, `applied` selon `PUT …/thresholds`, accusé idempotent, hors organisation, test de migration (`test_migrate.py` à étendre) | pytest : kit muet, capteur NPK invalide, alerte ouverte, hors organisation ; contrat live |
| Retrait de simulation | `parameters`, `health` | `health` |
| Retour arrière | Retirer les préfixes de `AGRI_REAL_ROUTES` ; la table de migration reste vide et inoffensive (migration additive) ; pas de `DROP` | idem |
| Estimation | 4 à 6 j | 3 j |

## 6. D3 — `fertilization` + `pest_risk`

| Rubrique | `fertilization` | `pest_risk` |
|---|---|---|
| Route | `GET /v1/fields/{field_id}/fertilization` | `GET /v1/fields/{field_id}/pest-risk` |
| Moteur | `fertility_status` (déjà là) + barème de doses N, P, K par culture et par stade | Règles agrométéorologiques par culture (température, humidité, phénologie) |
| Provenance | `source: rules`, `indicative: true` tant que l'étalonnage NPK n'est pas validé (obligation du Doc 16 § 6.3) | `source: rules`, `p_outbreak_7d/14d: null` |
| Prérequis | **Barème de doses validé par l'agronome (donnée absente du dépôt)** ; D0 | **Table de règles ravageurs rédigée et validée** (absente du dépôt) ; D0 |
| Risques | Dose erronée = conseil agronomique nuisible : mention « indicatif » obligatoire, aucune dose sans cycle actif ni capteur NPK valide ; barème externe à documenter | Faux positifs qui fatiguent l'utilisateur ; ne jamais exposer `disease_risk_binary` (synthétique) |
| Tests | pytest : classe NPK, `indicative`, capteur invalide (`npk_ok` faux), sans cycle (404) ; jeux de cas validés par l'agronome | pytest : un cas par règle, niveau limite, météo absente ; contrat live |
| Retrait de simulation | `fertilization`, `pest-risk` | idem |
| Retour arrière | Préfixes retirés de `AGRI_REAL_ROUTES`. Le barème et les règles sont des fichiers de données versionnés : revenir à la version précédente suffit | idem |
| Estimation | 3 j (si barème fourni) | 4 j (si règles fournies) |

**Point de blocage connu :** D3 dépend de contenu agronomique (barème, règles) que l'ingénierie ne doit pas inventer. Si l'agronome n'a pas livré ces tables à l'entrée de D3, la phase est **reportée** et D4 passe avant.

## 7. D4 — `diagnosis_analyze`

| Rubrique | Détail |
|---|---|
| Route | `POST /v1/diagnoses/analyze` (413 au-delà de la taille maximale) ; `POST /v1/diagnoses` reste l'enregistrement |
| Moteur | Inférence image via `ModelBackend` (`local` ONNX/joblib vérifié par SHA-256). À défaut de bundle : 503 `MODEL_UNAVAILABLE`, **jamais de verdict inventé** (il n'existe pas de règle de repli crédible pour une photo) |
| Provenance | `source: agriml`, `confidence.kind: class_probability`, `calibrated` vrai seulement après calibration ; abstention sous 0,7 |
| Prérequis | (1) Un bundle `vision_disease` **vérifié** (aujourd'hui : artefact synthétique, aucun bundle) ; (2) dépendances d'inférence installées (onnx…) ; (3) stockage objet confirmé pour `storage_key` ; (4) jeu d'images réelles étiquetées pour valider |
| Risques | Verdict faux présenté comme fiable (le plus grave du sprint) ; latence > 1,5 s ; images volumineuses ; confidentialité des photos (`PERSONAL_COLUMNS`) |
| Tests | pytest : bundle absent (503), empreinte fausse (refus), image trop grande (413), type MIME refusé, abstention, hors organisation ; jeu d'évaluation réel avec seuil de précision fixé avant le test |
| Retrait de simulation | `diagnoses/analyze` — **uniquement si le bundle passe les critères du Doc 16 § 5.3** ; sinon la route renvoie 503 et l'écran affiche l'état prévu |
| Retour arrière | Alias du modèle précédent (stage du `model_registry`) ou retrait du préfixe de `AGRI_REAL_ROUTES` ; pour un modèle, rollback par registre, pas par code |
| Estimation | 5 à 8 j + temps de collecte d'images, non estimable ici |

## 8. D5 — `assistant_transcribe`

| Rubrique | Détail |
|---|---|
| Route | `POST /v1/assistant/transcribe`, corps JSON `{audio_base64, content_type, duration_s ≤ 60, language_hint}` |
| Moteur | Aucun ASR local pour `wo` et `ff`. Option : fournisseur externe pour `fr`, `wo`/`ff` selon sa qualité réelle mesurée ; sinon `MODEL_UNAVAILABLE` 503 |
| Prérequis | Décision produit sur le fournisseur ; clause de confidentialité (audio = donnée personnelle) ; limite de 256 Kio du BFF à relever pour l'audio (adaptation imposée, à valider) |
| Risques | Qualité wolof/peul insuffisante ; coût ; envoi de la voix à un tiers ; limite de taille du proxy |
| Tests | pytest : trop long (`PAYLOAD_TOO_LARGE`), langue inconnue, modèle indisponible (503), limiteur 20/min ; évaluation sur un échantillon réel |
| Retrait de simulation | `transcribe` |
| Retour arrière | Retirer le préfixe ; l'écran garde la saisie texte |
| Estimation | 5 j (fournisseur externe) |

## 9. Tableau d'ordre de retrait des simulations

| Étape | Simulations retirées | Condition d'entrée | Condition de sortie |
|---|---|---|---|
| D0 | aucune (hybride + corrections) | accord sur E1 | 5 routes existantes passent le contrat live |
| D1 | `irrigation-need` | D0 | pytest et contrat live verts ; Playwright vert |
| D2 | `parameters`, `health` | D1 ; migration validée | idem ; migration réversible testée |
| D3 | `fertilization`, `pest-risk` | D1 ; **tables agronomiques fournies** | cas validés par l'agronome |
| D4 | `diagnoses/analyze` | bundle vérifié et critères § 5.3 | seuil de précision atteint sur images réelles |
| D5 | `assistant/transcribe` | fournisseur choisi | échantillon wo/ff évalué |

Les simulations des services V2 et V3 (2, 4, 10, 11, 15, 18) restent en place : `AGRI_MOCK=1` reste utile pour eux et les démonstrations.

## 10. Stratégie de rollback commune

| Niveau | Mécanisme | Délai |
|---|---|---|
| Route réelle défaillante | Retirer son préfixe de `AGRI_REAL_ROUTES`, redémarrer le BFF | minutes |
| Modèle défaillant | Remettre l'alias du modèle précédent dans `model_registry` ; la chaîne de repli retombe sur les règles (`fallback_step 2`) | minutes |
| Migration défaillante | Migrations **additives uniquement** pendant le sprint ; pas de suppression de colonne | — |
| Alerte | Repli > 5 % des appels ou erreurs OctOpus > 2 % pendant plus d'un jour : retour à l'étape précédente (seuils du Doc 16 § 5.5) | — |

## 11. Tests transverses et critères de qualité

- Couverture minimale de 80 % sur le code nouveau (règle d'équipe), mesurée par route.
- Pour chaque route : nominal, hors organisation (404), validation (400), absence de donnée (état vide), repli, forme de la provenance.
- Le Frontend n'est relancé en entier (610 tests + Playwright) qu'aux fins d'étape ; les tests unitaires du Frontend ne changent pas, puisque les contrats ne changent pas.
- Le dépôt n'étant pas versionné par git (le répertoire de travail n'est pas un dépôt), **sauvegarder le dossier avant D0** et à chaque fin d'étape.

## 12. Charge estimée du sprint (estimation)

| Étape | Jours-ingénieur |
|---|---|
| D0 | 8,5 |
| D1 | 3 à 4 |
| D2 | 7 à 9 |
| D3 | 7 (si les données agronomiques arrivent) |
| D4 | 5 à 8 |
| D5 | 5 |
| **Total** | **36 à 42 j** hors attente de données et revues |

Ces valeurs sont des ordres de grandeur d'une personne : aucune mesure de vélocité n'existe dans le dépôt.
