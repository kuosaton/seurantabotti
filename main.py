from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from datetime import date as date_type
from pathlib import Path
from types import SimpleNamespace

import httpx
from dotenv import load_dotenv

import config
from clients.eduskunta import (
    extract_documents,
    fetch_agenda_xml,
    fetch_committee_page,
    parse_agenda_matters,
)
from clients.kuluttajaliitto import build_context, fetch_statements
from clients.lausuntopalvelu import Proposal, fetch_recent, get_participation_flags
from delivery.email import build_daily_digest, build_weekly_digest, send_email
from processing.llm_scorer import score_item

# Committees included in the --weekly run. MmV and YmV stay disabled until
# their page structure is verified against a live capture (see
# internal-docs/seurantabotti-technical-spec.md "Remaining unknowns" #3).
_WEEKLY_COMMITTEES = ["talousvaliokunta"]

load_dotenv()


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


def _append_flagged(entry: dict) -> None:
    path = config.FLAGGED_PATH
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


def _score_proposal(client: httpx.Client, proposal: Proposal, ctx: dict) -> dict | None:
    on_distribution_list = False
    has_responded = False
    try:
        on_distribution_list, has_responded = get_participation_flags(
            client, proposal.id, "Kuluttajaliit"
        )
    except httpx.HTTPError as exc:
        print(
            f"  [WARN] could not read participation info for {proposal.id}: {exc}",
            file=sys.stderr,
        )

    if on_distribution_list:
        print(f"  [SKIP DISTRIBUTION] {proposal.title}")
        return {"_skip_reason": "jakelu", "jakelu_kuluttajaliitto": True}

    if has_responded:
        print(f"  [SKIP RESPONDED] {proposal.title}")
        return {"_skip_reason": "already_responded", "jakelu_kuluttajaliitto": False}

    try:
        result = score_item(proposal.title, proposal.abstract, "lausuntopalvelu", ctx)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"  [ERROR] scoring failed for {proposal.id}: {exc}", file=sys.stderr)
        return None

    result["jakelu_kuluttajaliitto"] = False
    return result


def _record_result(p: Proposal, result: dict, notified: bool, seen: dict) -> None:
    now = datetime.now(UTC).isoformat()
    seen[p.id] = {
        "first_seen": now,
        "title": p.title,
        "score": result["score"],
        "notified": notified,
        "notified_at": now if notified else None,
        "published_on": p.published_on.isoformat(),
    }
    _append_log(
        {
            "timestamp": now,
            "source": "lausuntopalvelu",
            "id": p.id,
            "title": p.title,
            "score": result["score"],
            "rationale": result.get("rationale", ""),
            "themes": result.get("themes", []),
            "jakelu_kuluttajaliitto": result["jakelu_kuluttajaliitto"],
            "notified": notified,
            "published_on": p.published_on.isoformat(),
            "deadline": p.deadline.date().isoformat() if p.deadline else None,
            "organization": p.organization_name,
            "url": p.url,
        }
    )


