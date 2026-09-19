# Command Centre Signal Integrity Plan

**Status:** Planned — no runtime behavior changes are authorized by this document alone  
**Created:** 2026-09-20  
**Audience:** Backend, synthetic-data, frontend, QA, and demo owners  
**Depends on:** `docs/13_REVIEW_QUEUE_DATA_VARIETY_PLAN.md` and `docs/14_CUSTOMER_AND_JOURNEY_DATA_VARIETY_PLAN.md`  
**Related:** `docs/02_USER_WORKFLOWS_AND_UX.md`, `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/07_TESTING_EVALUATION_AND_DEMO.md`, and `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md`

## 1. Decision and problem statement

The Command Centre is an operational entry point, not a decorative dashboard. It should show a small, varied set of real operational signals and take the user to the evidence behind each one. It must not repeat the same seeded event or alert until the screen looks busy.

The current behavior explains the generic output seen in the running application:

| Surface | Current implementation | Result |
|---|---|---|
| Recent activity | `dashboard_updates` selects the latest 20 canonical events by `CanonicalEvent.created_at`. The initial client request accepts all 20 and displays eight. | A reset that ingests many fixture records together can fill the feed with identical event types, even when their business `occurred_at` values differ. |
| Polling cursor | The `since` filter is also based on `created_at`; the browser cursor is its own request-start time. | A delayed or backfilled event can have meaningful business time but is hard to explain as a newly processed item. |
| Relative timestamps | `formatRelativeTime` treats every negative time difference as less than five seconds. | A future-dated synthetic event is incorrectly rendered as **just now**. |
| Priority issues | `GET /api/alerts` returns rule title, copy, severity, and order, but not `profile_id`, alert evidence, or a stable grouping key. | Similar unresolved-refund cards look like duplicates and cannot safely link to their journey. |
| KPI cards | Counts are live database totals, while the evaluation metrics come from the latest evaluation run. The dashboard combines four endpoints with no shared snapshot time. | Values are truthful individually, but there is no explicit definition of which clock/window explains a change. |
| Synthetic base data | The baseline can contain many instances of the same broken-refund pattern. | There is too little contrast between a calm profile, a review problem, and a genuinely active journey. |

The Stitch reference is a hierarchy and density reference only. It does not authorize invented agents, CRM tickets, payment values, provider status, SLA timers, “live pipeline” claims, or charts with fabricated numbers.

## 2. Guardrails

1. Use canonical event facts and deterministic rules only; no LLM decides an alert, identity result, or KPI.
2. Never read `data/truth/` from a runtime API, seed generator, resolver, or dashboard service.
3. A dashboard card may summarize an API field but may not invent a trend, a delta, an owner, a duration, or a business action.
4. Preserve the existing polling baseline. Do not add Kafka, SSE, Redis, background workers, or a new infrastructure layer.
5. Keep existing `/api/analytics/*`, `/api/alerts`, and `/api/dashboard/updates` responses compatible. Add fields/endpoints; do not silently redefine existing response fields.
6. Every alert, feed event, and count shown as current must be traceable to a database record and an explicit `as_of` time.

## 3. Target dashboard story mix

The full operations seed from document 14 should produce contrast, not six variations of the same card.

| Operational condition | Priority issues | Recent activity | KPI effect |
|---|---|---|---|
| Calm completed refund | No open refund alert. | Completion appears once with a resolved outcome. | Events/profiles increase; open alerts do not. |
| Flagship broken refund | One unresolved-refund and one repeat-contact alert for `ORD-204`, grouped under the same journey. | Return, support, and store events explain the escalation. | Open alerts and channel mix reflect real events. |
| Pending identity review | No invented journey problem. | A `review_required` identity outcome links to the review case, not a guessed profile. | Pending-review count rises. |
| Anonymous-to-known bridge | No alert unless a real journey rule fires. | Web-to-app identity outcome shows its evidence shortcut. | Auto-link rate is computed from actual decisions. |
| Single-channel customer | No alert by default. | One concise activity row. | Channel total shows the actual channel distribution. |

