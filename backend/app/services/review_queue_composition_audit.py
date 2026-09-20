"""Local/test-only aggregate diagnostics for pending identity reviews.

The audit identifies repeat review shapes in persisted decisions without
exposing event payloads, identifier values, candidate profile IDs, or hidden
evaluation truth. It is deliberately not an HTTP endpoint.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import IdentityOutcome, ReviewStatus
from app.db.models import CanonicalEvent, MatchDecision


@dataclass(frozen=True)
class PendingReviewCompositionGroup:
    """One persisted pending-review shape, represented only by aggregates."""

    channel: str
    score: int
    has_conflicts: bool
    evidence_fields: tuple[str, ...]
    decision_reason: str | None
    count: int


@dataclass(frozen=True)
class PendingReviewCompositionAudit:
    """Aggregate composition of all currently pending identity reviews."""

    pending_count: int
    groups: tuple[PendingReviewCompositionGroup, ...]


def audit_pending_review_composition(db: Session) -> PendingReviewCompositionAudit:
    """Group persisted pending reviews by their explainable decision shape."""
    rows = db.execute(
        select(MatchDecision, CanonicalEvent)
        .join(CanonicalEvent, CanonicalEvent.id == MatchDecision.canonical_event_id)
        .where(
            MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED,
            MatchDecision.review_status == ReviewStatus.PENDING,
        )
    ).all()

    group_counts: Counter[tuple[str, int, bool, tuple[str, ...], str | None]] = Counter()
    for decision, event in rows:
        key = (
            event.channel.value,
            decision.score,
            bool(decision.conflicts),
            _evidence_fields(decision.evidence),
            _normalize_reason(decision.decision_reason),
        )
        group_counts[key] += 1

    groups = tuple(
        PendingReviewCompositionGroup(
            channel=channel,
            score=score,
            has_conflicts=has_conflicts,
            evidence_fields=evidence_fields,
            decision_reason=decision_reason,
            count=count,
        )
        for (channel, score, has_conflicts, evidence_fields, decision_reason), count in sorted(
            group_counts.items(),
            key=lambda item: (
                -item[1],
                item[0][0],
                -item[0][1],
                item[0][2],
                item[0][3],
                item[0][4] or "",
            ),
        )
    )
    return PendingReviewCompositionAudit(pending_count=len(rows), groups=groups)


def _evidence_fields(evidence: list[dict]) -> tuple[str, ...]:
    """Extract the stable field vocabulary without retaining evidence values."""
    fields = {
        field.strip()
        for item in evidence
        if isinstance(item, dict)
        and isinstance((field := item.get("field")), str)
        and field.strip()
    }
    return tuple(sorted(fields))


def _normalize_reason(reason: str | None) -> str | None:
    """Normalize presentation-only reason text for reproducible grouping."""
    if not reason:
        return None
    normalized = " ".join(reason.split()).lower()
    return normalized or None
