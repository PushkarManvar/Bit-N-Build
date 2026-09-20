# JourneyLens — Verified PPT Content

Verification date: 2026-09-20 (Asia/Calcutta). All performance and count claims below come from actual repository commands or live local API responses, not example values in the API contract.

## Slide 1 — One customer, four disconnected records

**Bullet points**

- A website visit may contain only a device ID; an app event adds email; a support call adds phone and order; a store return adds a return reference.
- Without normalization, one customer appears as four records across web, mobile app, call centre, and physical store.
- Agents search multiple systems while repeated contacts look unrelated.
- The operational consequence is hidden: an unresolved refund can continue across channels without one owner seeing the complete story.
- Unsafe shortcuts create a second risk—two people with similar names can be merged incorrectly.

**Speaker note**

“Companies often see one frustrated customer as four unrelated records.” JourneyLens begins with the fragmented journey—not a dashboard—and reconstructs the evidence-backed customer story.

**Source**

`docs/01_PRODUCT_REQUIREMENTS.md` §§2–4; `docs/07_TESTING_EVALUATION_AND_DEMO.md` §6, 0:00–0:15.

## Slide 2 — JourneyLens turns fragments into an explainable journey

**Bullet points**

- Preserve the raw channel event before any downstream processing.
- Normalize inconsistent source fields into one canonical event model.
- Make a deterministic identity decision and store the evidence, score, conflicts, and outcome.
- Build a chronological customer timeline and detect unresolved-refund and repeat-contact patterns.
- Route uncertainty or conflicting strong identifiers to a human reviewer.

**Speaker note**

The golden path is raw event → canonical event → identity decision → unified journey → alert → human review when necessary. An LLM may summarize verified facts, but it never decides identity or alert truth.

**Source**

`docs/00_START_HERE.md` §§1, 5, 8; `docs/03_TECHNICAL_ARCHITECTURE.md` §§1–6.

## Slide 3 — The matcher is evidence-based, capped, and conservative

**Bullet points**

- Strong evidence: customer ID **100**, order ID **95**, verified email **90**, normalized phone **85**.
- Moderate evidence: device ID **45**, session ID **35**; weak evidence: name ≥92 **20**, name 85–91 **15**, same city **5**.
- Score = strongest match + at most 10 strong-support points + 5 moderate + 5 weak, capped at **100**.
- Auto-link threshold: **≥80**; review band: **50–79**; low-confidence/no candidate creates a separate profile.
- A strong conflict always forces `review_required`; name similarity alone never produces `auto_linked`.

**Speaker note**

The score is an explanation aid, not a probability. Conflict rules override the numeric result so an email pointing to one person and a phone pointing to another can never be auto-linked.

**Source**

`docs/04_DATA_IDENTITY_AND_RULES.md` §§4–8.

## Slide 4 — Riya: four channels become one journey

**Bullet points**

- Website: anonymous event carries `DEV-17`, `SESS-1001`, and `ORD-204`; outcome `new_profile`, score **0**.
- Mobile app: email + `DEV-17` + `ORD-204`; live explanation cites same device + same order; `auto_linked`, score **100**.
- Call centre: payload adds verified phone + email + `ORD-204`; live explanation cites same email + same order; `auto_linked`, score **100**.
- Physical store: normalized phone + `ORD-204`; live explanation cites same phone + same order; `auto_linked`, score **100**.
- Result: **4 events, 4 channels, 2 open alerts**—`unresolved_refund` (high) and `repeat_contact` (medium).

**Speaker note**

The later strong evidence does not erase the anonymous beginning; it bridges it into the same auditable profile. Every timeline card shows the identity outcome, score, and field-level reason.

**Source**

`docs/04_DATA_IDENTITY_AND_RULES.md` §9; `docs/07_TESTING_EVALUATION_AND_DEMO.md` S1–S2; `data/demo/unresolved_refund_riya.json`; live `GET /api/profiles/{profile_id}` after the verified demo run.

