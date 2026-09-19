# Data Pipeline Read Model and Implementation Plan

**Status:** Ready to execute  
**Created:** 2026-09-20  
**Audience:** Backend, data, frontend, QA, and demo owners  
**Related:** `docs/03_TECHNICAL_ARCHITECTURE.md`, `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/07_TESTING_EVALUATION_AND_DEMO.md`, and `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md`

## 1. Outcome

The Data Pipeline page must make the existing synchronous JourneyLens flow inspectable:

```text
raw accepted
  -> normalized canonical event
  -> identity decision
  -> profile link or human review
  -> journey rules and alerts
```

This work is a read model over the existing modular monolith. It is not a new ingestion platform. Do not add Kafka, workers, a data lake, connector health, replay controls, or invented telemetry.

The completed page must let an operator:

1. see truthful stage and per-channel counts;
2. browse persisted raw events, including normalization failures;
3. distinguish event time from receipt and processing time;
4. inspect one event from raw payload through canonical fields and identity evidence;
5. filter without losing stable pagination;
6. receive newly persisted events through polling; and
7. understand which facts are not recorded, especially duplicate attempts.

## 2. Current state

The processing path already exists and is covered by tests:

- `POST /api/events` validates the envelope and calls `services/event_ingestion.py`;
- `raw_events` preserves accepted payloads;
- `canonical_events` stores normalized records;
- `match_decisions` stores deterministic identity outcomes and evidence;
- linked events trigger the journey analyzer;
- `GET /api/events/{raw_event_id}` returns raw and canonical detail;
- `GET /api/events/{canonical_event_id}/match-explanation` returns identity evidence;
- analytics exposes partial counts; and
- `/pipeline` is currently an explicit placeholder.

The missing pieces are `BE-FE-04` and `BE-FE-05` from document 12: a stable event-list read model, a coherent pipeline snapshot, safe polling cursors, and the frontend that consumes them.

## 3. Non-negotiable rules

1. Raw payloads remain immutable evidence.
2. A list row never exposes raw payloads or full identifier values.
3. The inspector may show raw and normalized JSON only on deliberate selection; values render as text/JSON, never HTML.
4. Runtime pipeline code never reads `data/truth/`.
5. Identity truth comes from persisted `MatchDecision` rows, not frontend inference.
6. A strong conflict remains `review_required`; this page cannot override or resolve it.
7. `occurred_at`, `received_at`, and canonical `created_at` are separate clocks with separate labels.
8. Polling is the baseline. The UI says **Polling every 3 seconds**, not live stream or SSE.
9. Missing telemetry is `null` or explicitly unsupported, never estimated.
10. API errors use the shared error envelope.

## 4. Read-model interface

Place the seam in one backend module:

```text
app/services/pipeline_read_model.py
```

Its small interface should provide:

```text
get_pipeline_snapshot(filters, limit)
list_pipeline_events(filters, cursor, limit)
get_pipeline_updates(cursor, limit)
get_pipeline_event_detail(raw_event_id)
```

The implementation joins `RawEvent`, `CanonicalEvent`, and `MatchDecision` and computes aggregates. HTTP parsing stays in `app/api/routes/pipeline.py`; Pydantic wire shapes stay in `app/schemas/pipeline.py`.

Tests should exercise behavior through this interface or through the HTTP endpoints. Do not spread the same join and status logic across route handlers.

## 5. Proposed additive endpoints

### 5.1 Initial snapshot

```text
GET /api/pipeline/overview?limit=25&channel=&processing_status=&identity_outcome=
```

The response is one consistent initial-paint snapshot:

```json
{
  "as_of": "2026-09-20T12:00:00Z",
  "stages": {
    "raw_accepted": 190,
    "normalization_succeeded": 186,
    "normalization_failed": 4,
    "identity_decided": 186,
    "profile_linked": 179,
    "review_required": 7
  },
  "channels": {
    "web": { "raw": 62, "normalized": 61, "failed": 1 },
    "mobile_app": { "raw": 55, "normalized": 55, "failed": 0 },
    "call_center": { "raw": 36, "normalized": 34, "failed": 2 },
    "physical_store": { "raw": 37, "normalized": 36, "failed": 1 }
  },
  "events": [],
  "next_cursor": "opaque-or-null",
  "poll_cursor": "opaque-high-water-cursor",
  "duplicate_attempts": null,
  "duplicate_tracking_supported": false
}
```

