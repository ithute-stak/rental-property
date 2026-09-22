.PHONY: infra-up infra-down api-install api-run api-test migrate

infra-up:
	docker compose up -d db redis

infra-down:
	docker compose down

api-install:
	cd backend && python -m pip install -e '.[dev]'

api-run:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-test:
	cd backend && pytest

migrate:
	cd backend && alembic upgrade head
