# Guardian - common dev commands
# Usage: `make <target>`

.PHONY: install seed migrate backend always-on workers ui test lint format demo-reset

install:
	pip install -e ".[ui,dev]"

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

ui:
	streamlit run ui/app.py

test:
	pytest

lint:
	ruff check backend ui tests scripts

format:
	ruff format backend ui tests scripts

demo-reset:
	python scripts/demo_reset.py
