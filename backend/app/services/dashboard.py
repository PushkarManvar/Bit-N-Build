"""Dashboard polling feed (docs/05_API_CONTRACT.md section 10)."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ReviewStatus
from app.db.models import (
    CanonicalEvent,
    JourneyAlert,
    MatchDecision,
)
from app.schemas.demo import DashboardEventOut, DashboardUpdatesResponse
from app.schemas.profiles import AlertOut
from app.services.demo import latest_run


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def dashboard_updates(db: Session, since: datetime | None) -> DashboardUpdatesResponse:
    event_stmt = (
        select(CanonicalEvent, MatchDecision)
        .join(
            MatchDecision,
            MatchDecision.canonical_event_id == CanonicalEvent.id,
            isouter=True,
        )
        .order_by(CanonicalEvent.created_at.desc())
        .limit(20)
    )
    if since is not None:
        event_stmt = event_stmt.where(CanonicalEvent.created_at > since)

    events: list[DashboardEventOut] = []
    for canonical, decision in db.execute(event_stmt).all():
        events.append(
            DashboardEventOut(
                event_id=str(canonical.id),
                channel=canonical.channel,
                event_type=canonical.event_type,
                occurred_at=_to_utc(canonical.occurred_at),
                profile_id=str(canonical.profile_id) if canonical.profile_id else None,
                match_decision=decision.outcome if decision else None,
            )
        )

    alert_stmt = select(JourneyAlert).where(JourneyAlert.status == "open")
    if since is not None:
        alert_stmt = alert_stmt.where(JourneyAlert.created_at > since)
    alerts = [
        AlertOut(
            id=str(alert.id),
            type=alert.type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            recommended_action=alert.recommended_action,
            status=alert.status,
            order_id=alert.order_id,
            created_at=_to_utc(alert.created_at),
        )
        for alert in db.scalars(alert_stmt.order_by(JourneyAlert.created_at.desc())).all()
    ]

    open_alerts = int(
        db.scalar(
            select(func.count())
            .select_from(JourneyAlert)
            .where(JourneyAlert.status == "open")
        )
        or 0
    )
    pending = int(
        db.scalar(
            select(func.count())
            .select_from(MatchDecision)
            .where(MatchDecision.review_status == ReviewStatus.PENDING)
        )
        or 0
    )

    demo = latest_run(db)
    return DashboardUpdatesResponse(
        events=events,
        new_alerts=alerts,
        open_alerts=open_alerts,
        pending_reviews=pending,
        demo=demo,
    )