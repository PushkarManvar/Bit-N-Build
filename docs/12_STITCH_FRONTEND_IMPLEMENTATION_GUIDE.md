# JourneyLens Stitch Frontend Implementation Guide

**Status:** Ready to execute; full Review Detail and Data Pipeline fidelity have named backend gates  
**Audience:** Frontend engineers, backend reviewers, QA, and demo presenters  
**Visual source:** `stitch_journeylens_operations_platform/`  
**Runtime source:** Current FastAPI routes and Pydantic schemas in `backend/app/`  
**Last reconciled:** 2026-09-19

## 1. Purpose

This document turns the seven Stitch screens into an implementation sequence that a frontend engineer can follow from the current Next.js scaffold to a complete JourneyLens UI.

The finished frontend should look and behave very close to the supplied screens while remaining truthful to the product and backend. It must preserve the JourneyLens golden path:

1. receive and normalize a channel event;
2. show the explainable identity outcome;
3. show the unified customer journey;
4. expose unresolved-refund and repeat-contact alerts;
5. route uncertain identity decisions to human review; and
6. run the deterministic Riya/`ORD-204` demo.

This is an implementation guide, not permission to expand JourneyLens into a CRM, payment console, general data platform, or probabilistic AI product.

Stages 0–4, the Review Queue, and the supported Demo Controller can begin immediately. Full Review Detail and Data Pipeline work must wait for the backend gates in section 9 or ship only in the reduced form defined here. This guide is complete within the repository: engineers are expected to use the linked screens and the generated FastAPI OpenAPI schema rather than copy API payload definitions into a second contract.

## 2. Source-of-truth order

Use this precedence whenever the screen mockup, old documentation, and code disagree:

1. **Safety and product rules:** `AGENTS.md` and `docs/04_DATA_IDENTITY_AND_RULES.md`.
2. **Actual wire contract:** current FastAPI routes, enums, and Pydantic response models in `backend/app/`.
3. **Frozen contract intent:** `docs/05_API_CONTRACT.md`.
4. **User workflow:** `docs/02_USER_WORKFLOWS_AND_UX.md`.
5. **Visual composition:** the Stitch `screen.png`, `code.html`, and shared `DESIGN.md`.

The Stitch HTML is a visual and interaction reference. It contains demo-only text, hard-coded values, and claims about systems that are not part of JourneyLens. Do not copy those claims into production components.

## 3. Screen inventory and application routes

No new primary product surface should be added until these screens work.

| Priority | Application route | Stitch reference | Implementation role |
|---:|---|---|---|
| 1 | `/customers/[profileId]` | [Journey detail screenshot](../stitch_journeylens_operations_platform/customer_journey_detail_riya_sharma/screen.png) · [HTML](../stitch_journeylens_operations_platform/customer_journey_detail_riya_sharma/code.html) | Golden-path proof: alerts, cross-channel timeline, and match evidence |
| 2 | `/command-centre` | [Command Centre screenshot](../stitch_journeylens_operations_platform/command_centre/screen.png) · [HTML](../stitch_journeylens_operations_platform/command_centre/code.html) | Operational entry point and current system state |
| 3 | `/customers` | [Customer Explorer screenshot](../stitch_journeylens_operations_platform/customer_explorer/screen.png) · [HTML](../stitch_journeylens_operations_platform/customer_explorer/code.html) | Profile search, pagination, selection, and journey entry |
| 4 | `/reviews` | [Review Queue screenshot](../stitch_journeylens_operations_platform/review_queue/screen.png) · [HTML](../stitch_journeylens_operations_platform/review_queue/code.html) | Pending identity decisions |
| 5 | `/reviews/[matchDecisionId]` | [Review detail screenshot](../stitch_journeylens_operations_platform/match_review_detail_case_mr_003/screen.png) · [HTML](../stitch_journeylens_operations_platform/match_review_detail_case_mr_003/code.html) | Evidence comparison and audited resolution |
| 6 | `/demo` | [Demo Controller screenshot](../stitch_journeylens_operations_platform/demo_controller/screen.png) · [HTML](../stitch_journeylens_operations_platform/demo_controller/code.html) | Reset, start, monitor, and complete the fixed demo |
| 7 | `/pipeline` | [Data Pipeline screenshot](../stitch_journeylens_operations_platform/data_pipeline/screen.png) · [HTML](../stitch_journeylens_operations_platform/data_pipeline/code.html) | Inspect real ingestion and normalization data after supporting APIs exist |

The root route `/` should redirect to `/command-centre`.

## 4. Mandatory corrections to the Stitch content

These decisions are locked for the frontend implementation.

