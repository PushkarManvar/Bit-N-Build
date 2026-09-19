# JourneyLens Product Requirements Document

**Version:** 1.0  
**Status:** Approved MVP scope  
**Primary audience:** Product, design, frontend, backend, data, QA, and demo presenter

## 1. Executive summary

JourneyLens helps e-commerce support teams understand refund and return cases when customer interactions are fragmented across channels. It connects records using transparent identity evidence, builds one chronological journey, detects unresolved refund friction, and routes ambiguous cases to a human.

The MVP is a focused decision-support product built with synthetic data. It does not execute refunds, contact customers, or replace a CRM.

## 2. Problem statement

Support teams receive records from multiple systems, each with different fields and incomplete identity information. An anonymous website event may contain only a device ID. A mobile event may contain an email. A support call may contain a phone and order ID. A store interaction may contain a return reference.

Without normalization and identity resolution:

- the same customer appears as multiple records;
- agents manually search several systems;
- repeated contacts look unrelated;
- unresolved refunds remain hidden;
- weak name matches may merge different people; and
- management sees channel activity without the real customer story.

## 3. Product vision

> Give every support agent a trustworthy, evidence-backed view of the complete customer journey and the unresolved operational issue behind it.

## 4. Goals

### MVP goals

1. Normalize four deliberately inconsistent channel formats.
2. Link events using deterministic and inspectable identity evidence.
3. Protect against false merges and expose uncertainty.
4. Show the resulting customer journey in chronological order.
5. Detect unresolved refunds and repeat contact.
6. Produce measurable matching performance from labelled synthetic data.
7. Tell the complete product story in under two minutes.

### Non-goals

- Production-scale master data management.
- Customer consent or enterprise governance implementation.
- Real customer ingestion or PII handling.
- Payment gateway or refund execution.
- General customer-service ticketing.
- Autonomous identity or refund decisions.
- Predictive churn modelling.
- A general-purpose chatbot.

## 5. Personas

### Support agent

**Context:** Handling a customer asking why a refund has not arrived.  
**Need:** See the complete interaction history without searching several tools.  
**Decision:** What happened and what should I do next?  
**Risk:** Acting with incomplete context or asking the customer to repeat information.

### Support operations manager

**Context:** Monitoring unresolved cases and repeat contact.  
**Need:** Identify the journeys causing the most effort and escalation.  
**Decision:** Which cases should be prioritized?  
**Risk:** Optimizing channel-level metrics while missing journey-level failures.

### Data-quality reviewer

**Context:** Resolving a candidate identity match that cannot be safely automated.  
**Need:** Compare evidence and conflicts in one place.  
**Decision:** Merge, reject, or create a separate profile.  
**Risk:** Merging two different customers or fragmenting one customer unnecessarily.

## 6. Jobs to be done

| Situation | Motivation | Expected outcome |
|---|---|---|
| A customer contacts support about a refund | Understand everything that already happened | Resolve the case without repeated questioning |
| A record arrives with incomplete identifiers | Connect it safely to existing history | Preserve continuity without guessing |
| Evidence is ambiguous or contradictory | Examine the basis of the proposed match | Make and audit a human decision |
| Several contacts occur around one order | Recognize the journey-level pattern | Prioritize the unresolved case |
| The team claims its matcher works | Verify performance against known truth | Report honest precision, recall, F1, and false merges |

## 7. User stories

### Epic A — Ingestion and normalization

- As a system operator, I want each source payload preserved so processing decisions remain auditable.
- As a developer, I want four source adapters to produce one canonical schema so downstream logic is channel-independent.
- As an operator, I want duplicates and failures visible so they do not silently corrupt metrics.

### Epic B — Identity resolution

- As an agent, I want incoming events connected to an existing profile when strong evidence agrees.
- As a reviewer, I want ambiguous or conflicting events held for review.
- As an agent, I want an explanation of why an event was linked.
- As a customer, I should not be merged with another person because our names are similar.

### Epic C — Unified journey

- As an agent, I want all linked events in chronological order.
- As an agent, I want to distinguish web, app, call-centre, and store interactions.
- As an agent, I want to inspect the original source record behind any timeline item.

### Epic D — Journey intelligence

- As a manager, I want unresolved refunds detected automatically.
- As a manager, I want repeated contacts grouped as one journey problem.
- As an agent, I want each alert to include evidence and a recommended operational next action.

### Epic E — Human review

- As a reviewer, I want candidate profiles, evidence, conflicts, and missing fields side by side.
- As a reviewer, I want to approve a match, reject it, or create a new profile.
- As an auditor, I want the reviewer, action, note, and time preserved.

### Epic F — Evaluation and demonstration

- As a judge, I want to see a correct merge and correct non-merge.
- As a team, we want metrics calculated from hidden ground truth.
- As a presenter, I want a deterministic playback so the story never depends on live external services.

