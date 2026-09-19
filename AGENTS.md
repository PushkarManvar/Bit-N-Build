# JourneyLens Agent Instructions

These instructions apply to OpenCode and any other coding agent working in this repository.

## Mission

Build JourneyLens as a focused, explainable identity-resolution and broken-refund-journey product. Preserve the golden path:

1. ingest a raw channel event;
2. normalize it;
3. make an explainable identity decision;
4. show the unified customer timeline;
5. detect unresolved refund and repeated contact; and
6. route uncertainty to human review.

Do not turn the project into a generic CRM, chatbot, payment system, or enterprise data platform.

## Read before changing code

Always read:

- `README.md`
- `docs/00_START_HERE.md`
- the documentation relevant to the task

Task-specific sources:

- Product scope: `docs/01_PRODUCT_REQUIREMENTS.md`
- UX behavior: `docs/02_USER_WORKFLOWS_AND_UX.md`
- Architecture: `docs/03_TECHNICAL_ARCHITECTURE.md`
- Matching and alerts: `docs/04_DATA_IDENTITY_AND_RULES.md`
- API shapes: `docs/05_API_CONTRACT.md`
- Team plan: `docs/06_IMPLEMENTATION_AND_TEAM_PLAN.md`
- Tests and demo: `docs/07_TESTING_EVALUATION_AND_DEMO.md`

## Architecture rules

- Keep a modular monolith: Next.js frontend, FastAPI backend, PostgreSQL database.
- Preserve raw source payloads before downstream processing.
- Use deterministic rules for normalization, identity resolution, conflicts, and journey alerts.
- An LLM may summarize verified facts only; it must never decide identity or alert truth.
- A strong-identifier conflict always blocks automatic linking.
- Name similarity alone never auto-links.
- Runtime matching must never read hidden ground-truth files.
- Prefer polling for the baseline demo; SSE is optional.
- Avoid Kafka, Redis, microservices, background queues, and other infrastructure until the documented MVP proves a need.

## Code standards

### Backend

- Python 3.12.
- Type all public functions.
- Use Pydantic models at API boundaries.
- Keep HTTP concerns in `app/api/`; business rules belong in `app/services/`.
- Keep normalization and scoring functions pure where practical.
- Use one shared error response shape.
- Add or update pytest tests with every rule change.
- Run Ruff before committing.

### Frontend

- TypeScript strict mode.
- Use server components by default; add client components only for interaction.
- Centralize API types in `frontend/lib/types.ts` and requests in `frontend/lib/api.ts`.
- Implement loading, empty, error, and success states.
- Do not communicate status using colour alone.
- Keep core pages functional before adding visual polish or extra charts.

### Data and migrations

- Migrations are append-only after sharing with the team.
- Do not silently edit an applied migration; create a new one.
- Never commit `.env`, secrets, generated customer PII, or local database volumes.
- Synthetic visible data and hidden truth data must remain separate.

## Commands

Preferred commands:

```bash
make doctor
make setup
make up
make test
make lint
make down
```

Focused checks:

```bash
docker compose run --rm backend pytest -q
docker compose run --rm backend ruff check app tests
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm run lint
docker compose config
```

## Agent authority

Within the current repository, the agent may proceed without requesting separate permission to:

- inspect files and Git history;
- create or edit project files;
- install project-local dependencies;
- run formatters, linters, tests, and builds;
- run Docker Compose development commands;
- create feature branches;
- stage changes with `git add`; and
- create local commits after relevant verification passes.

The agent should make small, meaningful commits and may commit completed work without asking “May I commit?” first.

## Protected actions

The agent must not do any of the following without explicit user direction:

- force-push;
- rewrite shared history;
- run `git reset --hard` or destructive `git clean`;
- delete branches, tags, repositories, data volumes, or user files;
- push secrets;
- change repository visibility;
- bypass failing CI;
- weaken conflict or false-merge protections; or
- publish/deploy to an external environment that was not requested.

Ordinary `git push` is allowed only when the current task explicitly requests publishing to the configured remote. Local commits never require an extra confirmation.

## Git workflow

- Keep `main` runnable.
- Use short branches such as `backend/event-ingestion`, `frontend/journey-detail`, or `data/identity-tests`.
- Use Conventional Commit-style messages where practical.
- Do not mix unrelated refactors with feature work.
- Before committing, run the smallest relevant checks; before a handoff, run `make test` and `make lint` when available.
- Never commit generated secrets, `.env`, database data, or dependency directories.

## Required verification by change type

| Change | Minimum verification |
|---|---|
| Normalization or identity rule | Unit tests plus conflict/non-merge tests |
| API contract | API tests plus frontend type check |
| Database schema | Migration applies on a clean database |
| Frontend flow | Type check, lint, and core page smoke test |
| Docker/configuration | `docker compose config` and image build |
| CI workflow | YAML parse plus locally equivalent commands |
| Documentation only | Link/path and command review |

## Definition of done

A change is done when it is implemented, documented when necessary, covered by relevant tests, verified with the appropriate commands, and committed without breaking the golden path.
