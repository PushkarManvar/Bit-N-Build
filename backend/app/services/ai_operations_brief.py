"""Optional, facts-only LLM wording for the deterministic Friction Radar."""

import json
import logging
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.analytics import AiOperationsBrief, FrictionJourney, FrictionRadarResponse

SIGNALS = frozenset(
    {"unresolved_age", "support_channels", "support_contacts", "repeat_contact", "candidate_review"}
)
_CACHE_TTL = timedelta(minutes=5)
_brief_cache: dict[str, AiOperationsBrief] = {}
logger = logging.getLogger(__name__)


class _ProviderBrief(BaseModel):
    headline: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=420)
    focus_alert_id: str
    highlighted_signal: str


def _source_packet(radar: FrictionRadarResponse) -> dict[str, Any]:
    return {
        "score_version": radar.score_version,
        "score_max": radar.score_max,
        "summary": radar.summary.model_dump(),
        "journeys": [journey.model_dump() for journey in radar.journeys],
    }


def _cache_key(radar: FrictionRadarResponse) -> str:
    """Cache only a wording result for the exact deterministic source snapshot."""
    source = json.dumps(_source_packet(radar), sort_keys=True, separators=(",", ":"))
    return sha256(source.encode()).hexdigest()


def _prompt(radar: FrictionRadarResponse) -> str:
    return (
        "You are writing a short operations brief from verified JourneyLens facts. "
        "Never infer refund status, churn, identity, SLA, or any fact outside the source packet. "
        "Return ONLY this JSON object with no markdown: "
        '{"headline":"string","summary":"string","focus_alert_id":"string",'
        '"highlighted_signal":"unresolved_age|support_channels|support_contacts|'
        'repeat_contact|candidate_review"}. '
        "focus_alert_id must be an alert_id in the packet. highlighted_signal must be non-zero "
        "or true for that same journey. Source packet: "
        + json.dumps(_source_packet(radar), separators=(",", ":"))
    )


def _request_json(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - configured provider URLs only
            return json.loads(response.read().decode())
    except HTTPError as exc:
        provider_message = exc.read().decode(errors="replace")[:500]
        logger.warning(
            "AI provider request rejected: status=%s body=%s", exc.code, provider_message
        )
        retryable = exc.code == 429 or exc.code >= 500
        raise _ProviderFailure(
            f"provider request failed ({exc.code})", retryable=retryable
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise _ProviderFailure("provider request timed out", retryable=True) from exc


class _ProviderFailure(Exception):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


def _google(radar: FrictionRadarResponse, settings: Settings) -> _ProviderBrief:
    if not all(
        (settings.llm_primary_base_url, settings.llm_primary_api_key, settings.llm_primary_model)
    ):
        raise _ProviderFailure("primary AI configuration is incomplete", retryable=False)
    response = _request_json(
        f"{settings.llm_primary_base_url}/models/{settings.llm_primary_model}:generateContent",
        {"x-goog-api-key": settings.llm_primary_api_key},
        {
            "contents": [
                {"parts": [{"text": _prompt(radar)}]},
            ],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
        },
    )
    text = response["candidates"][0]["content"]["parts"][0]["text"]
    return _ProviderBrief.model_validate_json(text)


def _groq(radar: FrictionRadarResponse, settings: Settings) -> _ProviderBrief:
    if not all(
        (settings.llm_backup_base_url, settings.llm_backup_api_key, settings.llm_backup_model)
    ):
        raise _ProviderFailure("backup AI configuration is incomplete", retryable=False)
    response = _request_json(
        f"{settings.llm_backup_base_url}/chat/completions",
        {"Authorization": f"Bearer {settings.llm_backup_api_key}"},
        {
            "model": settings.llm_backup_model,
            "messages": [{"role": "user", "content": _prompt(radar)}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
    )
    return _ProviderBrief.model_validate_json(response["choices"][0]["message"]["content"])


def _signal_is_present(journey: FrictionJourney, signal: str) -> bool:
    return {
        "unresolved_age": journey.unresolved_age_days > 0,
        "support_channels": journey.distinct_channel_count > 0,
        "support_contacts": journey.support_contact_count > 0,
        "repeat_contact": journey.has_open_repeat_contact_alert,
        "candidate_review": journey.pending_candidate_review_count > 0,
    }.get(signal, False)


def generate_operations_brief(
    radar: FrictionRadarResponse, settings: Settings
) -> AiOperationsBrief:
    """Generate wording; deterministic radar facts remain the authority."""
    if not radar.journeys:
        raise AppError(
            "AI_BRIEF_NO_DATA",
            "No ranked journey is available to summarize.",
            "analytics",
            http_status=409,
        )
    cache_key = _cache_key(radar)
    cached = _brief_cache.get(cache_key)
    if cached and datetime.now(UTC) - cached.generated_at < _CACHE_TTL:
        return cached.model_copy(update={"cached": True})

    provider = "google"
    model = settings.llm_primary_model or ""
    try:
        draft = _google(radar, settings)
    except _ProviderFailure as primary_error:
        if not primary_error.retryable:
            raise AppError(
                "AI_BRIEF_UNAVAILABLE", str(primary_error), "ai_brief", http_status=503
            ) from primary_error
        provider, model = "groq", settings.llm_backup_model or ""
        try:
            draft = _groq(radar, settings)
        except _ProviderFailure as backup_error:
            raise AppError(
                "AI_BRIEF_UNAVAILABLE", str(backup_error), "ai_brief", http_status=503
            ) from backup_error
    except (KeyError, ValidationError, json.JSONDecodeError) as exc:
        raise AppError(
            "AI_BRIEF_UNAVAILABLE", "AI returned an invalid brief.", "ai_brief", http_status=503
        ) from exc
    focus = next(
        (journey for journey in radar.journeys if journey.alert_id == draft.focus_alert_id), None
    )
    if (
        focus is None
        or draft.highlighted_signal not in SIGNALS
        or not _signal_is_present(focus, draft.highlighted_signal)
    ):
        raise AppError(
            "AI_BRIEF_UNAVAILABLE",
            "AI brief did not match its verified source facts.",
            "ai_brief",
            http_status=503,
        )
    brief = AiOperationsBrief(
        **draft.model_dump(), provider=provider, model=model, generated_at=datetime.now(UTC)
    )
    _brief_cache[cache_key] = brief
    return brief