def _deliver_digest(flagged: list[dict], dry_run: bool) -> None:
    print(f"\n{len(flagged)} item(s) above threshold:")
    for item in sorted(flagged, key=lambda x: -x["score"]):
        print(f"  [{item['score']}/10] {item['proposal'].title}")
    subject, html_body, text_body = build_daily_digest(flagged)
    print(f"\nSubject: {subject}")
    print(text_body)
    if dry_run:
        print("\n--- DRY RUN: would send email ---")
        return
    recipient = os.environ.get("RECIPIENT_EMAIL", "?")
    answer = input(f"\nSend to {recipient}? [Y/n] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return
    send_email(subject=subject, html_body=html_body, text_body=text_body)
    print(f"Email sent to {recipient}")


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

    answer = input(f"Score {len(new_proposals)} proposal(s)? [Y/n] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    flagged = []
    total_logged = 0

    with httpx.Client() as client:
        for p in new_proposals:
            result = _score_proposal(client, p, ctx)
            if result is None:
                continue

            skip_reason = result.get("_skip_reason")
            if skip_reason in ("jakelu", "already_responded"):
                now = datetime.now(UTC).isoformat()
                seen[p.id] = {
                    "first_seen": now,
                    "title": p.title,
                    "score": 0,
                    "notified": False,
                    "notified_at": None,
                    "status": f"skipped_{skip_reason}",
                    "published_on": p.published_on.isoformat(),
                }
                continue

            score = result["score"]
            on_distribution_list = result["jakelu_kuluttajaliitto"]
            notified = score >= config.NOTIFY_THRESHOLD and not dry_run

            _record_result(p, result, notified, seen)

            if score >= config.NOTIFY_THRESHOLD:
                print(f"  [FLAG {score}/10] {p.title}")
                flagged.append({"proposal": p, **result})
                _append_flagged(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "source": "lausuntopalvelu",
                        "id": p.id,
                        "title": p.title,
                        "score": score,
                        "rationale": result.get("rationale", ""),
                        "themes": result.get("themes", []),
                        "jakelu_kuluttajaliitto": on_distribution_list,
                        "published_on": p.published_on.isoformat(),
                        "deadline": p.deadline.date().isoformat() if p.deadline else None,
                        "organization": p.organization_name,
                        "url": p.url,
                    }
                )
            elif score >= config.LOG_THRESHOLD:
                total_logged += 1
                print(f"  [LOG {score}/10] {p.title}")
            else:
                print(f"  [DROP {score}/10] {p.title}")

    _save_json(config.SEEN_PROPOSALS_PATH, seen)

    if not flagged:
        print(f"No items above notify threshold. Logged {total_logged} borderline items.")
        return

    _deliver_digest(flagged, dry_run)


def _collect_new_agendas(client: httpx.Client, seen_docs: dict) -> list[tuple]:
    """Return list of (committee_key, Document) for unseen upcoming agendas."""
    new_agendas: list[tuple] = []
    for committee_key in _WEEKLY_COMMITTEES:
        url = config.COMMITTEE_URLS[committee_key]
        display = config.COMMITTEE_DISPLAY_NAMES[committee_key]
        print(f"Fetching {display}...", flush=True)
        try:
            html = fetch_committee_page(client, url)
            docs = extract_documents(html)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"  [ERROR] could not fetch/parse {display}: {exc}", file=sys.stderr)
            continue
        agendas = [
            d
            for d in docs
            if d.tyyppikoodi.endswith("VE") and d.eduskuntatunnus and d.edktunnus not in seen_docs
        ]
        print(f"  {len(docs)} documents, {len(agendas)} new agendas")
        new_agendas.extend((committee_key, a) for a in agendas)
    return new_agendas


def _resolve_agenda_matters(client: httpx.Client, new_agendas: list[tuple]) -> list[tuple]:
    """Return list of (committee_key, Document, matters) for each agenda."""
    resolved: list[tuple] = []
    for committee_key, agenda in new_agendas:
        try:
            xml = fetch_agenda_xml(client, agenda.eduskuntatunnus)
            matters = parse_agenda_matters(xml)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(
                f"  [ERROR] could not fetch/parse {agenda.eduskuntatunnus}: {exc}",
                file=sys.stderr,
            )
            continue
        resolved.append((committee_key, agenda, matters))
    return resolved


def _score_weekly_matter(matter, committee_key: str, ctx: dict, dry_run: bool) -> dict | None:
    try:
        result = score_item(matter.title, matter.type, committee_key, ctx)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"  [ERROR] scoring {matter.eduskuntatunnus}: {exc}", file=sys.stderr)
        return None

    score = result["score"]
    notified = score >= config.NOTIFY_THRESHOLD and not dry_run
    _append_log(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "source": committee_key,
            "id": matter.eduskuntatunnus,
            "title": matter.title,
            "score": score,
            "rationale": result.get("rationale", ""),
            "themes": result.get("themes", []),
            "notified": notified,
        }
    )
    result["notified"] = notified
    return result


