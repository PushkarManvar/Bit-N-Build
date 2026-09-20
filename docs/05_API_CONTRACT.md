# JourneyLens API Contract

**Version:** 1.3 — Phase 0 / Gate G1 frozen
**Base path:** `/api`  
**Format:** JSON unless documented otherwise  
**Change note (v1.2 → v1.3):** canonical support-note context is now a bounded, additive `contact_reason` value; raw source payloads remain unchanged.

## 1. API conventions

- UUIDs are serialized as strings.
- Timestamps use ISO 8601 UTC; all timestamps are normalized to UTC on ingestion.
- Enum values use lowercase `snake_case`.
- List responses use `{ "items": [], "total": number }`.
- Envelope validation failures use HTTP 422.
- New successful ingestion returns HTTP 201.
- Duplicate ingestion (same channel + source ID + identical payload) returns HTTP 200 with `processing_status: "duplicate"` and creates no new rows.
- Source ID reused with a different payload returns HTTP 409.
- Raw acceptance with a downstream normalization failure returns HTTP 202 and keeps the raw event marked `failed`.
- All errors use the shared error response shape.

## 2. Shared types

### Channel

```text
web | mobile_app | call_center | physical_store
```

### Processing status

```text
received | normalized | failed
```

A duplicate is an API response status, not a persisted processing state.

### Event type

```text
product_viewed | app_login | order_placed | return_requested |
support_contacted | store_visited | refund_completed
```

### Contact reason (canonical support context)

```text
refund_not_received | return_status | other
```

This value is only present in canonical `attributes.contact_reason` for a
`support_contacted` event that supplied `attributes.notes`. It is intended for
safe, typed presentation; it is not a free-text field.

### Identity outcome (Gate G2+)

```text
auto_linked | review_required | new_profile
```

### Review decision (Gate G2+)

```text
approve_link | reject_link | create_profile
```

### Alert severity

```text
low | medium | high | critical
```

### Event envelope (frozen)

```json
{
  "source_event_id": "WEB-001",
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "schema_version": "1.0",
  "identifiers": [
    {
      "type": "device_id",
      "value": "DEV-17"
    }
  ],
  "entity_references": {
    "order_id": null
  },
  "attributes": {
    "product_id": "PROD-42",
    "page": "/products/42"
  }
}
```

Field rules:

| Field | Type | Required | Notes |
|---|---|---|---|
| `source_event_id` | string | yes | unique within a channel |
| `channel` | `Channel` | yes | |
| `event_type` | `EventType` | yes | |
| `occurred_at` | ISO 8601 | yes | converted to UTC |
| `schema_version` | string | yes | only `1.0` supported for G1 |
| `identifiers` | array | yes | `{type, value}`; empty array allowed |
| `entity_references` | object | yes | e.g. `order_id`; nullable values allowed |
| `attributes` | object | yes | free-form; must be JSON-serializable |

Identifier types for G1: `email`, `phone`, `device_id`, `session_id`, `customer_id`.

Normalization rules:

- `email`: trim and lowercase.
- `device_id`: trim and uppercase.
- `order_id`: trim and uppercase; spaces/underscores become hyphens.
- `occurred_at`: converted to UTC.
- Other identifier values: trimmed.
- For `support_contacted`, the raw `attributes.notes` value remains in the raw
  payload but is not copied to canonical attributes. The exact normalized
  phrases `refund not received` and `second follow-up` become
  `contact_reason: refund_not_received` and `contact_reason: return_status`.
  Any other supplied note becomes `contact_reason: other`.

### Error response

```json
{
  "error": {
    "code": "EVENT_ID_REUSED",
    "message": "Source event ID WEB-001 was reused with a different payload.",
    "stage": "ingestion",
    "raw_event_id": "b2f7...",
    "details": {
      "channel": "web",
      "source_event_id": "WEB-001"
    }
  }
}
```

Stable error codes:

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Envelope failed validation |
| `EVENT_ID_REUSED` | 409 | Same source ID, different payload |
| `NORMALIZATION_FAILED` | 202 | Raw persisted, normalization failed |
| `INGESTION_ERROR` | 500 | Unexpected failure |
| `PIPELINE_EVENT_NOT_FOUND` | 404 | No persisted raw event has the requested pipeline ID |

