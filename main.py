from __future__ import annotations

import argparse
import json
import sys
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
from dotenv import load_dotenv

import config
from clients.kuluttajaliitto import build_context, fetch_statements
from clients.lausuntopalvelu import fetch_recent, proposal_has_recipient
from delivery.email import build_daily_digest, send_email
from processing.llm_scorer import score_item

load_dotenv()

UTC = timezone.utc


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    if path.exists() and path.stat().st_size > 2:
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _append_log(entry: dict) -> None:
    with config.SCORE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _append_nostetut(entry: dict) -> None:
    path = config.NOSTETUT_PATH
    items = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists() and path.stat().st_size > 2
        else []
    )
    items.append(entry)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_context() -> dict:
    if config.CONTEXT_PATH.exists() and config.CONTEXT_PATH.stat().st_size > 2:
        return json.loads(config.CONTEXT_PATH.read_text(encoding="utf-8"))
    return {"last_updated": None, "recent_statements": []}


def _save_context(ctx: dict) -> None:
    tmp = config.CONTEXT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(config.CONTEXT_PATH)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_update_context() -> None:
    print("Fetching Kuluttajaliitto lausunnot...", flush=True)
    with httpx.Client() as client:
        statements = fetch_statements(client, per_page=100)
    ctx = build_context(statements)
    _save_context(ctx)
    print(f"Saved {len(statements)} statements to {config.CONTEXT_PATH}")


def cmd_daily(dry_run: bool) -> None:
    ctx = _load_context()
    if not ctx["recent_statements"]:
        print(
            "WARNING: Kuluttajaliitto context is empty. Run --update-context first.",
            file=sys.stderr,
        )

    seen = _load_json(config.SEEN_PROPOSALS_PATH)

    print("Fetching lausuntopalvelu proposals...", flush=True)
    with httpx.Client() as client:
        proposals = fetch_recent(client, top=config.LAUSUNTOPALVELU_FETCH_TOP)

    today = datetime.now(UTC).date()
    open_proposals = [p for p in proposals if p.deadline is None or p.deadline.date() >= today]
    new_proposals = [p for p in open_proposals if p.id not in seen]
    print(f"  {len(proposals)} fetched, {len(open_proposals)} open, {len(new_proposals)} new")

    if not new_proposals:
        print("Nothing new to score.")
        return

    flagged = []
    total_logged = 0

    with httpx.Client() as client:
        for p in new_proposals:
            in_kuluttajaliitto_jakelu = False
            try:
                in_kuluttajaliitto_jakelu = proposal_has_recipient(
                    client,
                    p.id,
                    "Kuluttajaliitto ry",
                )
            except Exception as exc:
                print(f"  [WARN] could not read Jakelu for {p.id}: {exc}", file=sys.stderr)

            try:
                result = score_item(
                    p.title,
                    p.abstract,
                    "lausuntopalvelu",
                    ctx,
                    signals={"jakelu_kuluttajaliitto": in_kuluttajaliitto_jakelu},
                )
            except Exception as exc:
                print(f"  [ERROR] scoring failed for {p.id}: {exc}", file=sys.stderr)
                continue

            score = result["score"]
            if in_kuluttajaliitto_jakelu and score < 10:
                score += 1
                result["score"] = score
                base_rationale = (result.get("rationale") or "").strip()
                extra = "Jakelulistalla on Kuluttajaliitto ry, mikä nostaa relevanssia."
                result["rationale"] = f"{base_rationale} {extra}".strip()

            notified = score >= config.NOTIFY_THRESHOLD and not dry_run

            seen[p.id] = {
                "first_seen": datetime.now(UTC).isoformat(),
                "title": p.title,
                "score": score,
                "notified": notified,
                "notified_at": datetime.now(UTC).isoformat() if notified else None,
            }

            _append_log(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "source": "lausuntopalvelu",
                    "id": p.id,
                    "title": p.title,
                    "score": score,
                    "rationale": result.get("rationale", ""),
                    "themes": result.get("themes", []),
                    "jakelu_kuluttajaliitto": in_kuluttajaliitto_jakelu,
                    "notified": notified,
                }
            )

            if score >= config.NOTIFY_THRESHOLD:
                flagged.append({"proposal": p, **result})
                _append_nostetut(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "source": "lausuntopalvelu",
                        "id": p.id,
                        "title": p.title,
                        "score": score,
                        "rationale": result.get("rationale", ""),
                        "themes": result.get("themes", []),
                        "jakelu_kuluttajaliitto": in_kuluttajaliitto_jakelu,
                        "deadline": p.deadline.date().isoformat() if p.deadline else None,
                        "organization": p.organization_name,
                        "url": p.url,
                    }
                )
            elif score >= config.LOG_THRESHOLD:
                total_logged += 1
                print(f"  [LOG {score}/10] {p.title[:70]}")
            else:
                print(f"  [DROP {score}/10] {p.title[:70]}")

    _save_json(config.SEEN_PROPOSALS_PATH, seen)

    if not flagged:
        print(f"No items above notify threshold. Logged {total_logged} borderline items.")
        return

    print(f"\n{len(flagged)} item(s) above threshold:")
    for item in flagged:
        print(f"  [{item['score']}/10] {item['proposal'].title[:70]}")

    subject, html_body, text_body = build_daily_digest(flagged)

    if dry_run:
        print("\n--- DRY RUN: would send email ---")
        print(f"Subject: {subject}")
        print(text_body)
    else:
        send_email(subject=subject, html_body=html_body, text_body=text_body)
        print(f"Email sent to {__import__('os').environ.get('RECIPIENT_EMAIL','?')}")


