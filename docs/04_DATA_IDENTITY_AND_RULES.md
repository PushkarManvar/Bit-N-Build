# JourneyLens Data, Identity Resolution, and Journey Rules

**Version:** 1.0  
**Purpose:** Make the core mechanism implementable, explainable, and testable.  
**Change note (Phase 0 freeze):** channel enum renamed to `call_center`; identity outcome `review_required` → `review_required`; the wire event envelope is frozen in `docs/05_API_CONTRACT.md` (`identifiers`, `entity_references`, `attributes`). This document is the matching-rule spec and is refined during Gate G2.

## 1. Canonical event model

Every source adapter must produce this logical structure (frozen wire shape in `docs/05_API_CONTRACT.md`):

| Field | Type | Required | Notes |
|---|---|---|---:|
| `channel` | enum | Yes | `web`, `mobile_app`, `call_center`, `physical_store` |
| `event_type` | enum | Yes | Frozen `EventType` vocabulary |
| `occurred_at` | timestamp | Yes | UTC |
| `identifiers` | array of `{type, value}` | Yes | Normalized strong/moderate identifiers |
| `entity_references` | object | Yes | e.g. `order_id`; uppercase normalized |
| `attributes` | JSON object | Yes | Free-form source fields, e.g. `customer_name`, `city` |

Identifier types (frozen): `email`, `phone`, `device_id`, `session_id`, `customer_id`. Order references live in `entity_references.order_id` and are treated as a strong identifier for matching.

## 2. Source mappings

### Web

| Source field | Canonical field |
|---|---|
| `event`, `type` | `event_type` |
| `timestamp` | `occurred_at` |
| `deviceId` | `device_id` |
| `sessionId` | `session_id` |
| `order_id` | `order_id` |

### Mobile app

| Source field | Canonical field |
|---|---|
| `action` | `event_type` |
| `createdAt` | `occurred_at` |
| `email_address`, `userEmail` | `email` |
| `device` | `device_id` |
| `orderNumber` | `order_id` |
| `customerName` | `customer_name` |

### Call centre

| Source field | Canonical field |
|---|---|
| `reason` | `event_type` |
| `callTime` | `occurred_at` |
| `caller_email` | `email` |
| `caller_phone` | `phone` |
| `order_ref` | `order_id` |
| `caller_name` | `customer_name` |
| `notes` | `attributes.notes` |

### Physical store

| Source field | Canonical field |
|---|---|
| `activity` | `event_type` |
| `transaction_time` | `occurred_at` |
| `phoneNumber` | `phone` |
| `return_order` | `order_id` |
| `customer` | `customer_name` |
| `store_city` | `city` |

## 3. Normalization rules

### Email

- Trim leading/trailing whitespace.
- Convert to lowercase.
- Reject as unusable if basic structure is absent.
- Preserve the original value only in the raw payload.

Example: ` RIYA.SHAH@EXAMPLE.COM ` → `riya.shah@example.com`

### Phone

- Remove spaces, hyphens, parentheses, and punctuation.
- For a 10-digit Indian number, add `+91`.
- For a 12-digit number beginning with `91`, add `+`.
- Do not invent missing digits.
- Store unusable input in attributes and return `null` canonical phone.

Example: `98765 43210` → `+919876543210`

### Order ID

- Trim.
- Uppercase.
- Remove spaces.
- Convert underscore separators to hyphens.

Example: `ord 204` → `ORD-204`

### Name

- Trim.
- Lowercase for comparison.
- Collapse repeated whitespace.
- Preserve a display-friendly version separately if desired.
- Do not remove meaningful tokens simply to force similarity.

Example: `Riya  Shah` → `riya shah`

### Event type

| Raw value | Canonical value |
|---|---|
| `return_initiated` | `return_started` |
| `return_request` | `return_requested` |
| `refund_pending` | `refund_status_checked` |
| `refund_not_received` | `support_call` |
| `customer_call` | `support_call` |
| `order_confirmed` | `order_placed` |
| `checkout_begin` | `checkout_started` |

Unknown event types may be accepted as `other` with the raw value in attributes, or rejected by a strict adapter. Choose one policy and test it consistently; for the MVP, accepting as `other` is safer for raw-data preservation.

## 4. Identity graph

A profile owns identifiers. Events supply identifiers. Candidate retrieval looks for profiles owning the normalized values present in the incoming event.

### Strong identifiers

- `customer_id`
- `order_id`
- verified `email`
- normalized `phone`

### Moderate and weak identifiers

- `device_id`
- `session_id`
- customer name
- city

Strong identifiers can justify auto-linking if they agree. Weak identifiers help bridge or rank candidates but do not override conflicts.

## 5. Candidate retrieval

1. Search `profile_identifiers` for every non-null strong and weak identifier.
2. Create one candidate entry per matching profile.
3. Record which fields retrieved each candidate.
4. If no exact candidate exists, optionally use fuzzy name search to produce review candidates.
5. Do not calculate final outcomes during retrieval.

### Candidate structure

```json
{
  "profile_id": "uuid",
  "retrieved_by": ["order_id", "phone"],
  "evidence": [],
  "conflicts": [],
  "score": 0
}
```

## 6. Evidence scoring

| Evidence | Weight | Category |
|---|---:|---|
| Same customer ID | 100 | Strong |
| Same order ID | 95 | Strong |
| Same verified email | 90 | Strong |
| Same normalized phone | 85 | Strong |
| Same device ID | 45 | Moderate |
| Same session ID | 35 | Moderate |
| Name similarity ≥92 | 20 | Weak |
| Name similarity 85–91 | 15 | Weak |
| Same city | 5 | Weak |

