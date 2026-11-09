"""Client HTTP minimal de l'API OctOpus ML, écrit en interne avec httpx.

Ne JAMAIS dépendre du paquet PyPI « octopus-ml » : c'est un projet sans lien, d'un autre auteur
(risque de chaîne d'approvisionnement). Ce module est la seule porte vers OctOpus, ce qui isole le fournisseur.

Points d'accès (documentation publique consultée le 26/10/2026) : `Authorization: Bearer <clé>` ;
POST /api/discover ; POST /api/run ; GET /api/run/{id}/status ; GET /api/run/{id}/stream (SSE) ;
POST /api/run/{id}/cancel ; POST /api/run/{id}/hint ; POST /api/run/{id}/predict-file (multipart « file », CSV) ;
GET /api/run/{id}/proof ; POST /api/proof/verify (public) ; GET/POST /api/schedules ;
/api/workspaces/{nom}/guardrails.
Les CORPS de requête et les noms d'états ne sont pas documentés : ils sont « à vérifier » auprès du fournisseur
et regroupés dans les dataclasses *Request ci-dessous pour être corrigés en un seul endroit.

Sécurité : la clé vient de OCTOPUS_API_KEY (Secrets Manager → External Secrets) et n'est jamais journalisée ni
affichée (`repr` masqué) ; HTTPS obligatoire hors localhost ; pas de suivi des redirections (la clé ne doit pas
partir vers un autre hôte) ; identifiants de run validés avant d'être insérés dans une URL.
Réessais : 429 et 503 (requête non traitée) pour toutes les méthodes ; 500/502/504 seulement pour GET, pour ne
pas lancer deux runs sur un POST dont on ignore s'il a abouti.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agriml import __version__
from agriml._optional import require

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://octopus.ml"
API_KEY_ENV = "OCTOPUS_API_KEY"
BASE_URL_ENV = "OCTOPUS_BASE_URL"
DEFAULT_TIMEOUT_S = 30.0
STREAM_READ_TIMEOUT_S = 300.0
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 30.0
RETRY_ALWAYS = frozenset({429, 503})
RETRY_IDEMPOTENT = frozenset({500, 502, 504})
ERROR_BODY_CHARS = 300
TERMINAL_STATES = frozenset({"completed", "succeeded", "success", "failed", "error", "cancelled", "canceled"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class OctopusError(RuntimeError):
    """Erreur de l'API OctOpus (le message ne contient jamais la clé)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class OctopusAuthError(OctopusError):
    """Clé absente, invalide ou sans droit (401 / 403)."""


class OctopusUnavailable(OctopusError):
    """Service indisponible : 429 / 5xx après réessais, ou erreur réseau."""


# --------------------------------------------------------------------------- corps de requête (à vérifier)


def _compact(obj: Any) -> dict[str, Any]:
    """dataclass → dict JSON sans les champs vides (tuples → listes)."""
    out = {}
    for key, value in asdict(obj).items():
        if value is None or value == () or value == {}:
            continue
        out[key] = list(value) if isinstance(value, tuple) else value
    return out


@dataclass(frozen=True)
class DiscoverRequest:
    """À vérifier : description du problème pour que l'agent propose objectif et métrique."""

    dataset_uri: str
    description: str
    target: str | None = None


@dataclass(frozen=True)
class RunRequest:
    """À vérifier : lancement d'un run autonome sur un instantané déjà filtré par l'exporteur."""

    dataset_uri: str
    target: str
    task: str
    metric: str
    objective: str
    workspace: str | None = None
    time_budget_min: int | None = None
    hints: tuple[str, ...] = ()
    guardrails: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduleRequest:
    """À vérifier : planification récurrente (réentraînement ou scoring avec contrôle de dérive)."""

    name: str
    cron: str
    run_id: str
    action: str = "retrain"
    workspace: str | None = None


@dataclass(frozen=True)
class SseEvent:
    event: str = "message"
    data: str = ""
    id: str | None = None
    retry: int | None = None

    def json(self) -> Any:
        return json.loads(self.data) if self.data else None


@dataclass(frozen=True)
class PredictFileResult:
    predictions: list
    total_rows: int


# --------------------------------------------------------------------------- SSE


def _sse_field(line: str) -> tuple[str, str]:
    name, sep, value = line.partition(":")
    return name, (value[1:] if value.startswith(" ") else value) if sep else ""


