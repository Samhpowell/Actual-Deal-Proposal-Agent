"""Structured JSON Logging Module for the Enterprise Deal Qualification & Proposal Agent."""

import datetime
import json
import logging
import sys
from typing import Any, Dict


class StructuredJSONLogHandler(logging.Handler):
    """Formats log records as structured JSON lines."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload: Dict[str, Any] = {
                "severity": record.levelname,
                "message": record.getMessage(),
                "timestamp": datetime.datetime.fromtimestamp(
                    record.created, tz=datetime.timezone.utc
                ).isoformat(),
                "logger": record.name,
                "module": record.module,
            }
            if hasattr(record, "structured_data") and getattr(record, "structured_data"):
                payload["metadata"] = getattr(record, "structured_data")
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


def get_structured_logger(name: str = "enterprise_deal_agent") -> logging.Logger:
    """Returns a logger configured with StructuredJSONLogHandler."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(StructuredJSONLogHandler())
        logger.propagate = False
    return logger
