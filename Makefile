# Guardian - common dev commands
# Usage: `make <target>`

.PHONY: install seed migrate backend always-on workers frontend frontend-install test lint format demo-reset

install:
	pip install -e ".[dev]"

frontend-install:
	cd frontend && npm install

seed:
	guardian-seed

migrate:
	alembic upgrade head

backend:
	guardian-backend

always-on:
	guardian-always-on

workers:
	guardian-workers

frontend:
	cd frontend && npm run dev

test:
	pytest

lint:
	ruff check backend tests scripts

format:
	ruff format backend tests scripts

demo-reset:
	python scripts/demo_reset.py