## Slide 5 — Aarav: the system proves it can refuse a bad merge

**Bullet points**

- The curated seed creates two separate Aarav Patel web profiles rather than collapsing them by name.
- The incoming physical-store Aarav record has no shared email, phone, order, customer ID, or device.
- Runtime decision: `review_required`, score **0**, no candidate suggested, and no positive identifier evidence recorded.
- The review queue states the missing strong identifiers and preserves the record without attaching it to either Aarav profile.
- Human action can keep it separate or create a new profile, with an append-only audit record.

**Speaker note**

This is the safety proof: JourneyLens accepts fragmentation when evidence is weak rather than risking a false merge. The visible review queue makes uncertainty explicit and actionable.

**Source**

`docs/04_DATA_IDENTITY_AND_RULES.md` §§7–9; `docs/07_TESTING_EVALUATION_AND_DEMO.md` S3; live `GET /api/reviews?status=pending` after the curated reset/demo.

## Slide 6 — Core product capabilities

**Bullet points**

- **Ingestion + normalization:** idempotent acceptance, immutable raw payload, canonical email/phone/order/time/event fields, and preserved failures.
- **Identity resolution:** exact candidate retrieval, deterministic score, strong-conflict block, stored alternatives, and field-level explanations.
- **Unified timeline:** chronological web/app/call/store events with channel, order, outcome, score, and “Why linked?” evidence.
- **Journey alerts:** one open `unresolved_refund` plus one `repeat_contact` alert for the flagship order, with deduplication.
- **Human review:** filterable queue with candidate, evidence, conflicts, missing identifiers, and approve/reject/create-profile actions.

**Speaker note**

These five capabilities form the product’s decision-support loop: see what arrived, know who it belongs to, understand the journey, detect the break, and intervene safely.

**Source**

`docs/00_START_HERE.md` §§1, 5; `docs/03_TECHNICAL_ARCHITECTURE.md` §§4–7; `docs/05_API_CONTRACT.md` §§3, 5–8.

## Slide 7 — Operational control and observability

**Bullet points**

- **Analytics:** live database counts and persisted offline evaluation metrics; unavailable measurements remain `null`.
- **Demo Controller:** reset plus deterministic six-step playback, 1×/2× pacing, progress, active-alert, and pending-review telemetry.
- **Data Pipeline:** truthful stage funnel from raw accepted → normalized → identity decided → profile linked.
- **Per-channel health:** raw, normalized, and failed counts for website, mobile app, call centre, and physical store.
- **Event inspector:** deliberate access to raw JSON, canonical fields, and identity evidence, with polling every 5 seconds.

**Speaker note**

The pipeline is a read model over the existing synchronous monolith, not a claim of streaming infrastructure. Counts come from persisted rows, and duplicate attempts remain explicitly unsupported rather than estimated.

**Source**

`docs/05_API_CONTRACT.md` §§9–11; `docs/16_DATA_PIPELINE_READ_MODEL_PLAN.md` §§1, 3–6; `docs/17_PIPELINE_EVENT_NARRATIVE_PLAN.md` §§2–6.

## Slide 8 — Technology stack: small enough to explain end to end

**Bullet points**

- Frontend: **Next.js 16**, **React 19**, strict **TypeScript 5.7**, Tailwind CSS 4, Lucide icons.
- Backend: **FastAPI** on **Python 3.12**, Pydantic Settings, typed API schemas, synchronous request pipeline.
- Data: **PostgreSQL 17**, SQLAlchemy 2, Psycopg 3, Alembic migrations, JSONB for source variation.
- Runtime: Docker Compose services for frontend, backend, and database; polling is the baseline live-update mechanism.
- Quality: GitHub Actions, Pytest + coverage, Ruff, ESLint, `tsc --noEmit`, Next production build, and Compose validation/build.

**Speaker note**

