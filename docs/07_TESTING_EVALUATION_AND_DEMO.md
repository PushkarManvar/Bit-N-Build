# JourneyLens Testing, Evaluation, and Demo Runbook

**Version:** 1.0  
**Purpose:** Prove correctness, protect the demo, and provide a repeatable presentation routine.

## 1. Quality strategy

The most important quality risk is an incorrect identity merge. Testing should therefore prioritize safety and rule correctness over superficial UI coverage.

### Test layers

| Layer | Focus | Examples |
|---|---|---|
| Unit | Pure rules and helpers | Email/phone/order normalization, score caps, conflicts |
| Service | Database-backed domain behavior | Candidate retrieval, review resolution, alert idempotency |
| API | Request/response contract | Status codes, validation, duplicate ingestion |
| Integration | Full processing path | Source event → profile → timeline → alert |
| UI | Critical interactions | Open journey, inspect evidence, keep Aarav separate |
| Demo rehearsal | Timing and resilience | Reset, playback, narration, fallback |

## 2. Critical test matrix

### Normalization

| Case | Input | Expected |
|---|---|---|
| Email case/space | ` RIYA.SHAH@EXAMPLE.COM ` | `riya.shah@example.com` |
| Indian phone | `98765 43210` | `+919876543210` |
| Phone punctuation | `+91-98765-43210` | `+919876543210` |
| Order spacing | `ord 204` | `ORD-204` |
| Order underscore | `ord_204` | `ORD-204` |
| Name whitespace | `Riya  Shah` | `riya shah` comparison value |
| Invalid timestamp | malformed | Raw preserved; processing failed |
| Unknown event | new source event | Accepted as `other` with raw value preserved |

### Identity resolution

| Case | Evidence | Expected |
|---|---|---|
| Exact customer ID | one profile | Auto-link |
| Exact order ID | one profile | Auto-link |
| Exact normalized email | one profile | Auto-link |
| Exact normalized phone | one profile | Auto-link |
| Device plus later email | same journey | Correct anonymous-to-known bridge |
| Same name only | weak | Never auto-link |
| Same name and city | weak | Review or new profile |
| Email and phone disagree | strong conflict | Manual review |
| Equal top candidates | near tie | Manual review |
| No candidates | none | New profile |

### Journey rules

| Case | Expected |
|---|---|
| Return + two contacts + no completion | Unresolved-refund and repeat-contact alerts |
| Return + one contact | No unresolved alert under MVP rule |
| Return + two contacts + completion | No unresolved alert |
| Analyzer runs twice | No duplicate open alerts |
| Three channels in 48 hours | Channel-switching alert if P2 enabled |

### Review

| Case | Expected |
|---|---|
| Approve match | Event linked, audit stored, rules rerun |
| Reject match | Candidate rejected, no accidental identifiers added |
| Create profile | Separate profile created and event linked |
| Approve without selected profile | 422 validation error |
| Resolve same case twice | Conflict or existing resolution returned safely |

### Synthetic dataset

The dataset is generated deterministically, not hand-authored:

```bash
# local (repository data/ directory)
python backend/scripts/generate_synthetic_data.py

# inside compose (data/ is mounted at /data)
docker compose run --rm --no-deps backend \
  python scripts/generate_synthetic_data.py
```

Validate the generated output against the frozen G1 contract:

```bash
docker compose run --rm --no-deps backend \
  python scripts/validate_synthetic_data.py
```

Composition targets (docs/04 §11): 30–40 customers, 180–250 source events,
3–5 invalid records, 3–8 duplicates, 5–10 manual-review candidates,
5 broken journeys, 2–3 same-name collisions, 5–8 anonymous-to-known
transitions.

Truth files are isolated in `data/truth/` (gitignored). Runtime matching,
ingestion, and API responses must never read them; only the evaluation step
does. `backend/tests/test_synthetic_dataset.py` verifies the dataset is valid,
on-target, deterministic, and free of truth identifiers.

## 3. Evaluation methodology

### Pair-level identity evaluation

Compare predicted event-to-profile assignments with hidden ground truth.

- **True positive:** Event correctly linked to its real customer.
- **False positive:** Event linked to the wrong customer.
- **False negative:** Event should have linked but did not.
- **True negative:** Non-match correctly kept separate.

### Metrics

\[
\text{Precision} = \frac{TP}{TP + FP}
\]

\[
\text{Recall} = \frac{TP}{TP + FN}
\]

\[
F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}
\]

\[
\text{False Merge Rate} = \frac{\text{Wrong cross-customer links}}{\text{Predicted links}}
\]

Precision and false-merge rate are more important than maximizing recall in this use case.

### Alert evaluation

Compare generated `(profile, order, alert_type)` tuples to `expected_alerts.csv`.

Report:

- expected alerts found;
- expected alerts missed;
- unexpected alerts created;
- duplicate open alerts.

### Metric integrity rules

- Never tune against events that are later presented as unseen evaluation.
- Do not expose truth IDs to runtime matching.
- Do not hard-code dashboard metric values.
- Save the evaluation output used in the final presentation.

## 4. Integration scenarios

### Scenario S1 — Riya correct merge

1. Reset database.
2. Ingest anonymous web event with `DEV-17`.
3. Ingest app event with email, `DEV-17`, and `ORD-204`.
4. Verify earlier event and new event resolve to Riya's profile.
5. Ingest call-centre event with phone and `ORD-204`.
6. Ingest store event with phone and `ORD-204`.
7. Verify four channels appear chronologically.
8. Verify match explanations contain the expected evidence.

