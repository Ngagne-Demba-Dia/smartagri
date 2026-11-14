# 25 — Rapport D0 : préparer l'intégration Frontend ↔ Backend

> Confidentiel — partenaires uniquement. Sprint D, étape D0. Branche Git : `sprint-d` (déjà existante, conservée).
> Références : doc 22 (écarts), doc 23 (plan), doc 24 (état de préparation), doc 16 baseline v1 (gelée, non modifiée).

## 1. Résumé

D0 corrige le bug E1, ajoute le bloc de provenance du Doc 16 § 9.2 sur 4 routes, code la chaîne de repli minimale et le registre « service par service » (mode hybride). **Aucun fichier de `web/` n'a été modifié**, aucune simulation retirée, aucun contrat Zod ni le Doc 16 touchés.

| Tâche | État |
|---|---|
| 1. Branche Sprint D | `sprint-d` existait déjà et est active : rien à recréer |
| 2. Écarts Backend / Doc 16 | § 2 ci-dessous (doc 22 vérifié et mis à jour) |
| 3. Bug E1 | Corrigé côté API |
| 4. Mode hybride | Registre backend livré ; patch BFF fourni **non appliqué** (§ 4.3) |
| 5. Bloc Provenance | 4 routes (§ 4.2) |
| 6. Repli minimal | Livré (§ 4.4) |
| 7. Rapport D0 + préparation D1 | Ce document, § 5 à 7 |

## 2. Écarts Backend / Doc 16 (état après D0)

| Écart (doc 22) | Avant D0 | Après D0 |
|---|---|---|
| E1 `crop` objet / chaîne | Ouvert | **Fermé** |
| E2 `rain_forecast_mm` jamais renseigné | Ouvert | Ouvert — premier travail de D1 |
| E3 aucune route n'envoie `provenance` | Ouvert | **Partiellement fermé** : 4 routes sur celles qui acceptent `OptionalProvenance` |
| E4 chaîne de repli non codée | Ouvert | **Fermé (minimal)** : bundle → OctOpus → règles → 503 |
| E5 bascule de simulation globale | Ouvert | **Moitié backend fermée** ; la moitié BFF attend votre décision (§ 4.3) |
| E6 aucun test d'inférence / provenance | Ouvert | **Partiellement fermé** : 28 tests (`tests/test_sprint_d0.py`) ; suite complète : 199 verts (171 avant D0) ; pas de test de contrat « live » |
| E7 contrat OctOpus non confirmé | Ouvert | Ouvert — l'étape 1 de la chaîne existe mais reste inutilisable tant que le contrat n'est pas confirmé |

Routes pas encore couvertes par la provenance : les routes **proposées** (`irrigation-need`, `kit_parameters`, `device_health`, etc.) n'existent pas encore ; leur schéma exige `ProvenanceSchema` (non nul), elles l'émettront dès leur création. Les alertes et les KPI n'ont pas de champ `provenance` dans les contrats : rien à ajouter.

## 3. Ce qui a été corrigé

**E1 — `crop`.** `irrigation_payload` renvoyait le dict `crop_state` dans `payload.crop`, alors que le Frontend attend une chaîne ou `null` (`IrrigationPayloadSchema`, 502 `BAD_RESPONSE` en mode réel).
- `payload.crop` = code de culture (`"onion"`) ou `null` sans cycle actif.
- Le détail (nom, jour, stade, Kc) n'est pas perdu : il passe dans `payload.crop_state` (champ ajouté, ignoré par le Zod non strict).
- Les recommandations déjà stockées en base avec l'ancienne forme sont **normalisées à la lecture** (`recommendation_view`), sans réécrire la base ni muter la ligne.

## 4. Ce qui a été ajouté

### 4.1 Fichiers

| Fichier | Rôle |
|---|---|
| `app/services/provenance.py` | Construit et valide le bloc § 9.2 (mêmes règles que le Zod : `none` sans valeur, `interval` avec p10 ≤ p90, source ∈ agriml/octopus/rules, repli 0..2) |
| `app/services/inference/fallback.py` | `predict_with_fallback` ; `predict_or_503` en est le cas à un seul moteur (comportement inchangé) |
| `app/core/service_modes.py` | Registre `real`/`mock` par service |
| `tests/test_sprint_d0.py` | Tests de D0 |
| Modifiés | `recommendations.py`, `weather.py`, `yield_forecast.py`, `assistant/service.py`, `api/v1/fields.py`, `inference/factory.py`, `core/config.py`, `main.py`, `.env.example` |

