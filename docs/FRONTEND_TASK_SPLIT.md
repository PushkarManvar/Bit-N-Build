# Frontend Task Split — Bhagya & Preet

Backend is fully shipped (G1–G7 merged, APIs live). This splits the Stitch-screen build
between the two of you. Read `docs/12_STITCH_FRONTEND_IMPLEMENTATION_GUIDE.md` first —
it is the blueprint. Do your tasks in the order below; dependencies matter.

## Setup (both, once)

```bash
git fetch origin
git switch main
git reset --hard origin/main
cp .env.example .env
docker compose up --build
```

- Frontend: <http://localhost:3000> · API docs: <http://localhost:8000/docs>
- Read `docs/05_API_CONTRACT.md` (frozen — never rename fields) and `docs/02_USER_WORKFLOWS_AND_UX.md`.

## Bhagya — Tasks 1, 3, 5 (journey + evidence)

| # | Task | Branch | Depends on |
|---|---|---|---|
| 1 | **Fix `frontend/lib/types.ts`** to frozen contract (`call_center`, `received\|normalized\|failed`, `auto_linked\|review_required\|new_profile`, new event types). Centralize types + requests in `lib/types.ts` / `lib/api.ts`. | `frontend/types` | — |
| 3 | **Customer Explorer** — `GET /api/profiles` list + search, empty/loading/error states. | `frontend/customer-explorer` | #1 |
| 5 | **Journey Detail + Match explanation** — `GET /api/profiles/{id}` timeline + alerts; `GET /api/events/{id}/match-explanation` evidence drawer (evidence, conflicts, raw + normalized payloads). | `frontend/journey-detail` | #3 |
| 7 | **Review queue + actions** — `GET /api/reviews`, `POST /api/reviews/{id}/resolve` (`approve_link` needs `selected_profile_id`; `reject_link` / `create_profile`). Confirmation + success states. | `frontend/review-queue` | #5 |

## Preet — Tasks 2, 4, 6 (dashboard + controls)

| # | Task | Branch | Depends on |
|---|---|---|---|
| 2 | **Command Centre / Dashboard** — KPI cards (`GET /api/analytics/overview`, `/analytics/channels`), alert list (`GET /api/alerts`), recent events feed polling `GET /api/dashboard/updates?since=`. | `frontend/dashboard` | #1 |
| 4 | **Demo controller** — `POST /api/demo/reset`, `POST /api/demo/start`, `GET /api/demo/{run_id}`, progress control + completed state. | `frontend/demo-controller` | #2 |
| 6 | **Demo wiring + polish** — full presenter flow: Command Centre → Run demo → open Riya alert → match explanation → Reviews → keep Aarav separate → metrics. Poll only while visible. | `frontend/demo-polish` | #4 + #7 |

## Rules

- **Never push to `main`.** Push your branch → open PR → tag the other for review → Pushkar merges.
- Before pushing a branch:
  ```bash
  docker compose run --rm frontend npm run typecheck
  docker compose run --rm frontend npm run lint
  ```
- Loading / empty / error states on every view; no colour-only status.
- TypeScript strict; server components by default; client components only for interaction.
- **Coordinating handoff:** Bhagya finishes #1 first — Preet starts #2 only after #1 is on main. The two lines join at #6/#7.
- Don't touch backend. If an API shape looks wrong, tell Pushkar before changing anything.

## Definition of done

Wired to the real API (no mock data), happy + empty + error states pass, typecheck + lint green, demo-able in under a minute.