# 26 — Rapport Sprint D1 : premier service réel `irrigation_need`

> Confidentiel — document réservé aux partenaires du projet SmartAgri92. Ne pas publier.
> Date : 2026-11-10. Périmètre : décisions de validation D0 (patch BFF appliqué, Doc 16 non rouvert, bascule service par service, aucun travail ML).

## 1. Synthèse

| Objectif D1 | Résultat |
|---|---|
| Traiter E2 (pluie annoncée) | **Fait** — la pluie prévue entre dans les recommandations et le besoin en eau. |
| Créer et valider `GET /v1/fields/{id}/irrigation-need` | **Fait** — route réelle, 12 tests dédiés. |
| Test de contrat live | **Fait** — `npm run test:live`, 7 tests contre une vraie API, passés. |
| Brancher `irrigation_need` en réel via le mode hybride | **Fait** — validé de bout en bout à travers le BFF (`AGRI_MOCK=1` + `AGRI_SERVICES=irrigation_need=real`). |
| Aucun retrait de simulation globale | **Respecté** — les 17 autres services restent simulés par défaut. |
| Aucun travail ML | **Respecté** — la route repose sur les règles FAO-56 (`source: rules`, étape de repli 2). |

Le Frontend RC n'a pas été modifié (seul le BFF a reçu l'adaptation d'intégration validée). Le Doc 16 n'a pas été modifié.

## 2. Route réelle fonctionnelle

`GET /v1/fields/{field_id}/irrigation-need` (service 3 du Doc 16), portée par organisation (404 hors organisation, 401 sans jeton).

Réponse (exactement les 8 clés du contrat `IrrigationNeedSchema`) : `field_id`, `window_hours` (24), `need_mm`, `volume_m3`, `defer`, `defer_reason`, `rain_expected_mm`, `provenance`.

Règle de calcul (`backend/app/services/irrigation_need.py`) :

- besoin = max(0, Kc × ET0 − pluie du jour) ; volume net = besoin × surface (ha) × 10 m³/mm/ha ;
- report (`defer = true`) si un besoin subsiste et que la pluie annoncée ≥ 5 mm (`RAIN_SKIP_MM`), avec motif « Pluie annoncée … » ;
- ET0 : Hargreaves sur les mesures du kit, sinon `et0_mm` du fournisseur météo, sinon Hargreaves sur la prévision ;
- données manquantes (pas de cycle cultural, pas d'ET0) : réponse 200, `need_mm = 0`, `volume_m3 = null`, `defer = false`, `defer_reason = "Besoin non calculable : …"` ;
- météo indisponible : seule l'erreur `WEATHER_UNAVAILABLE` est absorbée (pluie inconnue → `rain_expected_mm = null`) ; toute autre erreur reste une erreur ;
- provenance : `irrigation_fao56`, source `rules`, étape de repli 2, `stale = true` si la prévision vient d'un cache périmé, `data_as_of` = date de récupération de la prévision (sinon dernière mesure du kit).

### E2 — pluie annoncée

Nouveau module `backend/app/services/field_weather.py` (prévision 7 jours via le cache météo existant). `recommendations.irrigation_payload` reçoit la prévision : `rain_expected_mm` est renseigné et une pluie ≥ 5 mm fait passer l'action à « surveiller » avec la raison chiffrée (« 12 mm … »). Météo en panne : la recommandation est calculée sans pluie (pas d'erreur).

## 3. Validation du contrat live

Outillage :

- `backend/scripts/live_stack.py` : faux serveur Open-Meteo (port 8766, pluie et ET0 réglables), base SQLite temporaire initialisée, vraie API uvicorn (port 8765), fichier de pile JSON (`web/.live-stack.json`, ignoré par Git, supprimé après usage). Aucun accès réseau externe.
- `web/vitest.live.config.ts` + `web/tests/live/irrigation-need.live.ts`, script `npm run test:live`. Jamais lancé par `npm test`.

Le test se connecte réellement (`POST /v1/auth/token`), découvre ferme et parcelle, puis valide la charge utile avec le **vrai** `IrrigationNeedSchema` Zod du Frontend RC.

| # | Cas | Résultat |
|---|---|---|
| 1 | Enveloppe + charge utile conformes au schéma Zod | OK |
| 2 | `rain_expected_mm` = 6 mm de la pile ; `need_mm > 0` ; `defer = true` ; motif « Pluie annoncée » ; volume = besoin × surface × 10 ; provenance `rules` / étape 2 / non périmée | OK |
| 3 | Le schéma n'est pas vacueux : besoin négatif, provenance absente, `window_hours = 48` sont refusés | OK |
| 4 | Parcelle inconnue → 404 enveloppe d'erreur ; sans jeton → 401 | OK |
| 5 | Via le BFF, `irrigation_need=real` : un seul appel réseau, vers l'URL exacte de l'API réelle, réponse conforme au schéma | OK |
| 6 | Via le BFF, `pest_risk` reste simulé : aucun appel réseau | OK |
| 7 | Via le BFF, `AGRI_MOCK=0` sans exception : comportement d'avant (tout vers l'API réelle) | OK |

