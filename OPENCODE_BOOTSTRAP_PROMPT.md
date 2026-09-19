# OpenCode Bootstrap Prompt

Paste the prompt below into OpenCode from the repository root.

---

Read `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and the instruction files loaded by `opencode.json` before making changes.

Your task is to take this JourneyLens scaffold from “clone-ready foundation” to a verified development environment and the first working vertical slice.

Work autonomously inside this repository. You do not need to ask before editing files, installing project-local dependencies, running Docker Compose, running tests, staging changes, or creating local commits. Follow all protected-action rules in `AGENTS.md`; never force-push, rewrite history, delete data volumes, expose secrets, or weaken identity safety rules.

Execute this plan:

1. Inspect the repository and report any conflict between code and documentation.
2. Check Git, Docker Engine/Desktop, Docker Compose v2, Node.js, npm, and Python availability.
3. If Docker is missing, identify the operating system and provide the official installation command or link. Do not run privileged system installation commands without the user's authorization.
4. Copy `.env.example` to `.env` when `.env` does not exist. Never overwrite a populated `.env`.
5. Install frontend and backend dependencies locally and generate/update lock files. Keep supported versions compatible with the Dockerfiles and CI.
6. Validate `opencode.json`, Compose configuration, Python configuration, TypeScript configuration, and GitHub Actions YAML.
7. Build the Docker images and start PostgreSQL, backend, and frontend.
8. Verify the backend health endpoint, frontend response, API documentation, and database health.
9. Run backend tests, Ruff, frontend lint, frontend type checking, and the production frontend build.
10. Fix all scaffold/configuration problems you discover.
11. Implement the first documented vertical slice only:
    - accept one web event at `POST /api/events`;
    - preserve its raw payload;
    - normalize it into the canonical event shape;
    - return a documented processing response;
    - show the resulting event on the Journey Detail page;
    - add backend tests for the normalization and endpoint.
12. Do not add authentication, an LLM, SSE, enterprise integrations, or extra dashboard charts.
13. Update README/setup documentation if actual commands differ from documented commands.
14. Run the relevant verification again.
15. Create small local commits without asking for separate commit approval. Use messages such as:
    - `chore: verify development scaffold`
    - `feat(api): add first web event ingestion slice`
    - `feat(ui): render initial journey event`
16. Do not create a GitHub repository during this bootstrap unless the user explicitly asks you to continue directly into publishing. Use `GITHUB_PUBLISH_PROMPT.md` for the dedicated GitHub workflow.

At completion, provide:

- services started and their URLs;
- checks run and results;
- commits created;
- remaining blockers;
- the next three tasks from `docs/00_START_HERE.md`.

---

Recommended launch:

```bash
opencode --auto
```

The repository configuration still denies destructive Git commands and asks before pushes or privileged system changes.
