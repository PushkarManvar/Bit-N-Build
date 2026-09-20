"""Deterministic identity decision engine.

Scores candidate profiles against the incoming event, detects strong
conflicts, and decides one of: auto_linked, review_required, new_profile.
Pure and deterministic; all inputs are passed in (no database access).

Policy source: docs/04_DATA_IDENTITY_AND_RULES.md. A strong conflict always
blocks auto-linking; name similarity alone never auto-links.
"""

from dataclasses import dataclass, field

from app.core.enums import IdentityOutcome
from app.services.candidate_retriever import CandidateInfo
from app.services.normalizer import NormalizedEvent

AUTO_LINK_THRESHOLD = 80
REVIEW_THRESHOLD = 50
TIE_DELTA = 5
MAX_SCORE = 100
SAME_NAME_COLLISION_REASON = (
    "A matching name exists, but no identifier evidence supports a link."
)

STRONG_WEIGHTS: dict[str, int] = {
    "customer_id": 100,
    "order_id": 95,
    "email": 90,
    "phone": 85,
}
MODERATE_WEIGHTS: dict[str, int] = {"device_id": 45, "session_id": 35}

THRESHOLDS: dict[str, int] = {
    "auto_link": AUTO_LINK_THRESHOLD,
    "review_required": REVIEW_THRESHOLD,
}


@dataclass(frozen=True)
class Evidence:
    field: str
    incoming_value: str
    candidate_value: str
    result: str
    weight: int
    message: str


@dataclass(frozen=True)
class CandidateScore:
    profile_id: str
    retrieved_by: list[str]
    score: int
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionResult:
    outcome: IdentityOutcome
    score: int
    selected_profile_id: str | None
    evidence: list[dict]
    conflicts: list[dict]
    candidates: list[dict]
    reason: str
    thresholds: dict[str, int]


def _weight(field: str) -> int:
    return STRONG_WEIGHTS.get(field, MODERATE_WEIGHTS.get(field, 0))


def _is_strong(field: str) -> bool:
    return field in STRONG_WEIGHTS


def _event_field_map(event: NormalizedEvent) -> dict[str, str]:
    mapping: dict[str, str] = {ref["type"]: ref["value"] for ref in event.identifiers}
    order_id = event.entity_references.get("order_id")
    if order_id:
        mapping["order_id"] = str(order_id)
    return mapping


def _detect_conflicts(
    event_fields: dict[str, str],
    field_profile_map: dict[str, list[str]],
) -> list[dict]:
    """Strong identifiers that point to different profiles create a conflict."""
    strong_owner: dict[str, str] = {}
    for field_name in event_fields:
        if not _is_strong(field_name):
            continue
        owners = set(field_profile_map.get(field_name, []))
        if len(owners) != 1:
            continue
        strong_owner[field_name] = next(iter(owners))

    conflicts: list[dict] = []
    seen: set[tuple[str, str]] = set()
    strong_fields = list(strong_owner)
    for i, field_a in enumerate(strong_fields):
        for field_b in strong_fields[i + 1 :]:
            profile_a = strong_owner[field_a]
            profile_b = strong_owner[field_b]
            if profile_a != profile_b:
                key = (field_a, field_b)
                if key in seen:
                    continue
                seen.add(key)
                conflicts.append(
                    {
                        "fields": [field_a, field_b],
                        "message": (
                            f"{field_a} belongs to profile {profile_a} while "
                            f"{field_b} belongs to profile {profile_b}."
                        ),
                    }
                )
    return conflicts


def _score_candidate(
    candidate: CandidateInfo,
    event_fields: dict[str, str],
) -> CandidateScore:
    evidence: list[Evidence] = []
    for field_name in candidate.matched_fields:
        weight = _weight(field_name)
        if weight == 0 or field_name not in event_fields:
            continue
        value = event_fields[field_name]
        evidence.append(
            Evidence(
                field=field_name,
                incoming_value=value,
                candidate_value=value,
                result="exact_match",
                weight=weight,
                message=f"Same {field_name.replace('_', ' ')} matches the profile.",
            )
        )

    base = max((e.weight for e in evidence), default=0)
    strong_matches = [e for e in evidence if _is_strong(e.field)]
    moderate_matches = [e for e in evidence if e.field in MODERATE_WEIGHTS]

    extra = 0
    if len(strong_matches) >= 2:
        extra += 10
    if moderate_matches:
        extra += 5
    score = min(MAX_SCORE, base + extra)

    return CandidateScore(
        profile_id=candidate.profile_id,
        retrieved_by=candidate.matched_fields,
        score=score,
        evidence=evidence,
    )


