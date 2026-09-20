"""Facts-only AI operations brief service tests."""

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.schemas.analytics import (
    FrictionAgeDistributionBucket,
    FrictionJourney,
    FrictionRadarResponse,
    FrictionRadarSummary,
    FrictionScoreComponents,
)
from app.services import ai_operations_brief as brief_service


@pytest.fixture(autouse=True)
def clear_brief_cache() -> None:
    brief_service._brief_cache.clear()


def _radar() -> FrictionRadarResponse:
    return FrictionRadarResponse(
        as_of=datetime.now(UTC),
        score_version="friction_v1",
        score_max=60,
        summary=FrictionRadarSummary(
            attributable_open_refunds=1,
            unattributed_open_refunds=0,
            critical=1,
            elevated=0,
            watch=0,
        ),
        journeys=[
            FrictionJourney(
                alert_id="alert-1",
                profile_id="profile-1",
                display_name="Synthetic profile",
                order_id="ORD-1",
                friction_score=30,
                band="elevated",
                unresolved_age_days=5,
                distinct_channel_count=2,
                support_contact_count=1,
                has_open_repeat_contact_alert=False,
                pending_candidate_review_count=0,
                components=FrictionScoreComponents(
                    unresolved_age_points=20,
                    channel_points=6,
                    support_contact_points=4,
                    repeat_contact_points=0,
                    pending_candidate_review_points=0,
                ),
            )
        ],
        unresolved_age_distribution=[FrictionAgeDistributionBucket(bucket="4–7 days", count=1)],
        support_contact_channels=[],
    )


def _draft() -> brief_service._ProviderBrief:
    return brief_service._ProviderBrief(
        headline="Prioritize this refund",
        summary="The unresolved age is the largest persisted friction signal.",
        focus_alert_id="alert-1",
        highlighted_signal="unresolved_age",
    )


def test_brief_is_fact_valid_and_reuses_identical_snapshot_wording(monkeypatch) -> None:
    calls = 0

    def fake_google(*_args: object) -> brief_service._ProviderBrief:
        nonlocal calls
        calls += 1
        return _draft()

    monkeypatch.setattr(brief_service, "_google", fake_google)
    settings = Settings(llm_primary_model="test-primary")

    first = brief_service.generate_operations_brief(_radar(), settings)
    second = brief_service.generate_operations_brief(_radar(), settings)

    assert first.provider == "google"
    assert first.cached is False
    assert second.cached is True
    assert second.focus_alert_id == "alert-1"
    assert calls == 1


def test_retryable_primary_failure_uses_the_backup_provider(monkeypatch) -> None:
    def fail_google(*_args: object) -> brief_service._ProviderBrief:
        raise brief_service._ProviderFailure("rate limited", retryable=True)

    monkeypatch.setattr(brief_service, "_google", fail_google)
    monkeypatch.setattr(brief_service, "_groq", lambda *_args: _draft())
    settings = Settings(llm_primary_model="test-primary", llm_backup_model="test-backup")

    response = brief_service.generate_operations_brief(_radar(), settings)

    assert response.provider == "groq"
    assert response.model == "test-backup"