| Stitch content | Correct JourneyLens implementation |
|---|---|
| `Riya Sharma` / `PROF-RIYA-01` | Render the name and UUID returned by the API. The documented flagship customer is **Riya Shah**; never hard-code a profile ID. |
| Eight demo steps | The current scenario file contains **six** steps. Render `current_step` and `total_steps` returned by the API. |
| `call_centre` or `call-centre` wire value | Use API value `call_center`; present it as **Call Centre**. |
| `manual_review` | Use API value `review_required`; present it as **Needs review**. |
| `login_success`, `support_inquiry`, `support_escalation`, or other screen-only event values | Use only the current backend `EventType` values. Convert those values to friendly labels in a presenter function. |
| “Probabilistic engine,” “high-prob,” or probability language | JourneyLens uses deterministic evidence scoring. Label the number **Identity score**, not probability or AI confidence. |
| Kafka, SSE, S3/Blob, Shopify, CRM, Razorpay, gateway, or production connector claims | Remove them. The MVP is a modular monolith using polling, FastAPI, PostgreSQL, and synthetic demo data. |
| “Trigger manual gateway retry” | Replace with the API-provided recommended action as read-only guidance. JourneyLens does not execute refunds. |
| Fixed metrics such as `28`, `186`, `99.8%`, `42ms`, or `0 verified` | Always render API values. Render `—` and explanatory copy for `null`; never invent a default. |
| Loyalty tier, purchase value, account tenure, agent assignment, or current-user identity | Omit unless a real API field is added. There is currently no authentication or agent-profile contract. |
| “Approve link” enabled during a strong-identifier conflict | Disable it in the UI. A strong conflict blocks automatic linking and must not be bypassed casually. The backend must also enforce this before the action is enabled anywhere. |
| “Keep separate” and “Create new profile” treated as identical | Map deliberately: `reject_link` rejects only the proposed candidate and leaves the event unresolved; `create_profile` creates a separate profile and attaches the event. |

## 5. Canonical frontend vocabulary

Centralize these values in `frontend/lib/types.ts` and presentation labels in a separate formatter/presenter module. Never repeat ad hoc string mappings inside pages.

### 5.1 Channels

| API value | UI label | Icon | Color token |
|---|---|---|---|
| `web` | Website | Globe | Indigo `#4F46E5` |
| `mobile_app` | Mobile App | Smartphone | Violet `#7C3AED` |
| `call_center` | Call Centre | Headphones | Orange `#EA580C` |
| `physical_store` | Physical Store | Store | Teal `#0F766E` |

Every channel indicator must include both icon and text. Color alone is not sufficient.

### 5.2 Identity outcomes

| API value | UI label | Meaning |
|---|---|---|
| `auto_linked` | Linked automatically | Strong evidence agrees and no blocking conflict exists |
| `review_required` | Needs review | Evidence is incomplete, tied, or conflicting |
| `new_profile` | New profile created | No credible existing match was found |

### 5.3 Review actions

| API action | Button label | Result |
|---|---|---|
| `approve_link` | Approve selected match | Link the event to `selected_profile_id`; require confirmation |
| `reject_link` | Reject this candidate | Reject the candidate and leave the event unresolved |
| `create_profile` | Create separate profile | Create a new profile and attach the event to it |

### 5.4 Processing states

Persisted states are `received`, `normalized`, and `failed`. `duplicate` is an ingestion response outcome, not a persisted processing state. Do not add `matched` to the wire type.

### 5.5 Event types

The only current event values are:

```text
product_viewed
app_login
order_placed
return_requested
support_contacted
store_visited
refund_completed
```

Use sentence-case labels in the UI. Descriptions may be composed from `event_type`, `channel`, `order_id`, and `evidence_summary`; do not invent details such as products, amounts, agents, tickets, or payment providers.

## 6. Shared visual system

Implement the supplied [Journey Operations Console design system](../stitch_journeylens_operations_platform/journey_operations_console/DESIGN.md) once and reuse it everywhere.

### 6.1 Required tokens

- Canvas: `#F6F8FB`.
- Card/modal: `#FFFFFF`.
- Structural border: `#E4E7EC`.
- Control border: `#D0D5DD`.
- Main heading: `#172554`.
- Body: `#1E293B`.
- Secondary text: `#667085`.
- Primary action: `#4F46E5`.
- Linked/resolved: `#0F766E`.
- Warning/review: `#D97706`.
- Conflict/error: `#DC2626`.
- Font: Inter; use tabular figures for metrics and monospaced text for UUIDs, event IDs, and JSON.
- Eight-pixel spacing grid, 12px primary-card radius, 6px control radius, and restrained shadows only for overlays.

The existing dark scaffold in `frontend/app/globals.css` must be replaced by this light operations-console theme.

The current frontend does not yet include Tailwind or an icon package even though the Stitch HTML uses both. Add Tailwind as a project-local build dependency, matching the architecture decision in `docs/00_START_HERE.md`, and use one bundled SVG icon system such as Lucide. Do not copy Stitch's CDN scripts, Google-hosted logo URL, remote font tags, or Material Symbols dependency: the core demo must work without a runtime internet connection. Bundle Inter locally when a licensed font asset is available; until then, retain the documented system-sans fallback without fetching a font in the browser.

### 6.2 Shared shell

Desktop behavior:

- 240px fixed navigation rail.
- 64px fixed top bar.
- Content begins after both fixed regions.
- Global search sends the user to `/customers?search=...`; it is not a global multi-entity search.
- The queue badge uses the real pending-review count.
- The connectivity chip reflects health/poll success and must not claim “live ingestion” when polling is failing.

Responsive behavior:

- At 768–1279px, collapse the rail to icons and move secondary inspectors into slide-over panels.
- Below 768px, use a single-column layout, a dismissible navigation sheet, and full-height evidence/review sheets.
- Dense tables may scroll horizontally, but primary actions and row identity must remain visible.

### 6.3 Shared components

Create reusable components before duplicating screen markup:

