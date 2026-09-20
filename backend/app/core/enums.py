"""Shared JourneyLens enums.

Values are frozen in docs/05_API_CONTRACT.md. Any change requires a
decision-log entry and must be coordinated with the frontend team.
"""

from enum import StrEnum


class Channel(StrEnum):
    WEB = "web"
    MOBILE_APP = "mobile_app"
    CALL_CENTER = "call_center"
    PHYSICAL_STORE = "physical_store"


class ProcessingStatus(StrEnum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    FAILED = "failed"


class EventType(StrEnum):
    PRODUCT_VIEWED = "product_viewed"
    APP_LOGIN = "app_login"
    ORDER_PLACED = "order_placed"
    RETURN_REQUESTED = "return_requested"
    SUPPORT_CONTACTED = "support_contacted"
    STORE_VISITED = "store_visited"
    REFUND_COMPLETED = "refund_completed"


class ContactReason(StrEnum):
    """Bounded, list-safe context normalized from support source notes."""

    REFUND_NOT_RECEIVED = "refund_not_received"
    RETURN_STATUS = "return_status"
    OTHER = "other"


class IdentityOutcome(StrEnum):
    """Identity decision for a canonical event (Gate G2+)."""

    AUTO_LINKED = "auto_linked"
    REVIEW_REQUIRED = "review_required"
    NEW_PROFILE = "new_profile"


class ReviewDecision(StrEnum):
    """Human review action on a match decision (Gate G2+)."""

    APPROVE_LINK = "approve_link"
    REJECT_LINK = "reject_link"
    CREATE_PROFILE = "create_profile"


class AlertType(StrEnum):
    UNRESOLVED_REFUND = "unresolved_refund"
    REPEAT_CONTACT = "repeat_contact"


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROFILE_CREATED = "profile_created"


class ReviewQueueKind(StrEnum):
    """Server-derived classification for an unresolved review decision."""

    STRONG_IDENTIFIER_CONFLICT = "strong_identifier_conflict"
    AMBIGUOUS_MODERATE_MATCH = "ambiguous_moderate_match"
    SAME_NAME_COLLISION = "same_name_collision"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"


class ReviewQueuePriority(StrEnum):
    """Operational priority derived from a review queue classification."""

    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"


class DemoRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