def _deliver_weekly(
    committee_items: dict[str, list[dict]],
    total_scored: int,
    total_logged: int,
    dry_run: bool,
) -> None:
    week_number = datetime.now(UTC).isocalendar().week
    subject, html_body, text_body = build_weekly_digest(
        committee_items, week_number, total_scored, total_logged
    )
    total_flagged = sum(len(v) for v in committee_items.values())
    if dry_run:
        print(f"\n--- DRY RUN: would send weekly digest ({total_flagged} flagged) ---")
        print(f"Subject: {subject}\n")
        print(text_body)
    else:
        send_email(subject=subject, html_body=html_body, text_body=text_body)
        print(f"\nWeekly digest sent: {total_flagged} flagged, {total_logged} logged")


def cmd_weekly(dry_run: bool) -> None:
    ctx = _load_context()
    if not ctx["recent_statements"]:
        print(
            "WARNING: Kuluttajaliitto context is empty. Run --update-context first.",
            file=sys.stderr,
        )

    seen_docs = _load_json(config.SEEN_DOCUMENTS_PATH)

    with httpx.Client() as client:
        new_agendas = _collect_new_agendas(client, seen_docs)
        if not new_agendas:
            print("No new committee agendas to process.")
            return
        agenda_matters = _resolve_agenda_matters(client, new_agendas)

    total_matters = sum(len(m) for _, _, m in agenda_matters)
    if total_matters == 0:
        print("No matters scheduled in the new agendas.")
        return

    answer = input(f"Score {total_matters} matter(s)? [Y/n] ").strip().lower()
    if answer not in ("y", ""):
        print("Aborted.")
        return

    for _key, agenda in new_agendas:
        seen_docs[agenda.edktunnus] = {
            "first_seen": datetime.now(UTC).isoformat(),
            "eduskuntatunnus": agenda.eduskuntatunnus,
            "nimeke": agenda.nimeke,
            "score": None,
            "matter_scores": {},
        }

    committee_items: dict[str, list[dict]] = {k: [] for k in _WEEKLY_COMMITTEES}
    total_scored = 0
    total_logged = 0

    for committee_key, agenda, matters in agenda_matters:
        for matter in matters:
            result = _score_weekly_matter(matter, committee_key, ctx, dry_run)
            if result is None:
                continue
            score = result["score"]
            total_scored += 1
            seen_docs[agenda.edktunnus]["matter_scores"][matter.eduskuntatunnus] = {
                "score": score,
                "notified": result["notified"],
            }
            if score >= config.NOTIFY_THRESHOLD:
                print(f"  [FLAG {score}/10] {matter.eduskuntatunnus}: {matter.title}")
                committee_items[committee_key].append(
                    {
                        "title": matter.title,
                        "eduskuntatunnus": matter.eduskuntatunnus,
                        "score": score,
                        "rationale": result.get("rationale", ""),
                        "themes": result.get("themes", []),
                        "url": "",
                    }
                )
            elif score >= config.LOG_THRESHOLD:
                total_logged += 1
                print(f"  [LOG {score}/10] {matter.eduskuntatunnus}: {matter.title}")
            else:
                print(f"  [DROP {score}/10] {matter.eduskuntatunnus}: {matter.title}")

    _save_json(config.SEEN_DOCUMENTS_PATH, seen_docs)
    _deliver_weekly(committee_items, total_scored, total_logged, dry_run)


