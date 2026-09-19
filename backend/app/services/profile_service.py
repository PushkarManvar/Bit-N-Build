"""Profile and match-decision persistence for identity outcomes.

Creates/links profiles, upserts normalized identifiers, and records the
explainable match decision for every canonical event.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import IdentityOutcome, ReviewStatus
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    MatchDecision,
    ProfileIdentifier,
)
from app.services.identity_resolver import DecisionResult
from app.services.normalizer import NormalizedEvent

_EventLike = NormalizedEvent | CanonicalEvent


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _identifier_pairs(event: _EventLike) -> list[tuple[str, str]]:
    values = [(ref["type"], ref["value"]) for ref in event.identifiers if ref.get("value")]
    order_id = event.entity_references.get("order_id")
    if order_id:
        values.append(("order_id", str(order_id)))
    return values


def _display_name(event: _EventLike) -> str | None:
    raw = event.attributes.get("customer_name")
    if not raw:
        return None
    normalized = " ".join(str(raw).strip().split())
    return normalized or None


def _upsert_identifiers(db: Session, profile_id: uuid.UUID, event: _EventLike) -> None:
    """Claim identifiers for a profile, skipping values already owned anywhere.

    A normalized identifier belongs to exactly one profile (first seen wins).
    This keeps review reject/create paths from stealing identifiers that a
    candidate profile already owns (e.g. a shared device).
    """
    now = _now_utc()
    owned = set(
        db.execute(select(ProfileIdentifier.type, ProfileIdentifier.value)).all()
    )
    for id_type, value in _identifier_pairs(event):
        if (id_type, value) in owned:
            continue
        db.add(
            ProfileIdentifier(
                profile_id=profile_id,
                type=id_type,
                value=value,
                first_seen_at=now,
            )
        )
        owned.add((id_type, value))


def attach_event_to_profile(
    db: Session,
    canonical: CanonicalEvent,
    event: _EventLike,
    profile: CustomerProfile,
) -> None:
    """Attach a canonical event to an existing profile (auto-link or review approve)."""
    now = _now_utc()
    profile.last_seen_at = now
    if profile.display_name is None:
        profile.display_name = _display_name(event)
    _upsert_identifiers(db, profile.id, event)
    canonical.profile_id = profile.id


def create_profile_for_event(
    db: Session,
    canonical: CanonicalEvent,
    event: _EventLike,
) -> CustomerProfile:
    """Create a fresh profile and attach the event to it (new_profile or review reject)."""
    now = _now_utc()
    profile = CustomerProfile(
        display_name=_display_name(event),
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(profile)
    db.flush()
    attach_event_to_profile(db, canonical, event, profile)
    return profile


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
        review_status=(
            ReviewStatus.PENDING
            if decision.outcome == IdentityOutcome.REVIEW_REQUIRED
            else None
        ),
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
    profile = create_profile_for_event(db, canonical, event)
    persist_match_decision(db, canonical, decision, profile_id=profile.id)
    return profile


def apply_auto_link(
    db: Session,
    canonical: CanonicalEvent,
    event: NormalizedEvent,
    decision: DecisionResult,
    profile: CustomerProfile,
) -> None:
    attach_event_to_profile(db, canonical, event, profile)
    persist_match_decision(db, canonical, decision, profile_id=profile.id)


def apply_review_required(
    db: Session,
    canonical: CanonicalEvent,
    decision: DecisionResult,
) -> None:
    """Hold the event without linking; record the pending decision for review."""
    persist_match_decision(db, canonical, decision, profile_id=None)


def get_profile(db: Session, profile_id: str) -> CustomerProfile | None:
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        return None
    return db.get(CustomerProfile, profile_uuid)