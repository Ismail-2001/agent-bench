# agentbench Makefile — Professional engineering workflows

.PHONY: help install test lint format build clean

help:
	@echo "Available commands:"
	@echo "  install   Install dependencies and the package in editable mode"
	@echo "  test      Run all tests using pytest"
	@echo "  lint      Run ruff for linting"
	@echo "  format    Run ruff to format code"
	@echo "  build     Build the package (Hatch)"
	@echo "  clean     Remove temporary files and build artifacts"
	@echo "  docker    Build the production Docker image"

install:
	pip install -e ".[all,dev]"

test:
	pytest tests/

lint:
	ruff check .

format:
	ruff format .

build:
	pip install hatch
	hatch build

clean:
	rm -rf dist/ .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +

docker:
	docker build -t agentbench:latest .
