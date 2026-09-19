# Review Queue Data Variety and Backend Read-Model Plan

**Status:** Planned — do not implement from this document without the staged checks below  
**Created:** 2026-09-20  
**Audience:** Backend, data, frontend, QA, and demo owners  
**Related:** `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/07_TESTING_EVALUATION_AND_DEMO.md`, and `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md`

## 1. Decision and problem statement

The Review Queue should help an operator distinguish genuinely different kinds of unsafe or uncertain identity decisions. It must not become a list of dozens of almost identical `score 50` device-only matches.

The live local queue currently contains **63 pending decisions**. Many have the same shape:

- one device match;
- identity score `50`;
- no conflict;
- the same missing strong identifiers; and
- nearly identical reason and evidence text.

This is real output from the current deterministic resolver, not a frontend rendering fault. The resolver assigns a device match weight of `45` plus `5` corroboration, which is exactly the review threshold of `50`. Each such record is therefore correctly classified as `review_required`, but the collection has poor operator variety and poor demo value.

The Stitch reference is a visual target, not a truth source. Its queue has useful variety, but it includes unsupported claims such as made-up ticket IDs, loyalty tiers, SLAs, and customer facts. JourneyLens must earn visual variety from deterministic evidence and persisted data rather than copy those claims.

## 2. Non-negotiable guardrails

1. No LLM, random score, or name similarity can decide identity or queue priority.
2. A conflict between strong identifiers (`email`, `phone`, `customer_id`, or `order_id`) always blocks automatic linking.
3. A review row may describe only evidence, conflicts, identifiers, timestamps, and actions that the backend has actually persisted or deterministically derived.
4. Visible synthetic data remains separate from `data/truth/`; runtime code must never read hidden truth data.
5. Do not change the review threshold merely to make the screen look cleaner. First measure the outcome mix and fix the data/scenario mix deliberately.
6. `reject_link` and `create_profile` remain different audited outcomes.

## 3. Confirmed technical causes

| Observation | Current implementation cause | Effect on the screen |
|---|---|---|
| Repeated score `50` | `device_id` has weight `45`; a moderate match adds `5`; the review threshold is `50`. | Device-only candidates repeatedly enter review. |
| Repeated evidence text | Evidence is rendered as a string such as `Same device id matches the profile.` | Operators cannot immediately see evidence type, weight, or competing candidates. |
| Only one candidate shown | `GET /api/reviews` projects only the highest-scoring candidate. | A true tie or alternative cannot be understood in the queue. |
| No queue class or priority | The API returns generic `reason` text and raw `conflicts`; it returns no structured review class or priority. | The frontend cannot truthfully offer “critical conflict” versus “incomplete evidence” filters. |
| Near ties cannot exist for moderate IDs | `profile_identifiers` currently has a global unique constraint on `(type, value)`, including `device_id` and `session_id`. | Two profiles cannot share a device/session, so deterministic ambiguous moderate-identifier scenarios are impossible. |
| Queue composition is uncontrolled | The data generator targets 5–10 review candidates, but a dirty/local ingest history can produce many more pending rows. | The demo queue drifts away from the intended curated mix. |

## 4. Target operational mix

The first useful demo and local-development queue should contain **3–7 pending cases**, not 63. It should include the following truthfully generated case kinds.

| Case kind | Deterministic evidence | Expected outcome | Queue treatment |
|---|---|---|---|
| Strong identifier conflict | Two strong identifiers resolve to different existing profiles. | `review_required`; auto-link blocked. | `critical`; always first; show conflict fields and both candidate profiles. |
| Ambiguous moderate match | A shared device or session retrieves two profiles with equal/near-equal deterministic scores. | `review_required`; no strong identifier decides it. | `high`; show each candidate and the tie reason. |
| Incomplete evidence | One moderate identifier retrieves one profile, but strong identifiers are missing. | `review_required` at the existing policy threshold. | `standard`; show evidence weight and what is missing. |
| Same-name collision safety story | A name/city-only record has the same normalized name as an existing profile, but no retrieved identifier candidate. | `review_required`; no candidate is suggested or linkable. | `standard`; make the safe choice explicit: create a separate profile or reject the case. |