### Ingestion response (frozen)

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": "uuid-or-null",
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "processing_status": "normalized",
  "duplicate": false
}
```

## 3. Ingest one event

### `POST /api/events`

#### Request

```json
{
  "source_event_id": "WEB-001",
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "schema_version": "1.0",
  "identifiers": [
    {
      "type": "device_id",
      "value": "DEV-17"
    }
  ],
  "entity_references": {
    "order_id": null
  },
  "attributes": {
    "product_id": "PROD-42",
    "page": "/products/42"
  }
}
```

#### Responses

`201 Created` — processed:

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": "uuid",
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "processing_status": "normalized",
  "duplicate": false,
  "match_decision": "new_profile",
  "profile_id": "uuid",
  "match_score": 0
}
```

**Additive fields (Gate G2):** `match_decision` (`auto_linked | review_required | new_profile`), `profile_id`, and `match_score` are present on successful `201` ingestion responses. They are additive and do not change any G1 field. On duplicate (`200`) and normalization-failure (`202`) responses they are omitted.

`200 OK` — idempotent duplicate (same source ID + identical payload; no new rows):

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": "uuid",
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "processing_status": "duplicate",
  "duplicate": true
}
```

`202 Accepted` — raw persisted, normalization failed (schema version unsupported, ...):

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": null,
  "channel": "web",
  "event_type": "product_viewed",
  "occurred_at": "2026-09-19T08:30:00Z",
  "processing_status": "failed",
  "duplicate": false
}
```

`409 Conflict` — same source ID, different payload:

```json
{
  "error": {
    "code": "EVENT_ID_REUSED",
    "message": "Source event ID WEB-001 was reused with a different payload.",
    "stage": "ingestion",
    "raw_event_id": "uuid",
    "details": {
      "channel": "web",
      "source_event_id": "WEB-001"
    }
  }
}
```

`422 Unprocessable Entity` — envelope validation failed (missing required field, unsupported channel/event type, malformed timestamp).

#### Status behavior

| Situation | Status | Persistence |
|---|---|---:|
| New event fully processed | 201 | raw + canonical |
| Same source ID, identical payload | 200 | none (no new rows) |
| Same source ID, different payload | 409 | none |
| Envelope validation failed | 422 | none |
| Raw saved, normalization failed | 202 | raw only, marked `failed` |
| Database/service failure | 500 | as far as transaction reached |

## 4. Bulk ingestion

### `POST /api/events/bulk`

#### Request

```json
{
  "events": [
    {
      "source_event_id": "WEB-001",
      "channel": "web",
      "event_type": "product_viewed",
      "event_summary": {
        "title": "Product viewed",
        "detail": null,
        "kind": "product_view"
      },
      "has_order_reference": true,
      "occurred_at": "2026-09-19T08:30:00Z",
      "schema_version": "1.0",
      "identifiers": [
        {
          "type": "device_id",
          "value": "DEV-17"
        }
      ],
      "entity_references": {
        "order_id": null
      },
      "attributes": {
        "product_id": "PROD-42"
      }
    }
  ]
}
```

**Note:** bulk ingestion is planned but not implemented in Gate G1. For the hackathon, keep the maximum batch size small and explicit, such as 500 events.

## 5. List profiles

### `GET /api/profiles`

#### Query parameters

| Name | Type | Example |
|---|---|---|
| `page` | integer | `1` |
| `page_size` | integer | `20` |
| `search` | string | `riya` |
| `has_open_alert` | boolean | `true` |
| `review_required` | boolean | `false` |
| `channel` | channel | `call_center` |

#### Response

```json
{
  "items": [
    {
      "profile_id": "uuid",
      "display_name": "Riya Shah",
      "email": "riya.shah@example.com",
      "phone": "+919876543210",
      "channels_used": ["web", "mobile_app", "call_center", "physical_store"],
      "event_count": 6,
      "open_alert_count": 2,
      "review_required": false,
      "last_seen_at": "2026-09-19T09:20:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 31
}
```

## 6. Profile journey detail

### `GET /api/profiles/{profile_id}`

#### Response outline

