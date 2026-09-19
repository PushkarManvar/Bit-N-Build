# GitHub and Collaboration Setup

## Repository creation

Recommended initial settings:

- Name: `journeylens`
- Visibility: private until the team chooses otherwise
- Default branch: `main`
- Do not initialize with generated README or `.gitignore` when pushing this prepared repository

## First push

```bash
git init -b main
git add .
git commit -m "chore: initialize JourneyLens scaffold"
git remote add origin <repository-url>
git push -u origin main
```

## Collaborator onboarding

Each teammate should:

```bash
git clone <repository-url>
cd journeylens
cp .env.example .env
make doctor
make setup
make up
```

Then open the frontend, backend health endpoint, and API documentation.

## Recommended branch protection

After the initial push, protect `main` with:

- Require a pull request before merging.
- Require the `Backend`, `Frontend`, and `Docker configuration` checks.
- Require branches to be up to date before merging.
- Block force pushes and branch deletion.
- Allow squash merge.
- Keep administrator bypass disabled during the final build if practical.

## Agent commits

`AGENTS.md` and `opencode.json` allow project-local staging and commits without a separate prompt. Normal pushes occur only when the user has asked to publish to the configured remote. Force pushes remain denied.

## CI behavior

`.github/workflows/ci.yml` runs on pushes to `main` and all pull requests. It verifies:

- Python dependencies, Ruff, and pytest;
- Node dependencies, ESLint, TypeScript, and the Next.js production build;
- Docker Compose configuration and service image builds.

CI uses read-only repository contents permission and does not deploy.

## Secrets

The scaffold requires no GitHub Actions secrets. Add secrets only when deployment or an external service is introduced. Never place secrets in workflow YAML or repository variables intended for non-sensitive data.

## Pull-request review order

1. Product and scope alignment.
2. Identity-safety implications.
3. API or migration compatibility.
4. Automated test result.
5. UI behavior and accessibility.
6. Documentation and demo impact.
