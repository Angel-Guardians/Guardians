# Guardian - common dev commands
# Usage: `make <target>`

.PHONY: install seed migrate backend always-on workers ui test lint format demo-reset

install:
	uv sync --extra ui --extra dev

seed:
	uv run guardian-seed

migrate:
	uv run alembic upgrade head

backend:
	uv run guardian-backend

always-on:
	uv run guardian-always-on

workers:
	uv run guardian-workers

ui:
	uv run streamlit run ui/app.py

test:
	uv run pytest

lint:
	uv run ruff check backend ui tests scripts

format:
	uv run ruff format backend ui tests scripts

demo-reset:
	uv run python scripts/demo_reset.py

phase0:
	uv run python scripts/phase0.py