```json
{
  "profile": {
    "id": "uuid",
    "display_name": "Riya Shah",
    "identifiers": [
      {
        "type": "email",
        "display_value": "riya.shah@example.com",
        "first_seen_at": "2026-09-14T09:15:00Z"
      }
    ]
  },
  "timeline": [
    {
      "event_id": "uuid",
      "channel": "call_center",
      "event_type": "support_call",
      "occurred_at": "2026-09-16T12:30:00Z",
      "title": "Customer reports refund not received",
      "order_id": "ORD-204",
      "decision": "auto_linked",
      "score": 100,
      "evidence_summary": ["Exact order ID", "Exact normalized phone"]
    }
  ],
  "alerts": [
    {
      "id": "uuid",
      "type": "unresolved_refund",
      "severity": "high",
      "title": "Refund ORD-204 remains unresolved",
      "description": "Return activity and repeated contacts exist without a refund completion.",
      "recommended_action": "Prioritize refund resolution.",
      "status": "open"
    }
  ],
  "journey_summary": {
    "status": "unresolved_refund",
    "summary": "Riya used four channels over five days while attempting to resolve ORD-204.",
    "generated_by": "template"
  }
}
```

### `GET /api/alerts`

Open journey alerts across all profiles (Command Centre feed). **Additive endpoint (Gate G4).**

```json
{
  "items": [
    {
      "id": "uuid",
      "type": "unresolved_refund",
      "severity": "high",
      "title": "Refund ORD-204 remains unresolved",
      "description": "Return activity and repeated contacts exist without a refund completion.",
      "recommended_action": "Prioritize refund resolution.",
      "status": "open",
      "order_id": "ORD-204",
      "created_at": "2026-09-19T10:00:00Z"
    }
  ],
  "total": 1
}
```

## 7. Match explanation

### `GET /api/events/{canonical_event_id}/match-explanation`

#### Response

```json
{
  "event_id": "uuid",
  "event_context": {
    "channel": "call_center",
    "event_type": "support_call",
    "occurred_at": "2026-09-16T12:30:00Z"
  },
  "decision": "auto_linked",
  "selected_profile_id": "uuid",
  "score": 100,
  "thresholds": {
    "auto_link": 80,
    "review_required": 50
  },
  "evidence": [
    {
      "field": "order_id",
      "incoming_value": "ORD-204",
      "candidate_value": "ORD-204",
      "result": "exact_match",
      "weight": 95,
      "message": "Order ID matches the selected profile."
    }
  ],
  "conflicts": [],
  "alternative_candidates": [],
  "raw_payload": {},
  "normalized_fields": {}
}
```

## 8. Review queue

### `GET /api/reviews?status=pending`

This compatibility response remains frozen for current clients. New queue
surfaces use the additive endpoint below.

```json
{
  "items": [
    {
      "match_decision_id": "uuid",
      "event": {
        "channel": "physical_store",
        "event_type": "return_requested",
        "customer_name": "Aarav Patel",
        "occurred_at": "2026-09-18T10:30:00Z"
      },
      "best_candidate": {
        "profile_id": "uuid",
        "display_name": "Aarav Patel",
        "score": 55
      },
      "evidence": ["Similar name", "Same city"],
      "conflicts": [],
      "missing_strong_identifiers": ["email", "phone", "order_id", "customer_id"],
      "reason": "Weak supporting evidence exists, but no strong identity evidence is shared."
    }
  ],
  "total": 1
}
```

### `GET /api/review-queue`

Returns a server-classified page of pending review decisions for operations
work. It never returns raw payloads or unmasked identifier values. `review_kind`
and `priority` are derived only from persisted evidence, conflicts, candidates,
and the explicit same-name safety routing reason.

Supported query parameters:

- `limit`: 1–100, default 20;
- `cursor`: opaque keyset cursor bound to the active filters;
- `status`: only `pending` is supported initially;
- `channel`: `web|mobile_app|call_center|physical_store`;
- `kind`: `strong_identifier_conflict|ambiguous_moderate_match|same_name_collision|incomplete_evidence`; and
- `priority`: `critical|high|standard`.

The default order is critical, high, then standard priority; within a priority,
oldest decision first, then decision ID. `summary` and `total` apply the same
filters before cursor pagination. Reusing a cursor with different filters
returns the shared `VALIDATION_ERROR` envelope with HTTP 422.

