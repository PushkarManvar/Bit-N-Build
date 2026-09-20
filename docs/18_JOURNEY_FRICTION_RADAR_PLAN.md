# Journey Friction Radar Plan

**Status:** Planned — document and contract before implementation  
**Created:** 2026-09-20  
**Related:** `docs/01_PRODUCT_REQUIREMENTS.md`, `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/06_IMPLEMENTATION_AND_TEAM_PLAN.md`, and `docs/07_TESTING_EVALUATION_AND_DEMO.md`

## 1. Decision

Build the **Journey Friction Radar** before any further analytics surface. It
ranks *open, attributable unresolved-refund journeys* using deterministic,
persisted facts. Its single job is to help an operations user decide which
broken refund journey needs attention first.

The reference screen at `stitch_journeylens_operations_platform/stitch_new_one`
is visual inspiration only. It contains unsupported assertions about AI,
telemetry, latency, SLA, payment retries, and customer attributes. None of
those claims, controls, or labels may ship unless a future API supports them.

This is an operations-priority score, **not** a churn prediction, customer
sentiment score, or probability of refund failure.

## 2. Scope and safety boundaries

In scope:

- rank existing open `unresolved_refund` alerts by deterministic friction;
- expose the score components and the exact persisted facts that produced them;
- show an open-refund-age distribution and support-contact channel mix;
- link a row only to an existing profile journey; and
- render a truthful empty state when the current seed has no attributable open
  refunds.

Out of scope:

- LLM summaries, recommendations, or identity decisions;
- churn/correlation claims, revenue impact, SLA breach claims, or payment
  actions;
- new tables, migrations, background workers, or hidden-truth reads;
- a Recharts dependency. The first slice uses accessible HTML/CSS bars and
  tables; add a chart library only if a later interaction requirement cannot
  be met accessibly without one.

## 3. Eligible journey population

One radar row represents exactly one persisted `JourneyAlert` where:

```text
type == unresolved_refund
status == open
profile_id is not null
order_id is not null
```

Alerts missing a profile or order are excluded from the ranking because the
backend cannot truthfully attribute events to a profile/order journey. The
response reports `unattributed_open_refunds` so that exclusions are visible,
not silently discarded.

All per-journey events are persisted `CanonicalEvent` rows with the same
`profile_id` and `entity_references.order_id`. The event set never comes from
`data/truth/` and is not inferred from names or candidate scores.

## 4. Deterministic scoring contract (v1)

`as_of` is captured once by the endpoint. A journey score is the following
bounded priority aid on a 0–60 scale:

```text
friction_score =
    min(30, 4 * unresolved_age_days)
  + min(12, 3 * distinct_channel_count)
  + min(12, 4 * support_contact_count)
  + (10 if an open repeat_contact alert exists for the same profile/order else 0)
  + min(6, 6 * pending_candidate_review_count)
```

Component definitions:

| Component | Persisted source | Rule | Maximum |
|---|---|---|---:|
| `unresolved_age_days` | Earliest matching `return_requested.occurred_at` | Whole elapsed UTC days from that event to `as_of`; zero when no matching return event exists. | 30 |
| `distinct_channel_count` | Matching canonical events | Number of distinct channel enum values. | 12 |
| `support_contact_count` | Matching `support_contacted` events | Count, capped at three for scoring; raw count remains visible. | 12 |
| `repeat_contact` | Open `repeat_contact` alert for same profile/order | Binary. | 10 |
| `pending_candidate_review_count` | Pending review decisions whose candidate list contains this profile and whose canonical event has the same order | Count, capped at one for scoring. The label must say **candidate review**, not linked event. | 6 |

`return_requested` age is used rather than alert creation time: alert rows are
created during deterministic ingestion/reset, while the canonical occurrence
time describes when the customer journey began.

Bands are a UI grouping, not a severity field:

| Band | Score |
|---|---:|
| `critical` | 45–60 |
| `elevated` | 30–44 |
| `watch` | 1–29 |
| `none` | 0 |

The endpoint returns `score_version: "friction_v1"`, `score_max: 60`, and all
component values. The UI must render the formula in plain language and never
turn it into a causal claim.

## 5. Additive API contract

Add `GET /api/analytics/friction-radar?limit=5` (limit 1–50; default 5).
It returns only one internally consistent snapshot, ordered by
`friction_score DESC`, `unresolved_age_days DESC`, then `alert_id ASC`.