- `AppShell`, `SideNav`, `TopBar`, `ConnectivityStatus`;
- `MetricCard`, `Panel`, `EmptyState`, `ErrorState`, `SkeletonBlock`;
- `ChannelBadge`, `IdentityOutcomeBadge`, `SeverityBadge`, `ProcessingStatusBadge`;
- `SearchField`, `FilterBar`, `Pagination`, `ConfirmDialog`, `Toast`;
- `Timeline`, `TimelineEventCard`, `JsonViewer`, `EvidenceList`;
- `ApiErrorMessage` using the shared `{ error: { code, message, stage, raw_event_id, details } }` shape.

All icon-only buttons require an accessible name. All dialogs require focus trapping, Escape handling, focus return, and an explicit heading.

## 7. Frontend data architecture

### 7.1 Recommended file layout

```text
frontend/
  app/
    (operations)/
      layout.tsx
      command-centre/page.tsx
      customers/page.tsx
      customers/[profileId]/page.tsx
      reviews/page.tsx
      reviews/[matchDecisionId]/page.tsx
      demo/page.tsx
      pipeline/page.tsx
    page.tsx
    globals.css
  components/
    shell/
    ui/
    journey/
    reviews/
    demo/
    pipeline/
  lib/
    api.ts
    types.ts
    presenters.ts
    formatters.ts
    polling.ts
```

Use server components for initial page reads. Add small client components only for search input, filtering, polling, drawers, dialogs, pagination controls, and mutation feedback.

### 7.2 API client rules

- Keep all HTTP calls in `frontend/lib/api.ts`.
- Distinguish server and browser base URLs. In Docker, server components must call an internal value such as `BACKEND_INTERNAL_URL=http://backend:8000`; browser client components may use `NEXT_PUBLIC_API_URL=http://localhost:8000`. Do not make a server component call its own container at `localhost:8000`.
- Add `BACKEND_INTERNAL_URL` to the frontend service in `compose.yaml` and document both variables in `.env.example`.
- Set a bounded timeout and normalize network, JSON, and shared API errors into one frontend error type.
- Do not silently substitute mock data after a live request fails.
- Allow typed mock fixtures only in an explicit development/test mode.
- Encode query parameters with `URLSearchParams`.
- Treat 404, 409, 422, and 500 as distinct user outcomes.
- After a successful mutation, refresh the affected server data or update the local cache and then reconcile with the API response.

### 7.3 Polling rules

Polling is the baseline. Do not introduce SSE or a background queue.

- Command Centre: request `/api/dashboard/updates?since=...` every 3 seconds while visible.
- Demo Controller: request `/api/demo/{run_id}` every 1 second while `status === "running"`.
- Review Queue badge/list: refresh every 30 seconds while visible, matching the visual design.
- Stop or slow polling when `document.visibilityState !== "visible"`.
- Prevent overlapping requests with `AbortController`.
- After three consecutive failures, show a degraded connection state and a manual retry control.
- Announce meaningful status changes through an `aria-live="polite"` region; do not announce every poll.

Use this cursor algorithm for dashboard polling:

1. Capture `requestStartedAt` as an ISO-8601 UTC timestamp immediately before each request.
2. Send the last successfully committed cursor as `since`; omit it for the initial load.
3. On success, merge events by `event_id` and alerts by `id`, then set the committed cursor to that request's `requestStartedAt`.
4. On failure, keep the previous cursor so the next successful request covers the missed window.
5. Sort merged activity by `occurred_at` for event chronology and by `created_at` for alerts; never use array arrival order as business time.

The overlap between a request start and response makes duplicates possible by design; ID-based merging removes them without risking a missed update.

### 7.4 Contract field quick reference

Generate TypeScript types from or check them against `/openapi.json`. The minimum fields used by the UI are:

| Shape | Fields used by the frontend |
|---|---|
| `AnalyticsOverview` | `total_raw_events`, `normalized_events`, `failed_events`, nullable `duplicate_events`, `unified_profiles`, nullable `auto_link_rate`, nullable `review_required_rate`, `open_alerts`, nullable precision/recall/F1/false-merge/latency metrics |
| `ProfileSummary` | `profile_id`, nullable `display_name`, nullable `email`, nullable `phone`, `channels_used`, `event_count`, `open_alert_count`, `review_required`, `last_seen_at` |
| `ProfileListResponse` | `items`, `page`, `page_size`, `total` |
| `ProfileJourneyResponse` | `profile`, `timeline`, `alerts`, nullable `journey_summary` |
| `TimelineEvent` | `event_id`, `channel`, `event_type`, `occurred_at`, nullable `order_id`, `decision`, `score`, `evidence_summary` |
| `Alert` | `id`, `type`, `severity`, `title`, `description`, `recommended_action`, `status`, nullable `order_id`, `created_at` |
| `MatchExplanation` | `event_id`, `event_context`, `decision`, nullable `selected_profile_id`, `score`, `thresholds`, `evidence`, `conflicts`, `alternative_candidates`, `raw_payload`, `normalized_fields` |
| `ReviewItem` | `match_decision_id`, `event`, nullable `best_candidate`, `evidence`, `conflicts`, `missing_strong_identifiers`, `reason` |
| `DashboardUpdates` | `events`, `new_alerts`, `open_alerts`, `pending_reviews`, nullable `demo` |
| `DemoRun` | `run_id`, `status`, `current_step`, `total_steps`, nullable `last_event_id`, nullable `error` |

