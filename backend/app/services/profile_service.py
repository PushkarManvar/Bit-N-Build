"""Profile and match-decision persistence for identity outcomes.

Creates/link profiles, upserts normalized identifiers, and records the
explainable match decision for every canonical event.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    MatchDecision,
    ProfileIdentifier,
)
from app.services.identity_resolver import DecisionResult
from app.services.normalizer import NormalizedEvent


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _identifier_values(event: NormalizedEvent) -> list[tuple[str, str]]:
    values = [(ref["type"], ref["value"]) for ref in event.identifiers if ref.get("value")]
    order_id = event.entity_references.get("order_id")
    if order_id:
        values.append(("order_id", str(order_id)))
    return values


def _display_name(event: NormalizedEvent) -> str | None:
    raw = event.attributes.get("customer_name")
    if not raw:
        return None
    normalized = " ".join(str(raw).strip().split())
    return normalized or None


def _upsert_identifiers(db: Session, profile_id: uuid.UUID, event: NormalizedEvent) -> None:
    now = _now_utc()
    existing = set(
        db.scalars(
            select(ProfileIdentifier).where(ProfileIdentifier.profile_id == profile_id)
        ).all()
    )
    existing_pairs = {(row.type, row.value) for row in existing}
    for id_type, value in _identifier_values(event):
        if (id_type, value) in existing_pairs:
            continue
        db.add(
            ProfileIdentifier(
                profile_id=profile_id,
                type=id_type,
                value=value,
                first_seen_at=now,
            )
        )


def _link_canonical(db: Session, canonical: CanonicalEvent, profile_id: uuid.UUID) -> None:
    canonical.profile_id = profile_id


def persist_match_decision(
    db: Session,
    canonical: CanonicalEvent,
    decision: DecisionResult,
    *,
    profile_id: uuid.UUID | None,
) -> MatchDecision:
    record = MatchDecision(
        canonical_event_id=canonical.id,
        profile_id=profile_id,
        outcome=decision.outcome,
        score=decision.score,
        thresholds=decision.thresholds,
        evidence=decision.evidence,
        conflicts=decision.conflicts,
        candidates=decision.candidates,
        decision_reason=decision.reason,
    )
    db.add(record)
    db.flush()
    return record


def apply_new_profile(
    db: Session,
    canonical: CanonicalEvent,
    event: NormalizedEvent,
    decision: DecisionResult,
) -> CustomerProfile:
    now = _now_utc()
    profile = CustomerProfile(
        display_name=_display_name(event),
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(profile)
    db.flush()
    _upsert_identifiers(db, profile.id, event)
    _link_canonical(db, canonical, profile.id)
    persist_match_decision(db, canonical, decision, profile_id=profile.id)
    return profile


def apply_auto_link(
    db: Session,
    canonical: CanonicalEvent,
    event: NormalizedEvent,
    decision: DecisionResult,
    profile: CustomerProfile,
) -> None:
    now = _now_utc()
    profile.last_seen_at = now
    if profile.display_name is None:
        profile.display_name = _display_name(event)
    _upsert_identifiers(db, profile.id, event)
    _link_canonical(db, canonical, profile.id)
    persist_match_decision(db, canonical, decision, profile_id=profile.id)


def apply_review_required(
    db: Session,
    canonical: CanonicalEvent,
    decision: DecisionResult,
) -> None:
    """Hold the event without linking; record the decision for the review queue."""
    persist_match_decision(db, canonical, decision, profile_id=None)


def get_profile(db: Session, profile_id: str) -> CustomerProfile | None:
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        return None
    return db.get(CustomerProfile, profile_uuid)