Definitions:

- `raw_accepted`: persisted `RawEvent` count;
- `normalization_succeeded`: persisted `CanonicalEvent` count;
- `normalization_failed`: raw rows with `processing_status=failed`;
- `identity_decided`: persisted `MatchDecision` count;
- `profile_linked`: canonical events with non-null `profile_id`;
- `review_required`: pending review-required decisions, not every historical review;
- channel counts use raw channel for raw/failed and canonical channel for normalized; and
- duplicate fields remain unsupported until section 9 is explicitly approved.

`profile_linked` is the honest name for the final funnel stage. Do not label it **journey updated** because the current schema does not persist a separate journey-analysis completion fact.

Capture the high-water `(RawEvent.received_at, RawEvent.id)` before reading events. PostgreSQL should use a repeatable-read transaction for the snapshot. SQLite tests verify every event query is constrained to the captured high-water pair.

### 5.2 Older event pages

```text
GET /api/pipeline/events?cursor=<opaque>&limit=25&channel=&processing_status=&identity_outcome=
```

Default order is `received_at DESC, raw_event_id DESC`. Filters apply before totals and pagination. The cursor contains a version, the ordering pair, and a fingerprint of the active filters so it cannot be silently reused with a different query.

Each item contains only list-safe facts:

```json
{
  "raw_event_id": "uuid",
  "canonical_event_id": "uuid-or-null",
  "source_event_id": "CALL-104",
  "channel": "call_center",
  "event_type": "support_contacted",
  "occurred_at": "2026-09-20T11:55:00Z",
  "received_at": "2026-09-20T12:00:00Z",
  "processed_at": "2026-09-20T12:00:01Z",
  "processing_status": "normalized",
  "processing_error_code": null,
  "profile_id": "uuid-or-null",
  "identity_outcome": "auto_linked",
  "identity_score": 100,
  "needs_review": false
}
```

Rules:

- `event_type`, `processed_at`, profile, and identity fields are nullable for failed raw events;
- `processed_at` maps exactly to `CanonicalEvent.created_at`; it is canonical insert time, not a processing-duration metric;
- `processing_error_code` exposes a stable code only, not the complete internal error string;
- list rows do not include identifiers, arbitrary attributes, candidates, raw payloads, or evidence values; and
- `needs_review` is derived from the persisted decision/review status.

### 5.3 Incremental polling

```text
GET /api/pipeline/updates?cursor=<opaque>&limit=100&upper_bound_cursor=<opaque-when-draining>
```

For every poll:

1. capture a new upper high-water pair;
2. select rows strictly after the supplied cursor and at or below the upper bound;
3. return rows in ascending receipt order;
4. return `has_more: true` when the limit is reached; and
5. return that captured high-water value as `upper_bound_cursor`; and
6. advance to the captured upper bound only when all rows through it have been delivered.

If `has_more` is true, the client repeats the request with `cursor=next_cursor` and the same `upper_bound_cursor`. This makes the high-water boundary stable while a burst is drained.

The response also returns authoritative stage and channel counts so the frontend replaces its cards after each successful poll. A 101-event test must prove that burst paging loses and repeats nothing.

### 5.4 Inspector detail

```text
GET /api/pipeline/events/{raw_event_id}
```

Return one composed detail model:

- list-row overview;
- existing raw-event detail;
- nullable canonical-event detail; and
- nullable identity decision with thresholds, candidates, evidence, conflicts, and reason.

The route is keyed only by `raw_event_id`. The response includes `canonical_event_id` when available. This prevents the frontend from confusing the raw-detail ID with the match-explanation ID.

Keep the existing event and match-explanation endpoints compatible. The composed endpoint is additive and lets the pipeline inspector load a consistent view in one request.

## 6. Filters and visible states

Version one supports only fields that are persisted and indexed:

- channel: `web | mobile_app | call_center | physical_store`;
- processing status: `received | normalized | failed`;
- identity outcome: `auto_linked | review_required | new_profile`;
- source event ID: exact or case-insensitive prefix search; and
- received-time range, only after its timezone semantics are documented.