```json
{
  "as_of": "2026-09-20T12:00:00Z",
  "score_version": "friction_v1",
  "score_max": 60,
  "summary": {
    "attributable_open_refunds": 5,
    "unattributed_open_refunds": 0,
    "critical": 1,
    "elevated": 2,
    "watch": 2
  },
  "journeys": [
    {
      "alert_id": "uuid",
      "profile_id": "uuid",
      "display_name": "Riya Shah",
      "order_id": "ORD-204",
      "friction_score": 46,
      "band": "critical",
      "unresolved_age_days": 5,
      "distinct_channel_count": 4,
      "support_contact_count": 3,
      "has_open_repeat_contact_alert": true,
      "pending_candidate_review_count": 0,
      "components": {
        "unresolved_age_points": 20,
        "channel_points": 12,
        "support_contact_points": 12,
        "repeat_contact_points": 10,
        "pending_candidate_review_points": 0
      }
    }
  ],
  "unresolved_age_distribution": [
    { "bucket": "0 days", "count": 1 },
    { "bucket": "1–2 days", "count": 2 },
    { "bucket": "3–6 days", "count": 1 },
    { "bucket": "7+ days", "count": 1 }
  ],
  "support_contact_channels": [
    { "channel": "call_center", "count": 6, "share_percent": 60.0 }
  ]
}
```

Rules:

- `share_percent` is the percentage of support-contact events among attributable
  open-refund journeys, rounded consistently; it is `null` when that
  denominator is zero.
- Distribution counts sum to `attributable_open_refunds`; contact-channel counts
  sum to the uncapped raw support-contact total.
- The response includes no raw payloads, identifier values, hidden-truth IDs,
  LLM output, payment data, or invented customer fields.
- The endpoint is additive. Existing analytics, alert, profile, and review
  contracts remain unchanged.

## 6. Read-model implementation

Create `backend/app/services/friction_radar_read_model.py` as the only place
that joins `JourneyAlert`, `CanonicalEvent`, and `MatchDecision` for this
feature. The route remains a thin HTTP adapter; Pydantic response models live
in `backend/app/schemas/analytics.py`.

The implementation must capture `as_of` once, query the eligible alerts, and
derive every row from persisted data. It may use a bounded in-process
aggregation for this small MVP dataset; no speculative index or migration is
justified until a PostgreSQL query plan on representative data proves one is
needed.

## 7. Frontend plan

Add `/journey-intelligence` and a sidebar entry labelled **Journey
Intelligence**. Its subject is an operations analyst prioritising broken
refund journeys; its one job is to answer: *which open refund should I inspect
first, and why?*

Layout:

```text
Title + “deterministic priority aid” + refresh
Formula disclosure (0–60; not a churn prediction)
Attributable open-refund / critical / elevated / review-context cards
Ranked Friction Radar ------------------------ selected journey facts
Open-refund age distribution ---------------- support-contact channel mix
```

- Render ranks, score, band, order ID, and factual components. A selected row
  can link to `/customers/{profile_id}`; it cannot offer refund or payment
  actions.
- Use CSS progress bars with visible text values and tables/lists so the view
  remains accessible without a chart dependency.
- Show loading, error, no-attributable-open-refunds, and data states. The
  curated review seed legitimately has no unresolved refunds, so its empty
  state must say so rather than render demonstration values.
- Do not copy the Stitch screen's “AI bridge”, “recompute” control, latency,
  SLA, payment gateway, or customer-story copy.

## 8. Test matrix and delivery slices

| Slice | Public seam | Proof |
|---|---|---|
| 1 | `GET /api/analytics/friction-radar` | Empty database and curated seed return a truthful zero snapshot. |
| 2 | Same endpoint on a focused fixture | Hand-worked score components, sort order, bands, exclusions, distribution, and channel shares match literals. |
| 3 | Safety regression | A name-only event never contributes a linked journey; hidden truth is never read. |
| 4 | `/journey-intelligence` | Typecheck, lint, build, and desktop/tablet/mobile smoke checks show only API values. |
| 5 | Demo | Full seed shows ranked real refund journeys; curated seed shows the intentional empty state. |

## 9. Exit criterion

From a full synthetic reset, a presenter can open Journey Intelligence, point
to the top ranked open refund, read each score component, open the existing
customer journey, and explain that the ranking is deterministic—not an AI or
churn prediction. From the curated review reset, the page instead shows the
truthful no-open-refunds state.
