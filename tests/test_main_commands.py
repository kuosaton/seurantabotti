from __future__ import annotations

import json
from datetime import datetime, timedelta

import config
import main
from clients.kuluttajaliitto import Statement
from clients.lausuntopalvelu import Proposal


def _setup_state_paths(tmp_path, monkeypatch) -> tuple:
    state_dir = tmp_path / "state"
    context_dir = tmp_path / "context"
    state_dir.mkdir()
    context_dir.mkdir()

    seen_path = state_dir / "seen_proposals.json"
    score_log_path = state_dir / "score_log.jsonl"
    nostetut_path = state_dir / "nostetut.json"
    context_path = context_dir / "kuluttajaliitto.json"

    seen_path.write_text("{}", encoding="utf-8")
    score_log_path.write_text("", encoding="utf-8")
    nostetut_path.write_text("[]", encoding="utf-8")
    context_path.write_text(
        json.dumps({"last_updated": None, "recent_statements": []}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "SEEN_PROPOSALS_PATH", seen_path)
    monkeypatch.setattr(config, "SCORE_LOG_PATH", score_log_path)
    monkeypatch.setattr(config, "NOSTETUT_PATH", nostetut_path)
    monkeypatch.setattr(config, "CONTEXT_PATH", context_path)
    monkeypatch.setattr(config, "NOTIFY_THRESHOLD", 7)
    monkeypatch.setattr(config, "LOG_THRESHOLD", 4)
    monkeypatch.setattr(config, "LAUSUNTOPALVELU_FETCH_TOP", 5)

    return seen_path, score_log_path, nostetut_path, context_path


def test_cmd_daily_no_new_proposals_exits_cleanly(tmp_path, monkeypatch, capsys) -> None:
    seen_path, _score_log_path, _nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )

    proposal = Proposal(
        id="already-seen",
        title="Jo kasitelty",
        organization_name="Testi",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=3),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/p/already-seen",
    )

    seen_path.write_text(
        json.dumps({"already-seen": {"first_seen": "2026-01-01T00:00:00+00:00"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "fetch_recent", lambda client, top: [proposal])

    def _should_not_run(*args, **kwargs):
        raise AssertionError("score_item should not be called when there are no new proposals")

    monkeypatch.setattr(main, "score_item", _should_not_run)
    main.cmd_daily(dry_run=True)
    out = capsys.readouterr().out
    assert "Nothing new to score." in out


def test_cmd_daily_borderline_item_is_logged_only(tmp_path, monkeypatch) -> None:
    seen_path, score_log_path, nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )

    proposal = Proposal(
        id="borderline-1",
        title="Rajatapaus",
        organization_name="Testi",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=3),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/p/borderline-1",
    )

    monkeypatch.setattr(main, "fetch_recent", lambda client, top: [proposal])
    monkeypatch.setattr(main, "proposal_has_recipient", lambda client, pid, name: False)
    monkeypatch.setattr(
        main,
        "score_item",
        lambda *args, **kwargs: {"score": 5, "rationale": "Rajatapaus", "themes": []},
    )

    main.cmd_daily(dry_run=True)

    seen = json.loads(seen_path.read_text(encoding="utf-8"))
    assert seen["borderline-1"]["score"] == 5

    nostetut = json.loads(nostetut_path.read_text(encoding="utf-8"))
    assert nostetut == []

    log_lines = [
        line for line in score_log_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(log_lines) == 1
    log_entry = json.loads(log_lines[0])
    assert log_entry["score"] == 5
    assert log_entry["notified"] is False


def test_cmd_review_logged_prints_flagged_and_borderline(tmp_path, monkeypatch, capsys) -> None:
    _seen_path, score_log_path, _nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )
    now = datetime.now(main.UTC)

    entries = [
        {
            "timestamp": now.isoformat(),
            "title": "Nostettava",
            "score": 8,
            "rationale": "Selkea",
        },
        {
            "timestamp": now.isoformat(),
            "title": "Rajalla",
            "score": 5,
            "rationale": "Ehka",
        },
        {
            "timestamp": (now - timedelta(days=10)).isoformat(),
            "title": "Vanha",
            "score": 9,
            "rationale": "Ei pitaisi nayttaa",
        },
    ]
    score_log_path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
        encoding="utf-8",
    )

    main.cmd_review_logged(days=7)
    out = capsys.readouterr().out
    assert "NOSTETTU" in out
    assert "LOKITETTU" in out
    assert "Nostettava" in out
    assert "Rajalla" in out
    assert "Vanha" not in out