```json
{
  "items": [
    {
      "match_decision_id": "uuid",
      "created_at": "2026-09-20T08:00:00Z",
      "review_kind": "strong_identifier_conflict",
      "priority": "critical",
      "event": {
        "channel": "call_center",
        "event_type": "support_contacted",
        "customer_name": "Conflict Case",
        "occurred_at": "2026-09-20T08:00:00Z"
      },
      "candidates": [
        {
          "profile_id": "uuid",
          "display_name": "Conflict Alpha",
          "score": 90,
          "matched_fields": ["email"]
        }
      ],
      "evidence": [
        {
          "field": "email",
          "result": "exact_match",
          "weight": 90,
          "message": "Same email matches the profile."
        }
      ],
      "conflicts": [
        {
          "fields": ["email", "phone"],
          "message": "Email and phone resolve to different profiles."
        }
      ],
      "missing_strong_identifiers": ["customer_id", "order_id"],
      "reason_code": "strong_identifier_conflict",
      "reason": "Strong identifiers point to different profiles; a human must decide."
    }
  ],
  "next_cursor": "opaque-or-null",
  "total": 3,
  "summary": {
    "pending": 3,
    "critical_conflicts": 1,
    "incomplete_evidence": 1,
    "same_name_collisions": 1,
    "ambiguous_moderate_matches": 0
  }
}
```

### `POST /api/reviews/{match_decision_id}/resolve`

#### Request

```json
{
  "action": "create_profile",
  "selected_profile_id": null,
  "reviewer_name": "Demo Reviewer",
  "note": "Same name, but no shared strong identifier."
}
```

Allowed actions (frozen review decisions):

```text
approve_link | reject_link | create_profile
```

#### Response

```json
{
  "match_decision_id": "uuid",
  "review_status": "approved",
  "action": "create_profile",
  "profile_id": "new-profile-uuid",
  "resolved_at": "2026-09-19T10:00:00Z"
}
```

An `approve_link` request requires `selected_profile_id`.

## 9. Analytics

### `GET /api/analytics/overview`

```json
{
  "total_raw_events": 224,
  "normalized_events": 218,
  "failed_events": 3,
  "duplicate_events": 3,
  "unified_profiles": 31,
  "auto_link_rate": 84.6,
  "review_required_rate": 8.3,
  "open_alerts": 7,
  "match_precision": 0.96,
  "match_recall": 0.91,
  "match_f1": 0.93,
  "false_merge_rate": 0.02,
  "average_processing_latency_ms": 82
}
```

Return `null` for metrics that have not been computed. Do not return invented defaults.

### `GET /api/analytics/channels`

```json
{
  "web": 61,
  "mobile_app": 55,
  "call_center": 49,
  "physical_store": 53
}
```

### `GET /api/analytics/friction-radar` (additive)

Ranks only persisted, open `unresolved_refund` alerts that have both a resolved
profile and an order reference. It is an operational prioritization score, not
a churn prediction, payment-status claim, or automated resolution decision.
`limit` defaults to `5` and must be between `1` and `50`.

```json
{
  "as_of": "2026-09-20T12:00:00Z",
  "score_version": "friction_v1",
  "score_max": 60,
  "summary": {
    "attributable_open_refunds": 3,
    "unattributed_open_refunds": 1,
    "critical": 1,
    "elevated": 1,
    "watch": 1
  },
  "journeys": [
    {
      "alert_id": "d5c032c6-7c20-4f86-99c9-d46f187024e0",
      "profile_id": "9f4e47b9-c0bf-4723-90a1-437957a2b4a6",
      "display_name": "Riya Shah",
      "order_id": "ORD-204",
      "friction_score": 57,
      "band": "critical",
      "unresolved_age_days": 5,
      "distinct_channel_count": 3,
      "support_contact_count": 3,
      "has_open_repeat_contact_alert": true,
      "pending_candidate_review_count": 1,
      "components": {
        "unresolved_age_points": 20,
        "channel_points": 9,
        "support_contact_points": 12,
        "repeat_contact_points": 10,
        "pending_candidate_review_points": 6
      }
    }
  ],
  "unresolved_age_distribution": [
    { "bucket": "0 days", "count": 0 },
    { "bucket": "1–3 days", "count": 1 },
    { "bucket": "4–7 days", "count": 1 },
    { "bucket": "8+ days", "count": 1 }
  ],
  "support_contact_channels": [
    { "channel": "call_center", "count": 3, "share_percent": 50.0 }
  ]
}
```

The score is capped at `60`: `min(30, 4 × whole unresolved days)` +
`min(12, 3 × distinct support channels)` + `min(12, 4 × support contacts)` +
`10` for an open repeat-contact alert + `min(6, 6 × pending candidate reviews)`.
Unresolved age starts at the earliest persisted `return_requested` event for
the same profile and order. Candidate reviews are not treated as linked events.
`unattributed_open_refunds` is reported separately because it cannot be ranked
without a profile and order. All values are computed from persisted records at
the response timestamp.

