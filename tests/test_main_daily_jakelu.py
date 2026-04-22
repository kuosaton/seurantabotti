from __future__ import annotations

import json
from datetime import datetime, timedelta

import config
import main
from clients.lausuntopalvelu import Proposal


def test_cmd_daily_applies_jakelu_boost_and_persists_flag(tmp_path, monkeypatch) -> None:
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

    proposal = Proposal(
        id="test-proposal-id",
        title="Lakimuutos kuluttajille",
        organization_name="Testiministerio",
        abstract="Kuvaus",
        deadline=datetime.now(main.UTC) + timedelta(days=5),
        published_on=datetime.now(main.UTC),
        url="https://example.invalid/proposal/test-proposal-id",
    )

    monkeypatch.setattr(main, "fetch_recent", lambda client, top: [proposal])
    monkeypatch.setattr(main, "proposal_has_recipient", lambda client, pid, name: True)

    captured_signals: dict = {}

    def fake_score_item(title, abstract, source, context, signals=None):
        captured_signals.update(signals or {})
        return {"score": 6, "rationale": "Perustelu", "themes": ["kuluttajansuoja"]}

    monkeypatch.setattr(main, "score_item", fake_score_item)

    main.cmd_daily(dry_run=True)

    assert captured_signals == {"jakelu_kuluttajaliitto": True}

    seen = json.loads(seen_path.read_text(encoding="utf-8"))
    assert seen[proposal.id]["score"] == 7
    assert seen[proposal.id]["notified"] is False

    log_lines = [
        line for line in score_log_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(log_lines) == 1
    log_entry = json.loads(log_lines[0])
    assert log_entry["score"] == 7
    assert log_entry["jakelu_kuluttajaliitto"] is True

    nostetut = json.loads(nostetut_path.read_text(encoding="utf-8"))
    assert len(nostetut) == 1
    assert nostetut[0]["score"] == 7
    assert nostetut[0]["jakelu_kuluttajaliitto"] is True
    assert "Kuluttajaliitto ry" in nostetut[0]["rationale"]
