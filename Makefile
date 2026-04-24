.PHONY: check format lint test

check: format lint test

format:
	uv run ruff format --check .

lint:
	uv run ruff check .

test:
	uv run pytest -q \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=json:coverage.json
	uv run python scripts/check_coverage_thresholds.py \
		--file coverage.json \
		--line 95 \
		--branch 90
