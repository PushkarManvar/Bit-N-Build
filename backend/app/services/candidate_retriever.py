"""Candidate retrieval for identity resolution.

Finds profiles that own any normalized identifier value present in the
incoming event. Retrieval only gathers possible profiles; it never decides
the winner (see identity_resolver).

Gate G2 indexes strong and moderate identifiers: email, phone, device_id,
session_id, customer_id, and order_id (from entity_references). Name and city
are intentionally not indexed; name similarity alone never produces a link.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProfileIdentifier
from app.services.normalizer import NormalizedEvent

STRONG_IDENTIFIER_TYPES: frozenset[str] = frozenset({"email", "phone", "customer_id", "order_id"})
MODERATE_IDENTIFIER_TYPES: frozenset[str] = frozenset({"device_id", "session_id"})


@dataclass(frozen=True)
class EventField:
    field: str
    value: str


@dataclass(frozen=True)
class CandidateInfo:
    profile_id: str
    matched_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievalResult:
    candidates: list[CandidateInfo]
    field_profile_map: dict[str, list[str]] = field(default_factory=dict)


def event_fields(event: NormalizedEvent) -> list[EventField]:
    fields = [EventField(ref["type"], ref["value"]) for ref in event.identifiers]
    order_id = event.entity_references.get("order_id")
    if order_id:
        fields.append(EventField("order_id", str(order_id)))
    return fields


def retrieve_candidates(db: Session, event: NormalizedEvent) -> RetrievalResult:
    fields = event_fields(event)
    if not fields:
        return RetrievalResult(candidates=[])

    conditions = [
        (ProfileIdentifier.type == f.field) & (ProfileIdentifier.value == f.value)
        for f in fields
    ]
    from sqlalchemy import or_

    rows = db.scalars(
        select(ProfileIdentifier).where(or_(*conditions))
    ).all()

    profile_fields: dict[str, set[str]] = {}
    field_profiles: dict[str, list[str]] = {}
    for row in rows:
        profile_fields.setdefault(str(row.profile_id), set()).add(row.type)
        field_profiles.setdefault(row.type, []).append(str(row.profile_id))

    candidates = [
        CandidateInfo(profile_id=pid, matched_fields=sorted(matched))
        for pid, matched in profile_fields.items()
    ]
    return RetrievalResult(candidates=candidates, field_profile_map=field_profiles)