## 10. Data Pipeline (additive)

### `GET /api/pipeline/overview`

Returns one unfiltered, internally consistent initial snapshot for the Data Pipeline page. `limit` controls only the number of recent event rows and must be between 1 and 100; it defaults to `25`. The snapshot captures an opaque high-water position before it reads rows and aggregates; PostgreSQL uses repeatable-read isolation for that request.

```json
{
  "as_of": "2026-09-20T12:00:00Z",
  "stages": {
    "raw_accepted": 2,
    "normalization_succeeded": 1,
    "normalization_failed": 1,
    "identity_decided": 1,
    "profile_linked": 1,
    "review_required": 0
  },
  "channels": {
    "web": { "raw": 2, "normalized": 1, "failed": 1 },
    "mobile_app": { "raw": 0, "normalized": 0, "failed": 0 },
    "call_center": { "raw": 0, "normalized": 0, "failed": 0 },
    "physical_store": { "raw": 0, "normalized": 0, "failed": 0 }
  },
  "events": [
    {
      "raw_event_id": "b2f7dd88-4e7d-4c54-98e5-7ad1af930613",
      "canonical_event_id": "078c37ef-c93a-4dda-b515-419b44806593",
      "source_event_id": "WEB-001",
      "channel": "web",
      "event_type": "product_viewed",
      "occurred_at": "2026-09-19T08:30:00Z",
      "received_at": "2026-09-20T12:00:00Z",
      "processed_at": "2026-09-20T12:00:01Z",
      "processing_status": "normalized",
      "processing_error_code": null,
      "profile_id": "9f4e47b9-c0bf-4723-90a1-437957a2b4a6",
      "identity_outcome": "new_profile",
      "identity_score": 0,
      "needs_review": false
    }
  ],
  "next_cursor": "opaque-or-null",
  "poll_cursor": "opaque-high-water-cursor",
  "duplicate_attempts": null,
  "duplicate_tracking_supported": false
}
```

Count definitions:

- `raw_accepted`: persisted raw-event rows;
- `normalization_succeeded`: persisted canonical-event rows;
- `normalization_failed`: raw rows whose processing status is `failed`;
- `identity_decided`: persisted match-decision rows;
- `profile_linked`: canonical rows with a non-null profile ID; and
- `review_required`: decisions whose outcome is `review_required` and review status remains `pending`.

Event-row rules:

- Rows are ordered by `received_at DESC`, then `raw_event_id DESC`.
- `processed_at` is exactly `canonical_events.created_at`: the canonical insert time, not a duration or end-to-end latency measurement. It is `null` when no canonical event exists.
- Canonical and identity fields are nullable for failed raw events.
- `event_summary` is a deterministic, list-safe projection of canonical event
  type plus bounded context. It is `null` when no canonical event exists.
- `has_order_reference` reports only whether a canonical order reference is
  present; the list never returns that reference value. It is `null` when no
  canonical event exists.
- `processing_error_code` exposes only the stable code before the stored error message.
- `received` is a valid compatibility state but normal synchronous processing does not leave a committed row in that state. It appears only if a recovery/import path explicitly persists an interrupted record; callers should expect the filter to be empty in ordinary operation.
- The list never includes raw payloads, full identifiers, candidates, or evidence values.
- Duplicate attempts remain `null`/unsupported because the current idempotency contract creates no persisted duplicate-attempt row.

`next_cursor` is present only if an older overview page exists. `poll_cursor` is always an opaque update cursor, including for an empty database; callers use it with `GET /api/pipeline/updates`.

### `GET /api/pipeline/events`

Returns a filtered, keyset-paginated list of the same list-safe event rows shown by the overview. Supported optional filters are `channel`, `processing_status`, `identity_outcome`, and the case-insensitive `source_event_id` prefix. `limit` defaults to `25` and must be between 1 and 100.

```json
{
  "items": ["PipelineEventOut"],
  "total": 42,
  "next_cursor": "opaque-or-null"
}
```

Rows are ordered by `received_at DESC`, then `raw_event_id DESC`. Filters apply before both `total` and pagination. The opaque cursor includes the ordering pair and a fingerprint of the active filters; using it with different filters returns the shared `VALIDATION_ERROR` envelope with HTTP 422.

### `GET /api/pipeline/events/{raw_event_id}`

