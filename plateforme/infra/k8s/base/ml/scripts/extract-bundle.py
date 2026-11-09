"""Second conteneur d'initialisation de l'inférence : extrait le paquet vérifié dans /models/current.

Le filtre « data » de tarfile (Python >= 3.12) refuse les chemins absolus, les « .. », les liens
sortant du répertoire cible et les fichiers spéciaux.
"""

import sys
import tarfile
from pathlib import Path

BUNDLE_PATH = Path("/models/bundle.tar.gz")
TARGET_DIR = Path("/models/current")


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(BUNDLE_PATH, "r:gz") as archive:
            archive.extractall(TARGET_DIR, filter="data")
    except (OSError, tarfile.TarError) as exc:
        print(f"extraction du paquet impossible : {exc}", file=sys.stderr)
        return 1
    print(f"paquet extrait dans {TARGET_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
