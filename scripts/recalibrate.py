"""Re-score a curated set of historical proposals against the current SYSTEM_PROMPT.

Used after prompt edits to spot-check that:
  - The item that motivated the change moves in the expected direction.
  - Control items at other bands don't drift.

Run from the repo root:  uv run --extra dev python scripts/recalibrate.py

The --extra dev flag pulls in socksio, which httpx needs to reach the network
through the Claude Code sandbox's SOCKS proxy. Outside the sandbox, plain
`uv run python scripts/recalibrate.py` works too.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import httpx  # noqa: E402

import config  # noqa: E402
from clients.lausuntopalvelu import fetch_by_id  # noqa: E402
from processing.llm_scorer import score_item  # noqa: E402
from processing.score_classification import classify_score  # noqa: E402
from state_store import _load_context  # noqa: E402


@dataclass(frozen=True)
class CalibrationItem:
    proposal_id: str
    expected_band: str  # "flag", "log", or "drop"
    note: str  # why this item is in the set


# Curated 2026-05-22 calibration set. Add items here as needed.
CALIBRATION_SET: tuple[CalibrationItem, ...] = (
    CalibrationItem(
        proposal_id="f5ec573e-0940-4fb6-97e9-613f4a49b8a0",
        expected_band="flag",
        note="Tupakkalaki — drove the prompt edit. Was 6/10, should land 8+ given direct asukas impact.",
    ),
    CalibrationItem(
        proposal_id="5b0c3c43-8875-4e49-baa7-da68f19edbb5",
        expected_band="flag",
        note="Digitaalinen hoidon tarpeen arvio — clear flag control. Was 8/10.",
    ),
    CalibrationItem(
        proposal_id="a083b204-a363-470f-ab3c-281d449b6ad2",
        expected_band="log",
        note="Opintotukiuudistus — borderline LOG control. Was 4/10.",
    ),
    CalibrationItem(
        proposal_id="994d36b9-0476-4346-ac70-6f3ddf5ee2ba",
        expected_band="drop",
        note="STUK ydinlaitossääntely — clear DROP control. Was 1/10.",
    ),
)


def _load_old_scores() -> dict[str, int]:
    """Map proposal_id -> most recent score recorded in the lausuntopalvelu log."""
    path = config.LAUSUNTOPALVELU_SCORE_LOG_PATH
    by_id: dict[str, int] = {}
    if not path.exists():
        return by_id
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        item_id = entry.get("id")
        score = entry.get("score")
        if isinstance(item_id, str) and isinstance(score, int):
            by_id[item_id] = score
    return by_id


def main() -> int:
    ctx = _load_context()
    if not ctx.get("recent_statements"):
        print("ERROR: context/kuluttajaliitto.json has no recent_statements.", file=sys.stderr)
        return 1

    old_scores = _load_old_scores()

    rows = []
    with httpx.Client() as client:
        for item in CALIBRATION_SET:
            proposal = fetch_by_id(client, item.proposal_id)
            if proposal is None:
                print(f"  [MISS] {item.proposal_id} not found in API — skipping", file=sys.stderr)
                continue
            print(f"  Scoring {proposal.id}: {proposal.title[:80]}...", flush=True)
            result = score_item(proposal.title, proposal.abstract, "lausuntopalvelu", ctx)
            new_score = result["score"]
            new_band = classify_score(new_score)
            old_score = old_scores.get(item.proposal_id)
            rows.append(
                {
                    "id": item.proposal_id,
                    "title": proposal.title,
                    "expected_band": item.expected_band,
                    "old_score": old_score,
                    "new_score": new_score,
                    "new_band": new_band,
                    "rationale": result.get("rationale", ""),
                    "note": item.note,
                }
            )

    print()
    print("=" * 100)
    print("Calibration results")
    print("=" * 100)
    for r in rows:
        drift = "—" if r["old_score"] is None else f"{r['old_score']:>2} → {r['new_score']:<2}"
        band_match = "OK " if r["new_band"] == r["expected_band"] else "*** MISMATCH ***"
        print()
        print(f"[{band_match}] {r['title'][:90]}")
        print(
            f"   expected band: {r['expected_band']:<6}  score: {drift}  new band: {r['new_band']}"
        )
        print(f"   note:      {r['note']}")
        print(f"   rationale: {r['rationale']}")

    mismatches = [r for r in rows if r["new_band"] != r["expected_band"]]
    if mismatches:
        print()
        print(f"!! {len(mismatches)} item(s) drifted out of expected band — review the prompt.")
        return 2
    print()
    print("All items stayed in their expected bands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