def test_cmd_update_context_fetches_and_saves(monkeypatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main.httpx, "Client", FakeClient)

    def fake_fetch_statements(client, per_page):
        assert per_page == 100
        return [
            Statement(
                id=1,
                date="2026-04-22",
                title="T",
                excerpt="E",
                url="https://example.invalid/1",
            )
        ]

    monkeypatch.setattr(main, "fetch_statements", fake_fetch_statements)
    monkeypatch.setattr(main, "build_context", lambda statements: {"recent_statements": []})
    monkeypatch.setattr(main, "_save_context", lambda ctx: captured.update({"ctx": ctx}))

    main.cmd_update_context()
    assert captured["ctx"] == {"recent_statements": []}


def test_cmd_daily_handles_scoring_exception(tmp_path, monkeypatch) -> None:
    seen_path, score_log_path, _nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )

    proposal = Proposal(
        id="score-fail",
        title="Virhepolku",
        organization_name="Testi",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=3),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/p/score-fail",
    )
    monkeypatch.setattr(main, "fetch_recent", lambda client, top: [proposal])
    monkeypatch.setattr(main, "proposal_has_recipient", lambda client, pid, name: False)

    def _raise_score(*args, **kwargs):
        raise RuntimeError("scoring down")

    monkeypatch.setattr(main, "score_item", _raise_score)

    main.cmd_daily(dry_run=True)

    seen = json.loads(seen_path.read_text(encoding="utf-8"))
    assert seen == {}
    assert score_log_path.read_text(encoding="utf-8") == ""


def test_cmd_daily_non_dry_run_sends_email(tmp_path, monkeypatch) -> None:
    _seen_path, _score_log_path, _nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )
    calls: dict = {}

    proposal = Proposal(
        id="notify-1",
        title="Nostettava",
        organization_name="Testi",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=3),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/p/notify-1",
    )

    monkeypatch.setattr(main, "fetch_recent", lambda client, top: [proposal])
    monkeypatch.setattr(main, "proposal_has_recipient", lambda client, pid, name: False)
    monkeypatch.setattr(
        main,
        "score_item",
        lambda *args, **kwargs: {"score": 8, "rationale": "OK", "themes": []},
    )
    monkeypatch.setattr(
        main,
        "build_daily_digest",
        lambda flagged: ("S", "<p>H</p>", "T"),
    )
    monkeypatch.setattr(
        main,
        "send_email",
        lambda subject, html_body, text_body: calls.update(
            {"subject": subject, "html": html_body, "text": text_body}
        ),
    )

    main.cmd_daily(dry_run=False)
    assert calls["subject"] == "S"
    assert calls["html"] == "<p>H</p>"
    assert calls["text"] == "T"


def test_cmd_review_logged_no_log_file(tmp_path, monkeypatch, capsys) -> None:
    _seen_path, score_log_path, _nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )
    score_log_path.unlink()

    main.cmd_review_logged(days=7)
    out = capsys.readouterr().out
    assert "No score log found." in out


def test_cmd_preview_nostetut_empty_file(tmp_path, monkeypatch, capsys) -> None:
    _seen_path, _score_log_path, nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )
    nostetut_path.write_text("[]", encoding="utf-8")

    main.cmd_preview_nostetut()
    out = capsys.readouterr().out
    assert "nothing to preview" in out.lower()


def test_cmd_preview_nostetut_invalid_deadline_still_builds(tmp_path, monkeypatch, capsys) -> None:
    _seen_path, _score_log_path, nostetut_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )
    nostetut_path.write_text(
        json.dumps(
            [
                {
                    "title": "Aihe",
                    "organization": None,
                    "deadline": "invalid-date",
                    "url": "https://example.invalid/p/1",
                    "score": 7,
                    "rationale": "R",
                    "themes": ["t"],
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "build_daily_digest",
        lambda flagged: (
            "SUBJ",
            "HTML",
            "TEXT " + flagged[0]["proposal"].organization_name,
        ),
    )

    main.cmd_preview_nostetut()
    out = capsys.readouterr().out
    assert "Subject: SUBJ" in out
    assert "TEXT -" not in out
    assert "TEXT" in out
