# Pipeline Event Narrative and Variety Plan

**Status:** Planned — no runtime behavior changes are authorized by this document alone  
**Created:** 2026-09-20  
**Audience:** Backend, synthetic-data, frontend, QA, and demo owners  
**Depends on:** `docs/16_DATA_PIPELINE_READ_MODEL_PLAN.md`; uses the safe event-context work proposed in `docs/14_CUSTOMER_AND_JOURNEY_DATA_VARIETY_PLAN.md`  
**Related:** `docs/04_DATA_IDENTITY_AND_RULES.md`, `docs/05_API_CONTRACT.md`, `docs/07_TESTING_EVALUATION_AND_DEMO.md`, and `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md`

## 1. Decision and problem statement

The Data Pipeline is an operator-facing record of what the system received and decided. It must not look like a table of interchangeable source IDs, identical timestamps, and generic labels.

The current screenshot is truthful but hard to read as an operational story:

| Visible field | Current behavior | Why it feels generic |
|---|---|---|
| `Received` | A demo reset ingests the fixture files in a short batch, so many rows share nearly the same receipt time. | The table hides the meaningful business sequence in `occurred_at`. |
| Event type | The list renders only a broad enum label such as **Store visited** or **Support contacted**. | It omits the already persisted, safe categorical context that distinguishes a refund follow-up from an ordinary contact. |
| Profile | The list shows a shortened UUID. | The value is opaque and largely repeats information already communicated by the identity-outcome badge. |
| Canonical attributes | `store_city` and the controlled support-note values are present in source/canonical data but excluded from the list read model. | This is correct for privacy, but the product has no deliberate safe summary in their place. |
| Reset composition | `reset_demo` loads each channel file as a block. | The newest received records can cluster by channel and event type even when the synthetic dataset itself contains varied journeys. |

This plan changes the projection and presentation, not identity, normalization, raw preservation, or the underlying events. A generic row must become a concise statement of a persisted fact; it must never become a fabricated customer story.

## 2. Outcome

After implementation, a row can answer four operator questions at a glance:

1. **When did it happen?** Show business occurrence time as the primary clock and receipt/processing time as explicit secondary facts.
2. **What happened?** Show a deterministic, event-type-specific narrative assembled only from allowlisted canonical fields.
3. **What did the pipeline decide?** Preserve the processing and identity outcomes with plain-text labels, not colour alone.
4. **Where can I verify it?** Keep the source ID and an inspector action; raw payload, full identifiers, evidence, and full attributes remain on deliberate inspection only.

Examples of the intended density:

| Persisted fact | List-safe narrative |
|---|---|
| `return_requested` with an order reference | **Return requested** · Order reference recorded |
| `support_contacted` with normalized reason `refund_not_received` | **Support contact** · Refund not received |
| `support_contacted` with normalized reason `return_status` | **Support contact** · Return-status follow-up |
| `store_visited` with an order reference | **Store visit** · Order reference recorded |
| `refund_completed` with an order reference | **Refund completed** · Order reference recorded |
| failed raw record | **Not normalized** · Validation failed |

The list does **not** show an order ID, full city, free-form support note, email, phone, customer name, raw payload, candidate evidence, or a generated explanation. Those are either restricted data or facts that the list does not need.

## 3. Non-negotiable rules

1. Raw payloads stay immutable and the pipeline continues to read persisted `RawEvent`, `CanonicalEvent`, and `MatchDecision` records only.
2. No LLM, template completion service, or frontend guess writes event copy. Each narrative is a deterministic mapping with tests.
3. Runtime APIs, the generator, and presentation mappers never read `data/truth/`.
4. List rows remain list-safe. A narrative cannot expose identifiers, arbitrary attributes, raw notes, candidates, evidence values, or internal processing errors.
5. Existing pipeline cursor ordering remains `(received_at, raw_event_id)` and its high-water polling semantics remain unchanged. A more meaningful displayed clock must not silently change pagination correctness.
6. `occurred_at`, `received_at`, and canonical `created_at` remain separately labelled. Canonical `created_at` is insertion time, not a duration claim.
7. Failed rows remain null-honest: no canonical event, identity outcome, profile, or fabricated narrative beyond the stable processing error code/category.
8. The existing inspector remains the sole deliberate-disclosure surface for raw and normalized JSON.
9. New fields are additive API contract changes. Current consumers of `/api/pipeline/overview`, `/events`, and `/updates` keep working.

