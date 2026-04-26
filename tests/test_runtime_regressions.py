from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import resend

import config
import delivery.email as email_mod
import main
from clients.lausuntopalvelu import Proposal
from processing import llm_scorer


def _setup_state_paths(tmp_path, monkeypatch) -> tuple:
    state_dir = tmp_path / "state"
    context_dir = tmp_path / "context"
    state_dir.mkdir()
    context_dir.mkdir()

    seen_path = state_dir / "seen_proposals.json"
    score_log_path = state_dir / "score_log.jsonl"
    flagged_path = state_dir / "nostetut.json"
    context_path = context_dir / "kuluttajaliitto.json"

    seen_path.write_text("{}", encoding="utf-8")
    score_log_path.write_text("", encoding="utf-8")
    flagged_path.write_text("[]", encoding="utf-8")
    context_path.write_text(
        json.dumps({"last_updated": None, "recent_statements": []}),
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "SEEN_PROPOSALS_PATH", seen_path)
    monkeypatch.setattr(config, "SCORE_LOG_PATH", score_log_path)
    monkeypatch.setattr(config, "FLAGGED_PATH", flagged_path)
    monkeypatch.setattr(config, "CONTEXT_PATH", context_path)
    monkeypatch.setattr(config, "NOTIFY_THRESHOLD", 7)
    monkeypatch.setattr(config, "LOG_THRESHOLD", 4)
    monkeypatch.setattr(config, "LAUSUNTOPALVELU_FETCH_TOP", 5)

    return seen_path, score_log_path, flagged_path, context_path


def test_cmd_daily_uses_open_client_for_recipient_lookup(tmp_path, monkeypatch) -> None:
    _seen_path, _score_log_path, _flagged_path, _context_path = _setup_state_paths(
        tmp_path, monkeypatch
    )

    proposal = Proposal(
        id="client-open-check",
        title="Client open check",
        organization_name="Testi",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=3),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/p/client-open-check",
    )

    class FakeClient:
        def __init__(self):
            self.closed = True

        def __enter__(self):
            self.closed = False
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True
            return False

    fake_client = FakeClient()
    monkeypatch.setattr(main.httpx, "Client", lambda: fake_client)

    def fake_fetch_recent(client, top):
        assert client.closed is False
        return [proposal]

    seen_lookup_state = {"checked": False}

    def fake_get_participation_flags(client, pid, name):
        assert client.closed is False
        seen_lookup_state["checked"] = True
        return False, False

    monkeypatch.setattr(main, "fetch_recent", fake_fetch_recent)
    monkeypatch.setattr(main, "get_participation_flags", fake_get_participation_flags)
    monkeypatch.setattr(
        main,
        "score_item",
        lambda *args, **kwargs: {"score": 5, "rationale": "ok", "themes": []},
    )

    main.cmd_daily(dry_run=True)
    assert seen_lookup_state["checked"] is True


def test_llm_scorer_client_is_created_lazily_once(monkeypatch) -> None:
    calls = {"created": 0}

    def fake_create(**kwargs):
        return SimpleNamespace(
            content=[
                SimpleNamespace(text='{"score": 6, "rationale": "ok", "themes": ["asuminen"]}')
            ]
        )

    class FakeAnthropicClient:
        def __init__(self):
            calls["created"] += 1
            self.messages = SimpleNamespace(create=fake_create)

    llm_scorer._get_client.cache_clear()
    monkeypatch.setattr(llm_scorer.anthropic, "Anthropic", FakeAnthropicClient)

    try:
        llm_scorer.score_item("A", "B", "src", {"recent_statements": []})
        llm_scorer.score_item("A2", "B2", "src", {"recent_statements": []})
        assert calls["created"] == 1
    finally:
        llm_scorer._get_client.cache_clear()


def test_send_email_reads_env_defaults_at_call_time(monkeypatch) -> None:
    monkeypatch.setenv("SENDER_EMAIL", "sender@example.com")
    monkeypatch.setenv("RECIPIENT_EMAIL", "recipient@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    captured: dict = {}
    monkeypatch.setattr(
        resend.Emails, "send", staticmethod(lambda p: captured.update(p) or {"id": "x"})
    )

    email_mod.send_email(subject="s", html_body="<p>x</p>", text_body="x")

    assert captured["from"] == "sender@example.com"
    assert captured["to"] == ["recipient@example.com"]
    assert resend.api_key == "re_test_key"