def cmd_weekly(dry_run: bool) -> None:
    print("Weekly committee digest is not yet implemented (Sprint 2).", file=sys.stderr)
    sys.exit(1)


def cmd_midweek(dry_run: bool) -> None:
    print("Midweek committee check is not yet implemented (Sprint 2).", file=sys.stderr)
    sys.exit(1)


def cmd_review_logged(days: int = 7) -> None:
    if not config.SCORE_LOG_PATH.exists():
        print("No score log found.")
        return

    cutoff = datetime.now(UTC).timestamp() - days * 86400
    flagged = []
    borderline = []

    with config.SCORE_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            score = entry.get("score", 0)
            ts = datetime.fromisoformat(entry["timestamp"].rstrip("Z")).replace(tzinfo=UTC)
            if ts.timestamp() < cutoff:
                continue
            if score >= config.NOTIFY_THRESHOLD:
                flagged.append(entry)
            elif score >= config.LOG_THRESHOLD:
                borderline.append(entry)

    def _print_entries(entries: list[dict]) -> None:
        for entry in entries:
            print(f"[{entry['score']}/10] {entry['timestamp'][:10]}  {entry['title'][:70]}")
            print(f"  {entry.get('rationale', '')}")
            print()

    if not flagged and not borderline:
        print(f"No scored items above threshold in the last {days} days.")
        return

    if flagged:
        print(f"--- NOSTETTU ({len(flagged)} kpl, pistemäärä ≥{config.NOTIFY_THRESHOLD}) ---\n")
        _print_entries(flagged)

    if borderline:
        print(
            f"--- LOKITETTU ({len(borderline)} kpl, pistemäärä {config.LOG_THRESHOLD}–{config.NOTIFY_THRESHOLD - 1}) ---\n"
        )
        _print_entries(borderline)


def cmd_preview_nostetut() -> None:
    if not config.NOSTETUT_PATH.exists() or config.NOSTETUT_PATH.stat().st_size <= 2:
        print("nostetut.json is empty — nothing to preview.")
        return

    items = json.loads(config.NOSTETUT_PATH.read_text(encoding="utf-8"))
    if not items:
        print("nostetut.json is empty — nothing to preview.")
        return

    flagged = []
    for e in items:
        deadline = None
        if e.get("deadline"):
            try:
                d = date_type.fromisoformat(e["deadline"])
                deadline = datetime(d.year, d.month, d.day)
            except ValueError:
                pass
        proposal = SimpleNamespace(
            title=e.get("title", ""),
            organization_name=e.get("organization") or "–",
            deadline=deadline,
            url=e.get("url", ""),
        )
        flagged.append(
            {
                "proposal": proposal,
                "score": e.get("score", 0),
                "rationale": e.get("rationale", ""),
                "themes": e.get("themes", []),
            }
        )

    subject, _html_body, text_body = build_daily_digest(flagged)
    print(f"Subject: {subject}\n")
    print(text_body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Seurantabotti — Kuluttajaliitto monitoring tool")
    parser.add_argument("--daily", action="store_true", help="Run daily lausuntopalvelu check")
    parser.add_argument(
        "--weekly", action="store_true", help="Run weekly committee digest (Fridays)"
    )
    parser.add_argument(
        "--midweek", action="store_true", help="Run mid-week committee update check"
    )
    parser.add_argument(
        "--update-context",
        action="store_true",
        help="Refresh Kuluttajaliitto context from their website",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score items and log them, but do not send email",
    )
    parser.add_argument(
        "--review-logged",
        action="store_true",
        help="Print borderline (score 4–6) items from the last 7 days",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for --review-logged (default: 7)",
    )
    parser.add_argument(
        "--preview-nostetut",
        action="store_true",
        help="Preview nostetut.json as a formatted email digest",
    )
    args = parser.parse_args()

    if not any(
        [
            args.daily,
            args.weekly,
            args.midweek,
            args.update_context,
            args.review_logged,
            args.preview_nostetut,
        ]
    ):
        parser.print_help()
        sys.exit(1)

    if args.update_context:
        cmd_update_context()

    if args.daily:
        cmd_daily(dry_run=args.dry_run)

    if args.weekly:
        cmd_weekly(dry_run=args.dry_run)

    if args.midweek:
        cmd_midweek(dry_run=args.dry_run)

    if args.review_logged:
        cmd_review_logged(days=args.days)

    if args.preview_nostetut:
        cmd_preview_nostetut()


if __name__ == "__main__":
    main()
