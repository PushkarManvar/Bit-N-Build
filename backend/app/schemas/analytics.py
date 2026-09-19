"""Pydantic schemas for analytics endpoints (docs/05_API_CONTRACT.md section 9)."""

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