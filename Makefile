.PHONY: check format lint typecheck test quick-test precommit precommit-install

check: format lint typecheck test

format:
	uv run --extra dev ruff format --check .

lint:
	uv run --extra dev ruff check .

typecheck:
	uv run --extra dev pyright

test:
	uv run --extra dev pytest -q \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=json:coverage.json \
		--cov-report=lcov:lcov.info
	uv run --extra dev python scripts/check_coverage_thresholds.py \
		--file coverage.json \
		--line 95 \
		--branch 90

quick-test:
	uv run --extra dev pytest -q tests/test_llm_scorer.py tests/test_main_cli.py

precommit:
	uv run --extra dev pre-commit run --all-files

precommit-install:
	uv run --extra dev pre-commit install --hook-type pre-commit --hook-type pre-push
