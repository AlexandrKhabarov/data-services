.PHONY: fmt lint test build

fmt:
	python -m ruff format .

lint:
	python -m ruff check . && python -m ruff format --check . && python -m mypy app

test:
	python -m pytest --tb=short -q

build:
	python -m build --wheel
