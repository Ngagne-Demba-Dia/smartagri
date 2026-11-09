"""Ancien point d'entrée, conservé par compatibilité : le code vit dans `app.seed`.

Préférer `python -m app.seed [--create-schema]` (cible `make seed`).
"""

from __future__ import annotations

from app.seed import main

if __name__ == "__main__":
    raise SystemExit(main())
