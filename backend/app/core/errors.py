"""Application error types with stable error codes.

Error codes are part of the frozen API contract (docs/05_API_CONTRACT.md).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    stage: str
    raw_event_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    http_status: int = 500


class EventConflictError(AppError):
    """Same (channel, source_event_id) received with a different payload."""

    def __init__(self, *, channel: str, source_event_id: str, raw_event_id: str | None) -> None:
        super().__init__(
            code="EVENT_ID_REUSED",
            message=f"Source event ID {source_event_id} was reused with a different payload.",
            stage="ingestion",
            raw_event_id=raw_event_id,
            details={"channel": channel, "source_event_id": source_event_id},
            http_status=409,
        )


class NormalizationError(AppError):
    """Raw event persisted but normalization failed."""

    def __init__(
        self,
        *,
        message: str,
        raw_event_id: str,
        channel: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="NORMALIZATION_FAILED",
            message=message,
            stage="normalization",
            raw_event_id=raw_event_id,
            details={"channel": channel, **(details or {})},
            http_status=202,
        )


class IngestionError(AppError):
    """Unexpected failure during ingestion."""

    def __init__(
        self,
        *,
        message: str,
        raw_event_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="INGESTION_ERROR",
            message=message,
            stage="ingestion",
            raw_event_id=raw_event_id,
            details=details or {},
            http_status=500,
        )