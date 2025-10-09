from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

import structlog

from .config import CloudflareProjectsConfig


@dataclass(frozen=True)
class AuditEvent:
    category: str
    action: str
    actor: str
    project_id: str
    metadata: Mapping[str, Any]


class AuditLogger:
    """Structured logger that routes Cloudflare Projects events to Logpush."""

    def __init__(self, cfg: CloudflareProjectsConfig) -> None:
        self._cfg = cfg
        self._logger = structlog.get_logger(cfg.logging.structured_logger_name)
        self._redact_fields = set(cfg.logging.redact_fields)

    def log(self, event: AuditEvent) -> None:
        now = datetime.now(timezone.utc).isoformat()
        metadata = self._sanitize(event.metadata)
        self._logger.info(
            "audit_event",
            timestamp=now,
            category=event.category,
            action=event.action,
            actor=event.actor,
            project_id=event.project_id,
            metadata=metadata,
            dataset=self._cfg.logging.logpush_dataset,
        )

    def _sanitize(self, metadata: Mapping[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in metadata.items():
            if key in self._redact_fields:
                sanitized[key] = "***"
            else:
                sanitized[key] = value
        return sanitized


__all__ = ["AuditEvent", "AuditLogger"]
