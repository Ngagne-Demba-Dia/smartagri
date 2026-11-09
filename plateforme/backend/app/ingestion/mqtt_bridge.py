"""Pont MQTT → base : télémétrie, événements et acquittements des kits ; publication des commandes.

Usage : `python -m app.ingestion.mqtt_bridge`. Dépend de `paho-mqtt` (extra `mqtt`), importé paresseusement.
La logique métier (`handle_message`, `publish_pending_commands`) n'importe pas paho : elle est testée seule.

Le sujet MQTT fait foi pour l'identité du kit : en production, l'ACL du broker n'autorise un kit à publier
que sous son propre `device_id` (CONVENTIONS §4).
"""

from __future__ import annotations

import json
import logging
import queue
import re
import secrets
import signal
import ssl
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.base import as_utc
from app.db.models import Device
from app.db.session import build_engine, build_session_factory
from app.schemas.telemetry import TelemetryPoint
from app.services import devices as device_service
from app.services.telemetry import ingest_points

logger = logging.getLogger(__name__)

TOPIC_PREFIX = "agri92/v1/devices"
TOPIC_RE = re.compile(r"^agri92/v1/devices/(SA92-\d{6})/(telemetry|events|commands/ack)$")
SUBSCRIPTIONS = tuple(f"{TOPIC_PREFIX}/+/{suffix}" for suffix in ("telemetry", "events", "commands/ack"))
QOS = 1
MAX_PAYLOAD_BYTES = 16 * 1024
MAX_EVENT_TYPE_CHARS = 64
COMMAND_POLL_S = 5.0
RECONNECT_MIN_S, RECONNECT_MAX_S = 1, 120


@dataclass(frozen=True)
class HandleResult:
    """Issue du traitement d'un message (journalisée et testée)."""

    kind: str
    outcome: str
    serial: str | None = None
    detail: str = ""
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MqttTarget:
    host: str
    port: int
    tls: bool
    username: str = ""
    password: str = ""


def parse_mqtt_url(url: str) -> MqttTarget:
    """`mqtt://hôte:1883` ou `mqtts://hôte:8883` (TLS) ; identifiants facultatifs dans l'URL."""
    parts = urlsplit(url)
    if parts.scheme not in ("mqtt", "mqtts") or not parts.hostname:
        raise ValueError("MQTT_URL doit être de la forme mqtt://hôte:port ou mqtts://hôte:port.")
    tls = parts.scheme == "mqtts"
    return MqttTarget(host=parts.hostname, port=parts.port or (8883 if tls else 1883), tls=tls,
                      username=unquote(parts.username or ""), password=unquote(parts.password or ""))


def command_topic(serial: str) -> str:
    return f"{TOPIC_PREFIX}/{serial}/commands"


def _decode(payload: bytes) -> dict[str, Any] | None:
    if len(payload) > MAX_PAYLOAD_BYTES:
        return None
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _telemetry_point(serial: str, data: Mapping[str, Any], now: datetime) -> TelemetryPoint:
    """Accepte un point telemetry.v1 complet, ou le JSON brut du firmware v1.1 (horodaté à réception)."""
    if "schema" in data:
        point = TelemetryPoint.model_validate(data)
        if point.device_id != serial:
            raise ValueError("device_id différent du sujet MQTT")
        return point.model_copy(update={"source": "mqtt"})
    return TelemetryPoint.model_validate(
        {"schema": "telemetry.v1", "device_id": serial, "ts": now, "source": "mqtt", "kit": dict(data)}
    )


def _handle_telemetry(session: Session, settings: Settings, device: Device, data: Mapping[str, Any],
                      now: datetime) -> HandleResult:
    try:
        point = _telemetry_point(device.serial, data, now)
    except (ValidationError, ValueError) as exc:
        return HandleResult("telemetry", "rejected", device.serial, type(exc).__name__)
    result = ingest_points(session, settings, [point], {device.serial: device}, now)
    return HandleResult("telemetry", "ingested", device.serial, data=result.as_dict())


def _handle_ack(session: Session, device: Device, data: Mapping[str, Any], now: datetime) -> HandleResult:
    command_id, ok = data.get("id"), data.get("ok")
    if not isinstance(command_id, str) or not isinstance(ok, bool) or len(command_id) > 64:
        return HandleResult("ack", "rejected", device.serial, "format d'acquittement invalide")
    applied = device_service.apply_command_ack(session, device, command_id, ok, now)
    return HandleResult("ack", "applied" if applied else "ignored", device.serial)


def _handle_event(device: Device, data: Mapping[str, Any], now: datetime) -> HandleResult:
    # À vérifier : le format des événements n'est pas spécifié par CONVENTIONS §4 ; seul `type` est lu.
    event_type = data.get("type")
    if not isinstance(event_type, str) or not 0 < len(event_type) <= MAX_EVENT_TYPE_CHARS:
        return HandleResult("event", "rejected", device.serial, "champ `type` manquant ou invalide")
    last_seen = as_utc(device.last_seen_at)
    if last_seen is None or now > last_seen:
        device.last_seen_at = now
    logger.info("Événement kit %s : %s", device.serial, event_type)
    return HandleResult("event", "logged", device.serial, event_type)


