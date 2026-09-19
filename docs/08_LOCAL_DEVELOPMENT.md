# Local Development Setup

## Recommended Docker workflow

### Prerequisites

- Git
- Docker Desktop on Windows/macOS, or Docker Engine on Linux
- Docker Compose v2 (`docker compose`, not legacy `docker-compose`)

### Start

```bash
git clone <repository-url>
cd journeylens
make doctor
make setup
make up
make ps
```

Services:

| Service | URL/port |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend | <http://localhost:8000> |
| OpenAPI | <http://localhost:8000/docs> |
| PostgreSQL | `localhost:5432` |

### Logs

```bash
make logs
```

### Tests

```bash
make test
make lint
```

### Stop without deleting data

```bash
make down
```

### Intentional database reset

This deletes the local PostgreSQL volume:

```bash
docker compose down --volumes
```

Do not run the reset command unless local data may be discarded.

## Windows guidance

Use Docker Desktop with WSL 2. Clone the repository inside the WSL filesystem for better file-watching performance. Run commands from a WSL terminal.

## Native development

Docker remains the source-of-truth environment. Native processes may be useful for faster iteration.

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

When the backend runs outside Docker, set `DATABASE_URL` to use `localhost` rather than the Compose service name `db`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Port already in use

Stop the conflicting process or change the host-side port in `compose.yaml`. Keep container ports unchanged.

### Backend waits for database

```bash
docker compose ps
docker compose logs db
```

The backend begins only after the database health check passes.

### Dependency volume is stale

Rebuild the affected image. Remove only the named frontend dependency volume if necessary and after confirming it contains no user data.

### `.env` problems

Compare keys with `.env.example`. Never commit `.env`.

## Environment contract

| Variable | Used by | Meaning |
|---|---|---|
| `DATABASE_URL` | Backend | SQLAlchemy PostgreSQL URL |
| `CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | Frontend | Browser/server API base URL |
| `POSTGRES_*` | Database | Local Compose database settings |
