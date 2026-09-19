# Contributing to JourneyLens

## Setup

```bash
git clone <repository-url>
cd journeylens
cp .env.example .env
docker compose up --build
```

See `docs/08_LOCAL_DEVELOPMENT.md` for native and Docker workflows.

## Branches

Create a short-lived branch from `main`:

```bash
git switch main
git pull --ff-only
git switch -c backend/event-ingestion
```

Suggested prefixes:

- `frontend/`
- `backend/`
- `data/`
- `docs/`
- `fix/`

## Commits

Use small, reviewable commits:

```text
feat(api): ingest and preserve raw events
feat(identity): block strong identifier conflicts
test(journey): cover unresolved refund detection
fix(ui): distinguish same-name customer profiles
docs(setup): clarify Docker startup
```

Coding agents may stage and create local commits without requesting separate approval when relevant checks pass. Force-pushes and destructive history changes are prohibited.

## Pull requests

- Explain the user outcome, not only the files changed.
- Link the relevant requirement or documentation section.
- Include tests and screenshots for visible UI changes.
- State any API or migration change explicitly.
- Keep unrelated refactors separate.
- Require CI to pass before merge.

## Required checks

```bash
make lint
make test
docker compose config
```

For Docker-related changes:

```bash
docker compose build
```

## Product guardrails

- Synthetic data only.
- Do not auto-link using name alone.
- Strong conflicts require review.
- Do not use an LLM for identity matching or alert truth.
- Preserve raw input and explain automated decisions.
