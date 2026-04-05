.PHONY: fmt lint test build

fmt:
	uv run ruff format .

lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy app

test:
	uv run pytest --tb=short -q

build:
	uv build --wheel