def cmd_midweek(dry_run: bool) -> None:  # pylint: disable=unused-argument
    print(
        "Midweek committee check is not yet implemented (planned for version 0.3.0).",
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_review_logged(days: int = 7) -> None:
    if not config.SCORE_LOG_PATH.exists():
        print("No score log found.")
        return

    cutoff = datetime.now(UTC).timestamp() - days * 86400
    borderline = []

    with config.SCORE_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            score = entry.get("score", 0)
            ts = datetime.fromisoformat(entry["timestamp"].rstrip("Z")).replace(tzinfo=UTC)
            if ts.timestamp() < cutoff:
                continue
            if config.LOG_THRESHOLD <= score < config.NOTIFY_THRESHOLD:
                borderline.append(entry)

    if not borderline:
        print(f"No borderline items in the last {days} days.")
        return

    print(
        f"--- LOGGED ({len(borderline)} items, score {config.LOG_THRESHOLD}-{config.NOTIFY_THRESHOLD - 1}) ---\n"
    )
    for entry in borderline:
        print(f"[{entry['score']}/10] {entry['timestamp'][:10]}  {entry['title']}")
        print(f"  {entry.get('rationale', '')}")
        print()


def _load_flagged() -> list[dict]:
    if not config.FLAGGED_PATH.exists() or config.FLAGGED_PATH.stat().st_size <= 2:
        return []
    items = json.loads(config.FLAGGED_PATH.read_text(encoding="utf-8"))
    flagged = []
    for e in items:
        deadline = None
        if e.get("deadline"):
            try:
                d = date_type.fromisoformat(e["deadline"])
                deadline = datetime(d.year, d.month, d.day)
            except ValueError:
                pass
        published_on = None
        if e.get("published_on"):
            try:
                published_on = datetime.fromisoformat(e["published_on"])
            except ValueError:
                pass
        proposal = SimpleNamespace(
            title=e.get("title", ""),
            organization_name=e.get("organization") or "-",
            deadline=deadline,
            published_on=published_on,
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
    return flagged


def cmd_preview_flagged() -> None:
    flagged = _load_flagged()
    if not flagged:
        print("No flagged items to preview.")
        return
    subject, _html_body, text_body = build_daily_digest(flagged)
    print(f"Subject: {subject}\n")
    print(text_body)


def cmd_send_flagged(dry_run: bool) -> None:
    flagged = _load_flagged()
    if not flagged:
        print("No flagged items to send.")
        return
    _deliver_digest(flagged, dry_run)


def cmd_preview_logged(days: int = 7) -> None:
    if not config.SCORE_LOG_PATH.exists():
        print("No score log found.")
        return

    cutoff = datetime.now(UTC).timestamp() - days * 86400
    borderline = []

    with config.SCORE_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            score = entry.get("score", 0)
            ts = datetime.fromisoformat(entry["timestamp"].rstrip("Z")).replace(tzinfo=UTC)
            if ts.timestamp() < cutoff:
                continue
            if config.LOG_THRESHOLD <= score < config.NOTIFY_THRESHOLD:
                borderline.append(entry)

    if not borderline:
        print(f"No borderline items in the last {days} days.")
        return

    items = []
    for e in borderline:
        published_on = None
        if e.get("published_on"):
            try:
                published_on = datetime.fromisoformat(e["published_on"])
            except ValueError:
                pass
        deadline = None
        if e.get("deadline"):
            try:
                d = date_type.fromisoformat(e["deadline"])
                deadline = datetime(d.year, d.month, d.day)
            except ValueError:
                pass
        proposal = SimpleNamespace(
            title=e.get("title", ""),
            organization_name=e.get("organization") or "-",
            deadline=deadline,
            published_on=published_on,
            url=e.get("url", ""),
        )
        items.append(
            {
                "proposal": proposal,
                "score": e.get("score", 0),
                "rationale": e.get("rationale", ""),
                "themes": e.get("themes", []),
            }
        )

    subject, _html_body, text_body = build_daily_digest(items)
    print(f"Subject: {subject}\n")
    print(text_body)


def cmd_reset_state() -> None:
    print("This will erase all state: seen proposals, score log, and flagged items.")
    answer = input("Continue? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        return
    _save_json(config.SEEN_PROPOSALS_PATH, {})
    _save_json(config.SEEN_DOCUMENTS_PATH, {})
    config.FLAGGED_PATH.write_text("[]", encoding="utf-8")
    config.SCORE_LOG_PATH.write_text("", encoding="utf-8")
    print("State reset.")


# ---------------------------------------------------------------------------
# Interactive UI
# ---------------------------------------------------------------------------

_MENU = """
Lausuntobotti
─────────────────────────────────────
1  Daily check
2  Daily check (dry run)
3  Update Kuluttajaliitto context
4  Review logged items (7 days)
5  Review logged items (custom range)
6  Preview flagged
7  Preview logged (borderline)
8  Send flagged (resend last digest)
9  Reset state
h  Help
0  Exit
─────────────────────────────────────"""

_HELP = """
Option descriptions:
  1  Daily check              Fetch new lausuntopalvelu proposals, score with Claude,
                              and send email for items above threshold.
  2  Daily check (dry run)    Same as above but print the digest instead of sending.
  3  Update context           Re-fetch Kuluttajaliitto published statements used as
                              scoring context. Run this before the first daily check
                              and periodically to keep context current.
  4  Review logged (7 days)   Print borderline items (score 4-6) from the last 7 days
                              for manual calibration review.
  5  Review logged (custom)   Same as above with a custom day range.
  6  Preview flagged          Print the last flagged digest as plain text (no email).
  7  Preview logged           Print borderline items as a formatted digest (no email).
  8  Send flagged             Resend the last daily digest email without re-running
                              scoring. Useful for testing email delivery.
  9  Reset state              Erase all state files (seen proposals, score log,
                              flagged items) and start fresh.
  h  Help                     Show this help.
  0  Exit
"""


def _menu_review_custom() -> None:
    raw = input("Days to look back: ").strip()
    try:
        cmd_review_logged(days=int(raw))
    except ValueError:
        print(f"Invalid number: {raw!r}")


def _menu_preview_logged() -> None:
    raw = input("Days to look back (default 7): ").strip()
    try:
        cmd_preview_logged(days=int(raw) if raw else 7)
    except ValueError:
        print(f"Invalid number: {raw!r}")


def cmd_interactive() -> None:
    actions: dict[str, Callable[[], None]] = {
        "1": lambda: cmd_daily(dry_run=False),
        "2": lambda: cmd_daily(dry_run=True),
        "3": cmd_update_context,
        "4": lambda: cmd_review_logged(days=7),
        "5": _menu_review_custom,
        "6": cmd_preview_flagged,
        "7": _menu_preview_logged,
        "8": lambda: cmd_send_flagged(dry_run=False),
        "9": cmd_reset_state,
    }
    print(_MENU)
    while True:
        try:
            choice = input("> ").strip()
        except EOFError, KeyboardInterrupt:
            print()
            break

        if choice == "0":
            break
        if choice == "h":
            print(_HELP)
            continue
        action = actions.get(choice)
        if action is None:
            print(_HELP)
            continue
        action()
        print(_MENU)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Lausuntobotti – Kuluttajaliitto monitoring tool")
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
        help="Print borderline (score 4-5) items from the last 7 days",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back for --review-logged (default: 7)",
    )
    parser.add_argument(
        "--preview-flagged",
        action="store_true",
        help="Preview flagged items as an email digest",
    )
    parser.add_argument(
        "--send-flagged",
        action="store_true",
        help="Resend the last daily digest without re-running scoring",
    )
    parser.add_argument(
        "--preview-logged",
        action="store_true",
        help="Preview borderline items from the score log as a formatted digest",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Erase all state files and start fresh",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive menu",
    )
    args = parser.parse_args()

    if not any(
        [
            args.daily,
            args.weekly,
            args.midweek,
            args.update_context,
            args.review_logged,
            args.preview_flagged,
            args.send_flagged,
            args.preview_logged,
            args.reset_state,
            args.interactive,
        ]
    ):
        cmd_interactive()
        return

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

    if args.preview_flagged:
        cmd_preview_flagged()

    if args.send_flagged:
        cmd_send_flagged(dry_run=args.dry_run)

    if args.preview_logged:
        cmd_preview_logged(days=args.days)

    if args.reset_state:
        cmd_reset_state()

    if args.interactive:
        cmd_interactive()


if __name__ == "__main__":
    main()
