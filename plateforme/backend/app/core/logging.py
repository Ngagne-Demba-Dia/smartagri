"""Journalisation JSON sur la sortie standard (collectée par Loki/CloudWatch en production)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_RESERVED = set(vars(logging.makeLogRecord({})))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extras = {k: v for k, v in vars(record).items() if k not in _RESERVED and not k.startswith("_")}
        payload.update({k: v for k, v in extras.items() if isinstance(v, (str, int, float, bool, type(None)))})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
