"""Safe, additive operations read model for pending identity reviews."""

import base64
import binascii
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    Channel,
    IdentityOutcome,
    ReviewQueueKind,
    ReviewQueuePriority,
    ReviewStatus,
)
from app.core.errors import AppError
from app.db.models import CanonicalEvent, CustomerProfile, MatchDecision
from app.schemas.reviews import (
    ReviewEventOut,
    ReviewQueueCandidateOut,
    ReviewQueueConflictOut,
    ReviewQueueEvidenceOut,
    ReviewQueueItem,
    ReviewQueueListResponse,
    ReviewQueueSummary,
)
from app.services.identity_resolver import (
    AUTO_LINK_THRESHOLD,
    MODERATE_WEIGHTS,
    REVIEW_THRESHOLD,
    SAME_NAME_COLLISION_REASON,
    TIE_DELTA,
)

_STRONG_IDENTIFIER_TYPES = frozenset({"email", "phone", "customer_id", "order_id"})
_PRIORITY_RANK = {
    ReviewQueuePriority.CRITICAL: 3,
    ReviewQueuePriority.HIGH: 2,
    ReviewQueuePriority.STANDARD: 1,
}


@dataclass(frozen=True)
class ReviewQueueFilters:
    status: str = "pending"
    channel: Channel | None = None
    kind: ReviewQueueKind | None = None
    priority: ReviewQueuePriority | None = None


