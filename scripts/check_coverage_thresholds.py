from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 100.0
    return (numerator / denominator) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate line and branch coverage thresholds from coverage.json"
    )
    parser.add_argument("--file", default="coverage.json", help="Path to coverage JSON report")
    parser.add_argument("--line", type=float, default=95.0, help="Minimum line coverage percent")
    parser.add_argument(
        "--branch", type=float, default=90.0, help="Minimum branch coverage percent"
    )
    args = parser.parse_args()

    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    totals = data.get("totals", {})

    num_statements = int(totals.get("num_statements", 0))
    covered_lines = int(totals.get("covered_lines", 0))
    line_pct = _pct(covered_lines, num_statements)

    num_branches = int(totals.get("num_branches", 0))
    covered_branches = int(totals.get("covered_branches", 0))
    branch_pct = _pct(covered_branches, num_branches)

    print(
        f"Coverage totals: line={line_pct:.2f}% ({covered_lines}/{num_statements}), "
        f"branch={branch_pct:.2f}% ({covered_branches}/{num_branches})"
    )

    failed = False
    if line_pct < args.line:
        print(f"FAIL: line coverage {line_pct:.2f}% is below threshold {args.line:.2f}%")
        failed = True

    if branch_pct < args.branch:
        print(f"FAIL: branch coverage {branch_pct:.2f}% is below threshold {args.branch:.2f}%")
        failed = True

    if failed:
        return 1

    print("Coverage thresholds passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
