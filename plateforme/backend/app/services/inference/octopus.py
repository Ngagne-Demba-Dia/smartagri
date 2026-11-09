"""Moteur OctOpus : prédiction par lot via `POST {OCTOPUS_BASE_URL}/api/run/{run_id}/predict-file`.

Protocole documenté : requête multipart, champ `file` = CSV, en-tête `Authorization: Bearer {OCTOPUS_API_KEY}` ;
réponse `{"predictions": [...], "total_rows": n}`.

À vérifier auprès d'OctOpus (non documenté) : la forme exacte des éléments de `predictions` (nombre seul ou
objet), la conservation de l'ordre des lignes, le nom de la colonne d'identifiant de ligne renvoyée et les
codes d'erreur. Ce module accepte un nombre ou un objet par ligne et réordonne par `row_id` si présent.

Données personnelles : le CSV ne contient QUE les variables déclarées du modèle (`model_registry.features`,
liste filtrée par `PERSONAL_COLUMNS`) et un identifiant de ligne pseudonyme propre au lot (`r0`, `r1`…),
sans lien avec les identifiants de la base. Aucun identifiant d'exploitation, de parcelle ou de kit n'est envoyé.

Attention : le paquet PyPI « octopus-ml » est sans rapport avec ce service ; il n'est pas utilisé.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Sequence
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.services.inference.base import (
    FeatureRow,
    InferenceError,
    ModelEntry,
    Prediction,
    check_predictions,
    feature_matrix,
)
from app.services.inference.registry import serving_entry

logger = logging.getLogger(__name__)

RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
ROW_ID_COLUMN = "row_id"
MAX_ROWS = 10_000


def batch_csv(features: Sequence[str], matrix: Sequence[Sequence[Any]]) -> bytes:
    """CSV du lot : `row_id` pseudonyme puis les variables déclarées, dans l'ordre déclaré."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([ROW_ID_COLUMN, *features])
    for index, values in enumerate(matrix):
        writer.writerow([f"r{index}", *("" if value is None else value for value in values)])
    return buffer.getvalue().encode("utf-8")


def _reorder(predictions: list[Any], expected: int) -> list[Any]:
    """Réordonne par `row_id` quand chaque élément en porte un ; sinon l'ordre reçu est conservé."""
    if not predictions or not all(isinstance(item, dict) and ROW_ID_COLUMN in item for item in predictions):
        return predictions
    by_id = {str(item[ROW_ID_COLUMN]): item for item in predictions}
    ordered = [by_id.get(f"r{index}") for index in range(expected)]
    if any(item is None for item in ordered):
        raise InferenceError("Réponse OctOpus : identifiants de ligne manquants.")
    return [_unwrap({k: v for k, v in item.items() if k != ROW_ID_COLUMN}) for item in ordered]


def _unwrap(item: dict[str, Any]) -> Any:
    """`{"prediction": 3.2}` → 3.2 ; un objet à plusieurs clés (quantiles) reste un dict."""
    return item["prediction"] if set(item) == {"prediction"} else item


def parse_response(response: httpx.Response, expected: int) -> list[Prediction]:
    if response.status_code != 200:
        raise InferenceError(f"OctOpus a répondu HTTP {response.status_code}.")
    try:
        body = response.json()
    except ValueError as exc:
        raise InferenceError("Réponse OctOpus non JSON.") from exc
    if not isinstance(body, dict) or not isinstance(body.get("predictions"), list):
        raise InferenceError("Réponse OctOpus sans liste `predictions`.")
    total = body.get("total_rows")
    if total is not None and total != expected:
        raise InferenceError(f"OctOpus annonce {total} lignes pour {expected} envoyées.")
    return check_predictions(_reorder(body["predictions"], expected), expected)


class OctopusBatchBackend:
    name = "octopus"
    sources: tuple[str, ...] = ("octopus",)

    def __init__(self, session: Session, base_url: str, api_key: str, timeout_s: float,
                 client: httpx.Client | None = None) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_s, connect=min(timeout_s, 10.0))
        self._client = client

    def entry(self, model_name: str) -> ModelEntry:
        return serving_entry(self._session, model_name, self.sources)

    def _post(self, url: str, payload: bytes) -> httpx.Response:
        files = {"file": ("batch.csv", payload, "text/csv")}
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        if self._client is not None:
            return self._client.post(url, files=files, headers=headers, timeout=self._timeout)
        with httpx.Client(timeout=self._timeout, follow_redirects=False) as client:
            return client.post(url, files=files, headers=headers)

    def predict(self, model_name: str, rows: Sequence[FeatureRow]) -> list[Prediction]:
        if not rows:
            return []
        if not self._api_key:
            raise InferenceError("OCTOPUS_API_KEY absente : moteur OctOpus indisponible.")
        if len(rows) > MAX_ROWS:
            raise InferenceError(f"Lot trop volumineux pour OctOpus ({MAX_ROWS} lignes max).")
        entry = self.entry(model_name)
        if not entry.octopus_run_id or not RUN_ID_RE.match(entry.octopus_run_id):
            raise InferenceError(f"Identifiant de run OctOpus absent ou invalide pour {entry.name}.")
        payload = batch_csv(entry.features, feature_matrix(entry, rows))
        url = f"{self._base_url}/api/run/{entry.octopus_run_id}/predict-file"
        try:
            response = self._post(url, payload)
        except httpx.HTTPError as exc:
            raise InferenceError(f"OctOpus injoignable ({type(exc).__name__}).") from exc
        return parse_response(response, len(rows))
