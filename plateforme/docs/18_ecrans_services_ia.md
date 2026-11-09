# 18 — Écrans des services d'IA : sprint A et ordre des sprints suivants

Confidentiel — réservé aux partenaires de travail.

Ce document fixe les écrans web de quatre services d'IA qui n'en avaient pas : besoin d'irrigation (3), paramètres du kit (7), fertilisation (6) et risque ravageurs (9). Il donne aussi l'ordre des sprints B à D. Les décisions datent du 09/11/2026. Le document part de la baseline IA v1 du [doc 16](16_architecture_octopus.md), gelée le 08/11/2026, et du [doc 17](17_frontend_v0_1.md) v0.1.1.

- **Ce qui ne change pas** : le doc 16, les 18 contrats (`lib/contracts/`), le registre, les simulations (`mocks/`) et les docs 00 à 17, hors renvois. Un écran affiche ce que son contrat contient, rien de plus.
- **Source de vérité** : le code de `web/`. Les noms de champs cités sont ceux des schémas zod de `lib/contracts/field.ts` et `lib/contracts/device.ts`, qui recopient le doc 16 § 9.4.
- **Avant** : les 13 modules du [doc 10](10_web_ux.md) § 3 et le doc 17 (architecture du front, retrait d'une simulation au § 3, seuils au § 8). **Après** : le doc 17 est passé en v0.2 à la livraison du sprint A, puis en v0.2.1 à celle du sprint B (tableau du § 4).

**Statut d'un widget.** Chaque widget demandé reçoit un des trois statuts suivants :

| Statut | Sens | À l'écran |
|---|---|---|
| **contractuel** | Le champ existe dans le contrat du service | Valeur du contrat, avec sa provenance |
| **dérivé** | L'écran le calcule à partir de champs contractuels, du même service ou d'un autre | Mention visible de la règle de calcul ; jamais présenté comme une sortie du modèle |
| **candidat v1.x** | Le contrat ne le contient pas | Rien n'est dessiné. Le besoin est noté au § 7 pour une révision du doc 16 (§ 10 : approbation du CTO et du PO) |

Les numéros de service sont ceux du doc 16 § 9.3. Les chemins de fichiers sont relatifs à `web/`.

## 1. Décisions du 09/11/2026

| Décision | Effet |
|---|---|
| Corriger le doc 17 sur les langues | Doc 17 v0.1.1 : seul le français est disponible ; le wolof et le pulaar sont prévus, leurs fichiers de traduction sont vides. `web/README.md` est aligné. |
| Ouvrir le doc 18 | Ce document |
| Ordre du sprint A | 3 `irrigation_need`, 7 `kit_parameters`, 6 `fertilization`, 9 `pest_risk` |
| Ne pas toucher au doc 16 ni aux contrats | Les widgets hors contrat sont des candidats v1.x (§ 7), pas des champs ajoutés |
| Base de travail | Baseline IA v1 du 08/11/2026 |

| Phase | Service | Écran | Disponibilité au registre |
|---|---|---|---|
| MVP+ | 3 `irrigation_need` | `/irrigation` | MVP, V2 |
| V1.1 | 7 `kit_parameters` | `/kit` | V1.1 |
| V1.1 | 6 `fertilization` | `/fertilisation` | V1.1, V2 |
| V1.1 | 9 `pest_risk` | `/risques` | V1.1, V2 |

Les quatre routes sont **proposées** au doc 16 et absentes de `backend/app/api/v1` au 09/11/2026 :

- `GET /v1/fields/{id}/irrigation-need` ;
- `GET /v1/devices/{id}/parameters` ;
- `GET /v1/fields/{id}/fertilization` ;
- `GET /v1/fields/{id}/pest-risk`.

Les écrans se développent donc contre les simulations, qui existent déjà avec leurs tests.

## 2. Règles communes aux quatre écrans

1. **Hooks existants.** Chaque écran appelle les hooks déjà écrits dans `services/ai/` : `useIrrigationNeed`, `useKitParameters`, `useFertilization`, `usePestRisk`, plus `useWeather` pour l'irrigation. Aucun `fetch` dans un composant (doc 17 § 2).
2. **Provenance.** Chaque résultat affiche son bloc de provenance (`ProvenanceNote`) : modèle et version, source, âge du calcul et des données, confiance.
3. **Confiance.** Elle est rendue par `ConfidenceText`. Une confiance non calibrée n'est jamais affichée en pourcentage (doc 16 § 6.3). Un intervalle porte son unité.
4. **Périmé et repli.** Une valeur périmée n'est jamais montrée comme fraîche : l'étiquette « Périmé » vient de `provenanceState`. Quand `fallback_step > 0`, l'écran montre « Valeur de secours » et l'étape de repli.
5. **Abstention et vide.** Ils sont portés par la charge utile. L'écran les rend tels quels et ne remplace jamais une valeur absente par une valeur supposée : une valeur `null` s'affiche « — » ou « Non calculé ».
6. **Erreurs.** `QueryState` gère le chargement, l'erreur (avec « Réessayer ») et le vide. Une erreur 503 montre `ErrorNotice`. Un 404 qui signifie « rien de publié » est un état vide, pas une erreur (§ 4).
7. **Choix de l'objet.** Les écrans de parcelle utilisent `FieldPicker` et le paramètre d'URL `?parcelle=`, comme Météo. L'écran du kit prend le paramètre `?kit=` et une liste de kits.
8. **Textes.** Toutes les chaînes sont dans `messages/fr.json`. `wo.json` et `ff.json` restent vides : en wolof ou en pulaar, `TranslationBanner` signale que l'écran est en français.
9. **Aucune écriture.** Les quatre écrans sont en lecture. Le seul geste d'écriture lié, le réglage des seuils, reste sur l'écran Parcelle (`ThresholdForm`), avec ses droits actuels (§ 8).

**États simulés.** Les six scénarios du doc 17 § 7 servent de recette pour chaque écran. Les §§ 3 à 6 décrivent l'affichage attendu.

## 3. `/irrigation` — service 3 `irrigation_need` (MVP+)

**Contrat** : `IrrigationNeedSchema`, champs `field_id`, `window_hours` (toujours 24), `need_mm`, `volume_m3`, `defer`, `defer_reason`, `rain_expected_mm` et `provenance`. Sortie du doc 16 § 9.4 : « Besoin en mm sur 24 h ; report conseillé si pluie prévue ». La confiance est un intervalle (`interval`) en V2, ou `none` pour le bilan hydrique du MVP.

**Hooks** : `useAllFields` (socle), `useIrrigationNeed(fieldId)`, `useWeather(fieldId, 7)`.

| Widget demandé | Statut | Source | Affichage |
|---|---|---|---|
| Besoin aujourd'hui | contractuel | `need_mm` | « X mm sur les 24 prochaines heures » |
| Volume recommandé | contractuel | `volume_m3` | « Y m³ » ; `null` → « Non calculé » |
| Report d'arrosage | contractuel | `defer`, `defer_reason`, `rain_expected_mm` | Bandeau « Arrosage reporté » avec la raison du contrat, mot pour mot, et la pluie attendue (`null` → « — ») |
| Besoin sur 7 jours | dérivé | service 1, `days=7` : `et0_mm` et `precipitation_mm` par jour | « Demande climatique sur 7 jours » : Σ ET0 − Σ pluie, ramené à 0 si négatif, avec les deux termes affichés. Mention fixe : « calcul de l'écran, sans coefficient cultural ni réserve du sol ; ce n'est pas un besoin calculé par le modèle ». Seuls les jours où les deux valeurs existent comptent, et l'écran dit « sur N jours ». La provenance est celle du service 1. |
| Besoin sur 30 jours | candidat v1.x | — | Non dessiné (§ 7, C1) |
| Explication IA | dérivé, en partie | champs du contrat | Bloc « Lecture du résultat » : une phrase composée de `need_mm`, `volume_m3`, `defer` et `defer_reason`, et de l'état de la provenance. Ce n'est pas une explication produite par un modèle : l'explication générée est le candidat C2 (§ 7). |
| Confiance | contractuel | `provenance.confidence` | `ConfidenceText` avec l'unité « mm » : intervalle p10–p90 s'il existe, « Non communiquée » pour `none` |
| Provenance | contractuel | `provenance` | `ProvenanceNote` ; `irr_need_24h`, ou `irr_water_balance` en repli |

| Scénario | Ce que montre l'écran |
|---|---|
| `nominal` | Besoin, volume, intervalle de confiance calibré, provenance « À jour » ; bandeau de report si la pluie est probable |
| `stale` | Mêmes valeurs, étiquette « Périmé » |
| `fallback` | Étiquette « Valeur de secours », étape 2 (règles agronomiques), modèle `irr_water_balance` |
| `abstention` | Besoin affiché, volume « Non calculé », bandeau de report avec la raison du contrat (« Prévision trop incertaine : décision laissée aux seuils du kit. »), pluie « — » |
| `empty` | 0 mm et 0 m³ : « Pas d'arrosage nécessaire sur 24 h » |
| `error_503` | `ErrorNotice` et « Réessayer » sur le bloc du service 3 ; le bloc à 7 jours (service 1) reste indépendant |

## 4. `/kit` — service 7 `kit_parameters` (V1.1)

**Contrat** : `KitParametersSchema`, champs `device_id`, `version`, `emis_a`, `seuils{start,stop}`, `npk{n,p,k}` (seuils d'alerte en mg/kg), `etalonnage{adc_sec,adc_eau}`, `agro{culture,stade,date_semis,kc}`, `applied`, et `provenance` par bloc (`seuils`, `npk`, `etalonnage`, `agro`). Sortie du doc 16 § 9.4 : « Jeu de paramètres du § 6.1, provenance par bloc ». La confiance vaut `none`.

**Hooks** : `useDevices` (socle), `useKitParameters(deviceId)`. Durées de validité : `PARAM_VALIDITY_DAYS` (seuils 7 jours, NPK 30, étalonnage 180, agro 30) et `isBlockExpired`.

| Widget demandé | Statut | Source | Affichage |
|---|---|---|---|
| Choix du kit | socle | `useDevices` | Liste des kits de l'organisation (numéro de série, nom, parcelle) |
| Seuils d'irrigation | contractuel | `seuils`, `applied` | « Seuil conseillé : démarrage X %, arrêt Y % » tant que `applied` est faux, « Appliqué » sinon. À côté : le réglage en vigueur (`thresholds` du kit, socle) et un lien vers la parcelle du kit (`/parcelles/[id]`) pour le régler. Le web n'applique jamais un seuil conseillé (doc 17 § 8). |
| NPK | contractuel | `npk` | « Seuils d'alerte NPK (mg/kg) » : N, P, K. Ce sont des seuils d'alerte, pas des mesures, et l'écran le dit. |
| Calibration | contractuel | `etalonnage` | « Étalonnage de la sonde d'humidité » : valeur ADC à sec, valeur ADC dans l'eau |
| Culture et stade | contractuel | `agro` | Culture, stade, date de semis, Kc |
| Date de génération | contractuel | `emis_a`, `version` | « Jeu n° V, émis le … » |
| Confiance | contractuel | `provenance.*.confidence` | « Non communiquée » (`none`) |
| Provenance | contractuel | `provenance` par bloc | Un `ProvenanceNote` par bloc ; étiquette « Périmé » si `provenanceState` le dit **ou** si le bloc dépasse sa durée de validité (`isBlockExpired`), avec la durée en clair |

| Scénario | Ce que montre l'écran |
|---|---|
| `nominal` | Quatre blocs « À jour », seuils « conseillés » |
| `stale` | Étiquette « Périmé » sur les blocs concernés |
| `fallback` | « Valeur de secours » sur les blocs en repli |
| `abstention` | Stade et Kc `null` → « — » ; les autres blocs tels quels |
| `empty` | La simulation répond 404 « Aucun jeu de paramètres publié pour ce kit. » : l'écran montre cet état vide, pas une erreur |
| `error_503` | `ErrorNotice` et « Réessayer » |

Un 404 pour un kit hors de l'organisation est le même code. L'écran ne propose que les kits de `useDevices` : il ne peut donc pas le provoquer.

## 5. `/fertilisation` — service 6 `fertilization` (V1.1)

**Contrat** : `FertilizationSchema`, champs `field_id`, `crop`, `stage`, `n_kg_ha`, `p_kg_ha`, `k_kg_ha`, `npk_class` (`bas`, `moyen`, `eleve`), `indicative`, `caveat` et `provenance`. Sortie du doc 16 § 9.4 : « Doses N, P, K en kg/ha, classe NPK, mention « indicatif » tant que l'étalonnage n'est pas validé ». La confiance vaut `none` en V1.1 et sera un intervalle en V2.

**Hooks** : `useAllFields` (socle), `useFertilization(fieldId)`.

| Widget demandé | Statut | Source | Affichage |
|---|---|---|---|
| Dose recommandée | contractuel | `n_kg_ha`, `p_kg_ha`, `k_kg_ha` | Trois valeurs en kg/ha ; `null` → « Pas de dose calculée » |
| Mention « indicatif » | contractuel | `indicative`, `caveat` | Bandeau obligatoire au-dessus des doses tant que `indicative` est vrai, avec le texte de `caveat` mot pour mot |
| Classe NPK du sol | contractuel | `npk_class` | Bas, moyen ou élevé ; `null` → « — » |
| Culture et stade | contractuel | `crop`, `stage` | Tels quels ; `null` → « — » |
| Justification | dérivé | `crop`, `stage`, `npk_class`, `caveat` | Bloc « Lecture du résultat » : une phrase composée de ces champs. Ce n'est pas un raisonnement produit par le modèle. |
| Type d'engrais | candidat v1.x | — | Non dessiné (§ 7, C3) |
| Calendrier d'apport | candidat v1.x | — | Non dessiné (§ 7, C4) |
| Confiance | contractuel | `provenance.confidence` | « Non communiquée » en V1.1 ; intervalle en kg/ha en V2 |
| Provenance | contractuel | `provenance` | `ProvenanceNote` (`fert_reco`) |

| Scénario | Ce que montre l'écran |
|---|---|
| `nominal` | Doses, classe, bandeau « indicatif » |
| `stale`, `fallback` | Étiquettes « Périmé » ou « Valeur de secours » |
| `abstention` | Doses et classe NPK `null` : « Pas de dose calculée » et « — », bandeau et `caveat` maintenus |
| `empty` | Doses `null` : « Pas de dose calculée », classe NPK affichée, bandeau et `caveat` maintenus |
| `error_503` | `ErrorNotice` et « Réessayer » |

Les doses valent aussi `null` pour une culture que la simulation ne connaît pas.

## 6. `/risques` — service 9 `pest_risk` (V1.1)

**Contrat** : `PestRiskSchema`, champs `field_id`, `pests[]` et `provenance`. Chaque entrée de `pests[]` porte `pest_code`, `level` (`low`, `medium`, `high`), `p_outbreak_7d`, `p_outbreak_14d` et `factors[]`. Sortie du doc 16 § 9.4 : « Par ravageur ou maladie : niveau, P(foyer à 7 et 14 jours), facteurs ». La confiance est une probabilité (`probability`) pour le modèle appris, `none` pour les règles.

**Hooks** : `useAllFields` (socle), `usePestRisk(fieldId)`.

| Widget demandé | Statut | Source | Affichage |
|---|---|---|---|
| Score de risque | dérivé | `pests[].level` | « Niveau le plus élevé parmi les organismes suivis » : faible, moyen ou élevé. Ce n'est pas un score calculé par le modèle. |
| Ravageurs | contractuel, avec un dictionnaire d'affichage | `pests[]` | Une ligne par organisme : nom, niveau, P à 7 et à 14 jours, facteurs |
| Maladies potentielles | contractuel, avec un dictionnaire d'affichage | `pests[]` | Même présentation, dans une section distincte |
| P(foyer) à 7 et 14 jours | contractuel | `p_outbreak_7d`, `p_outbreak_14d` | En % **seulement** si `showsAsPercent(p, provenance.confidence.calibrated)` est vrai ; sinon le niveau seul et la mention « probabilité non calibrée ». `null` → « — ». |
| Facteurs météo | candidat v1.x pour la séparation | `factors[]` | Les facteurs forment une seule liste « Facteurs », sans séparer météo et culture (§ 7, C5) |
| Facteurs cultures | candidat v1.x pour la séparation | `factors[]` | Même liste |
| Confiance | contractuel | `provenance.confidence` | « Non calibrée : aucun pourcentage affiché », ou « Non communiquée » pour les règles |
| Provenance | contractuel | `provenance` | `ProvenanceNote` ; `pest_phenology`, ou `risk_rules` en repli |

**Ravageur ou maladie.** Le contrat ne dit pas si un `pest_code` est un ravageur ou une maladie. L'écran lit donc un dictionnaire d'affichage statique, dans `messages/fr.json`, qui donne pour chaque code un nom et un type. Ce dictionnaire ne change pas le contrat. Un code inconnu s'affiche tel quel, dans une section « Non classé ». La simulation n'émet que des insectes (`thrips_tabaci`, `tuta_absoluta`, `helicoverpa_armigera`, `plutella_xylostella`, `phthorimaea_operculella`) : en mode simulé, la section « Maladies » montre « Aucune maladie suivie pour cette culture ». Un type porté par le contrat lui-même est le candidat C6.

| Scénario | Ce que montre l'écran |
|---|---|
| `nominal` | Organismes de la culture, niveaux, facteurs. La simulation déclare une probabilité non calibrée : P n'est pas affichée en % |
| `stale` | Étiquette « Périmé » |
| `fallback` | « Valeur de secours » (`risk_rules`, étape 2) ; P `null` → « — », niveaux et facteurs maintenus |
| `abstention` | P `null` → « — », niveaux et facteurs maintenus |
| `empty` | `pests` vide : « Aucun organisme suivi pour cette parcelle » (c'est le cas de la carotte en simulation) |
| `error_503` | `ErrorNotice` et « Réessayer » |

## 7. Candidats de révision v1.x du doc 16

Ces widgets ont été demandés mais n'existent pas dans les contrats de la baseline v1. Aucun n'est ajouté par ce document. Chacun est à soumettre au CTO et au PO selon le doc 16 § 10 ; s'il est accepté, le contrat change d'abord, puis la simulation, puis l'écran.

| N° | Service | Widget | Ce qui manque | Piste |
|---|---|---|---|---|
| C1 | 3 | Besoin sur 30 jours | `window_hours` vaut toujours 24, et la météo s'arrête à 16 jours (`WEATHER_MAX_DAYS`) | Un horizon long dans le service 3, ou une projection climatologique à part, avec sa propre confiance |
| C2 | 3 | Explication IA | Aucun champ d'explication | Un champ `explanation` : facteurs principaux et texte court, avec sa provenance |
| C3 | 6 | Type d'engrais | Le contrat donne des doses d'éléments, pas des produits | `products[]` : produit, dose en kg/ha |
| C4 | 6 | Calendrier d'apport | Aucun champ de calendrier | `schedule[]` : stade ou date, dose |
| C5 | 9 | Facteurs météo et facteurs cultures | `factors[]` est une liste de textes | `factors[]` typé : `{kind: "meteo" \| "culture" \| …, label}` |
| C6 | 9 | Ravageur ou maladie | Aucun type par organisme | Un champ `kind` par entrée de `pests[]`, qui remplacerait le dictionnaire d'affichage |

## 8. Navigation, rôles et textes

**Navigation.** Les quatre écrans ne sont pas des modules du doc 10 : ce sont des **écrans de service**. `MODULES` (`lib/modules.ts`) garde ses 13 modules et son test. Une liste distincte, `SERVICE_SCREENS`, décrit les écrans de service. `Sidebar` les affiche dans leur groupe, après les modules, avec l'étiquette de version :

| Écran | Groupe | Étiquette | Service |
|---|---|---|---|
| `/irrigation` | IA | aucune (MVP) | 3 |
| `/risques` | IA | V1.1 | 9 |
| `/fertilisation` | Cultures | V1.1 | 6 |
| `/kit` | Matériel | V1.1 | 7 |

La barre d'onglets mobile ne change pas (`MOBILE_TABS`) : les écrans de service sont joignables par « Menu ». Le titre d'onglet passe par `moduleMetadata`, dont le type `ModuleTitleKey` reçoit les quatre clés.

**Rôles.** Les quatre rôles (agriculteur, responsable de coopérative, agronome, administrateur) lisent les quatre écrans dans leur organisation. Aucun écran n'écrit. Le lien de l'écran du kit vers la parcelle mène à `ThresholdForm`, dont les droits ne changent pas : l'agronome ne règle pas les seuils (`THRESHOLD_WRITERS`, doc 10 § 3.3).

**Textes.** Nouveaux espaces de noms dans `messages/fr.json` : `irrigation`, `kit`, `fertilization`, `pestRisk`, `pests` (dictionnaire d'affichage), plus quatre clés dans `modules`. `npm run i18n:check` doit passer sans erreur.

## 9. Plan de fichiers du sprint A

Pour chaque écran :

| Élément | Fichier |
|---|---|
| Page | `app/[locale]/(app)/{irrigation,kit,fertilisation,risques}/page.tsx`, sur le modèle de `meteo/page.tsx` |
| Écran | `features/irrigation/IrrigationView.tsx`, `features/kit/KitView.tsx`, `features/fertilization/FertilizationView.tsx`, `features/pest-risk/PestRiskView.tsx` |
| Calculs d'affichage | fonctions pures dans `lib/` (demande climatique à 7 jours, lecture du résultat, niveau maximal, classement par type) |
| Tests | tests Vitest de ces fonctions pures dans `tests/` ; les hooks sont déjà couverts par `tests/hooks.test.ts` |
| Navigation | `lib/service-screens.ts`, `components/Sidebar.tsx`, `lib/server/page-metadata.ts` |

**Hors périmètre** : `lib/contracts/`, `mocks/`, `services/ai/`, le doc 16, et les docs 00 à 15.

**Fini quand**, pour chaque écran :

- `npm run lint`, `npm run typecheck`, `npm run i18n:check`, `npm run test:coverage` et `npm run build` réussissent ;
- les six scénarios ont été passés en revue avec le panneau « Régler la simulation » ;
- chaque fichier source fait moins de 800 lignes.

À la fin du sprint, le doc 17 passe en v0.2 : son § 4 reçoit les quatre écrans, et la liste des services sans écran passe de onze à sept.

## 10. Sprints B à D

**Sprint B — santé du matériel, voix, diagnostic (livré le 09/11/2026, dans cet ordre).**

| Service | Écran | Remarques |
|---|---|---|
| 8 `disease_diagnosis` (V2) | `/maladies`, aujourd'hui une coquille | Photo, puis verdict ; abstention sous `VISION_ABSTAIN_BELOW` (0,7) : « incertain, faites vérifier ». Route d'analyse proposée ; `POST /v1/diagnoses` existe. **Livré** : `diagnosis/DiagnosisView`, photo réduite dans le navigateur, verdict recalculé côté web. |
| 17 `assistant_transcribe` | `/assistant` | Saisie vocale qui alimente le chat existant (service 16). Route proposée. **Livré** : `assistant/VoiceInput`, le texte va dans le brouillon, jamais envoyé seul. |
| 13 `device_health` | `/kit` et `/equipements` | État par capteur (`ok`, `degraded`, `fault`, `absent`) et risque de panne de pompe à 48 h. **Livré** : `kit/KitHealth`, affiché sur /kit et sur /equipements. |

La décision du 09/11 cite « santé des équipements (service 15) ». Dans le doc 16 § 9.3, la santé des équipements est le service **13** `device_health` ; le service 15 est `price_forecast` (prévision de prix). Ce document retient le service 13. Si la prévision de prix était visée, elle s'ajoute au sprint B sans rien changer d'autre.

**Sprint C — langues et tests d'interface.**

- **Wolof et pulaar** : traductions réelles de `messages/wo.json` et `messages/ff.json`, relues par des locuteurs natifs. Le bandeau `TranslationBanner` disparaît pour une langue quand son fichier est complet et que `i18n:check` le confirme.
- **Playwright** : parcours de bout en bout en mode simulé (connexion, tableau, parcelle, réglage de seuil, irrigation, alerte).
- **React Testing Library** : tests de composants avec un DOM. Il faut ajouter `jsdom` ou `happy-dom` en dépendance de développement, avec une version épinglée et publiée depuis au moins deux semaines, et choisir l'environnement de test fichier par fichier, pour que les tests actuels restent en environnement Node.

**Sprint D — première connexion à l'API réelle.**

1. **Validation des contrats.** Les schémas zod sont comparés au schéma OpenAPI de FastAPI pour chaque route **existante**. Un écart est une question pour le doc 16 § 10, pas une correction silencieuse.
2. **Retrait des simulations**, selon la procédure du doc 17 § 3 (test de contrat, suppression, registre, rien d'autre). Ordre proposé :
   - d'abord les routes existantes, en commençant par la météo (1), puis les recommandations (5), les alertes (13), les rapports (14), la carte (18), le rendement (12), l'assistant (16) et les seuils (7, `GET` et `PUT /thresholds`) ;
   - ensuite les routes proposées, dans l'ordre du sprint A (3, 7, 6, 9), puis les autres, chacune quand le backend la code et qu'une révision v1.x du doc 16 passe son statut à `existing`.
3. **Environnement.** Une session ne mélange jamais simulé et réel (doc 17 § 3). Le sprint D se fait donc contre l'API d'intégration, sans `AGRI_MOCK`, avec `API_BASE_URL`.

## 11. Limites

1. **Pas de test d'interface avant le sprint C.** Les écrans du sprint A sont vérifiés par `next build`, par les tests des fonctions pures et par une revue dans les six scénarios.
2. **Demande climatique à 7 jours.** Elle ignore le coefficient cultural et la réserve du sol. C'est un ordre de grandeur, présenté comme tel, pas un besoin.
3. **Maladies en simulation.** La simulation ne connaît que des insectes : la section « Maladies » de `/risques` reste vide tant que l'API ou une révision de la simulation n'envoie pas de code de maladie.
4. **Dictionnaire des organismes.** Il vit dans le front tant que le contrat ne porte pas de type (C6). Un code nouveau s'affiche brut, dans « Non classé ».
5. **Routes proposées.** Aucune des quatre routes du sprint A n'existe côté backend. Les écrans livrés au sprint A ne se branchent sur l'API qu'au sprint D, route par route.

## 12. Journal

| Version | Date | Changement |
|---|---|---|
| v0.1 | 09/11/2026 | Première version : décisions du 09/11, écrans des services 3, 7, 6 et 9, candidats v1.x, navigation, plan du sprint A, sprints B à D. |