Profile list rows already contain `channels_used`; do not issue a detail request per row. Detail requests are only for the selected Customer Explorer preview. The review list deliberately lacks rich incoming/candidate identifiers, and dashboard events deliberately lack raw IDs; those limitations are handled by `BE-FE-03` and `BE-FE-04`.

### 7.5 Deterministic presentation rules

- Missing profile name: display `Unknown customer` plus the shortened UUID.
- Short UUID: first eight characters, preserving the full value in accessible text/title and copy action.
- Email mask: preserve the domain and first local-part character, e.g. `r***@example.com`.
- Phone mask: preserve an explicit country prefix when present and the last four digits, e.g. `+91 •••••• 3210`.
- Timeline event label: title-case the canonical event type (`support_contacted` → `Support contacted`).
- Timeline description: use `evidence_summary.join(" · ")`; if empty, use `Event recorded through {Channel label}`. Do not infer product, ticket, agent, payment, or location details.
- Order filter: exact equality against `timeline[].order_id` after trimming and uppercasing the query.
- Journey synthesis when `journey_summary` is null: render `“{eventCount} events across {channelCount} channels, with {openAlertCount} open journey alerts.”` Hide the panel only when there are no events and no alerts.
- Invalid Customer Explorer page: if `total > 0` and the requested page exceeds the last page, replace the URL with the last valid page and refetch once; never loop.

## 8. Screen-by-screen build specification

### 8.1 Journey Detail — build first

**Route:** `/customers/[profileId]`  
**Primary API:** `GET /api/profiles/{profile_id}`  
**Evidence API:** `GET /api/events/{canonical_event_id}/match-explanation`

#### Required layout

1. Breadcrumb back to Customer Explorer.
2. Profile header showing API name, shortened profile UUID, known email/phone identifiers, channel count, event count, last activity, and alert count.
3. Alert rule panel before the timeline.
4. Timeline search/filter bar.
5. Reverse-chronological visual timeline, even though the API currently returns chronological data.
6. Known identifiers panel.
7. Read-only journey synthesis using verified fields only.
8. Match-evidence drawer opened from every timeline event.

#### Data behavior

- Derive email/phone from `profile.identifiers`; never assume array order.
- Derive channel count from unique timeline channels.
- Derive last activity from the maximum `occurred_at` value.
- Render every alert from `alerts`; do not assume exactly two.
- Use `alert.title`, `description`, and `recommended_action` verbatim unless a copy defect is fixed at the API.
- The backend returns `journey_summary: null`; hide that panel or generate only a deterministic frontend sentence from visible facts. Do not invoke an LLM.
- Timeline card copy must be deterministic and based on returned fields.
- `Why linked?` loads the match-explanation endpoint and opens the drawer.
- The drawer has **Explanation**, **Normalized fields**, and **Raw payload** tabs.
- In the explanation tab, show the decision, score, thresholds, evidence, conflicts, and alternatives. A conflict message must visually override the score.
- Raw JSON must be formatted, horizontally scrollable, selectable, and copyable.

#### Do not implement from the mockup

- Re-evaluate journey.
- Trigger a refund/payment retry.
- Match history until an endpoint exists.
- Loyalty tier, monetary values, SLA claims, CRM synchronization, payment-provider status, or agent names.

#### Acceptance criteria

- Riya's API-backed events render in correct time order and preserve all returned channels.
- `ORD-204` alerts are prominent and link to the relevant filtered timeline.
- Every event opens its own real evidence response.
- Empty timeline, no alerts, loading, 404, and network error states are complete.
- The page is usable with keyboard only and at 1280px, 1024px, and 390px widths.

### 8.2 Command Centre

**Route:** `/command-centre`  
**APIs:** `GET /api/analytics/overview`, `GET /api/alerts`, `GET /api/dashboard/updates`

#### Required layout

1. Page heading, connection state, last successful refresh, and manual refresh.
2. KPI row.
3. Priority journey issues.
4. Identity resolution overview.
5. Recent activity log.

#### Real field mapping

| UI item | API source |
|---|---|
| Unified profiles | `analytics.unified_profiles` |
| Events processed | `analytics.normalized_events` |
| Needs review | `dashboard.pending_reviews` |
| Active journey alerts | `analytics.open_alerts` or `dashboard.open_alerts` |
| Match precision/F1 | `analytics.match_precision` / `analytics.match_f1`; show `—` when null |
| Priority issues | `GET /api/alerts` |
| Recent activity | `dashboard.events` |
| New alerts during polling | `dashboard.new_alerts` |

The current alert response does not include `profile_id`, so the **View journey** action is blocked until backend gap `BE-FE-01` is resolved. Do not guess a profile from `order_id`.

Count authority is explicit: use the initial analytics response for KPI paint, then let the newest successful dashboard poll own `open_alerts` and `pending_reviews`. The alert panel uses `/api/alerts.items` and its `total`; the Review Queue list uses `/api/reviews.items`. If a count and list temporarily disagree, label the list with its own total and allow the next poll/refetch to reconcile—never alter either result locally to make them match.

Severity filtering may be client-side because the current alert list is small. The tabs must use actual enum values (`critical`, `high`, `medium`, `low`) or group them transparently; do not relabel a `high` backend alert as `critical`.

#### Acceptance criteria