def _evidence_payload(evidence: list[Evidence]) -> list[dict]:
    return [
        {
            "field": e.field,
            "incoming_value": e.incoming_value,
            "candidate_value": e.candidate_value,
            "result": e.result,
            "weight": e.weight,
            "message": e.message,
        }
        for e in evidence
    ]


def decide(
    event: NormalizedEvent,
    candidates: list[CandidateInfo],
    field_profile_map: dict[str, list[str]],
    *,
    same_name_collision: bool = False,
) -> DecisionResult:
    """Score all candidates and produce an explainable identity decision."""
    event_fields = _event_field_map(event)
    conflicts = _detect_conflicts(event_fields, field_profile_map)

    scored = [_score_candidate(c, event_fields) for c in candidates]
    scored.sort(key=lambda s: (-s.score, s.profile_id))

    candidate_payload = [
        {"profile_id": s.profile_id, "retrieved_by": s.retrieved_by, "score": s.score}
        for s in scored
    ]

    if not scored and same_name_collision:
        return DecisionResult(
            outcome=IdentityOutcome.REVIEW_REQUIRED,
            score=0,
            selected_profile_id=None,
            evidence=[],
            conflicts=[],
            candidates=[],
            reason=SAME_NAME_COLLISION_REASON,
            thresholds=THRESHOLDS,
        )

    if not scored:
        return DecisionResult(
            outcome=IdentityOutcome.NEW_PROFILE,
            score=0,
            selected_profile_id=None,
            evidence=[],
            conflicts=[],
            candidates=[],
            reason="No candidate profile shares an identifier with this event.",
            thresholds=THRESHOLDS,
        )

    best = scored[0]
    second = scored[1] if len(scored) > 1 else None

    if conflicts:
        return DecisionResult(
            outcome=IdentityOutcome.REVIEW_REQUIRED,
            score=best.score,
            selected_profile_id=None,
            evidence=_evidence_payload(best.evidence),
            conflicts=conflicts,
            candidates=candidate_payload,
            reason="Strong identifiers point to different profiles; a human must decide.",
            thresholds=THRESHOLDS,
        )

    if second is not None and (best.score - second.score) <= TIE_DELTA:
        return DecisionResult(
            outcome=IdentityOutcome.REVIEW_REQUIRED,
            score=best.score,
            selected_profile_id=None,
            evidence=_evidence_payload(best.evidence),
            conflicts=[],
            candidates=candidate_payload,
            reason=f"Top candidates are within {TIE_DELTA} points; a human must decide.",
            thresholds=THRESHOLDS,
        )

    if best.score >= AUTO_LINK_THRESHOLD:
        return DecisionResult(
            outcome=IdentityOutcome.AUTO_LINKED,
            score=best.score,
            selected_profile_id=best.profile_id,
            evidence=_evidence_payload(best.evidence),
            conflicts=[],
            candidates=candidate_payload,
            reason=f"Best candidate score {best.score} meets the auto-link threshold.",
            thresholds=THRESHOLDS,
        )

    if best.score >= REVIEW_THRESHOLD:
        return DecisionResult(
            outcome=IdentityOutcome.REVIEW_REQUIRED,
            score=best.score,
            selected_profile_id=None,
            evidence=_evidence_payload(best.evidence),
            conflicts=[],
            candidates=candidate_payload,
            reason=f"Best candidate score {best.score} is between review and auto-link thresholds.",
            thresholds=THRESHOLDS,
        )

    return DecisionResult(
        outcome=IdentityOutcome.NEW_PROFILE,
        score=best.score,
        selected_profile_id=None,
        evidence=_evidence_payload(best.evidence),
        conflicts=[],
        candidates=candidate_payload,
        reason=f"Best candidate score {best.score} is below the review threshold.",
        thresholds=THRESHOLDS,
    )
