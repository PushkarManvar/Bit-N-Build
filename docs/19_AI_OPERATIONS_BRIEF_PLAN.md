# AI Operations Brief and Journey Intelligence Upgrade

## Purpose

Make the Journey Intelligence page feel like an analyst's operational dossier:
it must show which open refund needs attention first, why it ranks there, and
what evidence supports that conclusion. The deterministic Friction Radar stays
the authority. An LLM may only turn the already-returned radar facts into an
optional, clearly labelled short brief.

## Non-negotiable boundaries

- Identity resolution, alert creation, score calculation, and score ordering
  remain deterministic and never call an LLM.
- The AI receives only the safe Friction Radar response: profile display name,
  order reference, score components, counts, bands, and alert IDs. It receives
  no raw payload, identifier value, hidden truth, or evidence detail.
- The AI is never allowed to resolve an alert, make a refund decision, claim
  payment status, or state a fact that was not supplied in its source packet.
- The main page remains fully useful when AI is disabled, unavailable, rate
  limited, or offline.
- Keys remain backend-only environment variables and are never returned by an
  endpoint or exposed through `NEXT_PUBLIC_*` configuration.

## Deterministic analytics additions

The existing radar response remains unchanged. The UI derives an operational
posture from its persisted fields:

| Signal | Source | Meaning |
|---|---|---|
| Highest score | first ranked journey | deterministic next journey to inspect |
| Repeat-contact exposure | `has_open_repeat_contact_alert` | a related alert is still open |
| Candidate review exposure | `pending_candidate_review_count` | a pending decision names that profile and order; it is not a link |
| Support concentration | `support_contact_channels` | raw support-contact count by channel |
| Age concentration | `unresolved_age_distribution` | whole elapsed days since earliest persisted return request |

No churn prediction, latency/SLA measurement, payment claim, or fabricated
trend enters the page.

## AI brief contract

### `POST /api/analytics/friction-radar/brief`

The request recomputes the deterministic radar at the request boundary and
uses its top five ranked journeys as the source packet. It returns:

```json
{
  "headline": "ORD-301 has the strongest persisted friction signal",
  "summary": "Vivaan Reddy has an elevated score of 43 from four unresolved days, two support contacts, an open repeat-contact alert, and one pending candidate review.",
  "focus_alert_id": "uuid",
  "highlighted_signal": "repeat_contact",
  "provider": "google",
  "model": "gemini-3.6-flash",
  "generated_at": "2026-09-20T12:00:00Z",
  "cached": false
}
```

`focus_alert_id` must exist in the source packet. `highlighted_signal` is one
of `unresolved_age`, `support_channels`, `support_contacts`,
`repeat_contact`, or `candidate_review`, and must be true/non-zero for the
selected journey. Pydantic validates the JSON response after provider output.

Provider order is Google AI Studio primary, then Groq backup. A fallback is
allowed only after timeout, HTTP 429, or HTTP 5xx. Invalid credentials,
invalid models, malformed output, and other client-side errors return a shared
`AI_BRIEF_UNAVAILABLE` error; they do not silently fall through to hide setup
issues. A five-minute in-process cache avoids repeated generation for an
unchanged deterministic source packet.

## UI design

Audience: an operations analyst triaging unresolved refunds. Single job:
identify the next journey to inspect and understand the supporting evidence.

Palette: **Ink** `#172554`, **Signal Violet** `#5146E5`, **Evidence Mint**
`#0F766E`, **Escalation Amber** `#B54708`, **Critical Red** `#B42318`, and
**Paper** `#F8FAFC`.

The signature element is the **case strip**: a horizontally readable score
decomposition that visually connects a ranked case to the exact source signals
that make up its friction score. It is data, not decoration.

```text
Operational posture / snapshot / refresh
┌── Priority case ─────────────┐ ┌── AI operations brief ─┐
│ selected order + score strip │ │ Generate / provider    │
│ factual signal chips         │ │ wording + source note  │
└──────────────────────────────┘ └────────────────────────┘
┌── Ranked case queue ─────────┐ ┌── Evidence & actions ──┐
│ compact selected row detail  │ │ score ledger           │
└──────────────────────────────┘ └────────────────────────┘
┌── Age concentration ─────────┐ ┌── Support concentration ┐
└──────────────────────────────┘ └─────────────────────────┘
```

The AI panel is intentionally quiet and never mimics a chat box. It has an
explicit source label, its provider/model, a retry action, and an unavailable
state that leaves the deterministic dossier intact.

## Tests and proof

Public seams:

1. `GET /api/analytics/friction-radar` remains the authoritative deterministic
   snapshot.
2. `POST /api/analytics/friction-radar/brief` returns a validated brief whose
   focus alert and highlighted signal exist in the snapshot, or a shared error.
3. The browser page loads the deterministic dossier even if the brief request
   fails, and can render a successful brief separately.

Proof includes API tests for empty data, validated provider output, invalid
provider output, and retryable primary-to-backup fallback. Frontend typecheck,
lint, production build, and a live browser smoke check complete the slice.
