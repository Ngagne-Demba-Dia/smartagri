# Trace OctOpus — Chantiers Vocaux (Wolof) & Modèles Sol/Grenier (SMART AGRI92)

Note conservée à la demande de l'utilisateur (2026-11-18) pour référence lors des prochaines étapes.

---

## 1. État des chantiers enregistrés sur OctOpus

| Chantier | Statut dans OctOpus | Détails clés à retenir |
|---|---|---|
| **Modèle Sol (v1/opt)** | Terminé | LightGBM optimisé à **95,8 %** (vs GBT 93,24 % initial, +2,56 pts). |
| **Modèle Grenier** | Terminé | XGBoost / Random Forest confirmé à **100 %** (sain / surveiller / critique, tri oignons). |
| **Calculatrice Arrosage** | Corrigé | Blocage pré-récolte **15 jours**. |
| **Assistant bilingue FR/Wolof** | Partiel | 10 conseils FR/Wolof. |
| **Corpus `wolof-audio-data`** | Partiel (bloqué côté import OctOpus) | **432 / 35 075 clips** importés (1,2 %) ; `wolof_tts`, `wolof_corpus`, `waxal_dataset`, `Pulaar`, `OpenSLR Kallaama` à 0. |
| **Transcription Wolof** | Terminé (partiel) | **287 / 432 clips** transcrits (`25 min 12 s`), moteur `OctOpus ASR 1 (wolof)`. |
| **ASR Wolof** | En attente validation | Projet `vtp_ca476c32ded9` créé avec 287 clips ; attend revue/approbation des transcriptions. |
| **TTS Wolof** | Bloqué sur contrainte durée / modèle | Corpus filtré prêt (`tts_valid_clips.csv`, **180 clips ≤ 12 s**). `CONCREE/Adia_TTS` refusé sur le jeu complet (clip max `24,9 s > 15 s`). Alternatives pré-entraînées proposées : **`bilalfaye/speecht5_tts-wolof-v0.2`** (MIT, wolof natif, recette SpeechT5 vérifiée), `bilalfaye/speecht5_tts-wolof`, `microsoft/speecht5_tts`, `parler-tts/parler-tts-mini-multilingual-v1.1`, `Qwen/Qwen3-TTS-12Hz-0.6B-Base`. |
| **NLP Wolof (intentions)** | Terminé (faible) | TF-IDF + SVM sur 432 phrases → **F1 max = 0.28** (nécessite `galsenai/wolof_corpus` 52 706 phrases). |

---

## 2. Points clés à garder en tête pour la suite

1. **Ne pas dépendre de l'import OctOpus pour les gros corpus vocaux** : télécharger directement `galsenai/wolof-audio-data`, `galsenai/wolof_tts`, `galsenai/wolof_corpus`, `galsenai/waxal_dataset` et OpenSLR 151 (voir `VOICE_DATASETS_LINKS.md`).
2. **Pour le TTS Wolof** : utiliser soit `tts_valid_clips.csv` (≤ 12 s) / découper les clips ≤ 15 s pour `CONCREE/Adia_TTS`, soit partir sur `bilalfaye/speecht5_tts-wolof-v0.2` (licence MIT).
3. **Pour le NLP Wolof** : passer de 432 phrases à `wolof_corpus` (52 706 lignes) pour dépasser F1 = 0.28.
4. **Pour Sol / Grenier** : penser à récupérer les résultats `optimization_results.csv` / modèles Sol 95,8 % et Grenier 100 % si besoin hors OctOpus.