JourneyLens deliberately remains a modular monolith. There is no Kafka, Redis, background queue, microservice mesh, or LLM dependency in the core path.

**Source**

`frontend/package.json`; `backend/pyproject.toml`; `backend/requirements.txt`; `backend/requirements-dev.txt`; `compose.yaml`; `.github/workflows/ci.yml`; `docs/03_TECHNICAL_ARCHITECTURE.md` §3.

## Slide 9 — Verified evaluation: safe precision, honest recall

**Bullet points**

- Test run: **106 passed**, 2 warnings, **10.01 s**.
- Pair evaluation: **TP 87, FP 0, FN 85, TN 6,968** across **120 assigned events**.
- Match precision **1.0000**, recall **0.5058**, F1 **0.6718**, false-merge rate **0.0000**.
- Alert evaluation: **9 found, 1 missed, 0 unexpected, 0 duplicates**; precision **1.0000**, recall **0.9000**.
- Dataset/effect: **35 truth customers, 189 truth events, 67 unassigned**; auto-link rate **29.1%**, review-required rate **35.4%**.

**Speaker note**

The headline is “zero measured false merges with 100% link precision,” not “perfect matching.” Recall is 50.58%, which accurately reflects the product’s conservative bias toward review and separation.

**Source**

Actual runs: `docker compose run --rm backend pytest -q` and `docker compose run --rm backend python scripts/evaluate_matching.py`; formulas in `docs/07_TESTING_EVALUATION_AND_DEMO.md` §3.

## Slide 10 — Data analytics: every number has a provenance

**Bullet points**

- Full-seed live overview: **191 raw**, **189 normalized**, **2 failed**, **67 unified profiles**, **9 open alerts**.
- Outcome rates: **29.1% auto-linked**, **35.4% review-required**; duplicate attempts and average latency are `null` because they are not persisted.
- Normalized channel counts: **web 62**, **mobile app 79**, **call centre 14**, **physical store 34**.
- Pipeline funnel: **191 raw → 189 normalized → 189 identity decisions → 122 profile-linked**; **67** pending review.
- Evaluation reads hidden truth offline; dashboard and pipeline counts are computed from real database rows and never hard-coded.

**Speaker note**

This is the insight layer: deterministic model quality beside operational database state. Keep the phrases “Real numbers from a deterministic matcher,” “Zero false merges,” and “Every count traceable to a database query.”

**Source**

Live `GET /api/analytics/overview`, `GET /api/analytics/channels`, and `GET /api/pipeline/overview` at 2026-09-20T03:58:47Z; `docs/05_API_CONTRACT.md` §§9–10; `docs/07_TESTING_EVALUATION_AND_DEMO.md` §3; `backend/scripts/evaluate_matching.py`.

## Slide 11 — Architecture: evidence flows forward; truth stays isolated

**Bullet points**

- **System context:** four synthetic sources → JourneyLens API → PostgreSQL, journey rules, and Next.js UI; hidden truth → offline evaluator.
- **Component flow:** Event API → raw store → source adapter/validator → candidate retrieval → identity engine → profile/decision stores → journey rules → alerts/query API → UI.
- **Request sequence:** accept raw first; return the existing result for an idempotent duplicate; otherwise normalize, resolve, persist, analyze, and commit.
- **ER view:** raw event produces one canonical event; profiles own identifiers/events/alerts; each canonical event has one decision; review actions append to decisions.
- **Data layers:** Bronze raw evidence, Silver canonical identity state, Gold alerts/analytics, and a separate Evaluation layer.

**Speaker note**

Use the generated architecture visual as the main image, then animate or reveal the golden path left to right. The isolation of hidden truth from runtime matching is part of the architecture, not just a testing convention.

**Source**

`docs/03_TECHNICAL_ARCHITECTURE.md` §§1–6; generated asset `docs/presentation-assets/journeylens-architecture.visual-check.2048x1320.light.png`; interactive source `docs/presentation-assets/journeylens-architecture.html`.