Do not add profile-name, email, phone, latency, connector, or error-message search to the first contract.

The `received` filter is retained for contract completeness, but ordinary synchronous ingestion does not leave a committed raw row in that state. It is expected to be empty unless a recovery/import path explicitly persists an interrupted record.

The page must implement:

- loading skeleton;
- empty database;
- filters with no results;
- failed raw event with no canonical record;
- normalized event with a decision;
- pending review event with no linked profile;
- polling degraded while the last successful snapshot remains visible;
- detail 404; and
- full initial-load error with retry.

## 7. Database and index work

The core read model should start without new business tables. Add an append-only migration only for query support:

- composite index on `raw_events(received_at, id)`;
- composite index on `raw_events(channel, processing_status, received_at, id)` if the query plan shows it is useful;
- index on `canonical_events(profile_id)` if absent and used by the detail/read model; and
- index on `match_decisions(outcome, review_status, created_at)` if the aggregate query needs it.

Verify indexes with PostgreSQL query plans against the generated 180–250 event dataset. Do not add speculative indexes based only on SQLite tests.

## 8. Frontend module plan

Add:

```text
frontend/components/pipeline/PipelineView.tsx
frontend/components/pipeline/PipelineStageCards.tsx
frontend/components/pipeline/ChannelCards.tsx
frontend/components/pipeline/EventStream.tsx
frontend/components/pipeline/EventInspector.tsx
```

Keep all wire types in `frontend/lib/types.ts` and all requests in `frontend/lib/api.ts`.

Recommended behavior:

1. the server page loads the initial snapshot;
2. `PipelineView` owns filters, pagination, selection, and three-second polling;
3. stage failures are displayed as a branch, not as a successful funnel step;
4. the stream clearly labels received, occurred, and processed times;
5. selecting a row opens overview, raw JSON, canonical JSON, and identity tabs;
6. failed events disable canonical and identity tabs with an explanation;
7. profile links appear only when the API returns a profile ID; and
8. polling stops or slows when the tab is hidden if this remains simple and testable.

## 9. Duplicate-attempt decision

The current duplicate contract returns the existing result and creates no new rows. Therefore the database cannot truthfully answer how many duplicate requests occurred or when they occurred.

Version one must return:

```json
{
  "duplicate_attempts": null,
  "duplicate_tracking_supported": false
}
```

Do not derive a duplicate count from generated fixture files or hidden truth.

If duplicate history becomes a requirement, approve a separate contract change and add an append-only ingestion-attempt audit table. That change must state which outcomes are recorded, how a 409 attempt affects persistence, retention rules, and whether the promise that duplicates create no rows is narrowed to **no new raw/canonical rows**. It is not part of the first pipeline slice.

## 10. Ordered task board

Each task should normally fit within two hours and end in a focused commit.

| Order | Task | Main files | Verification |
|---:|---|---|---|
| 1 | Freeze the read-model contract and add empty/normalized/failed/review sample responses. | `docs/05_API_CONTRACT.md`, `app/schemas/pipeline.py` | Schema examples validate; OpenAPI exposes additive models. |
| 2 | Add clean-database and seeded composition diagnostics for stage/channel counts and clock ordering. | `backend/tests/`, optional read-only script | Exact counts on an empty DB and deterministic seed. |
| 3 | Implement the deep pipeline read-model module and initial snapshot without polling. | `services/pipeline_read_model.py` | Service tests cover every count definition and null behavior. |
| 4 | Add `/api/pipeline/overview` and shared-envelope errors. | `api/routes/pipeline.py`, router | API contract tests for empty, mixed, and failed datasets. |
| 5 | Add filtered keyset pagination for `/api/pipeline/events`. | service, schemas, route | Done: equal timestamps, filter-before-count, stable next page, invalid cursor 422. |
| 6 | Add the composed inspector detail endpoint. | service, schemas, route | Done: normalized, failed, review-required, malformed-ID, and missing-ID tests. |
| 7 | Add high-water cursor polling and authoritative aggregate refresh. | service, route | Done: empty origin and 101-event burst prove no loss or duplicates. |
| 8 | Add only the indexes proven useful by the final queries. | new Alembic migration, if needed | Done: PostgreSQL query-plan review found no current index worth adding. |
| 9 | Add frontend types and request functions. | `frontend/lib/types.ts`, `frontend/lib/api.ts` | Done: strict typecheck and lint pass for overview, list, detail, and updates clients. |
| 10 | Build stage/channel cards and the real event stream. | `components/pipeline/`, pipeline page | Done: API-backed funnel, channel totals, filters, pagination, and loading/empty/error/success states. |
| 11 | Build the accessible inspector and ID-safe tabs. | `EventInspector.tsx` | Done: real detail drawer, keyboard tabs/Escape close, and separately labelled raw/canonical IDs. |
| 12 | Add polling, burst draining, degraded state, and stable selection. | `PipelineView.tsx` | Fake-timer polling tests and 101-event integration case. |
| 13 | Run end-to-end verification with generated data and the Riya demo. | backend/frontend tests | Pipeline updates while the six-step demo runs; golden path unchanged. |

