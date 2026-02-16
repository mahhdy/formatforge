.PHONY: install dev test lint format clean doctor run

install:
pip install -e .

dev:
pip install -e ".[all]"

test:
python -m pytest tests/ -v --tb=short

test-cov:
python -m pytest tests/ -v --cov=formatforge --cov-report=term-missing

test-e2e:
python -m pytest tests/e2e/ -v -m e2e

lint:
ruff check formatforge/ tests/
mypy formatforge/

format:
ruff format formatforge/ tests/
ruff check --fix formatforge/ tests/

clean:
rm -rf build/ dist/ *.egg-info/ __pycache__/ .pytest_cache/ htmlcov/ .coverage
find . -type d -name __pycache__ -exec rm -rf {} +

doctor:
python -m formatforge doctor

run:
python -m formatforge run