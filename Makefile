.PHONY: infra-up infra-down api-install api-run api-test migrate prod-preflight prod-validate prod-up prod-down prod-status prod-backup

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

prod-preflight:
	python3 tools/production_preflight.py server --env-file deploy/.env.production

prod-validate: prod-preflight
	docker compose --env-file deploy/.env.production -f docker-compose.prod.yml config >/dev/null
	bash -n deploy/backup.sh deploy/restore.sh deploy/smoke.sh

prod-up: prod-validate
	docker compose --env-file deploy/.env.production -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose --env-file deploy/.env.production -f docker-compose.prod.yml down

prod-status:
	docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps

prod-backup:
	bash deploy/backup.sh
