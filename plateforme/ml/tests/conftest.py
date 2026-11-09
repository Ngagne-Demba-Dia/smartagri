"""Fixtures partagées : données synthétiques minuscules, aucun accès réseau, aucun fichier hors tmp_path."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

TEST_SALT = "unit-test-salt-0123456789abcdef-0123456789"


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def salt_env() -> dict[str, str]:
    return {"AGRIML_PSEUDO_SALT": TEST_SALT, "AGRIML_PSEUDO_SALT_ID": "salt-test-v1"}


@pytest.fixture
def field_frame(rng) -> pd.DataFrame:
    """Jeu « irrigation » : 8 parcelles × 30 jours, avec colonnes personnelles à filtrer."""
    rows = []
    for f in range(8):
        for d in range(30):
            rows.append({"field_key": f"F{f:03d}", "device_id": f"ESP32-{f:02d}", "owner_name": f"Agriculteur {f}",
                         "phone": "+221 77 123 45 67", "lat": 14.6937 + f * 0.0137, "lon": -17.4441 - f * 0.011,
                         "ts": pd.Timestamp("2026-01-01") + pd.Timedelta(days=d),
                         "et0_mm": float(rng.uniform(4, 7)), "rain_eff_mm": float(rng.exponential(1)),
                         "target_need_mm_24h": float(rng.uniform(0, 8))})
    return pd.DataFrame(rows)