Returns one composed pipeline inspector model:

```json
{
  "event": "PipelineEventOut",
  "raw_event": "RawEventDetail",
  "canonical_event": "CanonicalEventDetail-or-null",
  "identity_decision": {
    "canonical_event_id": "uuid",
    "selected_profile_id": "uuid-or-null",
    "outcome": "auto_linked|review_required|new_profile",
    "score": 100,
    "thresholds": {},
    "evidence": [],
    "conflicts": [],
    "candidates": [],
    "reason": "persisted decision reason",
    "review_status": "pending|resolved|null"
  }
}
```

The route is keyed by `raw_event_id`; canonical and decision objects are nullable when normalization did not create downstream records. A malformed or unknown ID returns `PIPELINE_EVENT_NOT_FOUND` with HTTP 404 through the shared error envelope.

### `GET /api/pipeline/updates`

Returns events newer than an overview or previous update cursor. `cursor` is required; `limit` defaults to `100` and must be between 1 and 100. Events are ascending by `received_at`, then `raw_event_id`.

```json
{
  "as_of": "2026-09-20T12:00:05Z",
  "stages": { "raw_accepted": 2 },
  "channels": { "web": { "raw": 2, "normalized": 1, "failed": 1 } },
  "events": ["PipelineEventOut"],
  "next_cursor": "opaque-update-cursor",
  "upper_bound_cursor": "opaque-high-water-cursor",
  "has_more": false
}
```

Each response captures an upper high-water position and scopes both its event rows and authoritative aggregates to that position. When `has_more` is `true`, the caller must request the next page with `cursor=next_cursor` and the same `upper_bound_cursor`; this drains a burst without losses or duplicates. When `has_more` is `false`, `next_cursor` equals `upper_bound_cursor` and becomes the cursor for the next poll.

### Initial pipeline examples

The backend contract tests cover these snapshots:

- empty database;
- one normalized event;
- one persisted normalization failure; and
- one pending `review_required` event with no linked profile.

## 11. Demo controls

### `POST /api/demo/reset?seed=curated|full`

Resets demo-specific records and reloads deterministic synthetic fixtures. It
must not be exposed as a production operation. `seed=curated` is the default
and loads the three-case review queue (strong conflict, incomplete-evidence
bridge, and same-name safety). `seed=full` retains the larger data-generation
fixture set for evaluation work.

```json
{
  "status": "reset",
  "loaded": {
    "received": 8,
    "duplicates": 0,
    "failed": 0,
    "invalid": 0
  }
}
```

### `POST /api/demo/start`

```json
{
  "scenario": "unresolved_refund_riya",
  "interval_seconds": 1.5
}
```

Response:

```json
{
  "run_id": "demo-run-01",
  "status": "started",
  "total_steps": 6,
  "current_step": 0
}
```

### `GET /api/demo/{run_id}`

```json
{
  "run_id": "demo-run-01",
  "status": "running",
  "current_step": 3,
  "total_steps": 6,
  "last_event_id": "uuid",
  "error": null
}
```

### `GET /api/dashboard/updates?since={timestamp}`

Returns recent processed events, new alerts, changed review counts, and current demo status.

```json
{
  "events": [
    {
      "event_id": "uuid",
      "channel": "mobile_app",
      "event_type": "support_contacted",
      "occurred_at": "2026-09-15T09:00:00Z",
      "profile_id": "uuid-or-null",
      "match_decision": "auto_linked"
    }
  ],
  "new_alerts": [],
  "open_alerts": 2,
  "pending_reviews": 1,
  "demo": {
    "run_id": "demo-run-01",
    "status": "running",
    "current_step": 3,
    "total_steps": 6,
    "last_event_id": "uuid",
    "error": null
  }
}
```

## 12. Contract governance

- Treat this document and generated OpenAPI as the shared contract.
- Frontend mock fixtures must match these response shapes.
- Breaking changes require a decision-log entry.
- Add fields compatibly when possible; do not rename fields during the final six hours.
- API examples become integration-test fixtures.

## 13. API definition of done

- [ ] All endpoints appear in `/docs`.
- [ ] Example requests pass validation.
- [ ] Error responses use the shared error model.
- [ ] Duplicate behavior is verified.
- [ ] Frontend mock and live response shapes match.
- [ ] Review resolution validates action-specific fields.
- [ ] Analytics never return fabricated metrics.
- [ ] Demo reset/start/status complete three consecutive runs.