- All numbers come from APIs.
- Null evaluation metrics display `—` with “Not evaluated yet.”
- Polling adds or refreshes recent events without duplicating rows.
- Partial failures preserve successful panels and label the failed panel.
- Empty, skeleton, partial-error, full-error, and healthy states match the Stitch hierarchy.

### 8.3 Customer Explorer

**Route:** `/customers`  
**APIs:** `GET /api/profiles?page=&page_size=&search=`, then `GET /api/profiles/{profile_id}` for the selected preview

#### Required layout

1. Search and result count.
2. Profile table with customer, verified identifiers, channels, event count, active alerts, last activity, and action.
3. Desktop profile preview panel; use a drawer below desktop widths.
4. Pagination using API `page`, `page_size`, and `total`.

#### Current-contract behavior

- Search supports display name and identifier values. Debounce by 300–500ms and mirror the search in the URL.
- `ORD-204` is searchable because normalized order IDs are stored as profile identifiers by the backend. Treat this as a contract-backed search path, not a frontend scan.
- The current route does **not** implement channel, open-alert, review-required, or date filters even though the older contract documents them. Hide those controls until `BE-FE-02` is complete.
- `open_alert_count` and `review_required` are currently placeholder values in the backend profile summary. Do not present them as authoritative until `BE-FE-02` is complete.
- Load the selected profile detail to populate known identifiers, alerts, and recent events in the preview.
- Same-name profiles must show a shortened UUID plus a masked stable identifier. Never label them duplicates.
- The primary action is **Open full journey**, linking to `/customers/{profile_id}`.

Export CSV, batch actions, and **Send to Review Queue** are not supported by the API and must not ship as active controls.

#### Acceptance criteria

- Search, URL state, pagination, row selection, preview loading, and journey navigation work.
- Empty search, loading, timeout/network error, and invalid-page states are implemented.
- Email and phone masking is deterministic and does not alter the stored/API value.

### 8.4 Review Queue

**Route:** `/reviews`  
**API:** `GET /api/reviews`

#### Required layout

1. Queue heading and real pending count.
2. Compact queue summary; show only metrics that can be computed from the current response.
3. Search/filter bar.
4. Candidate-pair table/cards.
5. Review action linking to `/reviews/{match_decision_id}`.

#### Data behavior

- Render `event`, `best_candidate`, `evidence`, `conflicts`, `missing_strong_identifiers`, and `reason` directly from each review item.
- The score is an identity score. A conflict badge must remain prominent even when the score is high.
- The current response has no queue-created timestamp, priority, SLA, resolved-today count, average-review duration, incoming record ID, or pagination. Omit those claims until the backend supplies them.
- Search and channel filters may operate client-side over the returned pending items.
- Sort conflicts first, then original API order. Label that behavior; do not call it SLA ordering.

#### Acceptance criteria

- A strong conflict cannot appear as a safe match.
- Empty, loading, network-error, and default states work.
- Pending count stays synchronized with the shell badge.
- Every row has a keyboard-reachable **Review match** action.

### 8.5 Review Detail

**Route:** `/reviews/[matchDecisionId]`  
**Read API:** blocked on `BE-FE-03` for full fidelity  
**Mutation API:** `POST /api/reviews/{match_decision_id}/resolve`

#### Required layout

Preserve the Stitch hierarchy:

1. Breadcrumb, case ID, state, and identity score.
2. Conflict banner when `conflicts.length > 0`.
3. Incoming event versus candidate profile comparison.
4. Evidence/weight panel.
5. Reviewer note.
6. Sticky decision bar.
7. Confirmation dialog for `approve_link` and `create_profile`.
8. Success state showing the API result.

The current list response is not rich enough to reproduce the field-aligned discrepancy matrix after a page refresh. Implement the full route only after `BE-FE-03`, or pass list data for a temporary prototype while clearly handling direct-load failure. Do not create fictional profile fields to fill the matrix.

#### Resolution rules

- Require a non-empty reviewer name because the API requires it.
- `approve_link` requires `selected_profile_id`.
- Disable `approve_link` when a strong conflict exists. Backend enforcement is also required; frontend disabling is not a safety boundary.
- Until conflicts gain a typed severity, conservatively compute `approvalBlocked = conflicts.length > 0`. Do not parse message text to decide whether a conflict is strong.
- `reject_link` means **Reject this candidate**, not “create a separate customer.”
- `create_profile` means **Create separate profile** and is the correct demo action when the incoming Aarav record should become its own customer.
- Preserve the note limit of 500 characters and show the remaining count.
- On 409, show that another reviewer already resolved the case and refresh the queue.
- On success, show `review_status`, `action`, `profile_id`, and `resolved_at`, then offer return-to-queue and open-profile actions when a profile ID exists.

#### Acceptance criteria

- The exact API enum is submitted for each button.
- Merge confirmation names both the incoming record and target profile.
- Double submission is prevented.
- Conflict, validation, already-resolved, success, and network-failure states are tested.
- The Riya and Aarav names are never merged using name similarity alone.

### 8.6 Demo Controller

**Route:** `/demo`  
**APIs:** `POST /api/demo/reset`, `POST /api/demo/start`, `GET /api/demo/{run_id}`, `GET /api/dashboard/updates`

#### Required layout