def handle_message(topic: str, payload: bytes, session: Session, settings: Settings,
                   now: datetime) -> HandleResult:
    """Traite un message entrant ; l'appelant valide (commit) ou annule la transaction."""
    match = TOPIC_RE.match(topic)
    if match is None:
        return HandleResult("unknown", "ignored", detail="sujet hors contrat")
    serial, kind = match.groups()
    data = _decode(payload)
    if data is None:
        return HandleResult(kind, "rejected", serial, "JSON objet attendu (16 Kio max)")
    device = session.scalars(select(Device).where(Device.serial == serial)).first()
    if device is None or device.status != "active":
        return HandleResult(kind, "ignored", serial, "kit inconnu ou inactif")
    if kind == "telemetry":
        return _handle_telemetry(session, settings, device, data, now)
    if kind == "commands/ack":
        return _handle_ack(session, device, data, now)
    return _handle_event(device, data, now)


Publisher = Callable[[str, bytes], bool]


def publish_pending_commands(session: Session, publish: Publisher, now: datetime, limit: int = 100) -> int:
    """Publie les commandes de seuils en attente ; une commande publiée passe à `sent`."""
    sent = 0
    for device, row in device_service.pending_threshold_commands(session, limit):
        payload = json.dumps(device_service.threshold_command(row), separators=(",", ":")).encode()
        if publish(command_topic(device.serial), payload):
            row.sync_status, row.updated_at = "sent", now
            sent += 1
    return sent


# --- Boucle de production (paho-mqtt) ---------------------------------------------------------------------

def _process(factory: sessionmaker[Session], settings: Settings, topic: str, payload: bytes) -> None:
    with factory() as session:
        try:
            result = handle_message(topic, payload, session, settings, datetime.now(UTC))
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Échec du traitement d'un message (%s)", topic)
            return
    if result.outcome in ("rejected", "ignored"):
        logger.warning("Message %s %s : %s (%s)", result.kind, result.outcome, result.serial, result.detail)


def _flush_commands(factory: sessionmaker[Session], client: Any) -> None:
    def publish(topic: str, payload: bytes) -> bool:
        info = client.publish(topic, payload, qos=QOS)
        return info.rc == 0

    with factory() as session:
        try:
            if publish_pending_commands(session, publish, datetime.now(UTC)):
                session.commit()
        except Exception:
            session.rollback()
            logger.exception("Échec de la publication des commandes")


def _build_client(settings: Settings, target: MqttTarget, inbox: queue.Queue[tuple[str, bytes]]) -> Any:
    import paho.mqtt.client as mqtt  # dépendance optionnelle (extra `mqtt`)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"agri92-bridge-{secrets.token_hex(4)}")
    username = settings.mqtt_username or target.username
    if username:
        client.username_pw_set(username, settings.mqtt_password or target.password)
    if target.tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.reconnect_delay_set(min_delay=RECONNECT_MIN_S, max_delay=RECONNECT_MAX_S)

    def on_connect(cli: Any, _userdata: Any, _flags: Any, reason_code: Any, _props: Any) -> None:
        logger.info("Connecté au broker MQTT (%s)", reason_code)
        cli.subscribe([(topic, QOS) for topic in SUBSCRIPTIONS])

    def on_message(_cli: Any, _userdata: Any, message: Any) -> None:
        inbox.put((message.topic, bytes(message.payload)))

    client.on_connect, client.on_message = on_connect, on_message
    return client


def _connect_with_backoff(client: Any, target: MqttTarget, stop: threading.Event) -> bool:
    delay = RECONNECT_MIN_S
    while not stop.is_set():
        try:
            client.connect(target.host, target.port, keepalive=60)
            return True
        except OSError as exc:
            logger.warning("Broker MQTT injoignable (%s) ; nouvel essai dans %d s", exc, delay)
            stop.wait(delay)
            delay = min(delay * 2, RECONNECT_MAX_S)
    return False


def run(settings: Settings, stop: threading.Event) -> None:
    """Boucle principale : messages entrants traités un par un, commandes publiées périodiquement."""
    target = parse_mqtt_url(settings.mqtt_url)
    if settings.is_strict and not target.tls:
        raise ValueError("MQTT en clair interdit en staging/prod : utiliser mqtts:// (port 8883).")
    factory = build_session_factory(build_engine(settings.database_url))
    inbox: queue.Queue[tuple[str, bytes]] = queue.Queue(maxsize=10_000)
    client = _build_client(settings, target, inbox)
    if not _connect_with_backoff(client, target, stop):
        return
    client.loop_start()
    next_flush = 0.0
    try:
        while not stop.is_set():
            try:
                topic, payload = inbox.get(timeout=COMMAND_POLL_S)
                _process(factory, settings, topic, payload)
            except queue.Empty:
                pass
            if time.monotonic() >= next_flush:
                _flush_commands(factory, client)
                next_flush = time.monotonic() + COMMAND_POLL_S
    finally:
        client.disconnect()
        client.loop_stop()
        logger.info("Pont MQTT arrêté proprement")


def main() -> int:
    settings = get_settings()
    configure_logging()
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    run(settings, stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