The initial dashboard should have no more than eight activity rows and no more than three visible issue groups. The product may have more records; it should provide an honest “show more” or filtered destination rather than copying near-identical rows into the visible area.

## 4. Backend and API plan

### Phase 0 — Composition and clock audit

Add deterministic diagnostics against an empty seeded database before changing the UI:

- canonical event counts by `event_type`, channel, and profile;
- top repeated `(channel, event_type, profile_id, order_id)` patterns in the newest 20 canonical events;
- open alert counts by `(profile_id, order_id, type, severity)`;
- profile/order coverage for every alert;
- events whose `occurred_at` is later than the request's current UTC time; and
- evaluation-run timestamp and the source record count used for its metrics.

This audit distinguishes a seed-composition issue from a projection/query issue. It must not store scenario labels in runtime rows.

### Phase 1 — Stable operational snapshot

Keep the current endpoints. Add an additive `GET /api/dashboard/overview` endpoint for the Command Centre's initial paint:

```json
{
  "as_of": "2026-09-20T12:00:00Z",
  "metrics": {
    "unified_profiles": 28,
    "normalized_events": 186,
    "total_raw_events": 190,
    "pending_reviews": 3,
    "open_alerts": 3,
    "auto_link_rate": 76.3,
    "match_precision": null
  },
  "channels": {
    "web": 62,
    "mobile_app": 79,
    "call_center": 14,
    "physical_store": 34
  },
  "activity": [],
  "activity_cursor": "opaque-cursor",
  "issue_groups": [],
  "ungrouped_alerts": []
}
```

Before any dashboard query, the service captures an activity high-water pair `(processed_at, event_id)` in the same read transaction and returns it as opaque `activity_cursor`. When no canonical event exists, it returns the fixed versioned **origin cursor** `(1970-01-01T00:00:00Z, 00000000-0000-0000-0000-000000000000)`, encoded exactly like any other cursor. A poll from origin selects every later record; an empty poll retains the supplied cursor. `as_of` is only a display timestamp captured at transaction start; it is never used as a polling boundary. On PostgreSQL, run the overview reads in a `REPEATABLE READ` transaction so each query sees the same snapshot. SQLite tests do not model concurrent writers; they assert that every activity query is constrained to the captured high-water pair.

All count queries, issue groups, and initial activity are evaluated inside that transaction. `match_precision` retains the semantics of the latest persisted evaluation run and is `null` when no run exists; it is never turned into a default percentage.

The existing `/api/analytics/overview` and `/api/analytics/channels` remain valid. The frontend moves to the snapshot only after contract tests exist. This removes initial-paint disagreement without creating a second source of truth for the underlying counts.

### Phase 2 — Activity feed with two explicit clocks

Additive `DashboardActivityOut` fields:

```json
{
  "activity_id": "event:6d7...",
  "kind": "canonical_event",
  "event_id": "6d7...",
  "profile_id": "prof-...",
  "review_match_decision_id": null,
  "channel": "physical_store",
  "event_type": "store_visited",
  "occurred_at": "2026-09-20T11:58:00Z",
  "processed_at": "2026-09-20T12:00:01Z",
  "order_id": "ORD-204",
  "identity_outcome": "auto_linked",
  "summary": "Store visit recorded for ORD-204."
}
```

Rules:

- `processed_at` is the canonical creation/processing timestamp and is the polling cursor field. `occurred_at` remains the event's business time.
- The initial snapshot uses `processed_at DESC, event_id DESC`, limited to eight for display only. Its `activity_cursor` is the captured high-water pair, not the oldest displayed row; the initial load does not pretend to paginate older history. The UI may label a delayed event as **processed now • occurred 2d ago**; it must not disguise one clock as the other.
- The incremental endpoint accepts an opaque composite cursor based on `(processed_at, event_id)`, not a bare timestamp. For a poll, capture an upper high-water pair first, select pairs strictly greater than the supplied cursor and less than or equal to that upper bound, then return records in ascending processed order. This prevents equal-timestamp records from being lost or repeated unpredictably.
- Incremental response limit is 100. If a burst exceeds the limit, return `has_more: true` and set `next_cursor` to the last returned pair; the client immediately requests the next page until `has_more: false`. When no rows are returned, set `next_cursor` to the captured upper-bound cursor. This catches every record from a burst without advancing beyond unseen records.
- Keep `since` as a compatibility query parameter for one release after the cursor client is deployed. A request carrying both `since` and `cursor` returns 422. Legacy `since` requests retain the current event/new-alert response semantics; cursor responses add `activity`, `next_cursor`, `has_more`, `as_of`, authoritative `overview`, `issue_groups`, and `ungrouped_alerts`. Freeze the field-level contract and fixtures in `docs/05_API_CONTRACT.md` before switching the frontend.
- `activity_id` is stable and the frontend merges by it. A single canonical event appears at most once in the local activity list.
- A profile-less `review_required` decision has `profile_id: null` and a non-null `review_match_decision_id`; it can link only to the existing `/reviews` route. It must not claim focus on a particular case until document 13's review-queue API and a route/query focus contract are implemented.
- Summaries use the allowlisted event projection defined in document 14. No raw notes, addresses, agents, values, or ticket numbers appear here.

### Phase 3 — Correct time presentation

Fix the shared relative-time formatter before relying on it in a live feed:

- when a timestamp is more than five minutes in the future, render an absolute time plus **clock mismatch** rather than **just now**;
- when it is up to five minutes ahead, render **in less than 5 min**, not a past-tense label;
- use `processed_at` for “newly processed” presentation and `occurred_at` for chronology;
- retain an accessible full UTC/local timestamp in the `time` element; and
- test past, current, future, invalid, and missing timestamps.

This is a data-integrity correction, not visual polish.

### Phase 4 — Alert groups and safe destinations

The current analyzer pre-check prevents ordinary duplicate open rows for a single `(profile, order, type)`, but its nullable-order database uniqueness protection is incomplete under concurrency. The dashboard should still group rule alerts belonging to the same profile/order into one operational issue group.

Additive `DashboardIssueGroupOut`:

```json
{
  "group_id": "profile:...:order:ORD-204",
  "profile_id": "prof-...",
  "order_id": "ORD-204",
  "highest_severity": "high",
  "alert_count": 2,
  "alert_types": ["unresolved_refund", "repeat_contact"],
  "primary_alert_id": "alert-...",
  "title": "Refund ORD-204 remains unresolved",
  "description": "Return activity and repeated contacts exist without a refund completion.",
  "recommended_action": "Prioritize refund resolution.",
  "created_at": "2026-09-20T11:45:00Z"
}
```

Rules:

- Group by non-null `profile_id` and `order_id`. An alert without either is returned in additive `ungrouped_alerts: AlertOut[]`, rendered as an individual inspectable card, and never attached to a guessed customer.
- Select the primary alert by severity (`critical`, `high`, `medium`, `low`), then oldest `created_at`, then UUID. The primary title/description/action come from that alert; the group exposes all alert types/counts.
- Order groups by highest severity, then oldest primary `created_at`, then `group_id`. Return every active group and `issue_group_total`; the small MVP frontend shows three and expands its local list for **Show more**, without inventing a new alert destination.
- Include `profile_id` in additive `AlertOut` and in the group. The Command Centre can then link safely to `/customers/{profile_id}`. It shows the order ID in the destination context but must not claim the route opened with an order filter until a supported URL/query contract is added.
- Alert lifecycle/evidence follows document 14: a completed refund resolves its matching unresolved-refund alert. Resolved alerts leave the live issue list but remain auditable in a detail/evidence flow.
- Resolving one alert does not resolve another type in its group. If a refund completion arrives for Riya while the repeat-contact predicate remains true, the existing group remains with `alert_count: 1`, `alert_types: ["repeat_contact"]`, and its repeat-contact copy. The completed-refund fixture avoids a repeat-contact alert, so its sole group disappears after resolution.
- Each successful cursor poll returns the authoritative complete `issue_groups` and `ungrouped_alerts` lists, even when `new_alerts` is empty. The frontend replaces those two lists on every successful poll; it does not only merge additions. This removes a resolved issue from a long-lived browser correctly.
- Add an append-only migration for a null-safe open-alert uniqueness strategy (for example, a partial unique index using a stable `COALESCE(order_id, '')` expression where supported), retain the service pre-check, and add a concurrent/retry test. Do not turn a group into a new alert type or discard individual alert rows.