### Task 8 decision: no migration yet

On 2026-09-20, PostgreSQL 17 query plans were measured against the local persisted dataset (197 raw events, 195 canonical events, and 195 match decisions). The warmed overview and 101-row polling queries completed in approximately 1.1 ms and 0.5 ms respectively. PostgreSQL correctly selected sequential scans plus in-memory sorts for this small working set, while the existing unique indexes served the canonical and match-decision joins.

A rollback-only probe of `(raw_events.received_at, raw_events.id)` did not prove a current benefit, so no schema migration or speculative filter index was added. Revisit this decision with production-like volume or a measured regression; retain the same keyset ordering pair if an index becomes justified.

## 11. First implementation slice

Start with Tasks 1–4 only:

1. freeze the response models;
2. write failing API/service tests for empty, one normalized event, one failed event, and one review-required event;
3. implement `pipeline_read_model.py`; and
4. expose `/api/pipeline/overview` with the latest 25 rows and no live polling yet.

Exit condition:

> Reset a clean database, ingest one valid event and one normalization failure, open `/api/pipeline/overview`, and see exact stage/channel counts plus two truthful event rows.

Only after that works should the team add pagination, inspector composition, polling, and frontend polish.

The overview, later event-list endpoint, and later polling endpoint must all call the same read-model query/projection helpers. Contract tests should submit the same persisted records through each public endpoint and assert that status, IDs, clocks, and identity fields agree; routes must not reimplement the joins.

## 12. Verification matrix

| Scenario | Required proof |
|---|---|
| Empty database | All counts are zero, rates/unsupported telemetry are null, and the origin cursor is valid. |
| Valid event | Raw, canonical, decision, and linked-profile facts agree. |
| Normalization failure | Raw row remains visible; canonical and identity fields are null; stable error code is shown. |
| Review required | Decision is visible, profile remains null, and the row links only to review. |
| Duplicate request | Existing event remains single; duplicate telemetry stays unsupported in version one. |
| Reused source ID | 409 behavior remains unchanged and no fabricated stream row appears. |
| Equal receipt times | Pagination and polling neither lose nor repeat rows. |
| Filtered pagination | Totals and cursors describe the same filtered set. |
| Inspector | Raw payload, canonical fields, and decision evidence all belong to the selected raw event. |
| Runtime isolation | Pipeline modules never import or read `data/truth/`. |
| Golden path | Riya links, Aarav remains safe, and alerts still behave exactly as before. |

## 13. Definition of done

- the API contract, Pydantic models, frontend types, and examples agree;
- every displayed count is traceable to a defined database query;
- list and poll cursors are stable under equal timestamps;
- failures appear without pretending they have canonical or identity data;
- raw payloads are opened deliberately and rendered safely;
- polling degrades without clearing the last valid snapshot;
- backend pytest, Ruff, frontend typecheck, lint, and a core page smoke test pass;
- the generated dataset and Riya demo exercise the page; and
- no infrastructure or duplicate telemetry is invented.

## 14. Explicitly deferred

- duplicate-attempt audit persistence;
- bulk replay or reprocessing controls;
- pause/resume ingestion;
- SSE or WebSockets;
- source connector health and SLAs;
- latency percentiles until processing durations are actually persisted;
- blob-store, queue, DLQ, or Kafka claims;
- production PII access controls; and
- exporting raw events.
