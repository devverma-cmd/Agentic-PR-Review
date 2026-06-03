.PHONY: install run dev test lint format tunnel clean

install:
	pip install -e ".[dev]"

run:
	uvicorn app.api.server:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.api.server:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/
	mypy app/

format:
	black app/ tests/
	ruff check --fix app/ tests/

tunnel:
	ngrok http 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .ruff_cache dist build *.egg-info