## Slide 12 — Two-minute demo: tell one story, not a product tour

**Bullet points**

- **0:00–0:15:** one frustrated customer appears as four unrelated records; begin the controlled scenario.
- **0:15–0:35:** show raw preservation and normalization as web/app events arrive.
- **0:35–1:00:** open Riya’s explanation—`DEV-17` and `ORD-204` bridge the anonymous event; no LLM makes the merge.
- **1:00–1:25:** open the 4-channel Riya timeline and the two `ORD-204` alerts.
- **1:25–2:00:** show Aarav kept out of a merge, then close on one evidence-backed story with human control.

**Speaker note**

Keep the narration causal: fragmentation → evidence → identity → broken journey → safe review. Do not browse freely during the timed segment.

**Source**

`docs/07_TESTING_EVALUATION_AND_DEMO.md` §§6–7.

## Slide 13 — The six deterministic steps and presenter route

**Bullet points**

- Steps 1–2: web creates the anonymous `DEV-17`/`ORD-204` record; mobile app adds Riya’s email and bridges it.
- Step 3: call centre adds verified phone/email/order evidence and links at score 100.
- Step 4: store return adds phone/order evidence and triggers unresolved-refund + repeat-contact alerts.
- Steps 5–6: Aarav events demonstrate separation; use the curated Aarav store review row as the verified human-review proof.
- Route: **Command Centre → Run demo → Riya alert → Why linked? → timeline → Reviews → keep Aarav separate → metrics**.

**Speaker note**

Verified caveat: the current step-6 UI copy says it creates a review case, but `DEMO-APP-02` actually produced `new_profile` and pending reviews stayed at 3. Present the pre-seeded `CURATED-STORE-AARAV-01` case as the real review proof unless the scenario fixture/logic is corrected.

**Source**

`data/demo/unresolved_refund_riya.json`; `docs/05_API_CONTRACT.md` §11; `docs/07_TESTING_EVALUATION_AND_DEMO.md` §§6–7; live demo/pipeline/review responses from the verified run.

## Slide 14 — Product screens to place in the deck

**Bullet points**

- **Command Centre:** full-seed screenshot with 67 profiles, 189 processed, 67 pending reviews, 9 alerts, 29.1% auto-link, and 100.0% precision.
- **Riya Journey:** live screenshot with 4 events, 4 channels, 2 alerts, and score-100 explanation cards.
- **Review Queue:** curated screenshot with 3 pending cases—1 strong conflict, 2 candidate suggestions, and Aarav with no candidate/evidence.
- **Demo Controller:** completed 6/6 view with 2 active alerts and 3 pending reviews.
- **Data Pipeline:** 191 → 189 → 189 → 122 funnel, 2 normalization failures, 67 pending review, channel cards, filters, and inspector.

**Speaker note**

