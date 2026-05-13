import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.metrics import metrics_store


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        for key in ("method", "path", "status_code", "duration_ms", "user_id", "operation"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class MetricsLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        extra = {}
        for key in ("method", "path", "status_code", "duration_ms", "user_id", "operation"):
            if hasattr(record, key):
                extra[key] = getattr(record, key)
        metrics_store.record_log(record.levelname, record.getMessage(), extra)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_blog_logging_configured", False):
        return

    root.setLevel(logging.DEBUG)
    formatter = JsonFormatter()

    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    metrics_handler = MetricsLogHandler()
    metrics_handler.setLevel(logging.INFO)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.addHandler(metrics_handler)
    root._blog_logging_configured = True