## 8. Functional requirements

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| FR-001 | P0 | Accept a single raw event | Valid request returns a persistent raw event ID and processing outcome |
| FR-002 | P0 | Accept bulk demo events | Batch response reports received, processed, duplicate, failed, and review counts |
| FR-003 | P0 | Preserve raw payloads | Original JSON is retrievable and never modified by normalization |
| FR-004 | P0 | Detect source duplicates | Repeated `(source, source_record_id)` does not create new canonical data |
| FR-005 | P0 | Normalize four channels | Every supported source maps to the documented canonical fields |
| FR-006 | P0 | Preserve failed processing | Normalization failure keeps the raw event and records a reason |
| FR-007 | P0 | Retrieve identity candidates | Strong identifiers and device/session evidence produce candidate profiles |
| FR-008 | P0 | Score matches conservatively | Scores and thresholds follow the documented policy and remain capped |
| FR-009 | P0 | Block conflicting identities | A strong conflict always prevents auto-linking |
| FR-010 | P0 | Create a match decision | Candidates, selected profile, evidence, conflicts, score, and outcome are stored |
| FR-011 | P0 | Create new profiles | A low-confidence event can create a separate profile |
| FR-012 | P0 | Build a timeline | Linked events display chronologically with channel and identity explanation |
| FR-013 | P0 | Detect unresolved refunds | The Riya `ORD-204` scenario creates exactly one open high-severity alert |
| FR-014 | P0 | Detect repeat contact | Two or more relevant contacts in 72 hours create exactly one open alert |
| FR-015 | P0 | Prevent name-only merges | Similar names without corroboration never auto-link |
| FR-016 | P1 | List pending reviews | Review queue shows event, best candidate, evidence, conflicts, and reason |
| FR-017 | P1 | Resolve reviews | Reviewer can approve, reject, or create a profile and preserve an audit record |
| FR-018 | P1 | Search profiles | User can find profiles by name, email, phone, order, or alert status |
| FR-019 | P1 | Show overview metrics | Dashboard uses computed values rather than hard-coded claims |
| FR-020 | P1 | Run deterministic demo | Fixed events play in the intended order and can be reset |
| FR-021 | P2 | Detect channel switching | Three or more channels within 48 hours create a medium alert |
| FR-022 | P2 | Generate a journey summary | Summary only restates verified timeline and alert facts |

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Safety | Minimize false merges; conflict rules override score |
| Explainability | Every automated link is traceable to field-level evidence |
| Auditability | Raw events and decisions are append-only for the MVP |
| Performance | A single synthetic event normally processes in under one second locally |
| Reliability | The core demo works without an LLM or external integration |
| Idempotency | Duplicate source messages do not duplicate downstream records |
| Testability | Normalization, matching, conflict, and alert logic have automated tests |
| Privacy | Use synthetic data only; never commit credentials |
| Accessibility | Keyboard-reachable controls, labelled buttons, readable contrast, and non-colour status cues |
| Observability | Failures include a stage, code, message, and related raw event ID |

## 10. Success metrics

### Product and model metrics

| Metric | Meaning | MVP direction |
|---|---|---|
| Match precision | Share of predicted links that are correct | Prioritize over recall |
| Match recall | Share of true links discovered | Report honestly |
| F1 score | Balance of precision and recall | Compute from truth data |
| False-merge rate | Different customers incorrectly combined | Keep as low as possible; target ≤2% in synthetic data |
| Review rate | Events needing a human | Expected and acceptable for ambiguity |
| Alert precision | Generated alerts that match expected truth | Target 100% for seeded flagship cases |
| Processing latency | Event receipt to decision | Usually <1 second locally |

### Demonstration metrics

- Golden path succeeds on three consecutive resets.
- Full story completes in under two minutes.
- Presenter can reach raw evidence in two clicks from the journey.
- No external network dependency is required for the core story.

## 11. Assumptions

- Order IDs are strong identity evidence within this controlled refund domain.
- Synthetic data can represent missing fields, duplicates, conflicts, and anonymous-to-known transitions convincingly.
- A support agent benefits more from a trustworthy timeline than from autonomous resolution.
- A deterministic matcher is sufficient for the hackathon's targeted dataset.
- Judges will value explainability and safe non-merging as visible differentiation.

## 12. Dependencies

- Shared canonical schema and enum definitions.
- PostgreSQL connection and migrations.
- Stable sample payloads for all four channels.
- Hidden truth data accessible to the evaluation script but not ingestion.
- Mock API responses available to frontend before backend completion.

## 13. Risks and mitigations

| Risk | Early signal | Mitigation |
|---|---|---|
| Matching produces false merges | Aarav or conflict tests link automatically | Tighten thresholds; block on conflict; pivot if unresolved by hour 10 |
| Frontend waits for backend | UI work has no stable data shape | Freeze mocks from the API contract at hour 2 |
| Dataset looks too clean | Nearly every event auto-links | Add missing fields, formatting differences, duplicates, and conflicts |
| Dashboard obscures the mechanism | Demo begins with charts | Start at the event or alert and open evidence quickly |
| Live playback fails | Timing or SSE becomes unstable | Use polling and a pre-seeded fallback |
| LLM distracts the team | Summary work begins before G4 | Defer AI until all P0 acceptance tests pass |

## 14. Release criteria

The MVP may be presented only when:

- all P0 requirements pass;
- Riya's journey links correctly;
- both Aarav customers remain separate;
- the two primary alerts appear exactly once;
- metrics are generated from truth data;
- the review decision persists;
- the deterministic demo resets successfully; and
- a backup recording and screenshots exist.