@dataclass(frozen=True)
class ReviewQueueCursor:
    priority_rank: int
    created_at: datetime
    match_decision_id: uuid.UUID


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _filters_fingerprint(filters: ReviewQueueFilters) -> str:
    payload = {
        "channel": filters.channel.value if filters.channel else None,
        "kind": filters.kind.value if filters.kind else None,
        "priority": filters.priority.value if filters.priority else None,
        "status": filters.status,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _invalid_cursor() -> AppError:
    return AppError(
        code="VALIDATION_ERROR",
        message="Review queue cursor is invalid or does not match the active filters.",
        stage="review_queue",
        http_status=422,
    )


def _encode_cursor(item: ReviewQueueItem, filters: ReviewQueueFilters) -> str:
    payload = {
        "created_at": _to_utc(item.created_at).isoformat(),
        "filters": _filters_fingerprint(filters),
        "kind": "review_queue_v1",
        "match_decision_id": item.match_decision_id,
        "priority_rank": _PRIORITY_RANK[item.priority],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _decode_cursor(value: str, filters: ReviewQueueFilters) -> ReviewQueueCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if (
            payload.get("kind") != "review_queue_v1"
            or payload.get("filters") != _filters_fingerprint(filters)
        ):
            raise ValueError
        priority_rank = int(payload["priority_rank"])
        if priority_rank not in _PRIORITY_RANK.values():
            raise ValueError
        created_at = datetime.fromisoformat(payload["created_at"])
        decision_id = uuid.UUID(payload["match_decision_id"])
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise _invalid_cursor() from exc
    return ReviewQueueCursor(
        priority_rank=priority_rank,
        created_at=_to_utc(created_at),
        match_decision_id=decision_id,
    )


def _review_kind(decision: MatchDecision) -> ReviewQueueKind:
    if decision.conflicts:
        return ReviewQueueKind.STRONG_IDENTIFIER_CONFLICT

    candidates = sorted(
        decision.candidates,
        key=lambda item: (-item.get("score", 0), item["profile_id"]),
    )
    candidate_fields = [set(item.get("retrieved_by", [])) for item in candidates]
    if (
        len(candidates) >= 2
        and candidates[0].get("score", 0) - candidates[1].get("score", 0) <= TIE_DELTA
        and all(fields and fields <= MODERATE_WEIGHTS.keys() for fields in candidate_fields[:2])
    ):
        return ReviewQueueKind.AMBIGUOUS_MODERATE_MATCH
    if not candidates and decision.decision_reason == SAME_NAME_COLLISION_REASON:
        return ReviewQueueKind.SAME_NAME_COLLISION
    if (
        len(candidates) == 1
        and candidate_fields[0]
        and candidate_fields[0] <= MODERATE_WEIGHTS.keys()
        and REVIEW_THRESHOLD <= decision.score < AUTO_LINK_THRESHOLD
    ):
        return ReviewQueueKind.INCOMPLETE_EVIDENCE

    raise AppError(
        code="REVIEW_QUEUE_CLASSIFICATION_UNAVAILABLE",
        message="Pending review cannot be classified by the current queue policy.",
        stage="review_queue",
        http_status=409,
    )


def _priority(kind: ReviewQueueKind) -> ReviewQueuePriority:
    if kind == ReviewQueueKind.STRONG_IDENTIFIER_CONFLICT:
        return ReviewQueuePriority.CRITICAL
    if kind == ReviewQueueKind.AMBIGUOUS_MODERATE_MATCH:
        return ReviewQueuePriority.HIGH
    return ReviewQueuePriority.STANDARD


def _profile_names(db: Session, decisions: list[MatchDecision]) -> dict[str, str | None]:
    profile_ids: set[uuid.UUID] = set()
    for decision in decisions:
        for candidate in decision.candidates:
            try:
                profile_ids.add(uuid.UUID(candidate["profile_id"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not profile_ids:
        return {}
    return {
        str(profile.id): profile.display_name
        for profile in db.scalars(
            select(CustomerProfile).where(CustomerProfile.id.in_(profile_ids))
        )
    }


def _present_identifiers(canonical: CanonicalEvent) -> set[str]:
    present = {item["type"] for item in canonical.identifiers}
    if canonical.entity_references.get("order_id"):
        present.add("order_id")
    return present


def _safe_candidates(
    decision: MatchDecision,
    profile_names: dict[str, str | None],
) -> list[ReviewQueueCandidateOut]:
    candidates = sorted(
        decision.candidates,
        key=lambda item: (-item.get("score", 0), item["profile_id"]),
    )
    return [
        ReviewQueueCandidateOut(
            profile_id=candidate["profile_id"],
            display_name=profile_names.get(candidate["profile_id"]),
            score=candidate.get("score", 0),
            matched_fields=list(candidate.get("retrieved_by", [])),
        )
        for candidate in candidates
    ]


def _safe_evidence(decision: MatchDecision) -> list[ReviewQueueEvidenceOut]:
    return [
        ReviewQueueEvidenceOut(
            field=item["field"],
            result=item["result"],
            weight=item["weight"],
            message=item["message"],
        )
        for item in decision.evidence
    ]


def _conflict_message(fields: list[str]) -> str:
    readable = [field.replace("_", " ") for field in fields]
    if len(readable) == 2:
        return f"{readable[0].capitalize()} and {readable[1]} resolve to different profiles."
    return "Strong identifiers resolve to different profiles."


def _safe_conflicts(decision: MatchDecision) -> list[ReviewQueueConflictOut]:
    return [
        ReviewQueueConflictOut(
            fields=list(item.get("fields", [])),
            message=_conflict_message(list(item.get("fields", []))),
        )
        for item in decision.conflicts
    ]


def _queue_item(
    decision: MatchDecision,
    canonical: CanonicalEvent,
    profile_names: dict[str, str | None],
) -> ReviewQueueItem:
    kind = _review_kind(decision)
    attributes = canonical.attributes or {}
    return ReviewQueueItem(
        match_decision_id=str(decision.id),
        created_at=_to_utc(decision.created_at),
        review_kind=kind,
        priority=_priority(kind),
        event=ReviewEventOut(
            channel=canonical.channel,
            event_type=canonical.event_type,
            customer_name=attributes.get("customer_name"),
            occurred_at=_to_utc(canonical.occurred_at),
        ),
        candidates=_safe_candidates(decision, profile_names),
        evidence=_safe_evidence(decision),
        conflicts=_safe_conflicts(decision),
        missing_strong_identifiers=sorted(
            _STRONG_IDENTIFIER_TYPES - _present_identifiers(canonical)
        ),
        reason_code=kind.value,
        reason=decision.decision_reason or "",
    )


def _sort_key(item: ReviewQueueItem) -> tuple[int, datetime, str]:
    return (-_PRIORITY_RANK[item.priority], _to_utc(item.created_at), item.match_decision_id)


def _cursor_sort_key(cursor: ReviewQueueCursor) -> tuple[int, datetime, str]:
    return (-cursor.priority_rank, cursor.created_at, str(cursor.match_decision_id))


def list_review_queue(
    db: Session,
    filters: ReviewQueueFilters,
    *,
    limit: int = 20,
    cursor: str | None = None,
) -> ReviewQueueListResponse:
    """Return an opaque-cursor page of server-classified pending reviews."""
    statement = (
        select(MatchDecision, CanonicalEvent)
        .join(CanonicalEvent, CanonicalEvent.id == MatchDecision.canonical_event_id)
        .where(
            MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED,
            MatchDecision.review_status == ReviewStatus.PENDING,
        )
    )
    if filters.channel is not None:
        statement = statement.where(CanonicalEvent.channel == filters.channel)

    rows = list(db.execute(statement).all())
    profile_names = _profile_names(db, [decision for decision, _ in rows])
    matching_items = [
        _queue_item(decision, canonical, profile_names) for decision, canonical in rows
    ]
    if filters.kind is not None:
        matching_items = [item for item in matching_items if item.review_kind == filters.kind]
    if filters.priority is not None:
        matching_items = [item for item in matching_items if item.priority == filters.priority]
    matching_items.sort(key=_sort_key)

    summary = ReviewQueueSummary(
        pending=len(matching_items),
        critical_conflicts=sum(
            item.review_kind == ReviewQueueKind.STRONG_IDENTIFIER_CONFLICT
            for item in matching_items
        ),
        incomplete_evidence=sum(
            item.review_kind == ReviewQueueKind.INCOMPLETE_EVIDENCE
            for item in matching_items
        ),
    )
    page_cursor = _decode_cursor(cursor, filters) if cursor else None
    if page_cursor is not None:
        matching_items = [
            item for item in matching_items if _sort_key(item) > _cursor_sort_key(page_cursor)
        ]
    visible_items = matching_items[:limit]
    next_cursor = (
        _encode_cursor(visible_items[-1], filters)
        if len(matching_items) > limit and visible_items
        else None
    )
    return ReviewQueueListResponse(
        items=visible_items,
        total=summary.pending,
        next_cursor=next_cursor,
        summary=summary,
    )