### Score policy

- The final score is capped at 100.
- Multiple strong matches increase explanation strength, not an unbounded numeric total.
- A direct strong match establishes a base score equal to its strongest weight.
- Supporting evidence may raise the score up to 100.
- Weak evidence alone cannot produce a score of 80.
- A strong conflict overrides the score and forces review.

### Suggested deterministic calculation

1. Find the highest matching evidence weight.
2. Add at most 10 points for an additional agreeing strong identifier.
3. Add at most 5 points for moderate support.
4. Add at most 5 points for weak support.
5. Cap at 100.
6. If any strong conflict exists, label the outcome `review_required`.

This policy keeps the user-facing score understandable and avoids misleading values such as 270.

## 7. Conflict rules

Create a strong conflict when:

- email belongs to one profile and phone belongs to another;
- order belongs to one profile and verified email belongs to another;
- explicit customer ID disagrees with another strong identifier;
- a proposed merge would combine two different non-null verified emails or phones in a known collision fixture.

Conflict behavior:

1. Do not auto-link.
2. Persist all conflicting evidence.
3. Route to review.
4. Do not add new identifiers to a profile before review resolution.

## 8. Identity decision algorithm

```text
normalize event
retrieve exact candidates

if no candidates:
    create new profile
else:
    score each candidate
    detect strong conflicts across candidates and event
    rank candidates by score

    if any strong conflict:
        manual review
    else if best score >= 80:
        auto-link to best candidate
    else if best score >= 50:
        manual review
    else:
        create new profile

persist candidates, evidence, conflicts, score, thresholds, and outcome
```

### Tie policy

If the top two candidates are within five points and neither has uniquely decisive evidence, route to manual review.

### Name policy

Name similarity may retrieve or rank candidates. It may never produce `auto_linked` without a non-name identifier.

## 9. Flagship expected decisions

| Event | Evidence | Expected outcome |
|---|---|---|
| Anonymous web return | `DEV-17`, possibly `ORD-204` | New/anonymous profile container |
| Riya mobile status check | email + `DEV-17` + `ORD-204` | Auto-link; bridge prior web event |
| Riya support call | phone + `ORD-204` | Auto-link |
| Riya store return | phone + `ORD-204` | Auto-link |
| Aarav with same name/city only | weak name/city | Review or new profile; never auto-link |
| Email points to A, phone to B | strong conflict | manual review |

## 10. Journey rules

### Rule JR-001 — Unresolved refund

**Inputs:** Profile and order events.  
**Create alert when:**

- at least one return lifecycle event exists;
- no `refund_completed` event exists; and
- at least two support-related events exist.

**Output:** `unresolved_refund`, high severity.  
**Deduplication key:** profile + order + type + open status.

### Rule JR-002 — Repeat contact

**Create alert when:** At least two `support_call`, `support_ticket_created`, or `refund_status_checked` events occur within 72 hours for the same profile/order.

**Output:** `repeat_contact`, medium severity.

### Rule JR-003 — Channel switching

**Stretch rule:** At least three distinct channels occur within 48 hours.

**Output:** `channel_switching`, medium severity.

### Rule JR-004 — Checkout drop-off

**Stretch rule:** `checkout_started` has no later `order_placed` within 24 hours.

**Output:** `journey_dropoff`, low severity.

## 11. Synthetic dataset

### Visible source files

```text
data/raw/web_events.jsonl
data/raw/mobile_events.jsonl
data/raw/call_center_events.jsonl
data/raw/store_events.jsonl
```

### Hidden truth files

```text
data/truth/customers_truth.csv
data/truth/event_truth.csv
data/truth/expected_matches.csv
data/truth/expected_alerts.csv
```

Truth IDs must never be accepted by ingestion or exposed in normal UI responses.

### Dataset composition

- 30–40 customers
- 180–250 source events
- 3–5 invalid records
- 3–8 duplicate records
- 5–10 manual-review candidates
- 5 broken journeys
- 2–3 same-name collision cases
- 5–8 anonymous-to-known transitions

## 12. Required automated test cases

| ID | Test | Expected result |
|---|---|---|
| ID-01 | Same normalized email | Auto-link |
| ID-02 | Same phone with different formatting | Auto-link |
| ID-03 | Same order and phone | Auto-link with both evidence items |
| ID-04 | Same device then verified email | Anonymous event joins known profile |
| ID-05 | Same name only | No auto-link |
| ID-06 | Same name and city only | Review or new profile |
| ID-07 | Email/phone point to different profiles | manual review |
| ID-08 | Duplicate source record | Existing result returned |
| ID-09 | Top candidates nearly tied | manual review |
| JR-01 | Return + two contacts + no completion | One unresolved alert |
| JR-02 | Add refund completion | No new unresolved alert; existing state resolved if implemented |
| JR-03 | Run analyzer twice | No duplicate open alert |
| JR-04 | Two relevant contacts in 72 hours | One repeat-contact alert |

## 13. Data definition of done

- [ ] All source adapters pass fixture tests.
- [ ] Canonical values match documented examples.
- [ ] Every match decision has evidence or a reason for no candidates.
- [ ] Conflict tests cannot auto-link.
- [ ] Same-name tests cannot auto-link.
- [ ] Riya's four events resolve as expected.
- [ ] Alerts are idempotent.
- [ ] Truth files are isolated from runtime processing.