def parse_sse(lines: Iterable[str]) -> Iterator[SseEvent]:
    """Analyse un flux text/event-stream (spécification WHATWG) ; un événement incomplet en fin de flux est ignoré."""
    data: list[str] = []
    event, last_id, retry = "message", None, None
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line:
            if data:
                yield SseEvent(event or "message", "\n".join(data), last_id, retry)
            data, event, retry = [], "message", None
            continue
        if line.startswith(":"):
            continue
        name, value = _sse_field(line)
        if name == "data":
            data.append(value)
        elif name == "event":
            event = value
        elif name == "id" and "\0" not in value:
            last_id = value
        elif name == "retry" and value.isdigit():
            retry = int(value)


def check_identifier(value: str, what: str = "Identifiant") -> str:
    if not isinstance(value, str) or not _SAFE_ID.match(value):
        raise ValueError(f"{what} invalide : {value!r}")
    return value


def check_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS):
        return url.rstrip("/")
    raise ValueError(f"URL OctOpus refusée (HTTPS obligatoire hors localhost) : {url!r}")


# --------------------------------------------------------------------------- client


class OctopusClient:
    """Client synchrone ; utilisable comme gestionnaire de contexte (`with OctopusClient() as oc:`)."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout_s: float = DEFAULT_TIMEOUT_S, max_retries: int = MAX_RETRIES,
                 backoff_s: float = BACKOFF_BASE_S, transport: Any = None,
                 sleep: Callable[[float], None] = time.sleep):
        httpx = require("httpx", "Le client OctOpus")
        self._httpx = httpx
        self._api_key = api_key or os.environ.get(API_KEY_ENV) or None
        self.base_url = check_base_url(base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL)
        self.max_retries, self.backoff_s, self._sleep = max_retries, backoff_s, sleep
        self._client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(timeout_s), transport=transport,
                                    follow_redirects=False, headers={"User-Agent": f"agriml/{__version__}"})

    def __repr__(self) -> str:
        return f"OctopusClient(base_url={self.base_url!r}, api_key={'***' if self._api_key else None})"

    def __enter__(self) -> OctopusClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ transport

    def _headers(self, auth: bool, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json", **(extra or {})}
        if auth:
            if not self._api_key:
                raise OctopusAuthError(f"Clé API absente : définir {API_KEY_ENV}.")
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _delay(self, attempt: int, response: Any | None) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after and retry_after.strip().isdigit():
            return min(float(retry_after), BACKOFF_MAX_S)
        return min(self.backoff_s * 2**attempt, BACKOFF_MAX_S)

    @staticmethod
    def _retryable(method: str, status: int) -> bool:
        return status in RETRY_ALWAYS or (method == "GET" and status in RETRY_IDEMPOTENT)

    def _request(self, method: str, path: str, *, auth: bool = True, **kwargs: Any) -> Any:
        headers = self._headers(auth)
        for attempt in range(self.max_retries + 1):
            response = None
            try:
                response = self._client.request(method, path, headers=headers, **kwargs)
            except self._httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise OctopusUnavailable(f"{method} {path} : erreur réseau ({type(exc).__name__}).") from None
            else:
                if not (self._retryable(method, response.status_code) and attempt < self.max_retries):
                    return self._check(method, path, response)
            delay = self._delay(attempt, response)
            logger.warning("OctOpus %s %s : nouvel essai dans %.1f s (%d/%d).", method, path, delay, attempt + 1,
                           self.max_retries)
            self._sleep(delay)
        raise OctopusUnavailable(f"{method} {path} : réessais épuisés.")  # pragma: no cover - inatteignable

    @staticmethod
    def _check(method: str, path: str, response: Any) -> Any:
        status = response.status_code
        logger.debug("OctOpus %s %s → %d", method, path, status)
        if status < 400:
            return response
        body = response.text[:ERROR_BODY_CHARS]
        message = f"{method} {path} → HTTP {status} : {body}"
        if status in (401, 403):
            raise OctopusAuthError(message, status)
        if status == 429 or status >= 500:
            raise OctopusUnavailable(message, status)
        raise OctopusError(message, status)

    def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._request(method, path, **kwargs)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            raise OctopusError(f"{method} {path} : réponse non JSON.", response.status_code) from None

    @staticmethod
    def _run_path(run_id: str, suffix: str) -> str:
        return f"/api/run/{check_identifier(run_id, 'Identifiant de run')}/{suffix}"

    # ------------------------------------------------------------------ API

    def discover(self, request: DiscoverRequest) -> dict[str, Any]:
        return self._json("POST", "/api/discover", json=_compact(request))

    def start_run(self, request: RunRequest) -> dict[str, Any]:
        """Renvoie la réponse brute ; l'identifiant est lu par `run_id_of` (clé à vérifier)."""
        return self._json("POST", "/api/run", json=_compact(request))

    def status(self, run_id: str) -> dict[str, Any]:
        return self._json("GET", self._run_path(run_id, "status"))

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self._json("POST", self._run_path(run_id, "cancel"))

    def hint(self, run_id: str, message: str) -> dict[str, Any]:
        return self._json("POST", self._run_path(run_id, "hint"), json={"message": message})

    def proof(self, run_id: str) -> dict[str, Any]:
        return self._json("GET", self._run_path(run_id, "proof"))

    def verify_proof(self, proof: Mapping[str, Any]) -> dict[str, Any]:
        """Point d'accès public : aucune clé envoyée."""
        return self._json("POST", "/api/proof/verify", auth=False, json=dict(proof))

    def list_schedules(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/schedules")
        return payload.get("schedules", []) if isinstance(payload, dict) else list(payload)

    def create_schedule(self, request: ScheduleRequest) -> dict[str, Any]:
        return self._json("POST", "/api/schedules", json=_compact(request))

    def get_guardrails(self, workspace: str) -> dict[str, Any]:
        return self._json("GET", f"/api/workspaces/{check_identifier(workspace, 'Espace')}/guardrails")

    def set_guardrails(self, workspace: str, guardrails: Mapping[str, Any]) -> dict[str, Any]:
        """Méthode HTTP (PUT) à vérifier ; les garde-fous OctOpus sont une 2e barrière après l'exporteur."""
        path = f"/api/workspaces/{check_identifier(workspace, 'Espace')}/guardrails"
        return self._json("PUT", path, json=dict(guardrails))

    def predict_file(self, run_id: str, csv_path: str | Path) -> PredictFileResult:
        """Scoring par lot (ou secours) : le CSV ne doit contenir que des features + un id pseudonyme."""
        path = Path(csv_path)
        with path.open("rb") as handle:
            payload = self._json("POST", self._run_path(run_id, "predict-file"),
                                 files={"file": (path.name, handle, "text/csv")})
        predictions = list(payload.get("predictions", []))
        total = int(payload.get("total_rows", len(predictions)))
        if total != len(predictions):
            raise OctopusError(f"predict-file : {len(predictions)} prédictions pour {total} lignes annoncées.")
        return PredictFileResult(predictions, total)

    def stream_events(self, run_id: str, last_event_id: str | None = None) -> Iterator[SseEvent]:
        """Suit le run en SSE ; pas de réessai automatique : reprendre avec `last_event_id`."""
        extra = {"Accept": "text/event-stream", **({"Last-Event-ID": last_event_id} if last_event_id else {})}
        headers = self._headers(True, extra)
        timeout = self._httpx.Timeout(DEFAULT_TIMEOUT_S, read=STREAM_READ_TIMEOUT_S)
        path = self._run_path(run_id, "stream")
        with self._client.stream("GET", path, headers=headers, timeout=timeout) as response:
            if response.status_code >= 400:
                response.read()
                self._check("GET", path, response)
            yield from parse_sse(response.iter_lines())

    def wait_for_run(self, run_id: str, poll_s: float = 15.0, timeout_s: float = 6 * 3600) -> dict[str, Any]:
        """Interroge `status` jusqu'à un état terminal (noms d'états à vérifier) ; lève TimeoutError sinon."""
        waited = 0.0
        while True:
            status = self.status(run_id)
            if str(status.get("status", status.get("state", ""))).lower() in TERMINAL_STATES:
                return status
            if waited >= timeout_s:
                raise TimeoutError(f"Run {run_id} non terminé après {timeout_s:.0f} s.")
            self._sleep(poll_s)
            waited += poll_s


def run_id_of(response: Mapping[str, Any]) -> str:
    """Extrait l'identifiant de run (clé exacte à vérifier : « run_id » ou « id »)."""
    for key in ("run_id", "id", "runId"):
        if response.get(key):
            return check_identifier(str(response[key]), "Identifiant de run")
    raise OctopusError("Réponse de lancement sans identifiant de run.")
