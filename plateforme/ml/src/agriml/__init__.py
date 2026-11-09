"""agriml : apprentissage automatique agronomique de la plateforme Smart Agri92.

Un seul code pour la compétition (validation croisée sans fuite, ensembles) et pour la production
(inférence à partir des artefacts sauvegardés, surveillance de dérive, réentraînement).
"""

import os

# joblib/loky interroge « wmic » (absent de Windows 11) pour compter les cœurs physiques ; une valeur
# inférieure au nombre de cœurs logiques court-circuite cet appel (≈ cœurs physiques avec hyperthreading).
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(max(1, (os.cpu_count() or 2) // 2)))

__version__ = "0.1.0"
