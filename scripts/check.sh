#!/usr/bin/env bash
set -euo pipefail

uv run ruff format --check .
uv run ruff check .
uv run pytest -q \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=json:coverage.json
uv run python scripts/check_coverage_thresholds.py \
    --file coverage.json \
    --line 95 \
    --branch 90