1. Internal-demo label and scenario summary.
2. Start and reset controls.
3. Six-step progress list based on the checked-in scenario.
4. Live counters for dispatched events, alerts, and pending reviews. Show a linked-event count only when it can be derived from a resolved target profile.
5. Status/error panel and shortcuts to Riya journey, pipeline, and reviews when targets are known.

#### Supported controls

- **Run scenario:** send `{ "scenario": "unresolved_refund_riya", "interval_seconds": 1.5 }`.
- **1x / 2x before start:** may choose `1.5` or `0.75` seconds. Speed cannot be changed after a run starts.
- **Reset demo:** require confirmation because the endpoint clears operational demo data and reloads baseline fixtures.
- **Progress:** poll the run endpoint; use only `running`, `completed`, and `failed`.

Pause, resume, skip, retry-step, individual send-event, mock mode, completed-state seed, presenter notes persistence, and manual advance are not supported. Do not render them as working controls.

The start call ingests the first event immediately. The status endpoint advances elapsed steps lazily, so polling is required for the run to progress.

After completion, resolve the Riya navigation target through `GET /api/profiles?search=ORD-204`; do not hard-code a profile UUID or assume the most recent dashboard event belongs to Riya.

On reload, call `/api/dashboard/updates` without `since` and read its nullable `demo` object. If it contains a `running` run, restore `run_id`, `current_step`, and `total_steps`, then resume status polling. If it is `completed` or `failed`, restore that terminal state without starting a new run.

#### Acceptance criteria

- Start cannot be submitted twice while running.
- Reset cannot happen accidentally.
- Progress remains correct after navigation/reload when the latest run is returned through dashboard updates.
- Failed state shows the backend error and offers reset/start-again; do not claim per-step retry.
- Completion offers real navigation targets and works three consecutive times.

### 8.7 Data Pipeline

**Route:** `/pipeline`  
**Current partial APIs:** `GET /api/analytics/overview`, `GET /api/analytics/channels`, `GET /api/dashboard/updates`, `GET /api/events/{raw_event_id}`, and match explanation by canonical event ID

This screen is last because its Stitch design expects data the backend does not yet expose as a coherent list.

#### Preserve from the visual

- Funnel/stage cards.
- Four source-channel cards.
- Event stream.
- Event inspector with overview, raw payload, canonical fields, and decision evidence.
- Loading, empty, paused/degraded, and error states.

#### Remove or relabel

- Do not claim SSE; label the page **Polling every 3 seconds**.
- Do not claim S3/blob persistence, Kafka acknowledgment, connector version, DLQ, buffer capacity, P99 latency, hash lineage, 48-hour deduplication window, pause ingestion, or replay until supported.
- Do not display synthetic source health/latency as real telemetry.
- “Raw stored” is a valid conceptual stage, but a live count requires a real API field.

`BE-FE-04` and `BE-FE-05` are required for full fidelity. Until then, it is acceptable to ship a reduced pipeline page containing truthful analytics, channel counts, and recent normalized events, with unavailable sections explicitly labelled **Not exposed by the current API**.

#### Acceptance criteria

- No operational number or infrastructure claim is hard-coded.
- Failed and duplicate raw events appear only after the backend event-list endpoint supports them.
- Inspector IDs are not confused: raw-event retrieval takes `raw_event_id`; match explanation takes `canonical_event_id`.
- JSON tabs use real payloads and remain keyboard accessible.

## 9. Backend-to-frontend contract gaps

These are integration tasks, not permission for the frontend to guess data.

| ID | Required backend addition or correction | Screens unblocked | Frontend behavior before completion |
|---|---|---|---|
| `BE-FE-01` | Add `profile_id` to each `/api/alerts` item | Command Centre journey links | Render alert without journey link |
| `BE-FE-02` | Implement documented profile filters and compute real `open_alert_count` / `review_required` | Customer Explorer filters and badges | Hide unsupported filters and placeholder badges |
| `BE-FE-03` | Add `GET /api/reviews/{match_decision_id}` with canonical event ID, incoming identifiers/order/attributes, all candidates with identifiers, evidence, conflicts, thresholds, reason, and created time | Full Review Detail matrix | Use simplified in-navigation preview only; direct load must explain limitation |
| `BE-FE-04` | Add a paginated event-list endpoint returning raw and canonical IDs, source ID, channel, event type, received/occurred time, processing status, duplicate outcome where recorded, profile ID, and identity outcome | Data Pipeline stream | Show only recent canonical events from dashboard updates |
| `BE-FE-05` | Add truthful pipeline aggregate fields if the full funnel is required: raw count, normalized count, failure count, identity-decision count, journey-updated count, and per-channel counts | Data Pipeline funnel | Use only analytics fields that already exist |
| `BE-FE-06` | Enforce that an unresolved strong conflict cannot be approved through review resolution without a separately designed safe override policy | Review Detail safety | Disable approve in UI, but do not consider the issue fully secured |
| `BE-FE-07` | Make route behavior match the shared error envelope for not-found and validation failures | All screens | Normalize FastAPI `detail` responses as a temporary fallback |

Any schema change must update `docs/05_API_CONTRACT.md`, backend tests, `frontend/lib/types.ts`, and frontend contract fixtures together.

If a backend gap cannot be completed in the current milestone, the nominated scope lead records the reduced-screen choice in the decision log in `docs/06_IMPLEMENTATION_AND_TEAM_PLAN.md`. The entry must name the gap, chosen reduced behavior, hidden/disabled controls, acceptance criteria, owner, and follow-up trigger. A verbal agreement or a permanently decorative control is not sufficient.