Add `GET /api/alerts/{alert_id}` as an additive safe inspection endpoint. It returns the individual alert, additive `profile_id`, `resolved_at`, and the rule-evidence projection defined in document 14. It returns a shared-envelope 404 when absent. An ungrouped card opens this detail/evidence view instead of navigating to a guessed profile; a resolved alert remains inspectable by its ID from an alert group/detail link. This endpoint is read-only and does not introduce alert-management actions.

### Phase 5 — Metric definitions and evaluation provenance

Keep the KPI set small and make each label explicit:

| UI label | Source | Definition | Null/empty behavior |
|---|---|---|---|
| Unified profiles | `CustomerProfile` count | Current count of persisted profiles. | `0` on an empty database. |
| Events processed | `CanonicalEvent` count | Successfully normalized canonical events. | `0` on an empty database. |
| Needs review | pending `MatchDecision` count | Current identity decisions with pending review status. | `0` when none are pending. |
| Active journey alerts | open `JourneyAlert` count | Current open rule alerts, while issue groups are a separate presentation. | `0` when none are open. |
| Auto-link rate | `MatchDecision` outcomes | `auto_linked / all decisions`, as a lifetime demo total until a windowed contract is introduced. | `null`/`—` when there are no decisions. |
| Match precision | latest `EvaluationRun` | Evaluation-only metric, never a live operational ratio. | `null`/`—` when no evaluation exists. |

Do not add “last hour,” increase/decrease badges, latency, pipeline health, or accuracy claims without an API field, defined time window, and testable provenance. The snapshot includes optional `evaluation_as_of` from `EvaluationRun.created_at` and `evaluation_event_count` from the existing persisted `metrics.truth_events` key. The latter is the count of records evaluated by the offline evaluator, not a runtime truth-file read. It is null if either value is unavailable; no model migration is needed for this first version.

Every successful cursor poll also returns an additive authoritative `overview` object containing the current metrics, channels, `as_of`, and `activity_cursor`. The frontend replaces the KPI/channel state atomically from that object before updating its “last updated” label. This keeps the label truthful; it never presents initial-paint counts as a fresh live snapshot after events arrive.

### Phase 6 — Deterministic seed composition

Reuse document 14's named scenario constructors. The `operations_full` mode must include:

- one flagged Riya refund journey that produces a single two-alert issue group;
- at least one completed refund with no open refund alert;
- at least one bridge journey with a meaningful identity outcome;
- at least one pending review that is not displayed as a journey issue; and
- single-channel/customer records so channel counts and recent activity are not uniform.

The first eight activity records in a clean reset must include at least three event types and at least three channels. This is a seed acceptance test, not a frontend hard-coded ordering rule. If actual chronological events cannot satisfy it, the feed should remain truthful rather than shuffle data; adjust scenario timestamps and event order in the seed instead.

## 5. Frontend handoff

After the backend contract is available, the Command Centre should:

1. Fetch one dashboard overview snapshot for the initial paint instead of four independent resources.
2. Use the current poll overview's `as_of` only for a last-updated label, drain every `has_more` cursor page before advancing the local cursor, and show degraded state after three failed polls as it does today.
3. Display at most three issue groups, with explicit count/type labels when a group contains multiple rules.
4. Use the safe `profile_id` destination supplied by the API. A profile-less review event links only to Review Queue, not Customer Explorer or an unsupported direct-case URL.
5. Show both business and processing time when they materially differ; otherwise show the event's occurred time.
6. Replace active issue groups/ungrouped alerts with each successful authoritative poll response, while retaining skeleton, empty, partial-error, full-error, and no-active-issue states.