## 4. Résultats des tests

| Suite | Résultat |
|---|---|
| Backend (pytest) | **211 passed** (dont 12 nouveaux dans `tests/test_irrigation_need.py`) |
| Web (vitest) | **627 passed**, 31 fichiers (dont 17 dans `tests/service-mode.test.ts`) |
| Web — test live | **7 passed** (pile réelle, relancé après la dernière retouche de typage) |
| `tsc --noEmit` | propre |
| ESLint (fichiers touchés) | propre |

Points couverts côté backend : forme exacte, ETc − pluie avec volume net, report à ≥ 5 mm, pluie couvrant le besoin, absence de cycle, météo en panne avec/sans kit, cache périmé, portée par organisation, erreurs non météo non absorbées, E2 (retenue et absence de pluie si météo en panne).

Non mesuré : couverture chiffrée (80 %) — non relancée dans ce sprint.

## 5. Écarts et limites constatés

1. **Topologie hybride incomplète.** Avec `AGRI_MOCK=1` + `irrigation_need=real`, les routes hors registre (auth, fermes, parcelles) restent simulées : le jeton simulé est refusé par l'API réelle et les identifiants simulés (`fld-mboro-1`) ne sont pas des UUID réels. Une configuration réaliste est `AGRI_MOCK=0` + `AGRI_SERVICES=<services non livrés>=mock`, mais les handlers simulés répondent alors 404 sur des UUID réels. Le test live contourne ce point en fournissant un jeton réel au BFF ; il ne le résout pas.
2. **Contrat non expressif pour « non calculable ».** `need_mm` n'est pas nullable : l'état est porté par `need_mm = 0`, `volume_m3 = null` et un `defer_reason` explicatif. Un champ explicite exigerait de modifier le contrat (hors périmètre).
3. **Pas de probabilité de pluie** fournie par le fournisseur météo : la règle de report utilise le cumul prévu (≥ 5 mm), pas une probabilité.
4. **Besoin net seulement** : ni efficience d'irrigation, ni pluie efficace. La pluie utilisée est le cumul du jour.
5. **Le backend ne filtre pas les routes par mode** : seul le BFF route par service. `AGRI_SERVICES` côté backend sert au journal de démarrage et aux tests, pas au blocage de routes.
6. **Panneau `/api/dev/mock` et bandeau « mock »** (`isMockMode()`) ignorent le mode par service : ils affichent l'état global, pas l'état hybride.
7. **Licence Open-Meteo** : usage commercial soumis à licence (déjà identifié) ; sans effet sur le test, qui utilise un faux serveur.
8. **Contrat OctOpus toujours non confirmé** : aucune route de D1 n'en dépend.

## 6. Fichiers

Nouveaux : `backend/app/services/field_weather.py`, `backend/app/services/irrigation_need.py`, `backend/tests/test_irrigation_need.py`, `backend/scripts/live_stack.py`, `web/lib/service-mode.ts`, `web/tests/service-mode.test.ts`, `web/vitest.live.config.ts`, `web/tests/live/irrigation-need.live.ts`.
Modifiés : `backend/app/services/recommendations.py`, `backend/app/api/v1/fields.py`, `web/lib/server/upstream.ts`, `web/app/api/v1/[...path]/route.ts`, `web/package.json` (script `test:live`), `.gitignore`.

## 7. Plan D2 (proposition, à valider)

Conditions inchangées : bascule service par service, aucun retrait global des simulations, aucun travail ML tant que le contrat OctOpus n'est pas confirmé, que les données réelles n'existent pas et que les modèles ne sont pas validés. Le Doc 16 reste gelé (weather → rules, assistant → agriml).

1. **Résoudre l'écart n°1** : alignement des identifiants simulés / réels ou repli simulé sur 404 pour permettre une bascule réelle côté navigateur sans jeton fabriqué à la main. À arbitrer : modification du BFF/mocks (adaptation d'intégration) plutôt que du Frontend RC.
2. **Service suivant à brancher** : candidats à faible dépendance, sur le même modèle (règles + contrat live) — `weather` (déjà exposé avec provenance) puis `recommendations`. Un test de contrat live par service, réutilisant `live_stack.py`.
3. **Généraliser le test live** : paramétrer par service à partir du registre (route, schéma Zod, jeu de pile), exécution manuelle ou en CI séparée.
4. **Mode par service dans l'interface de développement** : panneau `/api/dev/mock` et bandeau alignés sur `AGRI_SERVICES` (écart n°6).
5. **Affiner la règle d'irrigation** si validation agronomique : pluie efficace, efficience, probabilité de pluie (écarts 3 et 4).
6. **Option** : contrat explicite pour « besoin non calculable » — uniquement par évolution de contrat validée avec les partenaires.
7. **Hors périmètre D2 tant que les conditions ne sont pas levées** : services ML (`soil_forecast`, `yield_forecast`, `pest_risk`, `disease_diagnosis`, `price_forecast`), contrat OctOpus.