## 10. Implementation stages and task board

Tasks are intentionally small and ordered by dependency. Each task should normally fit within two hours and end in a reviewable commit.

### Stage 0 — Contract and route foundation

- [ ] **FE-001:** Replace obsolete `Channel`, `ProcessingStatus`, and identity types in `frontend/lib/types.ts` with the current backend enums.
- [ ] **FE-002:** Add complete response/request types for analytics, alerts, profiles, match explanation, reviews, dashboard updates, and demo controls.
- [ ] **FE-003:** Expand `frontend/lib/api.ts` into typed endpoint functions with timeouts and shared error normalization.
- [ ] **FE-004:** Create the route group, root redirect, and empty page files for all seven screens.
- [ ] **FE-005:** Add contract-shaped fixtures for isolated component tests; mark them test-only.
- [ ] **FE-006:** Add separate Docker/server and browser API base URLs to `compose.yaml`, `.env.example`, and the API client.

**Gate:** TypeScript compiles; no frontend wire value contradicts `backend/app/core/enums.py`.

### Stage 1 — Visual foundation

- [ ] **FE-100:** Add project-local Tailwind and bundled SVG icon dependencies; do not retain any Stitch CDN resource.
- [ ] **FE-101:** Implement color, typography, spacing, radius, border, and focus tokens from `DESIGN.md`.
- [ ] **FE-102:** Build the responsive `AppShell`, navigation, top bar, global customer search, and connectivity state.
- [ ] **FE-103:** Build channel, identity, processing, severity, and review-status badges.
- [ ] **FE-104:** Build shared panels, metrics, buttons, inputs, skeletons, empty/error states, and JSON viewer.
- [ ] **FE-105:** Verify visible focus, skip link, landmark structure, text/icon dual encoding, and reduced-motion behavior.

**Gate:** A shell-only page matches the Stitch proportions at desktop/tablet/mobile without hard-coded business data.

### Stage 2 — Golden-path Journey Detail

- [ ] **FE-201:** Load and render profile header plus identifiers from `/api/profiles/{id}`.
- [ ] **FE-202:** Render alerts and deterministic recommended-action content.
- [ ] **FE-203:** Render the channel-colored timeline with search, channel filter, and order filter.
- [ ] **FE-204:** Build the match-explanation drawer and all three tabs.
- [ ] **FE-205:** Add Journey Detail loading, empty, no-alert, 404, partial-evidence-error, and full-error states.
- [ ] **FE-206:** Add component/integration tests for Riya timeline order and real evidence selection.

**Gate:** A user can open Riya, understand `ORD-204`, and inspect why an event was linked.

### Stage 3 — Command Centre

- [ ] **FE-301:** Connect analytics metrics with null-safe presentation.
- [ ] **FE-302:** Build the alert list and severity tabs without unsafe journey guessing.
- [ ] **FE-303:** Build recent activity and polling with deduplication.
- [ ] **FE-304:** Implement healthy, skeleton, empty, partial-failure, and retry states.
- [ ] **FE-305:** Connect shell queue badge and connection status to live responses.

**Gate:** The Command Centre contains no invented metric and updates safely through polling.

### Stage 4 — Customer Explorer

- [ ] **FE-401:** Implement URL-backed search and API pagination.
- [ ] **FE-402:** Build profile rows with masked identifiers, channel badges, event count, and last-seen time.
- [ ] **FE-403:** Build selected-profile preview using the profile-detail endpoint.
- [ ] **FE-404:** Add same-name differentiation and journey navigation.
- [ ] **FE-405:** Add loading, empty, network-error, and pagination-edge tests.
- [ ] **FE-406:** Add documented filters only after `BE-FE-02` passes its API tests.

**Gate:** Search for `ORD-204`, select Riya, and open her full journey.

### Stage 5 — Human review

- [ ] **FE-501:** Build Review Queue from the pending-review response.
- [ ] **FE-502:** Add conflict-first presentation and client-side search/channel filters.
- [ ] **FE-503:** Land `BE-FE-03` contract/types or explicitly constrain the temporary review-detail route.
- [ ] **FE-504:** Build review comparison, evidence panel, note input, and sticky actions.
- [ ] **FE-505:** Implement `approve_link`, `reject_link`, and `create_profile` with correct confirmation behavior.
- [ ] **FE-506:** Implement success, validation, already-resolved, and failure states.
- [ ] **FE-507:** Complete `BE-FE-06` before enabling approval for any conflicted record.

**Gate:** The demo reviewer creates a separate Aarav profile without a name-only or conflict-overridden merge.

### Stage 6 — Demo Controller

- [ ] **FE-601:** Implement reset confirmation and result summary.
- [ ] **FE-602:** Implement scenario start and pre-start speed choice.
- [ ] **FE-603:** Poll run status and render API-driven step progress.
- [ ] **FE-604:** Reconcile live alert/review counters through dashboard updates.
- [ ] **FE-605:** Add completed, failed, reset, reload-during-run, and double-start prevention tests.

**Gate:** Reset and run the six-step scenario three times without stale state or fabricated controls.

### Stage 7 — Data Pipeline

