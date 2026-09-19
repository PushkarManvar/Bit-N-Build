.PHONY: doctor setup up down logs ps build test lint format backend-test frontend-test clean

doctor:
	@./scripts/doctor.sh

setup:
	@./scripts/bootstrap.sh

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend frontend db

ps:
	docker compose ps

build:
	docker compose build

backend-test:
	docker compose run --rm backend pytest -q

frontend-test:
	docker compose run --rm frontend npm run typecheck
	docker compose run --rm frontend npm run lint

test: backend-test frontend-test

lint:
	docker compose run --rm backend ruff check app tests
	docker compose run --rm frontend npm run lint
	docker compose run --rm frontend npm run typecheck

format:
	docker compose run --rm backend ruff format app tests
	docker compose run --rm frontend npm run format

clean:
	docker compose down
