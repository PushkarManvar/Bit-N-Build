# JourneyLens API Contract

**Version:** 1.0  
**Base path:** `/api`  
**Format:** JSON unless documented otherwise

## 1. API conventions

- UUIDs are serialized as strings.
- Timestamps use ISO 8601 UTC.
- Enum values use `snake_case`.
- List responses use `{ "items": [], "total": number }`.
- Validation errors use HTTP 422.
- Raw acceptance with downstream processing failure may use HTTP 202.
- Duplicate ingestion returns the existing result with HTTP 200.
- New successful ingestion returns HTTP 201.

## 2. Shared types

### Channel

```text
web | mobile_app | call_centre | physical_store
```

### Processing status

```text
received | normalized | matched | failed | duplicate
```

### Identity decision

```text
auto_linked | manual_review | new_profile | rejected
```

### Alert severity

```text
low | medium | high | critical
```

### Error response

```json
{
  "error": {
    "code": "NORMALIZATION_FAILED",
    "message": "The event timestamp is invalid.",
    "stage": "normalization",
    "raw_event_id": "b2f7...",
    "details": {
      "field": "callTime"
    }
  }
}
```

## 3. Ingest one event

### `POST /api/events`

#### Request

```json
{
  "source": "mobile_app",
  "source_record_id": "APP-90021",
  "occurred_at": "2026-09-19T09:15:00Z",
  "payload": {
    "action": "refund_status_checked",
    "email_address": "RIYA.SHAH@EXAMPLE.COM",
    "device": "DEV-17",
    "orderNumber": "ord 204",
    "customerName": "Riya Shah"
  }
}
```

#### Successful response

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": "uuid",
  "status": "matched",
  "profile_id": "uuid",
  "match_decision": "auto_linked",
  "match_score": 100,
  "evidence": [
    {
      "field": "order_id",
      "result": "exact_match",
      "weight": 95,
      "message": "Order ORD-204 belongs to the selected profile."
    },
    {
      "field": "device_id",
      "result": "exact_match",
      "weight": 45,
      "message": "Device DEV-17 appeared in the earlier anonymous journey."
    }
  ],
  "new_alerts": []
}
```

#### Status behavior

| Situation | Status |
|---|---:|
| New event fully processed | 201 |
| Duplicate source record | 200 |
| Envelope validation failed | 422 |
| Raw saved, normalization failed | 202 |
| Database/service failure | 500 or 503 |

## 4. Bulk ingestion

### `POST /api/events/bulk`

#### Request

```json
{
  "events": [
    {
      "source": "web",
      "source_record_id": "WEB-001",
      "occurred_at": "2026-09-14T08:00:00Z",
      "payload": {
        "event": "return_initiated",
        "deviceId": "DEV-17",
        "sessionId": "SESS-1001",
        "order_id": "ORD-204"
      }
    }
  ]
}
```

#### Response

```json
{
  "received": 1,
  "processed": 1,
  "duplicates": 0,
  "failed": 0,
  "manual_review": 0,
  "results": [
    {
      "source_record_id": "WEB-001",
      "status": "matched",
      "raw_event_id": "uuid"
    }
  ]
}
```

For the hackathon, keep the maximum batch size small and explicit, such as 500 events.

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
| `channel` | channel | `call_centre` |

#### Response

```json
{
  "items": [
    {
      "profile_id": "uuid",
      "display_name": "Riya Shah",
      "email": "riya.shah@example.com",
      "phone": "+919876543210",
      "channels_used": ["web", "mobile_app", "call_centre", "physical_store"],
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
      "channel": "call_centre",
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

## 7. Match explanation

### `GET /api/events/{canonical_event_id}/match-explanation`

#### Response

```json
{
  "event_id": "uuid",
  "event_context": {
    "channel": "call_centre",
    "event_type": "support_call",
    "occurred_at": "2026-09-16T12:30:00Z"
  },
  "decision": "auto_linked",
  "selected_profile_id": "uuid",
  "score": 100,
  "thresholds": {
    "auto_link": 80,
    "manual_review": 50
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
        "score": 25
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

### `POST /api/reviews/{match_decision_id}/resolve`

#### Request

```json
{
  "action": "create_new_profile",
  "selected_profile_id": null,
  "reviewer_name": "Demo Reviewer",
  "note": "Same name, but no shared strong identifier."
}
```

Allowed actions:

```text
approve_match | reject_match | create_new_profile
```

#### Response

```json
{
  "match_decision_id": "uuid",
  "review_status": "approved",
  "action": "create_new_profile",
  "profile_id": "new-profile-uuid",
  "resolved_at": "2026-09-19T10:00:00Z"
}
```

An `approve_match` request requires `selected_profile_id`.

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
  "manual_review_rate": 8.3,
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
  "call_centre": 49,
  "physical_store": 53
}
```

## 10. Demo controls

### `POST /api/demo/reset`

Resets demo-specific records and reloads base fixtures. It must not be exposed as a production operation.

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

## 11. Contract governance

- Treat this document and generated OpenAPI as the shared contract.
- Frontend mock fixtures must match these response shapes.
- Breaking changes require a decision-log entry.
- Add fields compatibly when possible; do not rename fields during the final six hours.
- API examples become integration-test fixtures.

## 12. API definition of done

- [ ] All endpoints appear in `/docs`.
- [ ] Example requests pass validation.
- [ ] Error responses use the shared error model.
- [ ] Duplicate behavior is verified.
- [ ] Frontend mock and live response shapes match.
- [ ] Review resolution validates action-specific fields.
- [ ] Analytics never return fabricated metrics.
- [ ] Demo reset/start/status complete three consecutive runs.
