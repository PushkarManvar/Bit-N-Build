# JourneyLens — Team Kickoff

Read this fully, then follow the steps. You are already a collaborator on the repo — accept the GitHub invite first.

## Step 1 — Install (one-time)

- Git
- Docker Desktop (start it)
- A code editor

Nothing else. Everything runs in Docker.

## Step 2 — Clone + start

```bash
git clone https://github.com/PushkarManvar/Bit-N-Build.git
cd Bit-N-Build
cp .env.example .env
docker compose up --build
```

The first build takes 5–10 minutes. Then check:

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>
- DB: `localhost:5432`

## Step 3 — Daily start/stop

```bash
docker compose up            # start
docker compose down          # stop (keeps data)
docker compose down --volumes   # reset data — ONLY when told
```

## Step 4 — Work rules (non-negotiable)

1. **NEVER push to `main`. Nobody but Pushkar merges to `main`.**
2. Pull before starting work: `git pull`
3. Own branch per task: `git switch -c frontend/journey-detail`
4. Small commits, one intent each, Conventional Commit format:
   `feat(api): persist raw and canonical events`
5. Never commit: `.env`, secrets, `node_modules`
6. Before pushing a branch, run the checks:
   ```bash
   docker compose run --rm backend pytest -q
   docker compose run --rm backend ruff check app tests
   docker compose run --rm frontend npm run typecheck
   docker compose run --rm frontend npm run lint
   ```
7. Push your branch, then open a **Pull Request** on GitHub.
8. In the PR description write: what you built, how to test it, and any API contract change. Tag a teammate to review.
9. Pushkar reviews and merges. Do not merge your own PR.

## Step 5 — Read first, in order

Docs live in `docs/`:

1. `00_START_HERE.md` — read before anything else
2. `01_PRODUCT_REQUIREMENTS.md`
3. `05_API_CONTRACT.md` — frontend and backend share this; do not break it
4. `06_IMPLEMENTATION_AND_TEAM_PLAN.md` — your role assignment

## Roles

- **Preet + Bhagya (frontend):** Next.js pages in `frontend/app/`, components, types in `frontend/lib/types.ts`, API calls in `frontend/lib/api.ts`
- **Pushkar + Lalit (backend + data):** FastAPI in `backend/app/`, rules and services in `backend/app/services/`, fixtures in `data/`, hidden truth in `data/truth/`

## Golden rule

`main` must always run. Test before you claim something is done. If a contract field needs changing, tell the whole team before you change it.