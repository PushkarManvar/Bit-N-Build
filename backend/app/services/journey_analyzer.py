"""Deterministic journey alert rules (docs/04_DATA_IDENTITY_AND_RULES.md §10).

Rules implemented for Gate G4:
- JR-001 Unresolved refund (high)
- JR-002 Repeat contact (medium)

Open alerts are deduplicated by (profile, order, type) so the analyzer is
safe to run repeatedly (JR-03).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AlertSeverity, AlertStatus, AlertType, EventType
from app.db.models import CanonicalEvent, JourneyAlert

REPEAT_CONTACT_WINDOW = timedelta(hours=72)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

SUPPORT_EVENT_TYPES: frozenset[EventType] = frozenset({EventType.SUPPORT_CONTACTED})
RETURN_EVENT_TYPES: frozenset[EventType] = frozenset({EventType.RETURN_REQUESTED})
COMPLETION_EVENT_TYPES: frozenset[EventType] = frozenset({EventType.REFUND_COMPLETED})


def _events_for_profile(db: Session, profile_id: uuid.UUID) -> list[CanonicalEvent]:
    return list(
        db.scalars(
            select(CanonicalEvent)
            .where(CanonicalEvent.profile_id == profile_id)
            .order_by(CanonicalEvent.occurred_at)
        ).all()
    )


def _order_of(event: CanonicalEvent) -> str | None:
    value = event.entity_references.get("order_id")
    return str(value) if value else None


def _open_alert_exists(
    db: Session, profile_id: uuid.UUID, order_id: str | None, alert_type: AlertType
) -> bool:
    statement = select(JourneyAlert).where(
        JourneyAlert.profile_id == profile_id,
        JourneyAlert.type == alert_type,
        JourneyAlert.status == AlertStatus.OPEN,
    )
    if order_id is None:
        statement = statement.where(JourneyAlert.order_id.is_(None))
    else:
        statement = statement.where(JourneyAlert.order_id == order_id)
    return db.scalar(statement) is not None


def _add_alert(
    db: Session,
    profile_id: uuid.UUID,
    order_id: str | None,
    alert_type: AlertType,
    severity: AlertSeverity,
    title: str,
    description: str,
    recommended_action: str,
) -> JourneyAlert | None:
    if _open_alert_exists(db, profile_id, order_id, alert_type):
        return None
    alert = JourneyAlert(
        profile_id=profile_id,
        order_id=order_id,
        type=alert_type,
        severity=severity,
        title=title,
        description=description,
        recommended_action=recommended_action,
        status=AlertStatus.OPEN,
    )
    db.add(alert)
    db.flush()
    return alert


def analyze_profile(db: Session, profile_id: uuid.UUID) -> list[JourneyAlert]:
    """Evaluate all journey rules for a profile and create missing alerts.

    Idempotent: rerunning produces no duplicate open alerts (JR-03).
    """
    events = _events_for_profile(db, profile_id)
    created: list[JourneyAlert] = []
    created.extend(_rule_unresolved_refund(db, profile_id, events))
    created.extend(_rule_repeat_contact(db, profile_id, events))
    return created


def _rule_unresolved_refund(
    db: Session, profile_id: uuid.UUID, events: list[CanonicalEvent]
) -> list[JourneyAlert]:
    """JR-001: return exists, no completion, at least two support contacts."""
    buckets: dict[str | None, dict[str, object]] = {}
    for event in events:
        order = _order_of(event)
        bucket = buckets.setdefault(
            order, {"returns": 0, "supports": 0, "completed": False}
        )
        if event.event_type in RETURN_EVENT_TYPES:
            bucket["returns"] = int(bucket["returns"]) + 1
        if event.event_type in SUPPORT_EVENT_TYPES:
            bucket["supports"] = int(bucket["supports"]) + 1
        if event.event_type in COMPLETION_EVENT_TYPES:
            bucket["completed"] = True

    created: list[JourneyAlert] = []
    for order, bucket in buckets.items():
        if not (
            bucket["returns"] >= 1
            and not bucket["completed"]
            and bucket["supports"] >= 2
        ):
            continue
        label = f"Refund {order} remains unresolved" if order else "Refund remains unresolved"
        alert = _add_alert(
            db,
            profile_id,
            order,
            AlertType.UNRESOLVED_REFUND,
            AlertSeverity.HIGH,
            title=label,
            description="Return activity and repeated contacts exist without a refund completion.",
            recommended_action="Prioritize refund resolution.",
        )
        if alert is not None:
            created.append(alert)
    return created


def _rule_repeat_contact(
    db: Session, profile_id: uuid.UUID, events: list[CanonicalEvent]
) -> list[JourneyAlert]:
    """JR-002: two support contacts within 72 hours for the same profile/order."""
    support: dict[str | None, list[CanonicalEvent]] = {}
    for event in events:
        if event.event_type in SUPPORT_EVENT_TYPES:
            support.setdefault(_order_of(event), []).append(event)
    for order_events in support.values():
        order_events.sort(key=lambda e: _utc(e.occurred_at))

    created: list[JourneyAlert] = []
    for order, order_events in support.items():
        for index in range(len(order_events) - 1):
            gap = _utc(order_events[index + 1].occurred_at) - _utc(order_events[index].occurred_at)
            if gap <= REPEAT_CONTACT_WINDOW:
                alert = _add_alert(
                    db,
                    profile_id,
                    order,
                    AlertType.REPEAT_CONTACT,
                    AlertSeverity.MEDIUM,
                    title="Repeated support contact",
                    description="Multiple support contacts occurred within 72 hours.",
                    recommended_action=(
                        "Resolve the underlying issue and confirm resolution "
                        "with the customer."
                    ),
                )
                if alert is not None:
                    created.append(alert)
                break
    return created