## 4. Current-state audit before changes

Before changing a response or UI, add a deterministic diagnostic/test fixture that measures the current projection against a clean demo reset:

- count the newest 25 rows by channel and `event_type`;
- count distinct `received_at` seconds/minutes in that same page;
- count rows with an order reference, recognized support context, and recognized store context;
- assert that no existing list row exposes raw `attributes`, identifiers, evidence, or full processing-error text; and
- compare the same records by `received_at` and `occurred_at` so the team can see whether repetition is a seed-composition issue, a reset-order issue, or a presentation issue.

The diagnostic is test-only or a local development script. It must not create scenario labels or quality scores in runtime tables.

### Task 1 audit result — 2026-09-20

The read-only diagnostic ran against the current local pipeline snapshot with a 25-row window:

- 20 physical-store rows, 2 mobile-app rows, 2 web rows, and 1 call-centre row;
- 19 `store_visited` rows, 3 `product_viewed` rows, 2 `support_contacted` rows, and 1 `return_requested` row;
- 6 distinct receipt-time seconds but 25 distinct business occurrence-time seconds;
- 22 rows with an order reference, 19 with a valid store-context signal, and no recognized support-note signal in that newest window.

The screenshot is therefore primarily a reset/receipt-order and projection problem, not missing business-time variety. Task 6 remains conditional: the reset ingestion order may change only after the narrative fields and UI clock treatment are in place and a representative-window test proves it helps.

## 5. Presentation contract

### 5.1 Additive list model

Add a small, list-safe projection to `PipelineEventOut`. Every endpoint that returns a pipeline row—overview, paginated events, and polling updates—uses this same projection through `pipeline_read_model.py`.

```json
{
  "event_summary": {
    "title": "Support contact",
    "detail": "Refund not received",
    "kind": "support_refund_follow_up"
  },
  "has_order_reference": true
}
```

`event_summary` is nullable only when no canonical event exists. `has_order_reference` is nullable for failed rows and otherwise represents only the presence of a canonical order reference; it never returns the value.

The UI may omit `kind` from visible copy, but it is a stable typed field for accessible icons, filtering in a future contract, and tests. It is not a hidden business classification or a scenario label.

### 5.2 Allowed summary mapping

Create one pure backend mapper, for example:

```text
app/services/event_presentation.py
```

It receives canonical event type, canonical entity references, and a narrow, normalized presentation context. It returns only the fields above.

| Canonical event type | `title` | Permitted detail | `kind` |
|---|---|---|---|
| `product_viewed` | Product viewed | `null` | `product_view` |
| `app_login` | Mobile app sign-in | `null` | `app_sign_in` |
| `order_placed` | Order placed | `Order reference recorded` when present | `order_placed` |
| `return_started` or `return_requested` | Return requested | `Order reference recorded` when present | `return_requested` |
| `support_contacted` + `refund_not_received` | Support contact | `Refund not received` | `support_refund_follow_up` |
| `support_contacted` + `return_status` | Support contact | `Return-status follow-up` | `support_return_status` |
| `support_contacted` + no/other recognized reason | Support contact | `null` | `support_contact` |
| `store_visited` | Store visit | `Order reference recorded` when present | `store_visit` |
| `refund_completed` | Refund completed | `Order reference recorded` when present | `refund_completed` |
| supported but otherwise unmapped type | Existing humanized event-type label | `null` | `other` |

The mapper never accepts a raw `attributes` dictionary. Its only contextual inputs are:

- canonical order-reference presence; and
- a `contact_reason` enum derived by the normalizer from an exact allowlist.