- [ ] **FE-701:** Agree and land `BE-FE-04`/`BE-FE-05`, or formally select the reduced truthful version.
- [ ] **FE-702:** Build funnel and channel summaries from real aggregate fields.
- [ ] **FE-703:** Build the paginated/polled event stream.
- [ ] **FE-704:** Build event inspector with raw, canonical, and decision tabs.
- [ ] **FE-705:** Add loading, empty, failed-event, duplicate-event, polling-degraded, and inspector-error states.

**Gate:** Every displayed pipeline fact is traceable to an API response.

### Stage 8 — Integration and release quality

- [ ] **FE-801:** Complete cross-screen navigation and preserve useful return URLs/search state.
- [ ] **FE-802:** Test desktop, collapsed tablet navigation, mobile navigation, drawers, and tables.
- [ ] **FE-803:** Test keyboard-only use, dialog focus, accessible labels, status announcements, and contrast.
- [ ] **FE-804:** Verify all null, empty, loading, partial, error, conflict, success, and already-resolved states.
- [ ] **FE-805:** Run typecheck, lint, build, frontend smoke tests, backend tests, and the two-minute presenter route.
- [ ] **FE-806:** Remove every control that is still decorative, unsupported, or P2-only.

**Gate:** The complete golden path works with the real backend, and the UI makes no unsupported operational claim.

## 11. State matrix

Every data surface must have intentional states. A spinner alone is not sufficient.

| State | Required presentation |
|---|---|
| Initial loading | Stable skeleton with the final layout dimensions |
| Background refresh | Keep current data, show subtle refresh state |
| Empty | Explain what is absent and provide one valid next action |
| Partial failure | Keep successful panels; isolate and label the failed request |
| Full network failure | Clear message, retry, and last-updated time if stale data remains |
| 404 | Entity-specific not-found message and route back to its list |
| 409 review conflict | Explain that the case is already resolved; refresh queue |
| 422 validation | Preserve form values and associate messages with inputs |
| Mutation pending | Disable duplicate submit and show progress in the initiating control |
| Mutation success | Confirm the exact saved action and resulting profile when present |
| Polling degraded | Keep last good data, label it stale, and offer manual retry |

## 12. Test plan

### 12.1 Contract tests

- Parse representative responses for every API function.
- Assert exhaustive label mappings for all enums.
- Assert `call_center` is never serialized as `call_centre`.
- Assert `review_required` is never sent as `manual_review`.
- Assert null analytics metrics remain null and render as unavailable.

### 12.2 Critical UI flows

1. Search `ORD-204` → select Riya → open journey → open evidence.
2. Run demo → observe progress → open completed Riya journey.
3. Open Aarav review → read conflict → create separate profile → confirm success.
4. Attempt conflicted approval → control remains unavailable and no request is sent.
5. Simulate 404/409/422/500/network failure and verify the relevant state.
6. Navigate and resolve the core flows with keyboard only.

### 12.3 Visual checks

For every screen, compare at these widths:

- 1440px desktop;
- 1024px collapsed-navigation/tablet;
- 390px mobile.

Review shell dimensions, type hierarchy, card spacing, table density, channel colors, status dual encoding, overlays, and sticky actions. Pixel similarity must never take priority over accurate data, readable content, or accessibility.

## 13. Verification commands

Run the smallest checks during development and the full set before handoff.

```bash
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm run lint
docker compose run --rm frontend npm run build
docker compose run --rm backend pytest -q
docker compose config
```

Then run the application and smoke-test the fixed presenter route:

```text
Command Centre
→ Demo Controller
→ Reset demo
→ Run scenario
→ Open Riya journey
→ Inspect one match explanation
→ Review Queue
→ Create separate Aarav profile
→ Return to Command Centre
```

## 14. Pull-request and handoff rules

- Keep one screen or shared layer per pull request where practical.
- Do not mix visual refactoring with API-contract changes.
- Include screenshots for desktop and mobile plus the state variants changed.
- For every API integration, list endpoint, request/query, success shape, error behavior, and test command.
- If a mock is still present, name it explicitly and state the removal condition.
- A screen is not done while any visible primary control is decorative.
- A screen is not done if a hard-coded metric looks like live backend data.
- A screen is not done if status is communicated only by color.

Suggested commit sequence:

```text
fix(frontend): sync types with frozen API enums
feat(frontend): add Stitch operations shell and tokens
feat(frontend): build API-backed journey detail
feat(frontend): add match explanation drawer
feat(frontend): connect command centre metrics and polling
feat(frontend): add customer search and preview
feat(frontend): implement review queue and resolution
feat(frontend): add deterministic demo controller
feat(frontend): add truthful pipeline inspector
test(frontend): cover golden path and edge states
```

## 15. Frontend definition of done

The frontend is complete when:

- all seven supplied screens have a truthful implemented route or an explicitly approved reduced state;
- the visual system is shared rather than copied page by page;
- every runtime value comes from the backend or a clearly labelled deterministic presenter;
- the Riya/`ORD-204` timeline and alerts are understandable without backend knowledge;
- evidence is one click from every timeline event;
- a same-name or strong-conflict record cannot be accidentally merged;
- loading, empty, partial, error, and success states exist;
- desktop, tablet, mobile, keyboard, and contrast checks pass;
- TypeScript strict mode, lint, build, backend tests, and the demo smoke route pass; and
- the two-minute golden path remains focused on explainable identity resolution and broken-refund journeys.
