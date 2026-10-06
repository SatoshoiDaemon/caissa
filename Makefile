PYTHON ?= python

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m black --check src tests

security:
	$(PYTHON) -m bandit -r src -q

run:
	PYTHONPATH=src $(PYTHON) -m backend.run

services:
	docker compose up -d

services-down:
	docker compose down

reset-db:
	RESET_CONFIRM=CAISSA PYTHONPATH=src $(PYTHON) scripts/reset_mongo.py