The curated queue must include at least one strong conflict and one incomplete-evidence case. It may include one same-name collision story. Case labels must be derived from the resolver result; the generator must not write a label that runtime code blindly trusts.

This resolves a current documentation/code mismatch: the present resolver creates a profile when no identifier candidate exists, while the Aarav demo narration expects a safe human-review story. The intended policy is to route only an explicitly detected **same-name collision** to review, with no suggested candidate and no approval action. Name equality remains a routing safeguard, never matching evidence and never a link recommendation.

## 5. Staged implementation plan

### Phase 0 — Baseline and composition audit (no schema change)

**Goal:** prove why records are pending before changing behavior.

1. Add a read-only diagnostic query/service that groups pending `MatchDecision` records by:
   - channel;
   - `score`;
   - whether `conflicts` is empty;
   - matched evidence field names; and
   - normalized decision reason.
2. Record the result in a test fixture or checked-in diagnostic example. Do not commit live customer-like payloads beyond the synthetic dataset.
3. Reset the local demo only through the existing deterministic reset path, reload the frozen data, and compare the resulting pending count with the generator target of 5–10.
4. Identify whether the excess cases come from a dirty database, a seed-generation defect, or a resolver-policy defect.

**Exit criterion:** the team can explain every pending case category and reproduce the count from an empty local database.

### Phase 1 — Deterministic review-case fixtures

**Goal:** generate useful variety without weakening matching safety.

1. Add explicit synthetic scenario constructors to `backend/scripts/generate_synthetic_data.py` (or a small adjacent review-fixture module):
   - one email/phone strong conflict;
   - one customer-ID/email strong conflict;
   - one incomplete-evidence device case; and
   - one shared-moderate-identifier tie after Phase 3.
2. Keep source envelopes channel-authentic: web/mobile can contain device/session; call centre can contain phone/email; store events can contain order/customer references when appropriate.
3. Add expected **review-case categories** to offline evaluation data only. Do not expose `expected_outcome` or hidden truth IDs at runtime.
4. Add a deterministic integration test that ingests the fixture set into a clean database and asserts the exact review mix.
5. Before exposing a conflict case as actionable, enforce the selected safety policy in `resolve_review`: `approve_link` against a decision with non-empty `conflicts` returns `409`; `reject_link` and `create_profile` remain audited.

**Exit criterion:** a clean seeded database produces 3–7 pending reviews with at least one conflict and at least two distinct review classes.

### Phase 2 — Versioned review queue read model (API first)

**Goal:** give the frontend truthful information to render varied rows and a rich detail drawer.

Keep the existing `GET /api/reviews` response frozen for current clients. Add a new additive endpoint, `GET /api/review-queue`, for the richer operations read model. Update `docs/05_API_CONTRACT.md`, Pydantic schemas, and frontend types together in the same contract PR.

The endpoint may initially assemble data from `MatchDecision`, `CanonicalEvent`, `CustomerProfile`, and `ReviewAction`; it does not require a new table.

Proposed endpoint:

```text
GET /api/review-queue?limit=20&cursor=<opaque>&status=pending&channel=call_center&kind=strong_identifier_conflict&priority=critical
```

