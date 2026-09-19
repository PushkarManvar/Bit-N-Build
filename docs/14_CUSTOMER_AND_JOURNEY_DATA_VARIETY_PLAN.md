# Customer Explorer and Journey Data Variety Plan

**Status:** Planned — no runtime behavior changes are authorized by this document alone  
**Created:** 2026-09-20  
**Audience:** Backend, synthetic-data, frontend, QA, and demo owners  
**Depends on:** `docs/13_REVIEW_QUEUE_DATA_VARIETY_PLAN.md` for review-case variety  
**Related:** `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/07_TESTING_EVALUATION_AND_DEMO.md`, and `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md`

## 1. Decision and problem statement

The Customer Explorer and Journey Detail should tell different, evidence-backed customer stories. They must not look like the same generic profile repeated with a different name.

The Stitch screens are useful references for hierarchy, density, and information grouping. They are not a data specification: examples such as loyalty tiers, payment amounts, agents, ticket IDs, CRM notes, SLA clocks, and provider status must not be copied unless JourneyLens persists and exposes those facts.

The current backend exposes enough for a basic profile list and timeline, but it loses useful deterministic context:

| Surface | Current limitation | Why it feels generic |
|---|---|---|
| `GET /api/profiles` | `open_alert_count` is always `0` and `review_required` is always `false`; no latest-event context is returned. | Rows differ mostly by name, channel, and event count. |
| Customer search/filtering | The live route implements free-text search only even though the documented contract names alert/review/channel filters. | Operators cannot focus on a real operational segment. |
| `GET /api/profiles/{id}` | Timeline events expose channel, type, order, outcome, score, and string evidence only. | The useful persisted attributes—such as a refund contact note or store city—are not shown in a controlled form. |
| Journey summary | API always returns `journey_summary: null`. | The header cannot explain why this timeline matters. |
| Synthetic seed composition | The generator has normal, broken-refund, and anonymous-bridge helpers, but the profile API does not surface those differences as real calculated facts. | The variety exists in raw events but is invisible in the product. |

## 2. Safety and content rules

1. Identity remains deterministic: name similarity alone never links a profile.
2. The read model may summarize persisted facts, but never infer a payment, agent, SKU, loyalty tier, address, support ticket, or business SLA that is not present in the event data.
3. Event attributes are not blindly sent to the browser. Each display field must be an allowlisted, typed, and sanitized projection.
4. Profile identifiers remain masked in list views; full values remain restricted to the existing evidence/raw-payload policy.
5. `open_alert_count`, needs-review status, channel count, last activity, and order references are calculated from database records; no default number is shown as if it were real.
6. Runtime services and APIs never read `data/truth/`.

## 3. Target story mix

Use a deterministic full operations dataset with profiles that demonstrate different actual journeys. The demo may show a curated subset, but it must be generated from the same scenario definitions.

| Archetype | Real event pattern | Explorer signal | Journey signal |
|---|---|---|---|
| Flagship broken refund | Web/app activity, return request, two contacts, store visit, no refund completion for one order. | Four channels, open alerts, latest support/store event. | Unresolved refund and repeated-contact alerts with linked evidence. |
| Completed refund | Order/return activity followed by `refund_completed`. | Multiple events, no open refund alert. | A completed resolution sequence; no false unresolved-refund alert. |
| Anonymous-to-known bridge | Web device/session event followed by app email/device event. | Multiple channels and a clear latest event. | Evidence shows the deterministic bridge without an unsafe name match. |
| Single-channel profile | One or two events with a single identifier/channel. | Low event count and one channel. | Short, honest timeline—not a fake “customer 360” view. |
| Safe same-name collision | Same display name as another profile, but no shared strong identifier. | Stable differentiator such as masked identifier or profile suffix. | Explicitly stays separate; never rendered as a duplicate. |
| Review/exception case | Pending conflict or incomplete evidence from the Review Queue plan. | Needs-review state only when the profile is a persisted candidate, not copied to every profile. | Link to the review case only when the API proves that candidate relationship. |

The minimum demo set is five visible profiles covering the first five archetypes. Do not require every profile to have alerts or four channels; contrast is what makes the explorer useful.

## 4. Backend read-model plan

### Phase 0 — Profile and timeline composition audit

Before adding fields, create deterministic tests/diagnostics for a clean seeded database:

- profiles by distinct channel count;
- profiles by event count;
- profiles with open alerts by type/severity;
- profiles appearing as a persisted candidate in a pending review decision;
- timeline event types and the safe attributes available for each type; and
- expected archetype counts from the synthetic generator.

This determines whether generic output comes from seed data, API projection, or both. Store expected archetype labels only in offline fixture/evaluation data; runtime must derive signals from persisted events and decisions.

### Phase 1 — Truthful Customer Explorer summary fields

Keep `GET /api/profiles` compatible. Add optional fields only after contract review; never replace existing names.

Proposed additive `ProfileSummary` fields:

```json
{
  "channel_count": 4,
  "open_alert_count": 2,
  "highest_open_alert_severity": "high",
  "review_required": false,
  "latest_event": {
    "channel": "physical_store",
    "event_type": "store_visited",
    "occurred_at": "2026-09-20T08:00:00Z",
    "order_id": "ORD-204"
  },
  "recent_order_ids": ["ORD-204"]
}
```

Calculation rules:

- `open_alert_count` and `highest_open_alert_severity` query only open `JourneyAlert` rows for that profile.
- Keep the existing `review_required` field as the compatibility name. It is true only when this profile ID appears in the persisted `MatchDecision.candidates` list for at least one pending decision; it is false for an unlinked pending event with no candidate. This is a candidate-risk signal, not a claim that the profile owns the pending event. Do not add a second `has_pending_review` alias.
- `latest_event` is the maximum canonical `occurred_at`, with canonical event ID as a deterministic tie-breaker.
- `recent_order_ids` is a maximum of three distinct linked orders, sorted by their latest event time; omit the field or use `[]` when no order is known.
- identifiers use the server-side masking projection in Phase 1a; do not add city, address, amount, loyalty, or agent columns.

Implement the documented filters only when the API supports them: `search`, `channel`, `has_open_alert`, and the existing `review_required`. Every filter must apply before count and pagination. Use a deterministic order: event-time `last_seen_at DESC`, then profile UUID ascending.

`last_seen_at` is redefined as the maximum linked canonical `occurred_at`, not ingestion/processing time. Update profile attach/create logic with `max(existing_last_seen_at, canonical.occurred_at)` and add a migration/backfill that derives the value from linked canonical events. If two events have the same time, choose the greater canonical event UUID only for selecting `latest_event`; the profile list remains stable through the profile-UUID tie-breaker.

### Phase 1a — Identifier display projection

The API must stop treating a browser-only mask as a privacy boundary. Add a shared server-side identifier presentation helper and return safe display values:

```json
{
  "identifier_summaries": [
    { "type": "email", "display_value": "r***@example.com", "masked": true },
    { "type": "phone", "display_value": "+91 •••••• 3210", "masked": true },
    { "type": "order_id", "display_value": "ORD-204", "masked": false }
  ]
}
```

For compatibility, existing list `email` and `phone` fields change to masked values in the same release and are marked deprecated in the API contract; frontend consumers must move to `identifier_summaries`. Device IDs and session IDs are always shortened/masked in list and detail read models. Full identifier values remain available only in the existing controlled raw/normalized evidence path, never the explorer list.

### Phase 2 — Safe journey event projection

Keep the existing timeline fields and add an optional, allowlisted `event_summary` and `context` projection:

```json
{
  "event_id": "uuid",
  "event_type": "support_contacted",
  "event_summary": "Support contact recorded for ORD-204: refund not received.",
  "context": {
    "order_id": "ORD-204",
    "store_city": null,
    "contact_reason": "refund_not_received"
  }
}
```

The backend creates this projection from canonical fields plus type-specific allowlisted attributes:

| Event type | Allowed context | Deterministic summary pattern |
|---|---|---|
| `product_viewed` | optional `product_id` only when present and non-sensitive | `Website activity recorded.` |
| `app_login` | no free-text attributes | `Mobile app sign-in recorded.` |
| `order_placed` | `order_id` | `Order {order_id} recorded.` |
| `return_requested` | `order_id` | `Return requested for {order_id}.` |
| `support_contacted` | normalized `contact_reason` enum, `order_id` | `Support contact recorded for {order_id}: {reason}.` |
| `store_visited` | sanitized `store_city`, `order_id` | `Store visit recorded in {city}.` or `Store visit recorded.` |
| `refund_completed` | `order_id` | `Refund completion recorded for {order_id}.` |