### 4.2 Provenance émise

| Route | `model_name` | `source` / `fallback_step` | Confiance | `stale` |
|---|---|---|---|---|
| `GET /fields/{id}/recommendations` (par élément) | `irrigation_fao56` / `fertility_rules` | `rules` / 2 | `none` | `false` |
| `GET /fields/{id}/weather` | nom du fournisseur | `rules` / 2 | `none` | `true` si cache périmé |
| `GET /fields/{id}/yield-forecast` | modèle du registre | `agriml` ou `octopus` (lu dans `model_registry`) / 0 ou 1 | `interval` (p10, p90), `calibrated=false` | `true` si lue sans `refresh` et âgée de plus de 24 h |
| `POST /assistant/chat` | `assistant_llm` (version = modèle utilisé) | `agriml` / 1 si repli de modèle | `none` | `false` |

Choix à valider (l'enum du Doc 16 est gelée) :
- **Météo** : une prévision brute d'un fournisseur n'est pas un modèle AgriML ; `rules` est la source la plus proche. L'écran affichera donc « valeur de secours » pour la météo en mode réel.
- **Assistant** : pas de source « LLM externe » dans l'enum ; `agriml` est utilisé, le modèle réel figure dans `model_version`.
- **Recommandations** : `fallback_step=2` est correct (règles, pas du ML) mais l'UI l'affiche aussi comme « valeur de secours ». À arbitrer côté produit, pas côté contrat.
- **Prévision de rendement** : `calibrated=false` par prudence (aucune calibration mesurée), donc jamais affichée en pourcentage.

### 4.3 Mode hybride

Syntaxe unique, lue de la même façon par le backend et (après décision) par le BFF :

```
AGRI_MOCK=1                      # défaut de tous les services : mock (0 → real)
AGRI_SERVICES=irrigation_need=real,kit_parameters=mock,device_health=mock,fertilization=mock,pest_risk=mock,diagnosis_analyze=mock,assistant_transcribe=mock
```

- Les 18 services du Doc 16 § 9.3 ; `diagnosis_analyze` est accepté comme alias de `disease_diagnosis`.
- Un nom ou un mode inconnu **stoppe le démarrage** (`ConfigError`) : une faute de frappe ne laisse pas un service en simulation sans qu'on le sache.
- Les modes sont journalisés au démarrage (`Modes des services (défaut=…) : …`).
- `Settings.service_modes.is_real("irrigation_need")` est disponible pour les routes (D1).

**Décision en attente (contrainte « ne pas toucher au Frontend RC »).** Le doc 23 place l'aiguillage dans le BFF (`web/lib/mock-config.ts`, `web/lib/server/upstream.ts`), donc dans `web/`. Je ne l'ai pas modifié. Patch proposé, à appliquer seulement sur votre accord :

```ts
// web/lib/mock-config.ts — ajouter
const REAL_BY_DEFAULT = process.env.AGRI_MOCK !== "1";
export function serviceMode(service: string): "real" | "mock" {
  const entry = (process.env.AGRI_SERVICES ?? "").split(",")
    .map((p) => p.trim().split("=")).find(([name]) => name === service);
  return entry?.[1] === "real" ? "real" : entry?.[1] === "mock" ? "mock" : REAL_BY_DEFAULT ? "real" : "mock";
}
// web/lib/server/upstream.ts — upstreamFetch choisit le chemin par préfixe de route
//   const service = serviceForPath(new URL(input).pathname);   // table chemin → service
//   if (serviceMode(service) === "real") return fetch(input.replace(MOCK_BASE, apiBaseUrl()), init);
```

La validation Zod reste dans `parseContract` pour les deux chemins (risque R-09). Avec `AGRI_MOCK=0` et `AGRI_SERVICES` vide, le comportement actuel est strictement conservé.

### 4.4 Chaîne de repli

`predict_with_fallback(backends, model, rows, rules=None)` : essaie chaque moteur dans l'ordre (le premier qui répond gagne), puis la fonction de règles, sinon `MODEL_UNAVAILABLE` 503. Le résultat porte `step` (0 bundle local, 1 OctOpus, 2 règles) et `engine`, directement utilisables pour `fallback_step`. Les détails techniques restent dans les journaux, jamais dans la réponse.

**Limite assumée** : `build_backend` ne construit toujours qu'un seul moteur (`INFERENCE_BACKEND`). La chaîne multi-moteurs est prête mais pas encore câblée aux routes ; aucune route ML n'est ouverte, donc rien n'en dépend.

## 5. Services prêts à passer en réel

| Service | Prêt ? | Remarque |
|---|---|---|
| `irrigation_need` | **Oui, après E2** | Règles FAO-56 codées et testées ; provenance `rules`. Route à créer (D1) |
| `weather` | Oui | Route existante, provenance ajoutée, contrat conforme (au choix de source près, § 4.2) |
| `recommendations` | Oui | E1 corrigé, provenance ajoutée |
| `yield_forecast` | Route oui, **modèle non** | Aucun modèle validé ; renvoie 503 sans modèle en registre. À garder en mock pour l'usage réel |
| `assistant_chat` | Oui (si clé API) | Provenance ajoutée ; dépend de `ANTHROPIC_API_KEY` |
| `water_savings` (reports) | Route existante | Pas de provenance dans le contrat ; non vérifié ici |
| `kit_parameters`, `device_health`, `fertilization`, `pest_risk`, `diagnosis_analyze`, `assistant_transcribe` et les autres | **Non** | Route absente ou partielle (doc 22) ; rester en `mock` |

## 6. Risques restants

1. **R-01 (haute)** : aucun test de contrat « live » validant les vraies réponses avec les vrais schémas Zod. E1 en était un cas avéré ; d'autres écarts de forme peuvent exister. À faire en tête de D1 (script hors `web/`).
2. **E2** : le conseil d'irrigation ignore toujours la pluie annoncée.
3. **Décision BFF** : tant que le patch § 4.3 n'est pas appliqué, le mode hybride existe côté backend seulement ; le Frontend reste en bascule globale.
4. **Enum de provenance gelée** : météo et assistant sont représentés par la source la plus proche (§ 4.2), pas la plus exacte.
5. **E7 / R-06** : contrat OctOpus non confirmé ; l'étape 1 de la chaîne est inutilisable.
6. **R-02** : aucun modèle ML prêt (données synthétiques) ; ne rien présenter comme prédictif.
7. **Confidentialité** : documents et code restent locaux ; rien n'a été publié.
8. Le gabarit de test d'inférence demandé par E6 n'est pas fait (seul le repli est testé avec des moteurs factices).

## 7. Préparation de D1 — `irrigation_need`

Premier service réel, en règles FAO-56 (`source: rules`), pas du ML. Étapes proposées (3 à 4 jours, doc 23) :

1. **E2** : renseigner `rain_forecast_mm` depuis la météo en cache (somme sur 24 à 48 h) dans `irrigation_payload` ; ajouter `defer` et `rain_expected_mm` à la sortie.
2. Nouvelle route `GET /v1/fields/{field_id}/irrigation-need` (nom du service : `irrigation_need`), schéma `IrrigationNeedSchema` du Zod comme référence, `provenance` obligatoire via `rules_provenance("irrigation_fao56", ENGINE_VERSION, …)`, accès par `access.get_field_for` (isolation entre organisations).
3. Route conditionnée par `settings.service_modes` si l'on veut qu'elle réponde `503`/404 tant que le service est en `mock`.
4. Tests : cas nominal, pas de cycle, capteur invalide, pluie annoncée (report), isolation entre organisations, forme de la provenance.
5. Script de contrat « live » : appeler la route réelle et valider la réponse avec `IrrigationNeedSchema` (Zod) hors de `web/`.
6. Activation : `AGRI_SERVICES=irrigation_need=real` (après décision sur le patch BFF, § 4.3).

Décisions à prendre avant D1 : (a) appliquer ou non le patch BFF ; (b) accepter la représentation de la météo et de l'assistant dans l'enum gelée, ou rouvrir le Doc 16 (nouvelle baseline, hors D0).