The implementation should share, rather than duplicate, the normalization/allowlist mapping proposed by document 14. In particular, `Refund not received` and `Second follow-up` become the bounded values `refund_not_received` and `return_status`; free-form notes become `other` or null and never reach the list.

`store_city` may remain available to the Journey Detail projection defined in document 14, but it is deliberately excluded from this dense pipeline list. The pipeline's job is traceability, not a customer-location directory.

### 5.3 Stable error presentation

For a failed raw row, return no `event_summary`. The frontend uses the existing stable `processing_error_code` to render a fixed local label such as **Not normalized · Validation failed**. It must not render the raw processing error, and it must not claim that a missing canonical event had a business type.

## 6. Pipeline UI plan

### 6.1 Event stream columns

Replace the dense, repetitive table emphasis with the following factual hierarchy:

| Column | Primary content | Secondary content |
|---|---|---|
| Occurred | `occurred_at` in the user timezone | `Received` / `Processed` timestamps in a tooltip or compact detail line, labelled explicitly |
| Source | Source event ID | Recorded channel badge |
| What happened | `event_summary.title` | `event_summary.detail`, when non-null |
| Processing | Existing status and stable error code | No colour-only status |
| Identity decision | Existing outcome label | Score only where the existing contract makes it meaningful; pending review stays explicit |
| Inspect | Deliberate inspector action | — |

Remove the opaque shortened profile UUID from the default table. The identity-outcome badge already expresses whether an existing profile was linked, a new profile was created, or human review is required. The selected profile UUID remains available in the inspector's identity tab for an operator who needs that record-level detail.

The source table still sorts and paginates by receipt time. The heading must say **Newest received events first**, while each row makes the separate occurrence time visible. This is important after a batch reset: a user can see that records were loaded together without mistaking that shared receipt time for customer activity happening simultaneously.

### 6.2 Batch-reset clarity

Do not invent a “live” badge or pretend that a reset replayed production traffic. When the page is populated by a synthetic reset, the existing snapshot timestamp and the displayed clocks are sufficient evidence.

Improve fixture loading only if the audit proves reset file order makes the newest page needlessly one-dimensional:

1. parse all visible raw fixture envelopes;
2. retain the original envelope unchanged;
3. choose an explicitly documented deterministic ingestion order; and
4. verify the full reset has the same accepted, failed, duplicate, identity, and alert outcomes as before.

Interleaving file reads is not itself a product feature. It is allowed only to make a deterministic demo reset representative of the already generated cross-channel data. It must not alter business `occurred_at`, source IDs, raw payloads, or hidden-truth separation.

### 6.3 Inspector continuity

The inspector header and tabs remain raw-ID-safe. Add the same `event_summary` near the top as a convenience label, then retain the existing Decision, Canonical, and Raw tabs as the evidence source. The displayed label must be derived from the response, never reconstructed differently in the browser.

## 7. Data and normalization work

The generator already includes structured examples that can make narratives specific without adding fictional fields:

- Riya's `support_contacted` events have `Refund not received` and `Second follow-up` source notes;
- `store_visited` events carry `store_city` and may carry an order reference;
- return, order, and refund events carry an order reference when applicable; and
- invalid records exercise the failed/null branch.

The first implementation slice should not add arbitrary prose to fixture files. Instead:

1. normalize the two existing, recognized support-note values into the bounded `contact_reason` enum;
2. preserve all original raw note text only in the raw payload;
3. make the presenter consume the bounded enum; and
4. add scenario fixtures only when an existing event type lacks a testable allowed-context case.

If the enum belongs on `CanonicalEvent`, add an append-only migration and backfill only recognized values. If it remains within canonical JSON attributes, use a single typed accessor and validate its exact values. The implementation decision must be recorded in `docs/05_API_CONTRACT.md` and tested in both choices.

## 8. API, test, and frontend handoff