The frontend does not locally deduplicate different alerts with similar copy, calculate KPI values, infer group membership, or fabricate a trend.

## 6. Tomorrow's implementation order

| Order | Task | Owner | Verification |
|---:|---|---|---|
| 1 | Add seeded-data composition and timestamp diagnostics. | Backend/data | Exact expected counts plus future-time report. |
| 2 | Define and test `DashboardActivityOut`, opaque cursor encode/decode, burst catch-up, and compatibility with `since`. | Backend | Equal processed timestamps, delayed events, 101-event burst, no-loss, and no-duplicate tests. |
| 3 | Add the initial dashboard overview snapshot plus refreshed poll overview with `as_of` and a high-water cursor. | Backend | Empty-origin cursor, snapshot-boundary consistency, PostgreSQL transaction semantics, fresh KPI replacement, and null evaluation-metric tests. |
| 4 | Add `profile_id` to alerts, null-safe uniqueness protection, deterministic issue groups, ungrouped alerts, and alert detail. | Backend | Grouping, ordering, primary selection, null-profile, concurrent duplicate, 404, and safe-inspection tests. |
| 5 | Apply the alert closure/rule-evidence work from document 14. | Backend | Completion resolves only the matching unresolved-refund alert; any valid repeat-contact alert remains grouped. |
| 6 | Correct time formatting, drain cursor bursts, replace authoritative active issues, and connect supported destinations. | Frontend | Past/current/future clock tests, 101-event burst, resolved-group removal, and keyboard/screen-reader labels. |
| 7 | Update full/curated seed scenarios and visual smoke-test the dashboard. | Data/frontend | First eight activities meet mix target; 1440/1024/390 checks. |

## 7. Acceptance tests

| Scenario | Expected proof |
|---|---|
| Clean full reset | Initial activity contains at least three channels and event types, with no fabricated copy. |
| Empty database then first event | Origin cursor receives the first event without a reset or missed activity. |
| Equal processing timestamps | Cursor pagination neither loses nor repeats activity rows. |
| Burst during polling | A 101-event burst is fetched across cursor pages without loss, then the cursor reaches the captured high-water mark. |
| Delayed/backfilled event | Feed distinguishes processed time from occurred time. |
| Future timestamp | UI does not label it **just now**. |
| Riya's two rules | Two underlying alerts display as one issue group with count/type context and a safe journey link. |
| Completed refund | Resolved alert is absent from active issues; audit data remains available. |
| Riya refund completion | The unresolved-refund item resolves while an independently valid repeat-contact item remains as a one-alert group. |
| Ungrouped alert | It remains visible as an individual card and receives no guessed journey destination. |
| Pending review with no profile | Activity links to the review item and never guesses a profile. |
| Empty DB | Counts are zero; rate/evaluation metrics follow their documented null behavior. |
| Poll failure | Last successful data remains visible, polling is marked degraded, and retry works. |
| Runtime isolation | No dashboard, seed, or matching service reads `data/truth/`. |

## 8. Remaining data-plan audit

| Surface | Existing plan coverage | Separate plan needed now? | Decision |
|---|---|---:|---|
| Review Queue and review data | Document 13. | No. | Implement document 13 before expanding the review screen further. |
| Customer Explorer and Journey Detail | Document 14. | No. | Implement document 14 before adding richer profile/timeline UI. |
| Command Centre | This document. | No after this document lands. | Implement this document with the shared seed work in document 14. |
| Demo Controller | Document 14's named scenarios/reset modes plus existing workflow specification. | No. | It should consume the shared scenario constructors; another data plan would duplicate work. |
| Data Pipeline | `docs/16_DATA_PIPELINE_READ_MODEL_PLAN.md` now defines the `BE-FE-04` event-list and `BE-FE-05` aggregate contracts, inspector, polling, privacy rules, and duplicate-telemetry boundary. | No. | Implement document 16 as its own vertical slice; do not bundle it into the dashboard work. |

No other generic-data document is needed before these three planned surfaces are implemented. Do not create a document for visual-only refinements; use the existing design system and Stitch implementation guide for those.