Free-form source notes must not become browser copy. During normalization, map only these source keys and values into the projection:

| Source attribute | Acceptance rule | Output |
|---|---|---|
| `attributes.notes` on `support_contacted` | Trim, lowercase, max 120 characters; exact map `refund not received` → `refund_not_received`, `second follow-up` → `return_status`; all other values → `other`. | `contact_reason` enum only; never the original note. |
| `attributes.store_city` on `store_visited` | 2–48 characters matching `^[A-Za-z][A-Za-z .'-]{1,47}$`; normalize whitespace and title case. | `store_city`; otherwise omit it. |
| `attributes.product_id` on `product_viewed` | 1–64 characters matching `^[A-Za-z0-9_-]+$`. | `product_id`; otherwise omit it. |

All other attribute keys are omitted from `context`. Preserve the original raw payload only for existing evidence/audit handling.

### Phase 3 — Deterministic journey summary

Return a calculated **order-scoped** `journey_summary` only when the profile has events. It is a typed fact summary, not an LLM output.

```json
{
  "event_count": 7,
  "channel_count": 4,
  "open_alert_count": 2,
  "selected_order_id": "ORD-204",
  "journey_state": "refund_follow_up_needed",
  "summary": "7 events across 4 channels with 2 open journey alerts."
}
```

Select the order deterministically: first choose the order attached to the highest-severity open alert; ties use earliest alert creation time, then lexical order ID. If there is no open alert, choose the order of the latest canonical event using `occurred_at DESC`, then canonical UUID descending. Evaluate the state only from linked events for that selected order.

`journey_state` may be one of:

```text
refund_follow_up_needed | active_return | refund_completed | cross_channel_activity | no_open_issue
```

Precedence is deterministic: open unresolved-refund alert, then open repeat-contact alert, then a return with no later completion for the selected order, then a completion for the selected order, then cross-channel activity for that order, then no open issue. The API lists the underlying alert/event IDs in additive `source_event_ids` / `source_alert_ids` fields.

To make alert source IDs truthful, add an append-only migration for `JourneyAlert.rule_evidence` JSON. When the analyzer creates or updates an alert, it stores the ordered canonical event IDs and rule version used by that rule. On every analysis pass, it evaluates existing open alerts for the same profile/order/type: if the predicate is now false, it sets `status=resolved` and `resolved_at` to analysis time. A `refund_completed` event therefore closes the matching `unresolved_refund` alert. A `repeat_contact` alert remains independent; it closes only when its own documented predicate/resolution policy is met. The completed-refund fixture must not contain a repeat-contact alert, so it remains a calm profile.

### Phase 4 — Seed-data archetypes and reset modes

Refactor the synthetic generator into named deterministic scenario constructors rather than relying on filler output alone:

```text
flagship_broken_refund
completed_refund
anonymous_to_known_bridge
single_channel_profile
same_name_collision
review_queue_cases
```

Each constructor has an expected runtime outcome asserted through real ingestion. The existing `POST /api/demo/reset` remains compatible with a no-body request. Add an optional validated request body:

```json
{ "mode": "operations_full" }
```

`mode` is a `DemoSeedMode` enum: `operations_full | demo_curated`. The omitted-body default is `operations_full`, preserving current behavior. The response echoes `mode`, generated source count, and pending-review count. Test each mode from an empty database and reject unknown modes with 422. Keep this local/demo-only operation behind the existing demo route; do not add a frontend-only data switch.

The reset service then selects one of two explicit seed modes:

- `demo_curated`: the five-profile story set plus the 3–7 curated review queue;
- `operations_full`: the 30–40 profile dataset and the 5–10 review-candidate target.

Neither mode reads `data/truth/` at runtime.

## 5. Model and database decisions

Start with query-time read models. The existing `CustomerProfile`, `CanonicalEvent`, `MatchDecision`, `JourneyAlert`, and `ReviewAction` records already provide most source facts.

Add database fields only when they represent a stable fact required by multiple consumers:

| Candidate field | Add now? | Decision |
|---|---:|---|
| `contact_reason` on canonical event attributes or typed column | Yes, if normalizer can derive an enum. | Replaces unsafe free-text notes in product copy. |
| `event_summary` | No. | Derive server-side from canonical type, order, and allowed context. |
| `journey_state` | No initially. | Derive from current events/alerts; persist only if a historical policy version is needed. |
| `open_alert_count` | No. | Compute in profile list query. |
| `JourneyAlert.rule_evidence` | Yes. | Needed to make calculated summary source IDs inspectable and alert lifecycle reproducible. |
| customer city / address / loyalty / spend / agent | No. | Not required by the product contract and would invite fictional UI. |
| `scenario_name` on runtime profile | No. | Keep scenario labels in offline fixture/evaluation metadata only. |

If a typed `contact_reason` column is chosen, create an append-only migration, backfill only recognized values, and leave unknown values null. Do not rewrite raw event payloads.

## 6. API and frontend handoff contract

The backend owner provides an example for each archetype and explicitly documents null behavior.

| Consumer | Required API guarantee | Frontend behavior |
|---|---|---|
| Explorer table | Real `open_alert_count`, persisted-candidate `review_required`, masked identifier summaries, channels, latest event, deterministic pagination. | Differentiate rows with fact chips; explain that review status means a profile is a candidate, not the owner of an unlinked event. |
| Profile preview | Same summary fields plus real recent events/alerts. | Preview is a read-only shortcut; journey link remains primary. |
| Journey header | Calculated counts/state with source IDs. | State label links to the underlying alerts/events. |
| Timeline | Event summary, allowed context, outcome, score, and evidence shortcut. | Cards vary by real event type/context, not decorative paragraphs. |
| Evidence drawer | Existing raw/normalized/explanation endpoint remains source of truth. | Show details on demand; do not put raw PII into the timeline list. |

The frontend must retain loading, empty, partial-error, full-error, and no-alert states. A normal completed-refund profile should look calm and brief; an unresolved refund should be more prominent because real alerts make it so.

## 7. Tomorrow's implementation order

| Order | Task | Owner | Verification |
|---:|---|---|---|
| 1 | Add clean-seed archetype/composition diagnostics. | Backend/data | Exact scenario counts and query result test. |
| 2 | Replace hard-coded profile list alert/review values with real calculated values and event-time `last_seen_at`. | Backend | API test with alert/no-alert and candidate/non-candidate profiles; backfill test. |
| 3 | Add server-side masked identifier summaries, safe `latest_event`, severity, channel count, and recent-order projections. | Backend | Contract/Pydantic tests including masking, nulls, and ordering. |
| 4 | Add API filters with count-before-pagination semantics. | Backend | Filter/pagination integration tests. |
| 5 | Add allowlisted timeline context and deterministic summaries. | Backend | No raw free-text leakage; each event-type template covered. |
| 6 | Add alert rule-evidence persistence, closure lifecycle, and order-scoped deterministic journey summary. | Backend | Precedence and closure tests for broken, completed, bridge, and calm journeys. |
| 7 | Add validated curated/full reset modes and assert real-ingestion outcomes. | Data/backend | No-body compatibility; each mode deterministic; truth remains isolated. |
| 8 | Update Customer Explorer and Journey Detail against the additive contract. | Frontend | Typecheck, lint, build, visual checks at 1440/1024/390. |

Do not mix the review identifier-uniqueness migration from document 13 with this work. Integrate it only after its own tests pass.

## 8. Acceptance tests

| Scenario | Expected proof |
|---|---|
| Riya / broken refund | Four channels, correct alerts, deterministic summary cites its alert/event IDs. |
| Completed refund | Completion closes the matching unresolved-refund alert with `resolved_at`; no alarmist status in the fixture. |
| Anonymous bridge | Timeline shows the web-to-app link evidence; no name-based explanation. |
| Single channel | Explorer/timeline remains concise and honest. |
| Same-name collision | Two profiles stay visually distinguishable; neither is called a duplicate or auto-linked. |
| Search and filters | Search by name/email/phone/order and filters return truthful totals and stable pages. |
| Event context | Only allowlisted fields render; raw notes, addresses, agents, and payment data never leak into summary cards. |
| Empty/error states | No profiles, no alerts, 404 profile, and API failure produce usable states. |
| Runtime isolation | No API, generator runtime, or resolver reads `data/truth/`. |

## 9. Explicitly deferred

- CSV export, batch actions, and “send to review” controls until an API and workflow exist.
- Customer health scores, confidence percentages, value tiers, and SLA timers until they are real calculated product metrics.
- Profile merge/split/unmerge workflow.
- Any real payment/refund execution or external CRM integration.