### Scenario S2 — Broken refund journey

1. Start from S1.
2. Ensure the required second contact exists.
3. Ensure no `refund_completed` event exists.
4. Run journey analyzer.
5. Verify one unresolved-refund alert and one repeat-contact alert.
6. Run analyzer again and verify no duplicates.

### Scenario S3 — Aarav correct non-merge

1. Seed two separate Aarav Patel profiles with different strong identifiers.
2. Ingest an ambiguous Aarav store record.
3. Verify it does not auto-link.
4. Open review case.
5. Select `Create new profile` or `Keep separate` behavior.
6. Verify no existing Aarav profile gains the event's identifiers.

### Scenario S4 — Strong conflict

1. Seed email belonging to profile A.
2. Seed phone belonging to profile B.
3. Ingest one event containing both.
4. Verify manual review regardless of numeric score.

### Scenario S5 — Failure and duplicate handling

1. Submit an invalid source timestamp.
2. Verify raw record exists with failure reason.
3. Submit a valid event twice.
4. Verify only one canonical event exists.

## 5. Release checklist

### Backend

- [ ] Migrations run on a clean database.
- [ ] Health endpoint succeeds.
- [ ] Four source adapters work.
- [ ] Duplicate behavior works.
- [ ] Conflict and same-name tests pass.
- [ ] Alert idempotency passes.
- [ ] API examples match OpenAPI.

### Frontend

- [ ] Four core pages load.
- [ ] Empty/loading/error states work.
- [ ] Journey timeline is readable at demo resolution.
- [ ] Explanation drawer shows raw and normalized data.
- [ ] Review actions show confirmation/success.
- [ ] Status is not colour-only.

### Data and metrics

- [ ] Riya and both Aarav fixtures are correct.
- [ ] Truth data is isolated.
- [ ] Metrics are generated, not hard-coded.
- [ ] No false merge exists in flagship scenarios.
- [ ] Invalid and duplicate targets are present.

### Demo

- [ ] Reset works.
- [ ] Playback works three times consecutively.
- [ ] Completed-state seed works.
- [ ] Backup recording exists.
- [ ] Key screenshots exist.
- [ ] Presenter script is timed under two minutes.

## 6. Two-minute demo script

### 0:00–0:15 — Problem

> Companies often see one frustrated customer as four unrelated records: an anonymous website visitor, an app user, a support caller, and an in-store customer. That fragmentation hides repeated unresolved problems.

Show the empty/recent-event area and begin the controlled scenario.

### 0:15–0:35 — Ingest and normalize

> JourneyLens preserves every raw event and standardizes inconsistent fields such as email, phone, order ID, timestamp, and event type.

Show web and app events arriving.

### 0:35–1:00 — Explainable correct link

> This first web event is anonymous and contains device DEV-17. When Riya uses the app on the same device with her email and order ORD-204, JourneyLens connects the earlier event and explains the evidence.

Open the explanation drawer.

> The identity decision is deterministic and measurable; an LLM is not making the merge.

### 1:00–1:25 — Broken journey

> Riya later calls support and visits a store using the same normalized phone and order. JourneyLens now shows one four-channel journey and detects an unresolved refund with repeat contact.

Open the journey and alert.

### 1:25–1:45 — Safe non-merge

> This record is also named Aarav Patel. JourneyLens keeps it as a separate profile because there is no identifier evidence to support a link, and it refuses to merge on name similarity alone.

Choose `Create new profile` or `Keep separate`.

### 1:45–2:00 — Impact

> Instead of another dashboard, JourneyLens gives support teams one evidence-backed story, exposes the broken refund journey, and protects customers from unsafe identity merges.

Show metrics briefly.

## 7. Presenter route

Use this fixed click path:

```text
Command Centre
→ Run demo
→ Open Riya alert
→ Open one match explanation
→ Return to timeline
→ Open Reviews
→ Keep Aarav separate
→ Return to metric summary
```

Do not browse freely during the timed presentation.

## 8. Demo failure playbook

| Failure | Immediate response |
|---|---|
| Backend not responding | Load completed-state seed or backup recording |
| Polling stops | Refresh once; if unresolved, use completed-state seed |
| Event sequence stalls | Use `Retry step`; then switch to completed state |
| Metrics missing | Explain only visible verified outcomes; do not quote remembered numbers |
| LLM summary fails | Use template summary; core demo continues |
| Hosted deployment fails | Run local environment |
| Database state is dirty | Run demo reset and verify base fixture count |

## 9. Pivot rule

At hour 9–10, pivot to Refund Friction Radar if:

- correct merge and correct non-merge cannot both be made reliable;
- strong conflicts still auto-link;
- profile persistence blocks the complete vertical slice; or
- integration problems threaten all remaining UI work.

The pivot removes fuzzy matching, complex candidate comparison, and the identity-heavy review experience. It preserves known profile/order mappings, the unified timeline, unresolved-refund detection, repeat contact, and operational prioritization.

## 10. Final proof package

Prepare these artifacts:

- final evaluation JSON or CSV;
- architecture diagram;
- one screenshot of Riya's timeline;
- one screenshot of match evidence;
- one screenshot of Aarav being kept separate;
- two-minute backup recording;
- README with exact startup and reset commands;
- known-limitations list.

## 11. Known limitations statement

Use a clear statement if asked:

> JourneyLens is a hackathon prototype evaluated on labelled synthetic data. It demonstrates explainable identity and journey reasoning, but production use would require privacy controls, calibrated thresholds on real data, profile split/unmerge operations, governance, monitoring, and integration testing with source systems.
