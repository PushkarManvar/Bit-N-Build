# JourneyLens

Explainable customer identity resolution and broken-journey detection for e-commerce refunds.

JourneyLens connects fragmented web, mobile-app, call-centre, and physical-store events into an evidence-backed customer timeline. It detects unresolved refunds and repeated contact while routing uncertain identity matches to human review.

## Quick start with Docker

Prerequisites:

- Git
- Docker Desktop or Docker Engine with Docker Compose v2

```bash
git clone <repository-url>
cd journeylens
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>
- Backend API documentation: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

Stop the stack:

```bash
docker compose down
```

Delete local development data only when intentionally resetting:

```bash
docker compose down --volumes
```

## Development commands

```bash
make doctor       # Check required local tools
make setup        # Create .env and build images
make up           # Start the development stack
make logs         # Follow application logs
make test         # Run backend and frontend checks
make lint         # Run linters and type checks
make down         # Stop services without deleting data
```

## Repository layout

```text
backend/          FastAPI application and tests
frontend/         Next.js application
data/             Synthetic inputs and hidden evaluation truth
docs/             Product, workflow, architecture, and runbook documentation
scripts/          Setup and validation helpers
.github/          Continuous integration and collaboration templates
AGENTS.md         Project rules for OpenCode and other coding agents
opencode.json     OpenCode instructions and approval policy
```

## Start here

1. Read [docs/00_START_HERE.md](docs/00_START_HERE.md).
2. Read [AGENTS.md](AGENTS.md) before using a coding agent.
3. Follow [docs/08_LOCAL_DEVELOPMENT.md](docs/08_LOCAL_DEVELOPMENT.md).
4. Paste [OPENCODE_BOOTSTRAP_PROMPT.md](OPENCODE_BOOTSTRAP_PROMPT.md) into OpenCode for the first implementation session.
5. Use [GITHUB_PUBLISH_PROMPT.md](GITHUB_PUBLISH_PROMPT.md) when the verified repository is ready for GitHub.

## Current stage

This repository is an implementation-ready scaffold. The initial application includes health endpoints and a minimal frontend; the product vertical slice should be implemented in the order documented in `docs/00_START_HERE.md`.

## Safety boundary

- Synthetic data only.
- No real customer PII.
- No real refund execution.
- No LLM-driven identity decisions.
- Similar names alone must never auto-merge profiles.

## Documentation

The full documentation index is available in [docs/README.md](docs/README.md).
