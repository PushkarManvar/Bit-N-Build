"""Pydantic schemas for analytics endpoints (docs/05_API_CONTRACT.md section 9)."""

from datetime import datetime

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_raw_events: int
    normalized_events: int
    failed_events: int
    duplicate_events: int | None = None
    unified_profiles: int
    auto_link_rate: float | None = None
    review_required_rate: float | None = None
    open_alerts: int
    match_precision: float | None = None
    match_recall: float | None = None
    match_f1: float | None = None
    false_merge_rate: float | None = None
    average_processing_latency_ms: int | None = None


class ChannelsResponse(BaseModel):
    web: int
    mobile_app: int
    call_center: int
    physical_store: int


class FrictionScoreComponents(BaseModel):
    unresolved_age_points: int
    channel_points: int
    support_contact_points: int
    repeat_contact_points: int
    pending_candidate_review_points: int


class FrictionJourney(BaseModel):
    alert_id: str
    profile_id: str
    display_name: str | None
    order_id: str
    friction_score: int
    band: str
    unresolved_age_days: int
    distinct_channel_count: int
    support_contact_count: int
    has_open_repeat_contact_alert: bool
    pending_candidate_review_count: int
    components: FrictionScoreComponents


class FrictionRadarSummary(BaseModel):
    attributable_open_refunds: int
    unattributed_open_refunds: int
    critical: int
    elevated: int
    watch: int


class FrictionAgeDistributionBucket(BaseModel):
    bucket: str
    count: int


class FrictionSupportContactChannel(BaseModel):
    channel: str
    count: int
    share_percent: float | None


class FrictionRadarResponse(BaseModel):
    as_of: datetime
    score_version: str
    score_max: int
    summary: FrictionRadarSummary
    journeys: list[FrictionJourney]
    unresolved_age_distribution: list[FrictionAgeDistributionBucket]
    support_contact_channels: list[FrictionSupportContactChannel]