Prefer the live captures from this verification session. The backup images in `P:\Journeylens-backup\demo-screenshots\` are older and include stale values, including an unevaluated precision card and a `3030.0%` auto-link display bug.

**Source**

Live routes: `/command-centre`, `/customers/{Riya profile id}`, `/reviews`, `/demo`, `/pipeline`; backup directory `P:\Journeylens-backup\demo-screenshots\`.

## Slide 15 — Team execution: gates, pull requests, and green CI

**Bullet points**

- GitHub reports **28 merged pull requests**—stronger and more precise than the requested “19+” claim.
- Gate PRs: **#11 G1 ingestion**, **#13 G2 identity**, **#14 G4 alerts**, **#15 G5+G6 review/evaluation**, **#16 G7 demo**.
- G3 has no separately titled PR; its journey/timeline capability is present in the merged vertical slice and live UI, so say “G1–G7 capabilities shipped,” not “seven gate-named PRs.”
- Latest merged PR checked (#30): **Backend passed in 23 s, Docker configuration in 33 s, Frontend in 36 s**.
- Collaboration pattern: short feature branches, PR review into `main`, Conventional Commit-style titles, CI on pushes/PRs, and Dependabot maintenance.

**Speaker note**

The process story is evidence-driven: focused PRs advanced the product gate by gate while CI continuously checked backend, frontend, and Docker. Avoid claiming a separate G3 PR because GitHub does not show one.

**Source**

Actual commands: `gh pr list --repo PushkarManvar/Bit-N-Build --state merged --limit 100 ...` and `gh pr checks 30 --repo PushkarManvar/Bit-N-Build`; `.github/workflows/ci.yml`; `docs/00_START_HERE.md` §5; `docs/FRONTEND_TASK_SPLIT.md`.

## Verification transcript (presenter appendix, not a slide)

### Backend tests

```text
$ docker compose run --rm backend pytest -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed, 2 warnings in 10.01s
```

### Full-seed reset

```json
{"status":"reset","loaded":{"received":189,"duplicates":6,"failed":2,"invalid":2}}
```

### Matching and alert evaluation

```text
$ docker compose run --rm backend python scripts/evaluate_matching.py
tp: 87
fp: 0
fn: 85
tn: 6968
match_precision: 1.0
match_recall: 0.5058
match_f1: 0.6718
false_merge_rate: 0.0
assigned_events: 120
alert_found: 9
alert_missed: 1
alert_unexpected: 0
alert_duplicates: 0
alert_precision: 1.0
alert_recall: 0.9
auto_link_rate: 29.1
review_required_rate: 35.4
unassigned_events: 67
truth_customers: 35
truth_events: 189
evaluated_at: 2026-09-20T03:58:41.343373+00:00
```

### Live analytics snapshot

```json
{
  "total_raw_events": 191,
  "normalized_events": 189,
  "failed_events": 2,
  "duplicate_events": null,
  "unified_profiles": 67,
  "auto_link_rate": 29.1,
  "review_required_rate": 35.4,
  "open_alerts": 9,
  "match_precision": 1.0,
  "match_recall": 0.5058,
  "match_f1": 0.6718,
  "false_merge_rate": 0.0,
  "average_processing_latency_ms": null
}
```

### Live channel counts

```json
{"web":62,"mobile_app":79,"call_center":14,"physical_store":34}
```

### Live pipeline summary

```json
{
  "stages": {
    "raw_accepted": 191,
    "normalization_succeeded": 189,
    "normalization_failed": 2,
    "identity_decided": 189,
    "profile_linked": 122,
    "review_required": 67
  },
  "channels": {
    "web": {"raw":63,"normalized":62,"failed":1},
    "mobile_app": {"raw":79,"normalized":79,"failed":0},
    "call_center": {"raw":15,"normalized":14,"failed":1},
    "physical_store": {"raw":34,"normalized":34,"failed":0}
  },
  "duplicate_attempts": null,
  "duplicate_tracking_supported": false
}
```

## Key numbers box — verified values only

| Category | Verified value |
|---|---:|
| Backend tests | **106 passed** |
| Truth dataset | **35 customers / 189 events** |
| Match precision | **100.00%** |
| Match recall | **50.58%** |
| Match F1 | **67.18%** |
| False-merge rate | **0.00%** |
| Alert precision / recall | **100.00% / 90.00%** |
| Alerts found / expected | **9 / 10** |
| Full-seed live rows | **191 raw / 189 normalized / 2 failed** |
| Live profiles / open alerts | **67 / 9** |
| Auto-link / review-required rate | **29.1% / 35.4%** |
| Pipeline profile-linked / pending review | **122 / 67** |
| Riya demo proof | **4 events / 4 channels / 2 alerts** |
| Curated review queue | **3 pending / 1 strong conflict** |
| Deterministic demo | **6 steps / 6 complete** |
| Merged pull requests | **28** |
| Latest checked PR CI | **3/3 jobs passed** |
