.PHONY: install init-db ingest api dashboard test lint format migrate clean

install:
	python -m pip install -e ".[dev,dashboard]"

init-db:
	macro-data init-db

ingest:
	macro-data ingest

api:
	uvicorn macro_data_platform.api.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run src/macro_data_platform/dashboard/app.py --server.port 8501

test:
	pytest --cov=macro_data_platform --cov-report=term-missing

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

migrate:
	alembic upgrade head

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
