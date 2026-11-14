# 29 — Rapport d'exécution du Sprint D4 (`fertilization` + `pest_risk` : blocage agronomique documenté et préparation technique complète)

**Statut** : Préparation technique complète livrée et testée ; bascule par défaut retenue en `mock` jusqu'à validation agronomique des référentiels ISRA / DPV — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : `fertilization` (`GET /v1/fields/{id}/fertilization`, service 6 de Doc 16 § 9.3) et `pest_risk` (`GET /v1/fields/{id}/pest-risk`, service 9 de Doc 16 § 9.3).
**Références** : `docs/16_architecture_octopus.md` (intouché), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md` § 3.5, `ml/catalog/models.yaml` (`fert_reco`, `npk_calibration`, `risk_rules`).

---

## 1. État initial et vérification des prérequis agronomiques

La règle du plan validé pour D4 est explicite :
> *« Ne brancher en réel que si les règles/référentiels agronomiques et les données minimales existent. Sinon : documenter le blocage et produire la préparation technique complète. »*

### 1.1 Vérification des référentiels dans le dépôt
1. **Fertilisation (`fert_reco` / `npk_calibration`)** :
   - Le service `backend/app/services/agronomy.py` implémente volontairement `fertility_status()` en **3 classes qualitatives** (`bas`, `moyen`, `eleve`) assorties de l'avertissement `FERTILITY_CAVEAT` : *« Valeur indicative issue du capteur du kit (sensible à l'humidité et à la salinité). Aucune dose d'engrais n'est calculée sans étalonnage de laboratoire : demander l'avis d'un technicien agricole. »*
   - Le catalogue `ml/catalog/models.yaml` (`fert_reco`, l. 547-570 et `npk_calibration`, l. 523-546) exige :
     - soit un étalonnage capteur-laboratoire (`>= 30` paires capteur-labo par type de sol, `kappa >= 0,6`),
     - soit le barème régional ISRA validé par zone, culture et rendement visé (`<= 20 %` d'écart sur 50 cas revus par un agronome).
   - **Constat** : aucune table de barèmes ISRA validée ni aucune paire capteur-laboratoire (`sols.lab_results`) n'est présente dans la base ou dans le dépôt.
2. **Risques phytosanitaires (`risk_rules`)** :
   - Le catalogue `ml/catalog/models.yaml` (`risk_rules`, l. 326-348) exige le jeu obligatoire `phyto.reference` (seuils ISRA et DPV : température, humidité relative, pluie × stade × culture, et respect du plafond `<= 3` alertes par parcelle et par mois avec précision `>= 50 %`).
   - **Constat** : le jeu `phyto.reference` et les bulletins d'alerte DPV / FAMEWS (`phyto.outbreaks`) ne sont pas encore intégrés en base.

### 1.2 Décision D4
- **Blocage métier documenté** : absence des tables de référence agronomiques validées par l'ISRA (`barème de fumure`) et la DPV (`phyto.reference`).
- **Action réalisée** : livraison de la **préparation technique complète** côté backend (`GET /v1/fields/{field_id}/fertilization` et `GET /v1/fields/{field_id}/pest-risk`), conforme à 100 % aux contrats Zod `FertilizationSchema` et `PestRiskSchema`, avec :
  - **Par défaut (sans référentiel injecté)** : `fertilization` renvoie la classe NPK issue du kit (`bas` / `moyen` / `eleve`), `indicative = true`, `n_kg_ha = null`, `p_kg_ha = null`, `k_kg_ha = null` (aucune dose inventée) ; `pest_risk` renvoie `pests = []` (abstention honnête).
  - **Avec référentiel injecté (`app.state.fertilization_reference` / `app.state.pest_reference`)** : calcul immédiat des doses barème et des facteurs de risque météo × stade sans modification de code.

---

## 2. Modifications réalisées

### Backend (`plateforme/backend/`)
- **`app/services/fertilization.py`** :
  - Implémentation de `field_fertilization(session, field, now, reference=None)` construisant la réponse conforme à `FertilizationSchema` (`field_id`, `crop`, `stage`, `n_kg_ha`, `p_kg_ha`, `k_kg_ha`, `npk_class`, `indicative=True`, `caveat`, `provenance` `fert_reco` / `rules`).
- **`app/services/pest_risk.py`** :
  - Implémentation de `PestRule` et `field_pest_risk(session, field, forecast, now, reference=None)` construisant la réponse conforme à `PestRiskSchema` (`field_id`, `pests`, `provenance` `risk_rules` / `rules`, `p_outbreak_7d=None`, `p_outbreak_14d=None`).
- **`app/api/v1/fields.py`** :
  - Ajout des routes `GET /v1/fields/{field_id}/fertilization` et `GET /v1/fields/{field_id}/pest-risk` avec contrôle d'accès multi-organisation (`access.get_field_for`).

### Tests (`plateforme/backend/tests/` et `plateforme/web/tests/live/`)
- **`backend/tests/test_sprint_d4_d5_d6.py`** : test unitaire et d'intégration de `fertilization` et `pest_risk` dans les deux modes (par défaut sans référentiel et avec référentiels ISRA/DPV injectés).
- **`web/tests/live/prepared-services.live.ts`** : test de contrat live BFF → FastAPI validant `FertilizationSchema` et `PestRiskSchema`.

---

## 3. Tests exécutés

1. **Backend (`pytest`)** : `test_d4_fertilization_and_pest_risk_default_and_injected` passant.
2. **Contrat live (`vitest.live.config.ts`)** : validation Zod complète de `GET /v1/fields/{id}/fertilization` et `GET /v1/fields/{id}/pest-risk` via le BFF Next.

---

## 4. Risques et conditions de levée du blocage

1. **Risque agronomique en cas d'activation prématurée de doses chiffrées** : afficher des kg/ha d'engrais sur la seule foi d'une sonde NPK RS485 non étalonnée induirait un surdosage ou sous-dosage. Le mode par défaut (`n_kg_ha = null`, classes qualitatives seules) protège l'agriculteur.
2. **Condition de bascule par défaut en `real` avec doses et alertes** :
   - Fourniture et validation par un agronome ISRA de la table des barèmes par culture/zone (`fertilization_reference`).
   - Fourniture de la table `phyto.reference` (seuils T, HR, pluie × stade × culture ISRA/DPV).

---

## 5. Prochaines étapes (Sprint D5)

- Vérifier la disponibilité d'un corpus photo terrain et d'un bundle `vis_disease` pour **`diagnosis_analyze`**, documenter le blocage de modèle et livrer la route `POST /v1/diagnoses/analyze` complète.