Proposed response fields (names may be adjusted during contract review):

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
        "customer_name": "Aarav Patel",
        "occurred_at": "2026-09-20T08:00:00Z"
      },
      "candidates": [
        { "profile_id": "uuid", "display_name": "Aarav Patel", "score": 90, "matched_fields": ["email"] },
        { "profile_id": "uuid", "display_name": "Aarav Patel", "score": 85, "matched_fields": ["phone"] }
      ],
      "evidence": [
        { "field": "email", "result": "exact_match", "weight": 90, "message": "Same email matches the profile." }
      ],
      "conflicts": [
        { "fields": ["email", "phone"], "message": "Email and phone resolve to different profiles." }
      ],
      "missing_strong_identifiers": ["customer_id"],
      "reason_code": "strong_identifier_conflict",
      "reason": "Strong identifiers point to different profiles; a human must decide."
    }
  ],
  "next_cursor": "opaque-or-null",
  "total": 4,
  "summary": {
    "pending": 4,
    "critical_conflicts": 1,
    "incomplete_evidence": 2
  }
}
```

Rules for the read model:

- `review_kind` and `priority` are computed server-side from persisted evidence/conflicts, never supplied by the client.
- The initial executable classifier is:
  1. `strong_identifier_conflict` when `conflicts` is non-empty; priority `critical`.
  2. `ambiguous_moderate_match` when there is no conflict, at least two candidates are within `TIE_DELTA`, and the tied candidates are retrieved only through `device_id` and/or `session_id`; priority `high`.
  3. `same_name_collision` when the explicit safe-routing rule detects a normalized-name collision but identifier retrieval returns no candidate; priority `standard`; `candidates=[]`.
  4. `incomplete_evidence` when there is no conflict, exactly one candidate is retrieved only through moderate evidence, and the score is within the review range; priority `standard`.
- Stable default ordering is `priority_rank DESC`, `MatchDecision.created_at ASC`, then `MatchDecision.id ASC`. The opaque keyset cursor encodes those three values and the active filter set.
- Valid parameters are `limit=1..100` (default `20`), `status=pending` (only supported status initially), the documented channel enum, `kind` from the four classifier values, and `priority` from `critical|high|standard`. Invalid values return the shared 422 response.
- `summary` is always calculated over the **same filtered pending result set**, before the cursor is applied. It is never a front-end invented metric.
- A resolution removes its row from later cursor pages. After any successful resolution the client discards the cursor, refetches the first page and summary, and never attempts to preserve an old page position.
- Expose safe field names and evidence weights, not unmasked raw identifier values.
- `resolved today` and `average review time` are deferred until they are calculated from `ReviewAction.created_at` and `MatchDecision.created_at`, with defined timezone and inclusion rules.

**Exit criterion:** every visual queue label, filter, and summary is backed by a documented response field and API test.

### Phase 3 — Identifier uniqueness migration for real moderate-ID ambiguity

**Goal:** permit a shared device or session to produce a safe review case, while retaining hard uniqueness for strong identifiers.

Current database behavior forbids every `(identifier.type, identifier.value)` pair from appearing on more than one profile. That is too strong for devices and sessions, which can be shared, recycled, or ambiguous.

Create an append-only Alembic migration that:

1. Removes the global `uq_profile_identifiers_type_value` constraint.
2. Adds a partial unique index for only `email`, `phone`, `customer_id`, and `order_id`.
3. Adds non-unique lookup indexes for `device_id` and `session_id`.
4. Verifies existing rows before applying; fail safely if pre-existing strong-identifier duplicates are found.
5. Changes the SQLAlchemy `ProfileIdentifier` model to match the new database invariants.
6. Changes identifier persistence/upsert logic so `device_id` and `session_id` may be attached to more than one profile, while a strong identifier remains rejected if it already belongs to another profile.

Do **not** make strong identifiers non-unique. Existing conflict detection assumes a strong identifier has one owner; this migration preserves that invariant.

After the migration, extend candidate retrieval so one shared moderate ID can retrieve multiple candidate profiles. The existing resolver will then classify equal/near scores as `review_required` through its tie policy. Add tests for profile creation, auto-linking, and all three review-resolution paths before changing the seed data.

**Exit criterion:** shared `device_id`/`session_id` fixtures produce review-required ties, while duplicate email/phone/customer ID/order ID writes are rejected.

### Phase 4 — Persisted review classification only if the read model needs history

**Goal:** avoid premature schema changes.

Start by deriving `review_kind` and priority from immutable `MatchDecision.evidence`, `conflicts`, `candidates`, `score`, and `created_at`. Add new `match_decisions` columns only if a historical, policy-versioned classification is required:

```text
review_kind        varchar/enum, nullable during backfill
priority           varchar/enum, nullable during backfill
policy_version     varchar, nullable during backfill
```

If added, populate them when the decision is created, backfill deterministically, index `(outcome, review_status, priority, created_at)`, and document the policy version. Do not add an extra table merely to decorate the queue.

**Exit criterion:** the schema stores only facts or versioned policy outputs that cannot be safely recomputed.

## 6. Tomorrow's task board

| Order | Task | Owner | Validation |
|---:|---|---|---|
| 1 | Add pending-review composition diagnostic and clean-seed integration test. | Backend/data | `pytest` proves reproducible mix. |
| 2 | Decide the canonical 3–7 review-case fixture mix and add it to the deterministic generator. | Data + backend reviewer | Generator remains deterministic; hidden truth stays isolated. |
| 3 | Enforce the strong-conflict resolution policy (`approve_link` returns 409) and test it. | Backend | Conflict cannot link; reject/create-profile audit paths remain valid. |
| 4 | Write the additive `GET /api/review-queue` cursor/filter/read-model contract and example; keep `GET /api/reviews` compatible. | Backend + frontend reviewer | Pydantic/API tests; frontend type update. |
| 5 | Add structured candidate/evidence/conflict fields to the endpoint. | Backend | Contract test includes conflict and incomplete-evidence cases. |
| 6 | Add the partial-uniqueness migration for moderate IDs, only after Task 1 proves it is needed. | Backend | Clean migration, strong-identifier duplicate tests, tie test. |
| 7 | Replace frontend local derivations with the new API fields and render a dense table/detail view. | Frontend | Typecheck, lint, desktop/tablet/mobile screenshots. |

Keep each task in its own commit/PR. Do not combine the database migration with the visual redesign.

## 7. Test matrix

| Test | Expected result |
|---|---|
| Device-only candidate | Remains a deterministic incomplete-evidence review if its score meets threshold. |
| Strong email/phone conflict | Review required, `priority=critical`, automatic linking blocked, and an attempted `approve_link` returns 409. |
| Shared device across two profiles | Both candidates returned; tie produces review required; create/link/review flows preserve the intended identifier ownership policy. |
| Duplicate strong identifier insertion | Database rejects it after the partial-unique migration. |
| Name/city only | Does not retrieve candidates and never auto-links. |
| Review queue ordering | Conflict first, then defined priority, then oldest creation time. |
| Review resolution | Audit row written; approve/reject/create-profile behavior remains unchanged and safe. |
| Fresh seed | Pending count and review-kind mix meet target exactly. |
| API pagination/filter | Stable keyset order and no duplicate row across a static queue; after a resolution the client restarts at the first cursor page. |
| Runtime isolation | Resolver and API never read `data/truth/`. |

## 8. Acceptance criteria

This work is complete only when:

- a fresh deterministic seed produces a small, varied queue;
- every visible case is explainable from stored evidence;
- the backend exposes enough structured data for a truthful dense queue and detail view;
- moderate identifier ambiguity is supported without weakening strong-identifier uniqueness;
- the Riya merge and Aarav non-merge golden paths still pass;
- all new migrations, resolver rules, services, and endpoints have targeted pytest coverage; and
- the final screen does not depend on fictional SLA, CRM, loyalty, payment, or agent data.

## 9. Deferred decisions

These require an explicit product decision before implementation:

1. The plan chooses **no approval action for a strong conflict**. The backend must reject `approve_link` with a 409 for any decision with conflicts, even if a client submits an arbitrary profile ID. `reject_link` and `create_profile` remain available and audited. A future second-reviewer workflow would be a new product decision.
2. The curated demo seed has a target of **3–7** pending rows. The full operations generator retains the existing **5–10** review-candidate target. They are separate datasets/seed modes and must not be mixed in one demo reset.
3. Non-conflict priority is fixed for this first version: moderate-ID tie = `high`; incomplete evidence = `standard`; same-name collision = `standard`.
4. Whether review-age/SLA metrics are product requirements. If yes, define the calculation, business timezone, and paused states before adding a column or card.
