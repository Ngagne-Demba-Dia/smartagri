# Plan Collecte Datasets Classe B (Hugging Face & Dépôts Ouverts)

**Date** : 2026-11-22  
**Objectif** : Préparer les données open-source pour les modèles Classe B (`B4` Vision Maladies, `B1`/`B6` Humidité Sol Afrique de l'Ouest) en complément des futures remontées IoT du kit SmartAgri92.

---

## 1. B4 — Disease Detection (Hugging Face)

| Dataset Hugging Face | Volume | Cultures pertinentes Sénégal | Classes couvertes |
|---|---|---|---|
| `EdManZoeTech/plant-disease-detection` | ~35 725 images | **Maïs, Tomate** | Cercospora, rouille, mildiou, tache bactérienne, mosaïque, YLCV |
| `LeafNet75/Rice-Disease-Classification-Dataset` | ~4 078 images | **Riz** | Brown Spot, Leaf Blast, Neck Blast, Healthy |
| `Ramseyn-77/plant-disease-crop-health-15classes` | 15 classes RGB | **Tomate, Poivron, Pomme de terre** | Early/Late blight, Leaf Mold, Septoria, YLCV |
| `Project-AgML/Plant_leaf_diseases_dataset_classification` | ~116 930 lignes | **Maïs, Tomate** | Multi-maladies + sains |
| `BrandonFors/Plant-Diseases-PlantVillage-Dataset` | Splits standard | **Tomate, Maïs, multi-cultures** | Baseline labo |

> **Action terrain requise** : pré-entraîner sur `LeafNet75/Rice-Disease-Classification-Dataset` + `EdManZoeTech/plant-disease-detection`, puis fine-tuner sur photos smartphone prises au Sénégal (fond naturel, lumière forte, oignon/arachide/tomate).

---

## 2. B1 & B6 — Irrigation ML & Soil Calibration (Afrique de l'Ouest)

| Source | Couverture | Données |
|---|---|---|
| **AMMA-CATCH** (`https://www.amma-catch.org/`) | **Ferlo (Sénégal)**, Gourma (Mali), Niamey (Niger), Ouémé (Bénin) | Profils d'humidité du sol in-situ (0–1 m), température sol, flux |
| **ISMN** (`https://ismn.earth/`) | Stations Afrique de l'Ouest | Séries harmonisées sondes ↔ satellite |

> **Action terrain requise** : combiner AMMA-CATCH (pré-calibration sahélienne) avec les mesures réelles de la sonde capacitive du kit SmartAgri92 (`code-kitsmartagri92.ino`).
