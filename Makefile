# Guardian - common dev commands
# Usage: `make <target>`

.PHONY: install seed migrate backend always-on workers frontend test lint format demo-reset

install:
	pip install -e ".[frontend,dev]"

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
	streamlit run frontend/app.py

test:
	pytest

lint:
	ruff check backend frontend tests scripts

format:
	ruff format backend frontend tests scripts

demo-reset:
	python scripts/demo_reset.py