| Consumer | Backend guarantee | Frontend behavior |
|---|---|---|
| Overview/event/update rows | Every canonical row has one deterministic safe summary; failed rows have null summary and stable error code. | Render the server summary directly; do not make per-component label guesses. |
| Filtered pages and polling | The same summary mapper is used before pagination, after filtering, and during high-water drain. | Merged poll rows look identical to initial rows. |
| Inspector | Summary matches the selected raw-event response and IDs retain raw/canonical distinction. | Use response copy once; raw/canonical JSON stays on explicit tabs. |
| Synthetic reset | Existing source rows and outcomes remain deterministic. | Clearly show separate occurred and received clocks; do not claim an activity burst is a live customer burst. |

Required automated proofs:

1. Each mapping-table event type returns exactly the expected title, detail, kind, and order-reference boolean.
2. Unknown/free-form notes cannot appear in the API response or DOM; they map to the generic bounded support category.
3. A failed raw event returns `event_summary: null`, no canonical/identity fields, and a stable error label.
4. Overview, a filtered events page, and an updates response produce byte-equivalent summary fields for the same raw event.
5. Keyset pagination and the 101-event high-water burst test continue to lose and duplicate no rows.
6. The table shows the occurrence clock and labels receipt/processing clocks correctly even when all records were received in the same batch.
7. A reset's counts, duplicates, review cases, and alert outcomes remain unchanged before and after any documented ingestion-order adjustment.
8. Frontend typecheck, lint, production build, desktop/tablet/mobile visual checks, and keyboard inspector checks pass.

## 9. Implementation order

| Order | Task | Primary files | Exit condition |
|---:|---|---|---|
| 1 | Run the clean-reset composition/clock audit and freeze the exact safe summary examples. | `backend/tests/`, local diagnostic | Done: aggregate audit and list-safety test added; current local composition recorded above. |
| 2 | Add the bounded `contact_reason` normalization/accessor and its migration only if a typed column is chosen. | normalizer, models/migration, tests | Recognized notes are normalized; raw notes remain preserved and unexposed. |
| 3 | Add the pure shared event-presentation mapper and unit tests. | `app/services/event_presentation.py` | Mapping table and null/error behavior pass without a database. |
| 4 | Add additive pipeline schema fields and use the mapper from the one read-model seam. | `schemas/pipeline.py`, `services/pipeline_read_model.py`, route tests | Overview, list, updates, and detail agree on one summary. |
| 5 | Update the pipeline table and inspector hierarchy. | `frontend/components/pipeline/` | Occurred time and specific safe narrative are visible; UUID column is removed from the default table. |
| 6 | Adjust deterministic reset ingestion order only if Task 1 proves it is needed. | `services/demo.py`, reset tests | Representative newest page; no outcome/count regression. |
| 7 | Add browser and accessibility coverage; rerun the Riya demo. | frontend tests/demo runbook | Specific pipeline rows appear during the six-step story without raw-data leakage. |

## 10. Scope boundary

This plan does not authorize:

- names, emails, phone numbers, addresses, cities, order IDs, spend, tickets, agents, SLAs, payment status, or raw notes in the pipeline list;
- LLM-generated narratives, inferred emotions, inferred causes, or estimated processing durations;
- a new search/filter over free text, identifiers, or raw attributes;
- changes to deterministic identity decisions, conflict protections, or journey-rule truth;
- dashboard/Customer Explorer work already planned in documents 14 and 15; or
- a new seed-data system or scenario labels in runtime data.

The result should feel substantially less generic because the existing data is presented with useful, typed context—not because the product has been decorated with unverified detail.

## 11. Acceptance checkpoint

The work is ready for review when a clean reset plus the Riya demo shows, in the pipeline stream:

1. a clearly labelled business occurrence time distinct from batch receipt time;
2. a return request, a refund-not-received support contact, a return-status follow-up, and a store visit that are visibly different but backed only by persisted fields;
3. one failed row with honest null behavior;
4. an explicit pending-review or new-profile row when present;
5. consistent summaries in overview, pagination, polling, and inspector; and
6. no leaked raw notes, full identifiers, or hidden-truth data.
