# Fiche modèle — $name

> Document confidentiel — réservé aux partenaires de travail. Généré par `agriml.export` le $created_at
> (agriml $agriml_version, commit $git_sha). Les sections « À compléter » sont rédigées par l'équipe.

## 1. Identité

| Champ | Valeur |
|---|---|
| Tâche | $task |
| Métrique de décision | $metric |
| Modèle retenu | $final |
| Modèles du paquet | $members |
| Score CV (hors-pli) | $cv_score |
| Référence constante | $baseline |
| Seuil de décision (binaire) | $threshold |
| Validation croisée | $cv_scheme |
| Graines | $seeds |

## 2. Scores par modèle (CV)

| Modèle | CV | Écart-type entre plis |
|---|---|---|
$models_table

Hold-out (si étiquettes de test disponibles) : `$holdout`
AUC de validation adversariale train/test : `$adversarial_auc` (≈ 0,5 = distributions semblables).

## 3. Données

- Entraînement : `$train_data`
- Période, zones, cultures couvertes : **À compléter**
- Pseudonymisation : identifiants de parcelle / d'exploitant hachés (HMAC-SHA256) ; GPS arrondi à 0,01°.

## 4. Usage prévu et limites — À compléter

- Usage prévu : aide à la décision agronomique (pas de décision automatique irréversible).
- Hors périmètre : cultures, régions ou saisons absentes de l'entraînement.
- Limites connues : voir `evaluation.json` (scores par tranche, résidus, calibration).

## 5. Surveillance

- Dérive : PSI par variable (< 0,1 stable ; 0,1–0,25 modérée ; > 0,25 forte) et KS (`agriml.monitoring.drift`).
- Réentraînement : déclenché par `should_retrain`, promotion uniquement si la porte champion/challenger est franchie
  (`agriml.mlops.promotion`).

## 6. Intégrité

Chaque fichier du paquet est listé avec son SHA-256 dans `manifest.json` ; le service vérifie l'empreinte du
paquet (`agriml.export.verify_bundle`) avant chargement.
