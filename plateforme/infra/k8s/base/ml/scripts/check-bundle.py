"""Sonde de disponibilité de l'inférence : le paquet servi a bien l'empreinte attendue.

Recalcule le SHA-256 de /models/bundle.tar.gz et le compare à MODEL_BUNDLE_SHA256.
Code de sortie 0 si identique, 1 sinon (le pod est retiré du Service).
"""

import hashlib
import hmac
import os
import sys

BUNDLE_PATH = "/models/bundle.tar.gz"
CHUNK_BYTES = 1024 * 1024


def main() -> int:
    expected = os.environ.get("MODEL_BUNDLE_SHA256", "")
    digest = hashlib.sha256()
    try:
        with open(BUNDLE_PATH, "rb") as bundle:
            for chunk in iter(lambda: bundle.read(CHUNK_BYTES), b""):
                digest.update(chunk)
    except OSError as exc:
        print(f"paquet illisible : {exc}", file=sys.stderr)
        return 1
    if not hmac.compare_digest(digest.hexdigest(), expected):
        print("empreinte du paquet différente de MODEL_BUNDLE_SHA256", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
