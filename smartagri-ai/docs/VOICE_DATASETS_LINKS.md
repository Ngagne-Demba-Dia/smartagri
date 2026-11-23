# Liens & Procédure — Datasets Vocaux (Wolof, Pulaar, Sérère)

Note conservée à la demande de l'utilisateur (2026-11-18).

---

## 1. `galsenai/wolof-audio-data` (prioritaire)

- **URL** : https://huggingface.co/datasets/galsenai/wolof-audio-data
- **Méthode 1 (UI)** : Onglet **Files and versions** → télécharger les fichiers (`.parquet` ou dossier `data/`) ou **Clone repository**.
- **Méthode 2 (CLI)** :
```bash
pip install huggingface_hub
huggingface-cli download galsenai/wolof-audio-data --repo-type dataset --local-dir wolof-audio-data
```

---

## 2. Autres datasets HuggingFace (`galsenai`)

| Dataset | URL |
|---|---|
| **TTS en wolof** | https://huggingface.co/datasets/galsenai/wolof_tts |
| **Corpus wolof** | https://huggingface.co/datasets/galsenai/wolof_corpus |
| **Waxal (multilingue)** | https://huggingface.co/datasets/galsenai/waxal_dataset |

Même procédure : onglet **Files and versions** → Download ou `huggingface-cli download <repo> --repo-type dataset --local-dir <dossier>`.

---

## 3. OpenSLR Kallaama (Wolof, Pulaar, Sérère — ressource 151)

| Langue | Lien direct | Taille |
|---|---|---|
| **Wolof** | https://openslr.elda.org/resources/151/speech_dataset_wol.tar.gz | 5.4 Go |
| **Pulaar** | https://openslr.elda.org/resources/151/speech_dataset_fuc.tar.gz | 3.1 Go |
| **Sérère** | https://openslr.elda.org/resources/151/speech_dataset_srr.tar.gz | 3.9 Go |
