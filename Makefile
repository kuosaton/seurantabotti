.PHONY: check format lint typecheck test

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
		--cov-report=json:coverage.json
	uv run --extra dev python scripts/check_coverage_thresholds.py \
		--file coverage.json \
		--line 95 \
		--branch 85
